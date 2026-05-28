"""
Unified move utilities for chess games
Provides consistent move format across live games and imported PGNs
"""
import chess
import chess.pgn
from typing import List, Dict, Union


class MoveFormat:
    """
    Unified move format utilities

    Standard move format: {"san": "e4", "uci": "e2e4"}
    - san: Standard Algebraic Notation (human-readable)
    - uci: Universal Chess Interface format (machine-readable)
    """

    @staticmethod
    def normalize_moves(moves: Union[List[str], List[Dict]]) -> List[Dict]:
        """
        Normalize moves to standard format

        Args:
            moves: List of moves in any format:
                - List of UCI strings: ["e2e4", "d7d5"]
                - List of dicts: [{"san": "e4", "uci": "e2e4"}]

        Returns:
            List of move dicts: [{"san": "e4", "uci": "e2e4"}]
        """
        if not moves:
            return []

        # Already in correct format
        if isinstance(moves[0], dict) and 'san' in moves[0] and 'uci' in moves[0]:
            return moves

        # Convert UCI strings to dict format
        if isinstance(moves[0], str):
            board = chess.Board()
            normalized = []

            for move_uci in moves:
                try:
                    move = chess.Move.from_uci(move_uci)
                    san = board.san(move)
                    normalized.append({
                        'san': san,
                        'uci': move_uci
                    })
                    board.push(move)
                except Exception:
                    # Invalid move, skip
                    continue

            return normalized

        # Unknown format, return as-is
        return moves

    @staticmethod
    def to_uci_list(moves: Union[List[str], List[Dict]]) -> List[str]:
        """
        Convert moves to UCI string list

        Args:
            moves: List of moves in any format

        Returns:
            List of UCI strings: ["e2e4", "d7d5"]
        """
        if not moves:
            return []

        # Already UCI strings
        if isinstance(moves[0], str):
            return moves

        # Extract UCI from dict format
        if isinstance(moves[0], dict):
            return [m.get('uci', '') for m in moves if m.get('uci')]

        return []

    @staticmethod
    def to_san_list(moves: Union[List[str], List[Dict]]) -> List[str]:
        """
        Convert moves to SAN string list

        Args:
            moves: List of moves in any format

        Returns:
            List of SAN strings: ["e4", "d5"]
        """
        if not moves:
            return []

        # Extract SAN from dict format
        if isinstance(moves[0], dict) and 'san' in moves[0]:
            return [m['san'] for m in moves]

        # Convert UCI to SAN
        if isinstance(moves[0], str):
            board = chess.Board()
            san_list = []

            for move_uci in moves:
                try:
                    move = chess.Move.from_uci(move_uci)
                    san = board.san(move)
                    san_list.append(san)
                    board.push(move)
                except Exception:
                    continue

            return san_list

        return []

    @staticmethod
    def parse_uci_string(moves_str: str) -> List[Dict]:
        """
        Parse space-separated UCI string into standard format

        Args:
            moves_str: Space-separated UCI moves "e2e4 d7d5 e4e5"

        Returns:
            List of move dicts: [{"san": "e4", "uci": "e2e4"}]
        """
        if not moves_str or not moves_str.strip():
            return []

        uci_list = moves_str.strip().split()
        return MoveFormat.normalize_moves(uci_list)

    @staticmethod
    def parse_pgn_moves(pgn_game: chess.pgn.Game) -> List[Dict]:
        """
        Parse moves from a chess.pgn.Game object

        Args:
            pgn_game: chess.pgn.Game object

        Returns:
            List of move dicts: [{"san": "e4", "uci": "e2e4"}]
        """
        moves = []
        board = pgn_game.board()

        for move in pgn_game.mainline_moves():
            san = board.san(move)
            uci = move.uci()
            moves.append({
                'san': san,
                'uci': uci
            })
            board.push(move)

        return moves

    @staticmethod
    def replay_moves(moves: Union[List[str], List[Dict]],
                     start_fen: str = None) -> chess.Board:
        """
        Replay moves on a board and return final position

        Args:
            moves: List of moves in any format
            start_fen: Optional starting FEN (default: starting position)

        Returns:
            chess.Board with final position
        """
        board = chess.Board(start_fen) if start_fen else chess.Board()
        uci_moves = MoveFormat.to_uci_list(moves)

        for move_uci in uci_moves:
            try:
                move = chess.Move.from_uci(move_uci)
                board.push(move)
            except Exception:
                # Invalid move, stop replaying
                break

        return board

    @staticmethod
    def get_position_at_move(moves: Union[List[str], List[Dict]],
                            move_index: int,
                            start_fen: str = None) -> str:
        """
        Get FEN position after a specific move

        Args:
            moves: List of moves in any format
            move_index: Index of move (0-based)
            start_fen: Optional starting FEN

        Returns:
            FEN string of position after move_index
        """
        board = chess.Board(start_fen) if start_fen else chess.Board()
        uci_moves = MoveFormat.to_uci_list(moves)

        for i, move_uci in enumerate(uci_moves):
            if i > move_index:
                break
            try:
                move = chess.Move.from_uci(move_uci)
                board.push(move)
            except Exception:
                break

        return board.fen()


# Convenience functions
def normalize_moves(moves):
    """Shorthand for MoveFormat.normalize_moves()"""
    return MoveFormat.normalize_moves(moves)


def to_uci_list(moves):
    """Shorthand for MoveFormat.to_uci_list()"""
    return MoveFormat.to_uci_list(moves)


def to_san_list(moves):
    """Shorthand for MoveFormat.to_san_list()"""
    return MoveFormat.to_san_list(moves)


def create_move_analysis_entry(move_number: int, move_san: str, move_uci: str,
                                 player: str, evaluation: dict = None,
                                 commentary: str = None) -> dict:
    """
    Create a standardized move analysis entry

    Args:
        move_number: The move number (1, 2, 3, etc.)
        move_san: Move in SAN format (e.g., "e4", "Nf3")
        move_uci: Move in UCI format (e.g., "e2e4", "g1f3")
        player: 'White' or 'Black'
        evaluation: Optional evaluation data from Stockfish
        commentary: Optional AI commentary text

    Returns:
        Standardized move analysis dict
    """
    return {
        'move_number': move_number,
        'move_san': move_san,
        'move_uci': move_uci,
        'player': player,
        'evaluation': evaluation,
        'commentary': commentary
    }
