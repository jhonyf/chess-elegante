import json
import os
from datetime import datetime
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class GameStorage:
    """Simple file-based storage for chess games and PGNs"""

    def __init__(self, storage_dir='games'):
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(exist_ok=True)
        self.pgn_dir = self.storage_dir / 'pgns'
        self.pgn_dir.mkdir(exist_ok=True)
        self.index_file = self.storage_dir / 'index.json'
        self.pgn_index_file = self.pgn_dir / 'pgn_index.json'
        logger.info(f"Initializing GameStorage with directory: {self.storage_dir}")
        self._ensure_index()
        self._ensure_pgn_index()

    def _ensure_index(self):
        """Create index file if it doesn't exist"""
        if not self.index_file.exists():
            self.index_file.write_text(json.dumps([]))

    def _ensure_pgn_index(self):
        """Create PGN index file if it doesn't exist"""
        if not self.pgn_index_file.exists():
            self.pgn_index_file.write_text(json.dumps([]))

    def save_game(self, game_id, game_data):
        """
        Save a game to storage

        Args:
            game_id: Unique game identifier
            game_data: Dict with game information
                - fen: Current board position
                - moves: List of moves in UCI format
                - status: Game status (started, finished, resigned, etc.)
                - created_at: Timestamp when game was created
                - updated_at: Timestamp of last update
                - player_color: Color player is playing (white/black)
                - ai_level: AI difficulty level
        """
        logger.info(f"Saving game: {game_id} (status: {game_data.get('status')}, moves: {len(game_data.get('moves', []))})")
        game_file = self.storage_dir / f'{game_id}.json'

        # Add metadata
        if 'created_at' not in game_data:
            game_data['created_at'] = datetime.now().isoformat()
        game_data['updated_at'] = datetime.now().isoformat()
        game_data['game_id'] = game_id

        # Save game file
        game_file.write_text(json.dumps(game_data, indent=2))
        logger.debug(f"Game file written: {game_file}")

        # Update index
        self._update_index(game_id, game_data)

    def _update_index(self, game_id, game_data):
        """Update the index with game metadata"""
        index = self.load_index()

        # Remove existing entry if present
        index = [g for g in index if g['game_id'] != game_id]

        # Add new entry with summary info
        index.append({
            'game_id': game_id,
            'status': game_data.get('status', 'unknown'),
            'created_at': game_data.get('created_at'),
            'updated_at': game_data.get('updated_at'),
            'move_count': len(game_data.get('moves', [])),
            'ai_level': game_data.get('ai_level', 1),
            'player_color': game_data.get('player_color', 'white')
        })

        # Sort by updated_at (most recent first)
        index.sort(key=lambda x: x['updated_at'], reverse=True)

        self.index_file.write_text(json.dumps(index, indent=2))

    def load_game(self, game_id):
        """Load a game from storage"""
        logger.info(f"Loading game: {game_id}")
        game_file = self.storage_dir / f'{game_id}.json'

        if not game_file.exists():
            logger.warning(f"Game file not found: {game_id}")
            return None

        game_data = json.loads(game_file.read_text())
        logger.debug(f"Game loaded: {game_id} (moves: {len(game_data.get('moves', []))})")
        return game_data

    def load_index(self):
        """Load the game index"""
        if not self.index_file.exists():
            return []

        return json.loads(self.index_file.read_text())

    def list_games(self, status=None):
        """
        List all games, optionally filtered by status

        Args:
            status: Optional status filter (started, finished, resigned)

        Returns:
            List of game summaries
        """
        index = self.load_index()

        if status:
            index = [g for g in index if g['status'] == status]

        return index

    def delete_game(self, game_id):
        """Delete a game from storage"""
        game_file = self.storage_dir / f'{game_id}.json'

        if game_file.exists():
            game_file.unlink()

        # Update index
        index = self.load_index()
        index = [g for g in index if g['game_id'] != game_id]
        self.index_file.write_text(json.dumps(index, indent=2))

    # PGN Storage Methods

    def save_pgn(self, pgn_id, pgn_data):
        """
        Save a PGN to storage

        Args:
            pgn_id: Unique PGN identifier
            pgn_data: Dict with PGN information
                - pgn_text: Original PGN text
                - headers: Dict of PGN headers
                - moves: List of moves
                - name: User-provided name for the PGN
        """
        logger.info(f"Saving PGN: {pgn_id} (name: {pgn_data.get('name')}, moves: {len(pgn_data.get('moves', []))})")
        pgn_file = self.pgn_dir / f'{pgn_id}.json'

        # Add metadata
        if 'created_at' not in pgn_data:
            pgn_data['created_at'] = datetime.now().isoformat()
        pgn_data['updated_at'] = datetime.now().isoformat()
        pgn_data['pgn_id'] = pgn_id

        # Save PGN file
        pgn_file.write_text(json.dumps(pgn_data, indent=2))
        logger.debug(f"PGN file written: {pgn_file}")

        # Update index
        self._update_pgn_index(pgn_id, pgn_data)

    def _update_pgn_index(self, pgn_id, pgn_data):
        """Update the PGN index with metadata"""
        index = self.load_pgn_index()

        # Remove existing entry if present
        index = [p for p in index if p['pgn_id'] != pgn_id]

        # Extract display info
        headers = pgn_data.get('headers', {})
        white = headers.get('White', 'Unknown')
        black = headers.get('Black', 'Unknown')
        event = headers.get('Event', 'Unknown Event')

        # Add new entry with summary info
        index.append({
            'pgn_id': pgn_id,
            'name': pgn_data.get('name', f'{white} vs {black}'),
            'white': white,
            'black': black,
            'event': event,
            'result': headers.get('Result', '*'),
            'date': headers.get('Date', '????.??.??'),
            'created_at': pgn_data.get('created_at'),
            'updated_at': pgn_data.get('updated_at'),
            'move_count': len(pgn_data.get('moves', [])),
            'has_commentary': bool(pgn_data.get('move_analysis'))
        })

        # Sort by updated_at (most recent first)
        index.sort(key=lambda x: x['updated_at'], reverse=True)

        self.pgn_index_file.write_text(json.dumps(index, indent=2))

    def load_pgn(self, pgn_id):
        """Load a PGN from storage"""
        logger.info(f"Loading PGN: {pgn_id}")
        pgn_file = self.pgn_dir / f'{pgn_id}.json'

        if not pgn_file.exists():
            logger.warning(f"PGN file not found: {pgn_id}")
            return None

        pgn_data = json.loads(pgn_file.read_text())
        logger.debug(f"PGN loaded: {pgn_id} (moves: {len(pgn_data.get('moves', []))})")
        return pgn_data

    def load_pgn_index(self):
        """Load the PGN index"""
        if not self.pgn_index_file.exists():
            return []

        return json.loads(self.pgn_index_file.read_text())

    def list_pgns(self):
        """
        List all saved PGNs

        Returns:
            List of PGN summaries
        """
        return self.load_pgn_index()

    def delete_pgn(self, pgn_id):
        """Delete a PGN from storage"""
        logger.info(f"Deleting PGN: {pgn_id}")
        pgn_file = self.pgn_dir / f'{pgn_id}.json'

        if pgn_file.exists():
            pgn_file.unlink()
            logger.debug(f"PGN file deleted: {pgn_file}")
        else:
            logger.warning(f"PGN file not found for deletion: {pgn_id}")

        # Update index
        index = self.load_pgn_index()
        index = [p for p in index if p['pgn_id'] != pgn_id]
        self.pgn_index_file.write_text(json.dumps(index, indent=2))
        logger.info(f"PGN deleted and index updated: {pgn_id}")
