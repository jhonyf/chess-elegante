from flask import Flask, render_template, redirect, request, jsonify, session, Response, stream_with_context, url_for
import os
import chess
import chess.pgn
import io
from services.lichess_client import LichessClient
from services.game_storage_db import GameStorage  # Database-backed storage
from services.stockfish_engine import StockfishEngine
from services.ai_commentator import AICommentator
from core.auth import init_auth
from core.move_utils import MoveFormat, create_move_analysis_entry
import secrets
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime
from flask_login import login_required, current_user
from functools import wraps
import json
import time
import uuid
from werkzeug.middleware.proxy_fix import ProxyFix
from core.admin_utils import admin_required, job_manager
from services.curated_game_service import CuratedGameService
from database.models import ChessGame, db
from services.game_analysis_service import GameAnalysisService
from flask_migrate import Migrate

app = Flask(__name__)
secret_key = os.getenv('SECRET_KEY')
app.secret_key = secret_key
app.config['JSON_AS_ASCII'] = False
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
secure_cookie_env = os.getenv('SESSION_COOKIE_SECURE', '').lower()
app.config['SESSION_COOKIE_SECURE'] = secure_cookie_env in ('1', 'true', 'yes')

# Configure database
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'postgresql://localhost/chess_elegante')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize database and migrations
db.init_app(app)
migrate = Migrate(app, db)

# Trust proxy headers from ALB for correct HTTPS URL generation
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Get deployment metadata from environment
COMMIT_SHA = os.getenv('COMMIT_SHA', 'dev')

# Configure logging
def setup_logging():
    """Configure application logging with rotating file handler"""
    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Set up root logger (INFO level suppresses third-party debug logs)
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    # File handler with rotation (10MB max, keep 5 backups)
    file_handler = RotatingFileHandler(
        'logs/app.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)

    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)

    # Formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # Add handlers if not already added
    if not logger.handlers:
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    # Set DEBUG level for application loggers only (not third-party libraries)
    app_loggers = [
        'services.ai_commentator',
        'services.game_storage',
        'services.game_storage_db',
        'services.curated_game_service',
        'services.game_analysis_service',
        'StockfishEngine',
        'services.lichess_client',
        '__main__',  # For app.py when run directly
        'app'        # For app.py when imported
    ]
    for logger_name in app_loggers:
        logging.getLogger(logger_name).setLevel(logging.DEBUG)

    return logger

logger = setup_logging()

# Request/Response logging middleware
@app.before_request
def log_request():
    """Log incoming requests"""
    logger.info(f"REQUEST: {request.method} {request.path} | IP: {request.remote_addr} | Session: {session.get('game_id', 'None')}")
    if request.is_json:
        try:
            body = request.get_json(silent=True)
            if body:
                logger.debug(f"REQUEST BODY: {json.dumps(body, indent=2)}")
        except Exception as e:
            logger.warning(f"Failed to parse JSON body: {e}")

@app.after_request
def log_response(response):
    """Log outgoing responses"""
    logger.info(f"RESPONSE: {request.method} {request.path} | Status: {response.status_code}")
    if response.is_json and response.status_code != 200:
        logger.debug(f"RESPONSE BODY: {response.get_data(as_text=True)}")
    return response

@app.context_processor
def inject_deployment_info():
    """Inject deployment metadata into all templates"""
    return {
        'version': COMMIT_SHA
    }

lichess = LichessClient()
storage = GameStorage()
engine = StockfishEngine()

# Initialize authentication
init_auth(app, storage.Session)

# Initialize AI commentator (will be None if API key not set)
try:
    ai_commentator = AICommentator()
except Exception as e:
    print(f"AI Commentator not initialized: {e}")
    ai_commentator = None

# Initialize Game Analysis Service
game_analysis_service = GameAnalysisService(engine, ai_commentator)

# Helper function to get database session
def get_db_session():
    """Get a new database session"""
    return storage.Session()


def get_lichess_game_id(game_id):
    """
    Get the Lichess game ID for a given game UUID.
    For live games, this looks up the lichess_game_id from LiveGameState.
    Returns None if not found or not a live game.
    """
    game_data = storage.load_game(game_id)
    if not game_data:
        return None

    live_state = game_data.get('live_state')
    if live_state:
        return live_state.get('lichess_game_id')

    return None


# Authentication decorator for analyze page
def login_required_for_analyze(f):
    """Decorator that requires login for analyze page"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            # Only save next URL if it's not an API endpoint
            if not request.path.startswith('/api/'):
                session['next'] = request.url
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


# Authorization decorator for game ownership (URL parameter)
def game_owner_required(f):
    """Decorator that checks if current user owns the game (game_id from URL parameter)"""
    @wraps(f)
    def decorated_function(game_id, *args, **kwargs):
        # Query database to check ownership
        game = ChessGame.query.filter_by(id=game_id).first()

        if not game:
            return jsonify({
                'success': False,
                'error': 'Game not found'
            }), 404

        # Check if game belongs to current user
        if game.user_id != current_user.id:
            logger.warning(f"Unauthorized access attempt to game {game_id} by user {current_user.email}")
            return jsonify({
                'success': False,
                'error': 'Unauthorized: You do not own this game'
            }), 403

        return f(game_id, *args, **kwargs)
    return decorated_function


# Authorization decorator for active game ownership (session-based)
def active_game_owner_required(f):
    """Decorator that checks if current user owns the active game (game_id from session)"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        game_id = session.get('game_id')

        if not game_id:
            return jsonify({
                'success': False,
                'error': 'No active game'
            }), 400

        # Load game data to check ownership
        game_data = storage.load_game(game_id)
        if not game_data:
            logger.error(f"Game {game_id} not found in storage")
            return jsonify({
                'success': False,
                'error': 'Game not found'
            }), 404

        # Check if game belongs to current user
        if game_data.get('user_id') != current_user.id:
            logger.warning(f"Unauthorized access attempt to game {game_id} by user {current_user.email}")
            return jsonify({
                'success': False,
                'error': 'Unauthorized: You do not own this game'
            }), 403

        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    return render_template('home.html')


@app.route('/health')
def health():
    """Health check endpoint for load balancer and container orchestration"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.utcnow().isoformat()
    }), 200


@app.route('/api/version')
def version():
    """Return deployment version information"""
    return jsonify({
        'commit_sha': COMMIT_SHA,
        'sha_short': COMMIT_SHA[:7] if COMMIT_SHA != 'dev' else 'dev'
    }), 200


@app.route('/play')
@login_required
def play():
    return render_template('game.html', mode='play')


@app.route('/games')
def games():
    """Games library: curated games (public) and my games (requires auth)"""
    return render_template('games.html')


@app.route('/about')
def about():
    """About page"""
    return render_template('about.html')


@app.route('/learn')
def learn():
    """Main learn hub page"""
    return render_template('learn.html')


@app.route('/openings')
def openings():
    """Chess openings guide page"""
    return render_template('openings.html')


@app.route('/tactics')
def tactics():
    """Chess tactics guide page"""
    return render_template('tactics.html')


@app.route('/strategy')
def strategy():
    """Chess strategy & planning guide page"""
    return render_template('strategy.html')


@app.route('/endgames')
def endgames():
    """Chess endgames guide page"""
    return render_template('endgames.html')


@app.route('/analyze/<game_id>')
def analyze_game(game_id):
    """Analyze a specific game (public for curated games, requires auth for private games)"""
    try:
        # Load the game to check if it's curated
        game = storage.load_game(game_id)

        if not game:
            return "Game not found", 404

        # If it's a curated game, allow public access
        if game.get('is_curated', False):
            return render_template('game.html', mode='analyze', game_id=game_id)

        # For private games, require authentication and ownership check
        if not current_user.is_authenticated:
            session['next'] = request.url
            return redirect(url_for('auth.login'))

        # Check if user owns this private game
        if game.get('user_id') != current_user.id:
            return "Unauthorized access to private game", 403

        return render_template('game.html', mode='analyze', game_id=game_id)

    except Exception as e:
        print(f"Error loading game {game_id}: {e}")
        return "Error loading game", 500


@app.route('/api/games', methods=['GET'])
@login_required
def list_games():
    """API endpoint to get all games for current user (both live and imported)"""
    try:
        # Get all user's games (live and imported)
        user_games = storage.list_games(user_id=current_user.id)

        return jsonify({
            'success': True,
            'user_games': user_games
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/game/<game_id>', methods=['GET'])
def get_game(game_id):
    """API endpoint to get a specific game"""
    try:
        game_data = storage.load_game(game_id)
        if not game_data:
            return jsonify({
                'success': False,
                'error': 'Game not found'
            }), 404

        return jsonify({
            'success': True,
            'game': game_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/resume-game/<game_id>', methods=['POST'])
@login_required
@game_owner_required
def resume_game(game_id):
    """Resume a saved game"""
    try:
        game_data = storage.load_game(game_id)

        # Set as active game
        session['game_id'] = game_id

        # Reconstruct board from moves using unified format utilities
        moves = game_data.get('moves', [])
        board = MoveFormat.replay_moves(moves)

        # Get engine_type from live_state
        live_state = game_data.get('live_state', {})
        engine_type = live_state.get('engine_type', 'lichess')

        # No need to store in memory - database is source of truth

        return jsonify({
            'success': True,
            'game_id': game_id,
            'fen': board.fen(),
            'moves': moves,
            'status': live_state.get('status', 'started'),
            'engine_type': engine_type
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/delete-game/<game_id>', methods=['DELETE'])
@login_required
@game_owner_required
def delete_game(game_id):
    """Delete a live game"""
    try:
        logger.info(f"Deleting game {game_id} for user: {current_user.email}")

        # Delete the game
        storage.delete_game(game_id)
        logger.info(f"Game {game_id} deleted successfully")

        # No need to clean up memory - database is source of truth

        return jsonify({
            'success': True
        })
    except Exception as e:
        logger.error(f"Error deleting game {game_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/new-game', methods=['POST'])
@login_required
def new_game():
    """Start a new game against AI (Lichess or local Stockfish)"""
    try:
        data = request.json
        engine_type = data.get('engine_type', 'lichess')  # 'lichess' or 'stockfish'
        level = data.get('level', 1)  # AI difficulty
        logger.info(f"Creating new game with engine: {engine_type}, level: {level} for user: {current_user.email}")

        # Generate UUID for our database
        game_id = str(uuid.uuid4())
        logger.info(f"Generated game UUID: {game_id}")

        # Store game UUID in session
        session['game_id'] = game_id

        # Initialize chess board
        board = chess.Board()

        # No need to store in memory - database is source of truth

        lichess_game_id = None

        # Create game based on engine type
        if engine_type == 'lichess':
            # Create challenge against Lichess AI
            result = lichess.create_challenge_ai(level=level)
            lichess_game_id = result['id']
            logger.info(f"Lichess game created successfully: {lichess_game_id}")
        else:
            # Stockfish - no external game creation needed
            logger.info(f"Local Stockfish game created at level {level}")

        # Save game to storage with user_id
        storage.save_game(game_id, {
            'game_type': 'live',
            'engine_type': engine_type,
            'lichess_game_id': lichess_game_id,
            'current_fen': board.fen(),
            'moves': [],
            'status': 'started',
            'ai_level': level,
            'player_color': 'white'
        }, user_id=current_user.id)
        logger.info(f"Game {game_id} saved to storage for user {current_user.id}")

        return jsonify({
            'success': True,
            'game_id': game_id,
            'fen': board.fen(),
            'engine_type': engine_type
        })
    except Exception as e:
        logger.error(f"Failed to create new game: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/make-move', methods=['POST'])
@login_required
@active_game_owner_required
def make_move():
    """Make a move on behalf of the user"""
    try:
        data = request.json
        game_id = session.get('game_id')
        move_uci = data.get('move')  # e.g., 'e2e4'
        logger.info(f"Player making move: {move_uci} in game {game_id}")

        # Always load game from database (source of truth)
        logger.info(f"Loading game {game_id} from storage")
        game_data = storage.load_game(game_id)
        if not game_data:
            logger.error(f"Game {game_id} not found in storage")
            return jsonify({'success': False, 'error': 'Game not found'}), 404

        # Reconstruct board from moves using unified format utilities
        moves = game_data.get('moves', [])
        board = MoveFormat.replay_moves(moves)

        # Get engine_type from live_state
        live_state = game_data.get('live_state', {})
        engine_type = live_state.get('engine_type', 'lichess')
        ai_level = live_state.get('ai_level', 1)

        logger.info(f"Loaded game {game_id} - engine_type: {engine_type}, moves: {len(moves)}, FEN: {board.fen()}")

        try:
            move = chess.Move.from_uci(move_uci)
            if move not in board.legal_moves:
                logger.warning(f"Illegal move attempted: {move_uci}")
                return jsonify({'success': False, 'error': 'Illegal move'}), 400
        except ValueError:
            logger.warning(f"Invalid move format: {move_uci}")
            return jsonify({'success': False, 'error': 'Invalid move format'}), 400

        # Get SAN notation before making the move
        player_move_san = board.san(move)

        # Update local board with player's move
        board.push(move)

        # Check if game is over after player's move
        game_over_after_player_move = board.is_game_over()
        if game_over_after_player_move:
            logger.info(f"Game over after player's move. Checkmate: {board.is_checkmate()}")

        # Make move based on engine type
        if engine_type == 'lichess':
            # Get Lichess game ID and make move on Lichess
            lichess_game_id = get_lichess_game_id(game_id)
            if not lichess_game_id:
                logger.error(f"No Lichess game ID found for game {game_id}")
                return jsonify({'success': False, 'error': 'Lichess game not found'}), 404

            lichess.make_move(lichess_game_id, move_uci)
            logger.info(f"Move {move_uci} sent to Lichess game {lichess_game_id} successfully")

            # Save player move for Lichess games (AI move will come via stream)
            # Reuse moves list from initial load and append new move
            moves.append({'san': player_move_san, 'uci': move_uci})

            version = storage.save_game(game_id, {
                'game_type': 'live',
                'engine_type': engine_type,
                'lichess_game_id': live_state.get('lichess_game_id'),
                'current_fen': board.fen(),
                'moves': moves,
                'status': 'mate' if board.is_checkmate() else 'draw' if board.is_game_over() else 'started',
                'ai_level': ai_level,
                'player_color': 'white'
            }, user_id=current_user.id if current_user.is_authenticated else None, increment_version=True)

            ai_thinking = not game_over_after_player_move
        else:
            # Stockfish engine - check if we need AI response
            moves.append({'san': player_move_san, 'uci': move_uci})

            if game_over_after_player_move:
                # Game ended with player's move - no AI response needed
                logger.info(f"Game ended after player's move - skipping AI response")
                version = storage.save_game(game_id, {
                    'game_type': 'live',
                    'engine_type': engine_type,
                    'current_fen': board.fen(),
                    'moves': moves,
                    'status': 'mate' if board.is_checkmate() else 'draw',
                    'ai_level': ai_level,
                    'player_color': 'white'
                }, user_id=current_user.id if current_user.is_authenticated else None, increment_version=True)
            else:
                # Get AI response
                logger.info(f"Getting Stockfish AI move at level {ai_level}")
                ai_response = engine.make_ai_move(board.fen(), skill_level=ai_level)
                ai_move_uci = ai_response['move']
                ai_move_san = ai_response['move_san']

                # Apply AI move to board
                board.push(chess.Move.from_uci(ai_move_uci))
                logger.info(f"Stockfish AI played: {ai_move_san} ({ai_move_uci})")

                # Save game state for Stockfish games with both moves
                moves.append({'san': ai_move_san, 'uci': ai_move_uci})

                # Update game storage and increment version
                version = storage.save_game(game_id, {
                    'game_type': 'live',
                    'engine_type': engine_type,
                    'current_fen': board.fen(),
                    'moves': moves,
                    'status': 'mate' if board.is_checkmate() else 'draw' if board.is_game_over() else 'started',
                    'ai_level': ai_level,
                    'player_color': 'white'
                }, user_id=current_user.id if current_user.is_authenticated else None, increment_version=True)

            ai_thinking = False

        return jsonify({
            'success': True,
            'version': version,
            'move_accepted': True,
            'ai_thinking': ai_thinking,
            'estimated_ai_time_ms': 2000 if ai_thinking else 0  # Hint for polling
        })
    except Exception as e:
        logger.error(f"Failed to make move {move_uci}: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/game-state', methods=['GET'])
def game_state():
    """Get current game state including opponent's last move (legacy endpoint for initial load)"""
    try:
        game_id = session.get('game_id')

        if not game_id:
            return jsonify({'success': False, 'error': 'No active game'}), 400

        # Load game data from storage
        game_data = storage.load_game(game_id)
        if not game_data:
            logger.error(f"Game {game_id} not found in storage")
            return jsonify({'success': False, 'error': 'Game not found'}), 404

        # Get engine_type from live_state
        live_state = game_data.get('live_state', {})
        engine_type = live_state.get('engine_type', 'lichess')

        # For Lichess games, sync with Lichess API
        if engine_type == 'lichess':
            lichess_game_id = live_state.get('lichess_game_id')
            if not lichess_game_id:
                logger.error(f"No Lichess game ID found for game {game_id}")
                return jsonify({'success': False, 'error': 'Lichess game not found'}), 404

            # Get game state from Lichess via streaming endpoint
            stream = lichess.get_game_stream(lichess_game_id)

            latest_state = None
            for event in stream:
                if event.get('type') == 'gameFull':
                    latest_state = event.get('state', {})
                    break
                elif event.get('type') == 'gameState':
                    latest_state = event
                    break

            if not latest_state:
                return jsonify({'success': False, 'error': 'Could not get game state'}), 400

            # Get moves from state
            moves_str = latest_state.get('moves', '')
            moves_list = moves_str.split() if moves_str else []

            # Replay all moves to sync board state
            temp_board = chess.Board()
            for move_uci in moves_list:
                temp_board.push(chess.Move.from_uci(move_uci))

            # Check game status
            status = latest_state.get('status', 'started')
            winner = latest_state.get('winner')

            # No need to update in-memory - database is source of truth

            # Save updated game state
            storage.save_game(game_id, {
                'game_type': 'live',
                'engine_type': engine_type,
                'lichess_game_id': lichess_game_id,
                'current_fen': temp_board.fen(),
                'moves': moves_list,
                'status': status,
                'winner': winner,
                'ai_level': game_data.get('ai_level', 1),
                'player_color': 'white'
            })
        else:
            # Stockfish game - use stored data
            moves_list = game_data.get('moves', [])
            status = live_state.get('status', 'started')
            winner = live_state.get('winner')

            # Rebuild board from moves
            temp_board = MoveFormat.replay_moves(moves_list)

        # Load move analysis
        move_analysis = game_data.get('move_analysis', [])

        # Get version from live_state
        version = live_state.get('version', 0)

        # Determine current turn and if it's player's turn
        player_color = live_state.get('player_color', 'white')
        current_turn = 'white' if len(moves_list) % 2 == 0 else 'black'
        is_player_turn = (current_turn == player_color)

        # Get last move details
        last_move_data = None
        if moves_list:
            last_move_uci = moves_list[-1]
            # Try to get SAN notation
            try:
                temp_for_san = chess.Board()
                for m in moves_list[:-1]:
                    temp_for_san.push(chess.Move.from_uci(m) if isinstance(m, str) else chess.Move.from_uci(m.get('uci')))
                last_move_obj = temp_for_san.push(chess.Move.from_uci(last_move_uci) if isinstance(last_move_uci, str) else chess.Move.from_uci(last_move_uci.get('uci')))
                last_move_san = temp_for_san.san(last_move_obj)
            except:
                last_move_san = last_move_uci

            last_move_data = {
                'uci': last_move_uci if isinstance(last_move_uci, str) else last_move_uci.get('uci'),
                'san': last_move_san,
                'timestamp': game_data.get('updated_at')
            }

        return jsonify({
            'success': True,
            'version': version,
            'game_id': game_id,
            'engine_type': engine_type,
            'status': status,
            'fen': temp_board.fen(),
            'moves': moves_list,
            'move_analysis': move_analysis,
            'current_turn': current_turn,
            'player_color': player_color,
            'is_player_turn': is_player_turn,
            'last_move': last_move_data,
            'winner': winner,
            'ai_level': live_state.get('ai_level', 1),
            'timestamp': game_data.get('updated_at')
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/game-stream')
def game_stream():
    """Server-Sent Events endpoint for real-time game updates"""
    def generate():
        game_id = session.get('game_id')

        if not game_id:
            yield f"data: {json.dumps({'error': 'No active game'})}\n\n"
            return

        logger.info(f"Starting SSE stream for game: {game_id}")

        # Get Lichess game ID
        lichess_game_id = get_lichess_game_id(game_id)
        if not lichess_game_id:
            logger.error(f"No Lichess game ID found for game {game_id}")
            yield f"data: {json.dumps({'error': 'Lichess game not found'})}\n\n"
            return

        try:
            # Get the Lichess game stream
            stream = lichess.get_game_stream(lichess_game_id)
            last_move_count = 0
            game_ended = False

            for event in stream:
                event_type = event.get('type')
                logger.debug(f"SSE event received: {event_type}")

                if event_type == 'gameFull':
                    # Initial game state
                    state = event.get('state', {})
                    moves_str = state.get('moves', '')
                    moves_list = moves_str.split() if moves_str else []
                    last_move_count = len(moves_list)

                    # No need to track board in memory - database is source of truth

                    # Send initial state
                    data = {
                        'moves': moves_list,
                        'last_move': moves_list[-1] if moves_list else None,
                        'status': state.get('status', 'started'),
                        'winner': state.get('winner')
                    }
                    yield f"event: game_update\ndata: {json.dumps(data)}\n\n"

                elif event_type == 'gameState':
                    # Game state update (new move, status change, etc.)
                    moves_str = event.get('moves', '')
                    moves_list = moves_str.split() if moves_str else []
                    status = event.get('status', 'started')
                    winner = event.get('winner')

                    # Only send update if there are new moves
                    if len(moves_list) > last_move_count:
                        last_move_count = len(moves_list)

                        # Build board from moves
                        temp_board = chess.Board()
                        for move_uci in moves_list:
                            temp_board.push(chess.Move.from_uci(move_uci))

                        # Load game to get ai_level
                        game_data = storage.load_game(game_id)
                        ai_level = game_data.get('live_state', {}).get('ai_level', 1) if game_data else 1

                        # Save game state
                        storage.save_game(game_id, {
                            'game_type': 'live',
                            'lichess_game_id': lichess_game_id,
                            'current_fen': temp_board.fen(),
                            'moves': moves_list,
                            'status': status,
                            'winner': winner,
                            'ai_level': ai_level,
                            'player_color': 'white'
                        })

                        logger.info(f"New move detected, sending update. Moves: {len(moves_list)}")

                        data = {
                            'moves': moves_list,
                            'last_move': moves_list[-1] if moves_list else None,
                            'status': status,
                            'winner': winner
                        }

                        # Send game update
                        if status == 'started':
                            yield f"event: game_update\ndata: {json.dumps(data)}\n\n"
                        else:
                            # Game ended
                            yield f"event: game_end\ndata: {json.dumps(data)}\n\n"
                            game_ended = True
                            break

                    # Check for status changes even without new moves
                    elif status != 'started':
                        data = {
                            'moves': moves_list,
                            'last_move': moves_list[-1] if moves_list else None,
                            'status': status,
                            'winner': winner
                        }
                        yield f"event: game_end\ndata: {json.dumps(data)}\n\n"
                        game_ended = True
                        break

            # If stream ended but game hasn't ended, send keep-alive pings
            # This should not normally happen, but handles edge cases
            if not game_ended:
                logger.warning(f"Lichess stream ended for game {game_id} but game not finished")
                # Send a keep-alive comment every 15 seconds
                while True:
                    yield ": keep-alive\n\n"
                    time.sleep(15)

        except GeneratorExit:
            logger.info(f"SSE client disconnected from game: {game_id}")
        except Exception as e:
            logger.error(f"Error in game stream: {str(e)}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',  # Disable buffering in nginx
            'Connection': 'keep-alive'
        }
    )


@app.route('/api/resign', methods=['POST'])
@login_required
@active_game_owner_required
def resign():
    """Resign the current game"""
    try:
        game_id = session.get('game_id')

        # Load game to determine engine type
        game_data = storage.load_game(game_id)
        if not game_data:
            logger.error(f"Game {game_id} not found")
            return jsonify({'success': False, 'error': 'Game not found'}), 404

        # Get engine_type from live_state
        live_state = game_data.get('live_state', {})
        engine_type = live_state.get('engine_type', 'lichess')

        # Resign based on engine type
        if engine_type == 'lichess':
            # Get Lichess game ID and resign on Lichess
            lichess_game_id = live_state.get('lichess_game_id')
            if not lichess_game_id:
                logger.error(f"No Lichess game ID found for game {game_id}")
                return jsonify({'success': False, 'error': 'Lichess game not found'}), 404

            lichess.resign_game(lichess_game_id)
            logger.info(f"Resigned Lichess game {lichess_game_id}")
        else:
            # Stockfish game - just update status locally
            logger.info(f"Resigned local Stockfish game {game_id}")

        # Update game status
        game_data['status'] = 'resigned'
        game_data['winner'] = 'black'  # Player is always white
        storage.save_game(game_id, game_data, user_id=current_user.id if current_user.is_authenticated else None)

        # Clear active game from session
        session.pop('game_id', None)

        return jsonify({'success': True})
    except Exception as e:
        logger.error(f"Failed to resign game: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/analyze-position', methods=['POST'])
def analyze_position():
    """Get analysis for the current position using local Stockfish"""
    try:
        data = request.json
        fen = data.get('fen')
        depth = data.get('depth', 20)  # Default depth 20
        multipv = data.get('multipv', 3)  # Default 3 variations

        if not fen:
            return jsonify({'success': False, 'error': 'No FEN provided'}), 400

        # Analyze with local Stockfish engine
        analysis = engine.analyze_position(fen, depth=depth, multipv=multipv)

        return jsonify({
            'success': True,
            'analysis': analysis
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/analyze-best-move', methods=['POST'])
def analyze_best_move():
    """Get best move analysis with AI commentary explaining why it's best"""
    try:
        data = request.json
        fen = data.get('fen')
        game_context = data.get('context', {})

        if not fen:
            return jsonify({'success': False, 'error': 'No FEN provided'}), 400

        logger.info(f"Analyzing best move for position FEN: {fen[:50]}...")

        # Use GameAnalysisService to get best move with commentary
        result = game_analysis_service.get_best_move_commentary(fen, game_context)

        if not result.get('success'):
            logger.warning(f"Best move analysis failed: {result.get('error')}")
            return jsonify(result), 400

        logger.info(f"Best move analysis complete: {result.get('best_move')} ({result.get('evaluation_text')})")

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in analyze-best-move endpoint: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/evaluate-move', methods=['POST'])
@login_required
@active_game_owner_required
def evaluate_move():
    """Evaluate a specific move using Stockfish and save to game analysis"""
    try:
        data = request.json
        fen = data.get('fen')
        move_uci = data.get('move')
        game_id = session.get('game_id')
        logger.info(f"Evaluating move: {move_uci} from position FEN: {fen[:50]}...")

        if not fen or not move_uci:
            logger.warning("Evaluate move called without FEN or move")
            return jsonify({'success': False, 'error': 'FEN and move required'}), 400

        # Safety check: only evaluate White (player) moves
        board = chess.Board(fen)
        if not board.turn:  # If Black to move
            logger.warning("Attempted to evaluate AI move")
            return jsonify({
                'success': False,
                'error': 'Cannot evaluate AI moves - only player moves are evaluated'
            }), 400

        # Get SAN notation for the move
        move_obj = chess.Move.from_uci(move_uci)
        move_san = board.san(move_obj)

        # Evaluate the move
        evaluation = engine.evaluate_move(fen, move_uci)
        logger.info(f"Move evaluation complete: {evaluation.get('classification')} (loss: {evaluation.get('eval_loss')} cp)")

        # Generate AI commentary for blunders and mistakes
        commentary = None
        classification = evaluation.get('classification')
        if classification in ['blunder', 'mistake'] and ai_commentator:
            try:
                logger.info(f"Generating AI commentary for {classification}: {move_san}")
                commentary = ai_commentator.get_move_commentary(
                    fen=fen,
                    move_san=move_san,
                    evaluation_data=evaluation
                )
                logger.info(f"AI commentary generated successfully for {classification}")
            except Exception as e:
                logger.error(f"Failed to generate AI commentary for {classification}: {str(e)}", exc_info=True)
                commentary = None

        # Save evaluation to game storage (with commentary for blunders)
        if game_id:
            game_data = storage.load_game(game_id)
            if game_data:
                # Get current move list and calculate move number
                moves = game_data.get('moves', [])
                move_count = len(moves)
                move_number = (move_count + 1) // 2  # Integer division for move number
                player = 'White' if move_count % 2 == 0 else 'Black'

                # Get or create move_analysis list (handle None case)
                move_analysis = game_data.get('move_analysis') or []

                # Create analysis entry using standard format
                analysis_entry = create_move_analysis_entry(
                    move_number=move_number,
                    move_san=move_san,
                    move_uci=move_uci,
                    player=player,
                    evaluation=evaluation,
                    commentary=commentary  # Will be set for blunders
                )

                # Add to analysis list
                move_analysis.append(analysis_entry)

                # Save back to storage
                game_data['move_analysis'] = move_analysis
                storage.save_game(game_id, game_data, user_id=current_user.id if current_user.is_authenticated else None)
                logger.info(f"Move evaluation saved for game {game_id}, move {move_number}")

        # Add commentary to evaluation object if available
        if commentary:
            evaluation['commentary'] = commentary

        return jsonify({
            'success': True,
            'evaluation': evaluation,
            'move_san': move_san
        })
    except Exception as e:
        logger.error(f"Failed to evaluate move: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/evaluate-move-ai', methods=['POST'])
@login_required
@active_game_owner_required
def evaluate_move_ai():
    """Get AI commentary for an evaluated move and save to game analysis"""
    try:
        data = request.json
        fen = data.get('fen')
        move_san = data.get('move_san')
        move_uci = data.get('move_uci')
        evaluation_data = data.get('evaluation_data')
        game_id = session.get('game_id')
        logger.info(f"Requesting AI commentary for move: {move_san} in game {game_id}")

        if not fen or not move_san or not move_uci or not evaluation_data:
            logger.warning("AI commentary called without required data")
            return jsonify({'success': False, 'error': 'FEN, move_san, move_uci, and evaluation_data required'}), 400

        # Check if AI commentator is available
        if not ai_commentator:
            logger.warning("AI commentator not available")
            return jsonify({
                'success': False,
                'error': 'AI commentator not available. Please set ANTHROPIC_API_KEY.'
            }), 400

        # Get AI commentary
        commentary = ai_commentator.get_move_commentary(
            fen=fen,
            move_san=move_san,
            evaluation_data=evaluation_data
        )
        logger.info("AI commentary generated successfully")

        # Update existing analysis entry with commentary
        game_data = storage.load_game(game_id)
        if game_data:
            # Get or create move_analysis list (handle None case)
            move_analysis = game_data.get('move_analysis') or []

            # Find the most recent analysis entry matching this move
            # (should be the last entry if called right after evaluate_move)
            updated = False
            for entry in reversed(move_analysis):
                if entry.get('move_uci') == move_uci and entry.get('commentary') is None:
                    # Update this entry with commentary
                    entry['commentary'] = commentary
                    updated = True
                    logger.info(f"Updated existing analysis entry for move {entry.get('move_number')}")
                    break

            # If no existing entry found, create a new one (fallback for backwards compatibility)
            if not updated:
                moves = game_data.get('moves', [])
                move_count = len(moves)
                move_number = (move_count + 1) // 2
                player = 'White' if move_count % 2 == 0 else 'Black'

                analysis_entry = create_move_analysis_entry(
                    move_number=move_number,
                    move_san=move_san,
                    move_uci=move_uci,
                    player=player,
                    evaluation=evaluation_data,
                    commentary=commentary
                )
                move_analysis.append(analysis_entry)
                logger.info(f"Created new analysis entry for move {move_number}")

            # Save back to storage
            game_data['move_analysis'] = move_analysis
            storage.save_game(game_id, game_data, user_id=current_user.id if current_user.is_authenticated else None)
            logger.info(f"Move commentary saved for game {game_id}")

        return jsonify({
            'success': True,
            'commentary': commentary
        })
    except Exception as e:
        logger.error(f"Failed to get AI commentary: {str(e)}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/parse-pgn', methods=['POST'])
def parse_pgn():
    """Parse a PGN string and return game data"""
    try:
        data = request.json
        pgn_text = data.get('pgn', '')

        if not pgn_text:
            return jsonify({
                'success': False,
                'error': 'No PGN provided'
            }), 400

        # Parse PGN
        pgn = chess.pgn.read_game(io.StringIO(pgn_text))

        if not pgn:
            return jsonify({
                'success': False,
                'error': 'Invalid PGN format'
            }), 400

        # Extract headers
        headers = {}
        for header in ['Event', 'Site', 'Date', 'Round', 'White', 'Black', 'Result', 'WhiteElo', 'BlackElo', 'TimeControl', 'ECO', 'Opening']:
            value = pgn.headers.get(header)
            if value:
                headers[header] = value

        # Extract moves using unified format
        moves = MoveFormat.parse_pgn_moves(pgn)

        return jsonify({
            'success': True,
            'headers': headers,
            'moves': moves,
            'move_count': len(moves),
            'pgn_text': pgn_text
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/pgns', methods=['GET'])
@login_required_for_analyze
def list_pgns():
    """API endpoint to get user's saved PGNs (imported games, excluding curated)"""
    try:
        # List imported games for current user only, excluding curated games
        games = storage.list_games(user_id=current_user.id, game_type='imported')

        # Filter out curated games
        user_games = [g for g in games if not g.get('is_curated', False)]

        # Format for game list display
        games_list = [
            {
                'game_id': g['id'],
                'name': g['name'],
                'white': g['white_player'] or 'Unknown',
                'black': g['black_player'] or 'Unknown',
                'event': g['event'] or 'Unknown Event',
                'result': g['result'] or '*',
                'date': g['game_date'] or '????.??.??',
                'created_at': g['created_at'],
                'updated_at': g['updated_at'],
                'move_count': g['move_count'],
                'has_commentary': g['has_analysis'],
                'is_curated': g.get('is_curated', False)
            }
            for g in user_games
        ]

        return jsonify({
            'success': True,
            'games': games_list
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/curated-games', methods=['GET'])
def list_curated_games():
    """API endpoint to get all curated games (famous games)

    Query parameters:
        opening: Filter by opening name (optional)
    """
    try:
        # Get optional opening filter
        opening_filter = request.args.get('opening')

        # Get all curated games
        curated_games = storage.get_curated_games(opening=opening_filter)

        # Format for game list display
        games_list = [
            {
                'game_id': g.id,
                'name': g.name,
                'white': g.white_player or 'Unknown',
                'black': g.black_player or 'Unknown',
                'event': g.event or 'Unknown Event',
                'result': g.result or '*',
                'date': g.game_date or '????.??.??',
                'opening': g.opening or '',
                'created_at': g.created_at.isoformat() if g.created_at else None,
                'updated_at': g.updated_at.isoformat() if g.updated_at else None,
                'move_count': len(g.moves) if g.moves else 0,
                'has_commentary': bool(g.move_analysis),
                'is_curated': True
            }
            for g in curated_games
        ]

        return jsonify({
            'success': True,
            'games': games_list
        })
    except Exception as e:
        logger.error(f"Error listing curated games: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/game/<game_id>/data', methods=['GET'])
def get_game_data(game_id):
    """API endpoint to get a specific game's data (public for curated, auth required for private)"""
    try:
        game = storage.load_game(game_id)
        if not game:
            return jsonify({
                'success': False,
                'error': 'Game not found'
            }), 404

        # If it's a curated game, allow public access
        is_curated = game.get('is_curated', False)

        # For private games, require authentication and ownership
        if not is_curated:
            if not current_user.is_authenticated:
                return jsonify({
                    'success': False,
                    'error': 'Authentication required'
                }), 401

            # Check ownership
            if game.get('user_id') != current_user.id:
                return jsonify({
                    'success': False,
                    'error': 'Unauthorized access to private game'
                }), 403

        # Format for game display (compatible with frontend expectations)
        game_data = {
            'game_id': game['id'],
            'user_id': game['user_id'],
            'name': game['name'],
            'moves': game['moves'],
            'move_analysis': game['move_analysis'],
            'headers': {
                'Result': game['result'],
                'White': game['white_player'],
                'Black': game['black_player'],
                'WhiteElo': str(game['white_elo']) if game['white_elo'] else None,
                'BlackElo': str(game['black_elo']) if game['black_elo'] else None,
                'Event': game['event'],
                'Site': game['site'],
                'Date': game['game_date'],
                'Opening': game['opening'],
                'ECO': game['eco'],
            },
            'created_at': game['created_at'],
            'updated_at': game['updated_at'],
        }

        return jsonify({
            'success': True,
            'game': game_data
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/save-pgn', methods=['POST'])
@login_required_for_analyze
def save_pgn():
    """API endpoint to save a PGN as imported game"""
    try:
        data = request.json
        pgn_text = data.get('pgn_text', '')
        name = data.get('name', '')
        headers = data.get('headers', {})
        moves = data.get('moves', [])

        if not moves:
            return jsonify({
                'success': False,
                'error': 'No moves provided'
            }), 400

        # Generate unique ID based on timestamp
        game_id = str(uuid.uuid4())

        # Save as imported game
        user_id = current_user.id if current_user.is_authenticated else None

        game_data = {
            'game_type': 'imported',
            'name': name,
            'moves': moves,  # Already in unified format from parse_pgn
            'result': headers.get('Result'),
            'white_player': headers.get('White'),
            'black_player': headers.get('Black'),
            'white_elo': storage._parse_elo(headers.get('WhiteElo')),
            'black_elo': storage._parse_elo(headers.get('BlackElo')),
            'event': headers.get('Event'),
            'site': headers.get('Site'),
            'game_date': headers.get('Date'),
            'opening': headers.get('Opening'),
            'eco': headers.get('ECO'),
        }

        storage.save_game(game_id, game_data, user_id=user_id)

        return jsonify({
            'success': True,
            'game_id': game_id
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400


@app.route('/api/generate-commentary/<game_id>', methods=['POST'])
@login_required
@game_owner_required
def generate_commentary(game_id):
    """API endpoint to generate AI commentary for a game (PGN or live game)"""
    # Delegate to service (handles all business logic and database updates)
    db_session = get_db_session()
    try:
        from services.curated_game_service import CuratedGameService
        service = CuratedGameService(db_session, engine, ai_commentator)

        # Generate commentary (service handles status updates, validation, etc.)
        result = service.generate_commentary_for_game(game_id, require_curated=False)

        if result['status'] == 'success':
            return jsonify({
                'success': True,
                'move_analysis': result.get('move_analysis'),
                'message': result.get('message')
            })
        else:
            return jsonify({
                'success': False,
                'error': result.get('message')
            }), 400

    finally:
        db_session.close()


# ================================================================================
# ADMIN ROUTES - Curated Game Management
# ================================================================================

@app.route('/admin')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard for managing curated games"""
    return render_template('admin.html', user=current_user)


@app.route('/admin/api/curated-games', methods=['GET'])
@login_required
@admin_required
def get_curated_games():
    """Get all curated games with their status"""
    try:
        games = storage.get_curated_games()
        return jsonify({
            'success': True,
            'games': [game.to_summary_dict() for game in games]
        })
    except Exception as e:
        logger.error(f"Failed to fetch curated games: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/admin/api/upload-curated-game', methods=['POST'])
@login_required
@admin_required
def upload_curated_game():
    """Upload a new curated game from PGN"""
    try:
        data = request.get_json()
        pgn_text = data.get('pgn')

        if not pgn_text:
            return jsonify({'success': False, 'error': 'PGN text is required'}), 400

        # Parse PGN
        pgn = chess.pgn.read_game(io.StringIO(pgn_text))
        if not pgn:
            return jsonify({'success': False, 'error': 'Invalid PGN format'}), 400

        # Extract headers
        headers = dict(pgn.headers)

        # Extract moves
        board = chess.Board()
        moves = []
        for move in pgn.mainline_moves():
            san = board.san(move)
            uci = move.uci()
            moves.append({'san': san, 'uci': uci})
            board.push(move)

        # Create curated game
        game_data = {
            'name': f"{headers.get('White', 'Unknown')} vs {headers.get('Black', 'Unknown')}",
            'moves': moves,
            'game_type': 'imported',
            'white_player': headers.get('White'),
            'black_player': headers.get('Black'),
            'white_elo': int(headers.get('WhiteElo', 0)) if headers.get('WhiteElo', '').isdigit() else None,
            'black_elo': int(headers.get('BlackElo', 0)) if headers.get('BlackElo', '').isdigit() else None,
            'event': headers.get('Event'),
            'site': headers.get('Site'),
            'game_date': headers.get('Date'),
            'result': headers.get('Result'),
            'opening': headers.get('Opening'),
            'eco': headers.get('ECO'),
            'is_curated': True,
            'commentary_status': 'pending'
        }

        game_id = storage.save_curated_game(game_data, user_id=current_user.id)

        logger.info(f"Curated game uploaded: {game_id} by user: {current_user.email}")

        return jsonify({
            'success': True,
            'game_id': game_id,
            'message': 'Curated game uploaded successfully'
        })

    except Exception as e:
        logger.error(f"Failed to upload curated game: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/admin/api/generate-commentary/<game_id>', methods=['POST'])
@login_required
@admin_required
def generate_curated_commentary(game_id):
    """Trigger commentary generation for a curated game (async)"""
    try:
        # Verify game exists and is curated (query database model)
        db = get_db_session()
        try:
            game = db.query(ChessGame).filter_by(id=game_id).first()
            if not game:
                return jsonify({'success': False, 'error': 'Game not found'}), 404

            if not game.is_curated:
                return jsonify({'success': False, 'error': 'Only curated games can have commentary generated'}), 400
        finally:
            db.close()

        # Create service and submit background job
        def generate_commentary_task():
            """Task to run in background"""
            from app import get_db_session
            db = get_db_session()
            try:
                service = CuratedGameService(db, engine, ai_commentator)
                result = service.generate_commentary_for_game(game_id, require_curated=True)
                return result
            finally:
                db.close()

        # Submit job
        job_manager.submit_job(game_id, generate_commentary_task)

        logger.info(f"Commentary generation job submitted for game {game_id}")

        return jsonify({
            'success': True,
            'message': 'Commentary generation started',
            'job_id': game_id
        })

    except Exception as e:
        logger.error(f"Failed to start commentary generation: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/admin/api/commentary-status/<game_id>', methods=['GET'])
@login_required
@admin_required
def get_commentary_status(game_id):
    """Get the status of commentary generation for a game"""
    try:
        # Get job status
        job_status = job_manager.get_job_status(game_id)

        # Get game status from database (query model, not storage)
        db = get_db_session()
        try:
            game = db.query(ChessGame).filter_by(id=game_id).first()
            if not game:
                return jsonify({'success': False, 'error': 'Game not found'}), 404

            return jsonify({
                'success': True,
                'game_id': game_id,
                'job_status': job_status.get('status', 'unknown'),
                'db_status': game.commentary_status,
                'generated_at': game.commentary_generated_at.isoformat() if game.commentary_generated_at else None,
                'move_count': len(game.moves) if game.moves else 0,
                'has_analysis': bool(game.move_analysis)
            })
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Failed to get commentary status: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/admin/api/curated-game/<game_id>', methods=['PATCH'])
@login_required
@admin_required
def update_curated_game(game_id):
    """Update curated game metadata"""
    try:
        data = request.get_json()
        updates = {}

        # Allow updating these fields
        if 'name' in data:
            updates['name'] = data['name']

        storage.update_curated_game(game_id, updates)

        logger.info(f"Updated curated game {game_id}")

        return jsonify({
            'success': True,
            'message': 'Game updated successfully'
        })

    except Exception as e:
        logger.error(f"Failed to update curated game: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/admin/api/curated-game/<game_id>', methods=['DELETE'])
@login_required
@admin_required
def delete_curated_game(game_id):
    """Delete a curated game"""
    try:
        storage.delete_curated_game(game_id)

        logger.info(f"Deleted curated game {game_id}")

        return jsonify({
            'success': True,
            'message': 'Game deleted successfully'
        })

    except Exception as e:
        logger.error(f"Failed to delete curated game: {e}", exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 400


if __name__ == '__main__':
    app.run(debug=True, port=5000)
