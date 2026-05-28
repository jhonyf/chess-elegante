"""
Database models for Chess Elegante
"""
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Column, String, Integer, Text, DateTime, Boolean, JSON, func, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from flask_login import UserMixin
import uuid

db = SQLAlchemy()
Base = db.Model


class User(Base, UserMixin):
    """
    User model for authentication
    Supports OAuth providers (Google, Apple)
    """
    __tablename__ = 'users'

    id = Column(String(100), primary_key=True)  # UUID or OAuth provider ID
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255))
    picture = Column(String(500))  # Profile picture URL
    provider = Column(String(20), nullable=False)  # 'google' or 'apple'
    provider_id = Column(String(255), unique=True, nullable=False)  # ID from OAuth provider
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_login = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Admin privileges
    is_admin = Column(Boolean, default=False, nullable=False)

    # Relationships
    chess_games = relationship('ChessGame', back_populates='user', cascade='all, delete-orphan')

    def get_id(self):
        """Required by Flask-Login"""
        return str(self.id)

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'email': self.email,
            'name': self.name,
            'picture': self.picture,
            'provider': self.provider,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None,
        }


class ChessGame(Base):
    """
    Unified chess game model
    Stores all chess games (live and imported) with move analysis

    Move Format:
        All moves stored in unified format: [{"san": "e4", "uci": "e2e4"}, ...]
        Use move_utils.normalize_moves() to convert any format to this standard
    """
    __tablename__ = 'chess_games'

    id = Column(String(100), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(100), ForeignKey('users.id'), nullable=True, index=True)  # NULL for shared/anonymous
    name = Column(String(255))  # User-defined name or auto-generated

    # Core game data (all games)
    moves = Column(JSON, nullable=False)  # List of move dicts: [{"san": "e4", "uci": "e2e4"}]
    move_analysis = Column(JSON)  # Stockfish evaluations + AI commentary for each move

    # Game metadata (optional, richer for imported games)
    game_type = Column(String(20), nullable=False, index=True)  # 'live' or 'imported'
    result = Column(String(10))  # '1-0', '0-1', '1/2-1/2', '*'

    # Optional rich metadata (used by both live and imported games)
    white_player = Column(String(255))
    black_player = Column(String(255))
    white_elo = Column(Integer)
    black_elo = Column(Integer)
    event = Column(String(255))
    site = Column(String(255))
    game_date = Column(String(20))  # PGN date format (YYYY.MM.DD)
    opening = Column(String(255))
    eco = Column(String(10))  # ECO code

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Curated/Famous game fields
    is_curated = Column(Boolean, default=False, nullable=False, index=True)
    commentary_status = Column(String(20))  # 'pending', 'processing', 'completed', 'failed'
    commentary_generated_at = Column(DateTime)

    # Relationships
    user = relationship('User', back_populates='chess_games')
    live_state = relationship('LiveGameState', uselist=False, back_populates='game', cascade='all, delete-orphan')

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'moves': self.moves or [],
            'move_analysis': self.move_analysis,
            'game_type': self.game_type,
            'result': self.result,
            'white_player': self.white_player,
            'black_player': self.black_player,
            'white_elo': self.white_elo,
            'black_elo': self.black_elo,
            'event': self.event,
            'site': self.site,
            'game_date': self.game_date,
            'opening': self.opening,
            'eco': self.eco,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_curated': self.is_curated,
            'commentary_status': self.commentary_status,
            'commentary_generated_at': self.commentary_generated_at.isoformat() if self.commentary_generated_at else None,
        }

    def to_summary_dict(self):
        """Convert model to summary dictionary for lists"""
        return {
            'id': self.id,
            'name': self.name,
            'game_type': self.game_type,
            'white_player': self.white_player or 'Unknown',
            'black_player': self.black_player or 'Unknown',
            'result': self.result or '*',
            'event': self.event,
            'game_date': self.game_date,
            'opening': self.opening,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'move_count': len(self.moves) if self.moves else 0,
            'has_analysis': bool(self.move_analysis),
            'is_curated': self.is_curated,
            'commentary_status': self.commentary_status,
        }


class LiveGameState(Base):
    """
    Live game session state
    Tracks active games in progress (Lichess or local Stockfish)
    Can be deleted after game finishes (ChessGame persists)
    """
    __tablename__ = 'live_game_states'

    game_id = Column(String(100), ForeignKey('chess_games.id'), primary_key=True)

    # State version for conflict resolution
    version = Column(Integer, nullable=False, default=0)  # Incremented on each state change

    # Engine configuration
    engine_type = Column(String(20), nullable=False, default='lichess')  # 'lichess' or 'stockfish'
    lichess_game_id = Column(String(100), unique=True, index=True)  # NULL for stockfish games
    status = Column(String(20), nullable=False, index=True)  # 'started', 'finished', 'resigned', etc.
    player_color = Column(String(10), nullable=False)  # 'white' or 'black'
    ai_level = Column(Integer, nullable=False)  # 1-8 for lichess, 1-5 for stockfish
    current_fen = Column(Text)  # Current board position

    # Relationships
    game = relationship('ChessGame', back_populates='live_state')

    def to_dict(self):
        """Convert model to dictionary"""
        return {
            'game_id': self.game_id,
            'version': self.version,
            'engine_type': self.engine_type,
            'lichess_game_id': self.lichess_game_id,
            'status': self.status,
            'player_color': self.player_color,
            'ai_level': self.ai_level,
            'current_fen': self.current_fen,
        }
