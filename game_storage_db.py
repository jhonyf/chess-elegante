"""
Database-backed storage for chess games
Unified storage layer for both live and imported games
"""
import os
import logging
from datetime import datetime
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker, scoped_session
from models import Base, ChessGame, LiveGameState
from move_utils import normalize_moves

logger = logging.getLogger(__name__)


class GameStorage:
    """Database-backed storage for chess games"""

    def __init__(self, database_url=None):
        """
        Initialize database connection

        Args:
            database_url: PostgreSQL connection string (uses DATABASE_URL env var if not provided)
        """
        if database_url is None:
            database_url = os.getenv('DATABASE_URL', 'postgresql://chess:chess@localhost:5432/chess_elegante')

        logger.info(f"Initializing GameStorage with database: {database_url.split('@')[-1]}")  # Hide credentials

        # Create engine
        self.engine = create_engine(
            database_url,
            pool_pre_ping=True,  # Verify connections before using
            pool_size=5,
            max_overflow=10
        )

        # Create session factory (thread-safe)
        session_factory = sessionmaker(bind=self.engine)
        self.Session = scoped_session(session_factory)

        logger.info("GameStorage initialized successfully")

    def _get_session(self):
        """Get a new database session"""
        return self.Session()

    # ==================== CHESS GAME METHODS ====================

    def save_game(self, game_id, game_data, user_id=None, increment_version=False):
        """
        Save or update a chess game in the database
        Handles both live games and imported games

        Args:
            game_id: Unique game identifier
            game_data: Dict with game information
                Core fields (all games):
                - moves: List of moves
                - game_type: 'live' or 'imported'
                - move_analysis: Optional analysis data
                - name: Optional user-defined name

                Live game specific:
                - fen: Current board position
                - status: Game status (started, finished, resigned, etc.)
                - player_color: Color player is playing (white/black)
                - ai_level: AI difficulty level
                - lichess_game_id: Lichess game ID

                Imported game specific:
                - white_player, black_player: Player names
                - white_elo, black_elo: Player ratings
                - event, site, game_date, opening, eco: Metadata
                - result: Game result

            user_id: ID of user who owns this game (None = shared/anonymous)
            increment_version: If True, increment the version in LiveGameState (for state sync)

        Returns:
            int: The new version number if this is a live game, None otherwise
        """
        session = self._get_session()
        try:
            game_type = game_data.get('game_type', 'live')

            # Normalize moves to unified format
            raw_moves = game_data.get('moves', [])
            normalized_moves = normalize_moves(raw_moves) if raw_moves else []

            logger.info(f"Saving {game_type} game: {game_id} (moves: {len(normalized_moves)})")

            # Check if game exists
            game = session.query(ChessGame).filter_by(id=game_id).first()

            if game:
                # Update existing game with normalized moves
                if raw_moves:
                    game.moves = normalized_moves
                game.move_analysis = game_data.get('move_analysis', game.move_analysis)
                game.name = game_data.get('name', game.name)
                game.result = game_data.get('result', game.result)

                # Update metadata if provided
                if 'white_player' in game_data:
                    game.white_player = game_data['white_player']
                if 'black_player' in game_data:
                    game.black_player = game_data['black_player']
                if 'white_elo' in game_data:
                    game.white_elo = game_data['white_elo']
                if 'black_elo' in game_data:
                    game.black_elo = game_data['black_elo']
                if 'event' in game_data:
                    game.event = game_data['event']
                if 'site' in game_data:
                    game.site = game_data['site']
                if 'game_date' in game_data:
                    game.game_date = game_data['game_date']
                if 'opening' in game_data:
                    game.opening = game_data['opening']
                if 'eco' in game_data:
                    game.eco = game_data['eco']

                game.updated_at = datetime.utcnow()
                logger.debug(f"Updated existing game: {game_id}")

                # Update live state if it exists and data is provided
                if game_type == 'live' and game.live_state:
                    if 'engine_type' in game_data:
                        game.live_state.engine_type = game_data['engine_type']
                    if 'status' in game_data:
                        game.live_state.status = game_data['status']
                    if 'current_fen' in game_data:
                        game.live_state.current_fen = game_data['current_fen']
                    if 'lichess_game_id' in game_data:
                        game.live_state.lichess_game_id = game_data['lichess_game_id']

                    # Increment version if requested (for state sync)
                    if increment_version:
                        game.live_state.version += 1
                        logger.debug(f"Incremented version to {game.live_state.version} for game {game_id}")

            else:
                # Create new game with normalized moves
                game = ChessGame(
                    id=game_id,
                    user_id=user_id,
                    name=game_data.get('name'),
                    moves=normalized_moves,
                    move_analysis=game_data.get('move_analysis'),
                    game_type=game_type,
                    result=game_data.get('result'),
                    white_player=game_data.get('white_player'),
                    black_player=game_data.get('black_player'),
                    white_elo=game_data.get('white_elo'),
                    black_elo=game_data.get('black_elo'),
                    event=game_data.get('event'),
                    site=game_data.get('site'),
                    game_date=game_data.get('game_date'),
                    opening=game_data.get('opening'),
                    eco=game_data.get('eco'),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(game)
                logger.debug(f"Created new {game_type} game: {game_id} for user: {user_id or 'anonymous'}")

                # Create live state if this is a live game
                if game_type == 'live':
                    engine_type = game_data.get('engine_type', 'lichess')
                    lichess_game_id = game_data.get('lichess_game_id')

                    # Validate: lichess_game_id is required only for Lichess games
                    if engine_type == 'lichess' and not lichess_game_id:
                        raise ValueError(f"lichess_game_id is required for Lichess games")

                    live_state = LiveGameState(
                        game_id=game_id,
                        engine_type=engine_type,
                        lichess_game_id=lichess_game_id,
                        status=game_data.get('status', 'started'),
                        player_color=game_data.get('player_color', 'white'),
                        ai_level=game_data.get('ai_level', 1),
                        current_fen=game_data.get('fen')
                    )
                    session.add(live_state)
                    logger.debug(f"Created live state for game: {game_id} with engine: {engine_type}")

            session.commit()
            logger.info(f"Game saved successfully: {game_id}")

            # Return the new version if this is a live game
            new_version = None
            if game_type == 'live' and game.live_state:
                new_version = game.live_state.version

            return new_version

        except Exception as e:
            session.rollback()
            logger.error(f"Error saving game {game_id}: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def load_game(self, game_id):
        """Load a game from the database"""
        session = self._get_session()
        try:
            logger.info(f"Loading game: {game_id}")
            game = session.query(ChessGame).filter_by(id=game_id).first()

            if not game:
                logger.warning(f"Game not found: {game_id}")
                return None

            game_dict = game.to_dict()

            # Include live state if it exists
            if game.live_state:
                game_dict['live_state'] = game.live_state.to_dict()

            logger.debug(f"Game loaded: {game_id} (moves: {len(game_dict.get('moves', []))})")
            return game_dict

        except Exception as e:
            logger.error(f"Error loading game {game_id}: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def list_games(self, user_id=None, game_type=None, status=None):
        """
        List games, optionally filtered by user, type, or status

        Args:
            user_id: User ID to filter games
            game_type: 'live' or 'imported'
            status: Status filter (only applies to live games with active state)

        Returns:
            List of game summaries
        """
        session = self._get_session()
        try:
            query = session.query(ChessGame).order_by(desc(ChessGame.updated_at))

            # Filter by user_id if provided
            if user_id:
                query = query.filter(ChessGame.user_id == user_id)

            # Filter by game_type if provided
            if game_type:
                query = query.filter(ChessGame.game_type == game_type)

            # Filter by status (only for live games)
            if status:
                query = query.join(LiveGameState).filter(LiveGameState.status == status)

            games = query.all()

            # Return summaries
            result = []
            for game in games:
                summary = game.to_summary_dict()
                # Add live state info if exists
                if game.live_state:
                    summary['status'] = game.live_state.status
                    summary['ai_level'] = game.live_state.ai_level
                    summary['player_color'] = game.live_state.player_color
                result.append(summary)

            return result

        except Exception as e:
            logger.error(f"Error listing games: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def delete_game(self, game_id):
        """Delete a game from the database (cascades to live state)"""
        session = self._get_session()
        try:
            logger.info(f"Deleting game: {game_id}")
            game = session.query(ChessGame).filter_by(id=game_id).first()

            if game:
                session.delete(game)
                session.commit()
                logger.info(f"Game deleted: {game_id}")
            else:
                logger.warning(f"Game not found for deletion: {game_id}")

        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting game {game_id}: {e}", exc_info=True)
            raise
        finally:
            session.close()

    # ==================== LIVE GAME STATE METHODS ====================

    def update_live_state(self, game_id, state_data):
        """
        Update live game state separately

        Args:
            game_id: Game ID
            state_data: Dict with state updates (status, current_fen, etc.)
        """
        session = self._get_session()
        try:
            live_state = session.query(LiveGameState).filter_by(game_id=game_id).first()

            if not live_state:
                logger.warning(f"Live state not found for game: {game_id}")
                return

            if 'status' in state_data:
                live_state.status = state_data['status']
            if 'current_fen' in state_data:
                live_state.current_fen = state_data['current_fen']

            session.commit()
            logger.debug(f"Updated live state for game: {game_id}")

        except Exception as e:
            session.rollback()
            logger.error(f"Error updating live state for {game_id}: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def delete_live_state(self, game_id):
        """
        Delete live state for a finished game (keeps ChessGame record)
        Useful for cleanup after game ends
        """
        session = self._get_session()
        try:
            live_state = session.query(LiveGameState).filter_by(game_id=game_id).first()

            if live_state:
                session.delete(live_state)
                session.commit()
                logger.info(f"Live state deleted for game: {game_id}")

        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting live state for {game_id}: {e}", exc_info=True)
            raise
        finally:
            session.close()

    # ==================== CURATED GAME METHODS ====================

    def get_curated_games(self, opening=None):
        """Get all curated games, optionally filtered by opening

        Args:
            opening: Optional opening name to filter by

        Returns:
            List of ChessGame objects
        """
        session = self._get_session()
        try:
            query = session.query(ChessGame).filter_by(is_curated=True)

            # Apply opening filter if provided
            if opening:
                query = query.filter(ChessGame.opening == opening)

            games = query.order_by(ChessGame.created_at.desc()).all()
            logger.info(f"Retrieved {len(games)} curated games" + (f" for opening '{opening}'" if opening else ""))
            return games
        except Exception as e:
            logger.error(f"Error fetching curated games: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def save_curated_game(self, game_data, user_id=None):
        """
        Save a curated game (admin-only)

        Args:
            game_data: Dict with game data including is_curated=True
            user_id: ID of the admin user creating the curated game

        Returns:
            game_id: ID of saved game
        """
        import uuid
        session = self._get_session()
        try:
            game_id = str(uuid.uuid4())

            # Ensure curated flag is set
            game_data['is_curated'] = True
            game_data['user_id'] = user_id  # Set to admin user who created it

            game = ChessGame(id=game_id, **game_data)
            session.add(game)
            session.commit()

            logger.info(f"Curated game saved: {game_id}")
            return game_id

        except Exception as e:
            session.rollback()
            logger.error(f"Error saving curated game: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def update_curated_game(self, game_id, updates):
        """
        Update curated game metadata

        Args:
            game_id: Game ID
            updates: Dict with fields to update
        """
        session = self._get_session()
        try:
            game = session.query(ChessGame).filter_by(id=game_id, is_curated=True).first()

            if not game:
                raise ValueError(f"Curated game not found: {game_id}")

            # Update allowed fields
            for key, value in updates.items():
                if hasattr(game, key):
                    setattr(game, key, value)

            session.commit()
            logger.info(f"Curated game updated: {game_id}")

        except Exception as e:
            session.rollback()
            logger.error(f"Error updating curated game: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def delete_curated_game(self, game_id):
        """Delete a curated game"""
        session = self._get_session()
        try:
            game = session.query(ChessGame).filter_by(id=game_id, is_curated=True).first()

            if not game:
                raise ValueError(f"Curated game not found: {game_id}")

            session.delete(game)
            session.commit()
            logger.info(f"Curated game deleted: {game_id}")

        except Exception as e:
            session.rollback()
            logger.error(f"Error deleting curated game: {e}", exc_info=True)
            raise
        finally:
            session.close()

    # ==================== HELPER METHODS ====================

    def _parse_elo(self, elo_str):
        """Parse ELO rating from string to integer"""
        if not elo_str:
            return None
        try:
            return int(elo_str)
        except (ValueError, TypeError):
            return None
