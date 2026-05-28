import os
from anthropic import Anthropic
from openai import OpenAI
import chess
import logging

logger = logging.getLogger(__name__)


# Prompt templates
SYSTEM_PROMPT = """You are Irving Chernev, author of "Logical Chess: Move by Move."
You write concise, 2–3 sentence commentary focusing on clarity,
logic, and education. Be direct but constructive."""


def build_single_move_prompt(fen, move_san, turn, context):
    """Build user prompt for single move commentary"""
    return f"""Position (FEN): {fen}
Move played: {move_san}
Turn: {turn}

Context:
{context}

Provide the commentary."""


def build_batch_moves_prompt(moves_info):
    """Build user prompt for batch move commentary"""
    return f"""{SYSTEM_PROMPT}

You are analyzing a complete chess game and providing commentary for each move.

Below is information about {len(moves_info)} moves from a chess game.

IMPORTANT: Separate each move's commentary with exactly this delimiter on its own line:
==MOVE_SEPARATOR==

Here are the moves:

{chr(10).join([f"--- Move {i+1} ---{chr(10)}{info}" for i, info in enumerate(moves_info)])}

Now provide commentary, separated by ==MOVE_SEPARATOR=="""


def build_best_move_prompt(fen, best_move, turn, context):
    """Build user prompt for best move commentary"""
    return f"""Position (FEN): {fen}
Turn: {turn}
Best move to play: {best_move}

Context:
{context}

Explain why {best_move} is the best move in this position. Focus on the key reasons: tactical opportunities, strategic goals, or critical threats it addresses."""


BEST_MOVE_SYSTEM_PROMPT = """You are Irving Chernev, author of "Logical Chess: Move by Move."
You write concise, 2–3 sentence commentary focusing on clarity, logic, and education.
Be direct but constructive. Explain WHY this move is best, considering tactics, strategy, and key principles."""


class AICommentator:
    def __init__(self):
        """
        Initialize AI Commentator
        api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
        """
        #self.api_key =  os.getenv('ANTHROPIC_API_KEY')
        self.api_key =  os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            logger.error("Anthropic API key not found")
            raise Exception("Anthropic API key not found. Set ANTHROPIC_API_KEY environment variable.")

        self.client = OpenAI(api_key=self.api_key) # Anthropic(api_key=self.api_key)
        logger.info("AICommentator initialized successfully")

    def get_move_commentary(self, fen, move_san, evaluation_data, board_state=None):
        """
        Get AI commentary on a move

        Args:
            fen: FEN string of position before the move
            move_san: Move in SAN notation (e.g., 'e4', 'Nf3')
            evaluation_data: Dict with evaluation info (classification, eval_loss, best_move, etc.)
            board_state: Optional dict with game context (move number, material, etc.)

        Returns:
            str: AI-generated commentary
        """
        board = chess.Board(fen)
        context = self._build_move_context(board, move_san, evaluation_data)
        turn = "White" if board.turn else "Black"
        user_prompt = build_single_move_prompt(fen, move_san, turn, context)

        classification = evaluation_data.get('classification', 'unknown')

        try:
            logger.info(f"Requesting AI commentary for move: {move_san} (classification: {classification})")
            logger.debug(f"Using model: gpt-5.1")
            logger.debug(f"Prompt: {user_prompt}")

            response = self.client.responses.create(
                model="gpt-5.1",
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]
            )

            commentary = response.output_text
            logger.info(f"AI commentary generated successfully (length: {len(commentary)} chars)")
            logger.debug(f"Commentary: {commentary}")
            return commentary

        except Exception as e:
            logger.error(f"Failed to generate AI commentary: {str(e)}", exc_info=True)
            return f"Unable to generate commentary: {str(e)}"

    def get_batch_commentary(self, moves_data):
        """
        Get AI commentary for multiple moves in a single API call

        Args:
            moves_data: List of dicts, each containing:
                - move_number: int
                - move_san: str (e.g., 'e4', 'Nf3')
                - player: str ('White' or 'Black')
                - evaluation_data: dict with evaluation info
                - fen_before: FEN string before the move

        Returns:
            list: List of commentary strings, one per move
        """
        if not moves_data:
            return []

        # Build formatted move info for each move
        moves_info = []
        for move_data in moves_data:
            move_number = move_data['move_number']
            move_san = move_data['move_san']
            player = move_data['player']
            eval_data = move_data['evaluation_data']
            fen = move_data['fen_before']

            board = chess.Board(fen)
            context = self._build_move_context(board, move_san, eval_data)

            move_info = f"""Move {move_number}. {move_san} ({player})
FEN: {fen}
Turn: {player}

Context:
{context}"""
            moves_info.append(move_info)

        # Use the shared prompt builder
        user_prompt = build_batch_moves_prompt(moves_info)

        try:
            logger.info(f"Requesting batch AI commentary for {len(moves_data)} moves")
            logger.debug(f"Using model: gpt-5.1")

            response = self.client.responses.create(
                model="gpt-5.1",
                input=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]
            )

            full_commentary = response.output_text
            logger.debug(f"Batch commentary received (length: {len(full_commentary)} chars)")

            commentaries = [c.strip() for c in full_commentary.split('==MOVE_SEPARATOR==')]
            logger.info(f"Batch commentary parsed into {len(commentaries)} segments")

            # Ensure we have the right number of commentaries
            while len(commentaries) < len(moves_data):
                logger.warning(f"Missing commentary for move {len(commentaries) + 1}, adding placeholder")
                commentaries.append("Commentary not available")

            logger.info(f"Batch commentary generation complete for {len(moves_data)} moves")
            return commentaries[:len(moves_data)]

        except Exception as e:
            logger.error(f"Failed to generate batch commentary: {str(e)}", exc_info=True)
            return [f"Unable to generate commentary: {str(e)}"] * len(moves_data)

    def get_best_move_commentary(self, fen, best_move, evaluation_cp=None, evaluation_mate=None,
                                   pv_line=None, alternative_moves=None, game_context=None):
        """
        Get AI commentary explaining why a move is the best in the position

        Args:
            fen: Position FEN string
            best_move: Best move in SAN notation
            evaluation_cp: Centipawn evaluation (or None)
            evaluation_mate: Mate score (or None)
            pv_line: List of continuation moves
            alternative_moves: List of alternative PVs
            game_context: Optional dict with game context

        Returns:
            str: AI-generated commentary
        """
        board = chess.Board(fen)
        turn = "White" if board.turn else "Black"
        context = self._build_best_move_context(
            board, best_move, evaluation_cp, evaluation_mate,
            pv_line, alternative_moves, game_context
        )
        user_prompt = build_best_move_prompt(fen, best_move, turn, context)

        try:
            logger.info(f"Requesting AI commentary for best move: {best_move}")
            response = self.client.responses.create(
                model="gpt-5.1",
                input=[
                    {"role": "system", "content": BEST_MOVE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt}
                ]
            )
            return response.output_text.strip()
        except Exception as e:
            logger.error(f"Failed to generate best move commentary: {e}", exc_info=True)
            return f"Unable to generate commentary: {str(e)}"

    def _build_best_move_context(self, board, best_move, evaluation_cp, evaluation_mate,
                                  pv_line, alternative_moves, game_context):
        """Build context string for best move commentary"""
        context_parts = []

        # Material count
        context_parts.append(self._get_material_context(board))

        # Evaluation
        if evaluation_mate is not None:
            turn = "White" if board.turn else "Black"
            context_parts.append(f"Position: Mate in {abs(evaluation_mate)} for {turn}")
        elif evaluation_cp is not None:
            eval_pawns = evaluation_cp / 100
            context_parts.append(f"Position evaluation: {eval_pawns:+.2f} pawns")

        # Best move and continuation
        context_parts.append(f"Best move: {best_move}")
        if pv_line and len(pv_line) > 1:
            context_parts.append(f"Best continuation: {' '.join(pv_line)}")

        # Alternative moves
        if alternative_moves:
            alt_moves = []
            for pv in alternative_moves[:2]:
                san_moves = pv.get('san_moves', [])
                if san_moves:
                    cp = pv.get('cp')
                    if cp is not None:
                        alt_moves.append(f"{san_moves[0]} ({cp/100:+.2f})")
                    else:
                        alt_moves.append(san_moves[0])
            if alt_moves:
                context_parts.append(f"Alternative moves: {', '.join(alt_moves)}")

        # Game context if provided
        if game_context:
            move_number = game_context.get('move_number')
            if move_number:
                context_parts.append(f"Move number: {move_number}")

        return "\n".join(context_parts)

    def _get_material_context(self, board):
        """Get material balance description"""
        white_material = self._count_material(board, chess.WHITE)
        black_material = self._count_material(board, chess.BLACK)
        material_diff = white_material - black_material

        if material_diff > 0:
            return f"White is up {material_diff} points of material."
        elif material_diff < 0:
            return f"Black is up {abs(material_diff)} points of material."
        else:
            return "Material is equal."

    def _build_move_context(self, board, move_san, evaluation_data):
        """Build context string for a move"""
        context_parts = []

        # Material count
        context_parts.append(self._get_material_context(board))

        # Position evaluation
        eval_before = evaluation_data.get('evaluation_before', 0)
        eval_after = evaluation_data.get('evaluation_after', 0)
        eval_loss = evaluation_data.get('eval_loss', 0)
        classification = evaluation_data.get('classification', 'unknown')
        best_move = evaluation_data.get('best_move')

        # Convert evaluation to pawns
        eval_before_pawns = eval_before / 100
        eval_after_pawns = eval_after / 100
        eval_loss_pawns = eval_loss / 100

        context_parts.append(f"Position evaluation before move: {eval_before_pawns:+.2f} pawns")
        context_parts.append(f"Position evaluation after {move_san}: {eval_after_pawns:+.2f} pawns")
        context_parts.append(f"Evaluation loss: {eval_loss_pawns:.2f} pawns")
        context_parts.append(f"Move classification: {classification}")

        if best_move:
            context_parts.append(f"Best move was: {best_move}")

        return "\n".join(context_parts)

    def _count_material(self, board, color):
        """Count material value for a given color"""
        piece_values = {
            chess.PAWN: 1,
            chess.KNIGHT: 3,
            chess.BISHOP: 3,
            chess.ROOK: 5,
            chess.QUEEN: 9,
            chess.KING: 0
        }

        total = 0
        for piece_type in piece_values:
            total += len(board.pieces(piece_type, color)) * piece_values[piece_type]

        return total
