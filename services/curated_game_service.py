"""
Curated Game Service
Handles commentary generation for famous/curated chess games
"""
import logging
from datetime import datetime
from sqlalchemy.orm import Session
from database.models import ChessGame
from services.stockfish_engine import StockfishEngine
from services.ai_commentator import AICommentator
from services.game_analysis_service import GameAnalysisService

logger = logging.getLogger(__name__)


class CuratedGameService:
    """Service for generating commentary on curated games"""

    def __init__(self, db_session, stockfish_engine=None, ai_commentator=None):
        """
        Initialize the service

        Args:
            db_session: SQLAlchemy database session
            stockfish_engine: Optional StockfishEngine instance
            ai_commentator: Optional AICommentator instance
        """
        self.db = db_session
        stockfish = stockfish_engine or StockfishEngine()

        # AI commentator is optional
        try:
            commentator = ai_commentator or AICommentator()
        except Exception as e:
            logger.warning(f"AI Commentator not available: {e}")
            commentator = None

        # Initialize the game analysis service
        self.analysis_service = GameAnalysisService(stockfish, commentator)

    def generate_commentary_for_game(self, game_id, require_curated=False):
        """
        Generate full game commentary for a game (curated or regular)
        This function is designed to run in background

        Args:
            game_id: ID of the ChessGame to analyze
            require_curated: If True, only allow curated games (for admin workflow)

        Returns:
            dict: Result with status and message
        """
        try:
            logger.info(f"Starting commentary generation for game {game_id}")

            # Fetch game
            game = self.db.query(ChessGame).filter_by(id=game_id).first()
            if not game:
                raise ValueError(f"Game {game_id} not found")

            if require_curated and not game.is_curated:
                raise ValueError(f"Game {game_id} is not a curated game")

            # Check if commentary already exists
            if game.commentary_status == 'completed':
                raise ValueError(f"Commentary already exists for game {game_id}")

            if not game.moves:
                raise ValueError(f"No moves in game {game_id}")

            # Update status to processing
            game.commentary_status = 'processing'
            self.db.commit()

            # Analyze all moves (reuse existing evaluations if available)
            move_analysis = self._analyze_all_moves(game)

            # Update game with analysis
            game.move_analysis = move_analysis
            game.commentary_status = 'completed'
            game.commentary_generated_at = datetime.utcnow()
            self.db.commit()

            logger.info(f"Commentary generation completed for game {game_id}")
            return {
                'status': 'success',
                'message': f'Generated commentary for {len(move_analysis)} moves',
                'move_count': len(move_analysis),
                'move_analysis': move_analysis
            }

        except Exception as e:
            logger.error(f"Commentary generation failed for game {game_id}: {e}", exc_info=True)

            # Update status to failed
            try:
                game = self.db.query(ChessGame).filter_by(id=game_id).first()
                if game:
                    game.commentary_status = 'failed'
                    self.db.commit()
            except Exception as db_error:
                logger.error(f"Failed to update game status: {db_error}")

            return {
                'status': 'failed',
                'message': str(e)
            }

    def _analyze_all_moves(self, game):
        """
        Analyze all moves in a game and generate commentary
        Reuses existing evaluations if available

        Args:
            game: ChessGame instance

        Returns:
            list: Move analysis data
        """
        moves = game.moves or []
        existing_analysis = game.move_analysis

        # Log what we have
        logger.info(f"Analyzing {len(moves)} moves for game {game.id}")
        if existing_analysis:
            logger.info(f"Found existing analysis with {len(existing_analysis)} entries")
            # Log first entry to see structure
            if existing_analysis:
                logger.debug(f"First analysis entry structure: {existing_analysis[0].keys() if existing_analysis[0] else 'None'}")
        else:
            logger.info(f"No existing analysis found, will evaluate all moves")

        # Use the common game analysis service
        # Use batch commentary for efficiency (faster for many moves)
        # Reuse existing evaluations if available
        move_analysis = self.analysis_service.analyze_game_moves(
            moves=moves,
            use_batch_commentary=True,
            existing_analysis=existing_analysis
        )

        return move_analysis
