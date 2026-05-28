"""
Game Analysis Service
Common service for analyzing chess games and generating commentary
"""
import logging
from core.move_utils import create_move_analysis_entry
import chess

logger = logging.getLogger(__name__)


class GameAnalysisService:
    """Service for analyzing chess games with Stockfish and AI commentary"""

    def __init__(self, stockfish_engine, ai_commentator=None):
        """
        Initialize the service

        Args:
            stockfish_engine: StockfishEngine instance
            ai_commentator: Optional AICommentator instance
        """
        self.stockfish = stockfish_engine
        self.ai_commentator = ai_commentator

    def analyze_game_moves(self, moves, use_batch_commentary=True, existing_analysis=None):
        """
        Analyze all moves in a game and optionally generate commentary

        Args:
            moves: List of move dictionaries with 'san' and 'uci' keys
            use_batch_commentary: If True, generate commentary in batch (faster)
            existing_analysis: Optional list of existing move analysis (will reuse evaluations)

        Returns:
            list: Move analysis data with evaluations and optional commentary
        """
        board = chess.Board()
        move_analysis = []
        moves_data_for_batch = []
        previous_evaluation = None  # Track previous move's evaluation for position reuse

        logger.info(f"Analyzing {len(moves)} moves")

        for i, move_dict in enumerate(moves):
            try:
                move_number = (i // 2) + 1
                is_white = i % 2 == 0
                player = 'White' if is_white else 'Black'

                # Get move in different formats
                san = move_dict.get('san')
                uci = move_dict.get('uci')

                if not san or not uci:
                    logger.warning(f"Move {i} missing san or uci notation, skipping")
                    continue

                # Get position before move
                fen_before = board.fen()

                # Try to reuse existing evaluation if available
                evaluation = None
                if existing_analysis:
                    # Find matching entry by move_number and player
                    matching_entry = None
                    for entry in existing_analysis:
                        if (entry.get('move_number') == move_number and
                            entry.get('player') == player and
                            entry.get('move_san') == san):
                            matching_entry = entry
                            break

                    if matching_entry and matching_entry.get('evaluation'):
                        evaluation = matching_entry['evaluation']
                        logger.info(f"✓ Reusing existing evaluation for move {move_number}. {san} ({player})")
                    else:
                        logger.debug(f"No matching evaluation found for move {move_number}. {san} ({player})")

                # If no existing evaluation, evaluate the move
                if not evaluation:
                    logger.info(f"⚙ Evaluating move {i+1}: {san}")
                    # Pass previous move's after-position analysis to avoid duplicate analysis
                    previous_position_analysis = None
                    if previous_evaluation and '_after_position_analysis' in previous_evaluation:
                        previous_position_analysis = previous_evaluation['_after_position_analysis']

                    evaluation = self.stockfish.evaluate_move(fen_before, uci, previous_position_analysis)

                # Create analysis entry
                analysis_entry = create_move_analysis_entry(
                    move_number=move_number,
                    move_san=san,
                    move_uci=uci,
                    player=player,
                    evaluation=evaluation,
                    commentary=None  # Will be filled later if batch commentary is used
                )

                # If not using batch commentary, generate individual commentary
                if self.ai_commentator and not use_batch_commentary and evaluation:
                    try:
                        commentary = self.ai_commentator.get_move_commentary(
                            fen_before,
                            san,
                            evaluation
                        )
                        analysis_entry['commentary'] = commentary
                    except Exception as e:
                        logger.warning(f"Failed to generate commentary for move {i}: {e}")

                # Prepare data for batch commentary if needed
                if use_batch_commentary and evaluation:
                    moves_data_for_batch.append({
                        'move_number': move_number,
                        'move_san': san,
                        'player': player,
                        'evaluation_data': evaluation,
                        'fen_before': fen_before
                    })

                move_analysis.append(analysis_entry)

                # Store this evaluation for next move's position reuse
                previous_evaluation = evaluation

                # Apply the move to board
                board.push(chess.Move.from_uci(uci))

                # Log progress every 10 moves
                if (i + 1) % 10 == 0:
                    logger.info(f"Analyzed {i + 1}/{len(moves)} moves")

            except Exception as e:
                logger.error(f"Error analyzing move {i}: {e}", exc_info=True)
                # Add error entry
                move_analysis.append(create_move_analysis_entry(
                    move_number=move_number,
                    move_san=san,
                    move_uci=uci,
                    player=player,
                    evaluation=None,
                    commentary=f"Error: {str(e)}"
                ))
                previous_evaluation = None  # Reset on error to avoid invalid reuse
                continue

        # Generate batch commentary if requested
        if use_batch_commentary and self.ai_commentator and moves_data_for_batch:
            logger.info(f"Requesting batch commentary for {len(moves_data_for_batch)} moves")
            try:
                commentaries = self.ai_commentator.get_batch_commentary(moves_data_for_batch)
                logger.info(f"Received {len(commentaries)} commentaries")

                # Assign commentaries to move_analysis
                commentary_index = 0
                for analysis in move_analysis:
                    if analysis['commentary'] is None and commentary_index < len(commentaries):
                        analysis['commentary'] = commentaries[commentary_index]
                        commentary_index += 1
            except Exception as e:
                logger.error(f"Failed to generate batch commentary: {e}", exc_info=True)

        logger.info(f"Completed analysis of {len(move_analysis)} moves")
        return move_analysis

    def get_best_move_commentary(self, fen, game_context=None):
        """
        Get AI commentary explaining why a move is the best in the position

        Args:
            fen: Current position FEN string
            game_context: Optional dict with game context (move history, material, etc.)

        Returns:
            dict: {
                'best_move': str (SAN notation),
                'evaluation': float,
                'commentary': str (AI-generated explanation),
                'pv_line': list (continuation moves)
            }
        """
        if not self.ai_commentator:
            logger.warning("AI commentator not available, returning analysis without commentary")

        try:
            # Get position analysis from Stockfish
            analysis = self.stockfish.analyze_position(fen, depth=18, multipv=3)

            if not analysis or not analysis.get('pvs') or len(analysis['pvs']) == 0:
                logger.warning("No analysis available for position")
                return {
                    'success': False,
                    'error': 'No analysis available for this position'
                }

            # Get best move (first principal variation)
            best_pv = analysis['pvs'][0]
            best_move_san = best_pv.get('san_moves', [])[0] if best_pv.get('san_moves') else None
            evaluation_cp = best_pv.get('cp')
            evaluation_mate = best_pv.get('mate')
            pv_line = best_pv.get('san_moves', [])[:5]  # First 5 moves of best line

            if not best_move_san:
                return {
                    'success': False,
                    'error': 'Could not determine best move'
                }

            # Generate AI commentary if available
            commentary = None
            if self.ai_commentator:
                try:
                    commentary = self.ai_commentator.get_best_move_commentary(
                        fen=fen,
                        best_move=best_move_san,
                        evaluation_cp=evaluation_cp,
                        evaluation_mate=evaluation_mate,
                        pv_line=pv_line,
                        alternative_moves=None, # analysis['pvs'][1:3] Next 2 best moves
                        game_context=game_context
                    )
                except Exception as e:
                    logger.error(f"Failed to generate best move commentary: {e}", exc_info=True)
                    commentary = "Commentary generation failed"

            # Format evaluation text
            if evaluation_mate is not None:
                eval_text = f"Mate in {abs(evaluation_mate)}"
                eval_score = evaluation_mate
            elif evaluation_cp is not None:
                eval_text = f"{evaluation_cp / 100:+.2f}"
                eval_score = evaluation_cp / 100
            else:
                eval_text = "0.00"
                eval_score = 0

            return {
                'success': True,
                'best_move': best_move_san,
                'evaluation': eval_score,
                'evaluation_text': eval_text,
                'pv_line': pv_line,
                'commentary': commentary,
                'depth': analysis.get('depth', 18)
            }

        except Exception as e:
            logger.error(f"Error getting best move commentary: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
