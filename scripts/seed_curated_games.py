"""
Seed curated chess games from YAML file.

This script reads curated_games.yaml which contains pre-selected classical games
with static UUIDs for SEO purposes. Each game is seeded with its fixed UUID.

Usage:
    python seed_curated_games.py           # Seed all games
    python seed_curated_games.py --list    # List all curated games in DB
"""

import os
import sys
import yaml
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from database.models import ChessGame
from core.move_utils import MoveFormat
from datetime import datetime
import chess
import chess.pgn
from io import StringIO

# Get database URL from environment
DATABASE_URL = os.environ.get('DATABASE_URL')
if not DATABASE_URL:
    print("Error: DATABASE_URL environment variable not set")
    sys.exit(1)

# Create database connection
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()


def parse_pgn_moves(pgn_text):
    """
    Parse PGN text and extract moves in UCI format.

    Args:
        pgn_text: PGN game string

    Returns:
        list: List of UCI move strings
    """
    try:
        pgn_io = StringIO(pgn_text)
        game = chess.pgn.read_game(pgn_io)
        if not game:
            return []

        return MoveFormat.parse_pgn_moves(game)
    except Exception as e:
        print(f"Error parsing PGN: {e}")
        return []


def seed_games():
    """Load games from YAML and seed into database"""

    yaml_path = os.path.join(PROJECT_ROOT, 'seed_data', 'curated_games.yaml')

    if not os.path.exists(yaml_path):
        print(f"Error: YAML file not found at {yaml_path}")
        return

    print(f"Reading curated games from {yaml_path}")

    with open(yaml_path, 'r') as f:
        data = yaml.safe_load(f)

    games_data = data.get('games', [])
    if not games_data:
        print("No games found in YAML file")
        return

    print(f"Found {len(games_data)} games to seed")
    print()

    game_count = 0
    skipped_count = 0

    for game_data in games_data:
        uuid = game_data.get('uuid')
        opening = game_data.get('opening', 'Unknown Opening')
        white = game_data.get('white', 'Unknown')
        black = game_data.get('black', 'Unknown')
        event = game_data.get('event', 'Unknown Event')
        site = game_data.get('site', 'Unknown')
        date = game_data.get('date', '????.??.??')
        result = game_data.get('result', '*')
        eco = game_data.get('eco', '')
        white_elo = game_data.get('white_elo')
        black_elo = game_data.get('black_elo')
        pgn_text = game_data.get('pgn', '')

        if not uuid:
            print(f"Warning: Skipping game without UUID: {white} vs {black}")
            continue

        # Check if game already exists
        existing_game = session.query(ChessGame).filter_by(id=uuid).first()
        if existing_game:
            print(f"✓ Exists: {white} vs {black} ({opening}) [UUID: {uuid}]")
            skipped_count += 1
            continue

        # Parse moves from PGN
        moves = parse_pgn_moves(pgn_text)
        if not moves:
            print(f"✗ Error: No moves found for {white} vs {black}")
            continue

        # Generate name
        name = f"{white} vs {black} ({event}, {date})"

        # Create ChessGame record
        chess_game = ChessGame(
            id=uuid,
            user_id=None,  # Curated games are not user-owned
            name=name,
            moves=moves,
            move_analysis=None,  # No analysis yet
            game_type='imported',
            result=result,
            white_player=white,
            black_player=black,
            white_elo=white_elo,
            black_elo=black_elo,
            event=event,
            site=site,
            game_date=date,
            opening=opening,
            eco=eco,
            is_curated=True,
            commentary_status='pending',
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        session.add(chess_game)
        game_count += 1

        print(f"+ Added: {white} vs {black} ({opening}) [UUID: {uuid}]")

    # Commit all games
    try:
        session.commit()
        print()
        print("="*80)
        print(f"✓ Successfully seeded {game_count} new games!")
        print(f"  {skipped_count} games already existed in database")
        print(f"  Total curated games: {game_count + skipped_count}")
        print("="*80)
    except Exception as e:
        session.rollback()
        print()
        print(f"✗ Error seeding games: {e}")
        raise
    finally:
        session.close()


def list_curated_games():
    """List all curated games in the database (grouped by opening)"""
    curated_games = session.query(ChessGame).filter_by(is_curated=True).order_by(ChessGame.opening, ChessGame.white_player).all()

    print("="*80)
    print(f"CURATED GAMES IN DATABASE ({len(curated_games)} total)")
    print("="*80)
    print()

    # Group by opening
    games_by_opening = {}
    for game in curated_games:
        opening = game.opening or 'Unknown'
        if opening not in games_by_opening:
            games_by_opening[opening] = []
        games_by_opening[opening].append(game)

    for opening in sorted(games_by_opening.keys()):
        games = games_by_opening[opening]
        print(f"{opening} ({len(games)} games):")
        print("-" * 80)
        for game in games:
            print(f"  {game.white_player} vs {game.black_player}")
            print(f"    Event:  {game.event} ({game.game_date})")
            print(f"    Result: {game.result}")
            print(f"    UUID:   {game.id}")
            print(f"    URL:    /analyze/{game.id}")
            print()

    session.close()


def main():
    print("="*80)
    print("CURATED CHESS GAMES SEEDER")
    print("="*80)
    print()

    if len(sys.argv) > 1 and sys.argv[1] == '--list':
        list_curated_games()
    else:
        # Check if there are already curated games
        existing_count = session.query(ChessGame).filter_by(is_curated=True).count()

        if existing_count > 0:
            print(f"Found {existing_count} curated games already in the database.")
            print("This script will skip existing games and only add new ones.")
            print()
            response = input("Continue? (y/n): ")
            if response.lower() != 'y':
                print("Aborted.")
                session.close()
                sys.exit(0)

        seed_games()
        print()
        print("To view all curated games, run: python seed_curated_games.py --list")


if __name__ == '__main__':
    main()
