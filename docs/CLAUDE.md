# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Chess Elegante is a Flask-based web application for playing chess against AI opponents and analyzing games. It integrates with the Lichess Board API to play against Stockfish AI, uses a local Stockfish engine for position analysis and move evaluation, provides PGN analysis and navigation, and optionally provides AI-powered move commentary via the Anthropic API.

## Code Preferences

## Working Style
- Make code changes directly without testing
- Don't try to run test, run server, run commands in bash, instead ask me to perform it and wait
- Focus on efficient, token-conscious responses, reduce verbose summary at the end
- Be concise and Skip unnecessary explanations unless asked

## Development Commands

### Setup
```bash
# Create and activate virtual environment
python -m venv venv
source venv/bin/activate  # On macOS/Linux
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env to add:
# - DATABASE_URL: PostgreSQL connection string
# - LICHESS_API_TOKEN (required): Get from https://lichess.org/account/oauth/token
# - GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET: For OAuth
# - ANTHROPIC_API_KEY (optional): For AI commentary feature
# - SECRET_KEY (optional): Auto-generated if not set

# Set up database (PostgreSQL)
docker-compose up -d  # Start PostgreSQL in Docker

# Initialize database and migrations
flask db init            # Set up Flask-Migrate
flask db migrate -m "Initial migration"
flask db upgrade
```

### Running the Application
```bash
# Start the Flask development server
python app.py

# Server runs on http://localhost:5000
```

### Database Migrations
```bash
# Add new field to model (edit models.py)
# Generate migration
flask db migrate -m "Add field description"

# Review migration
cat migrations/versions/[latest].py

# Apply migration
flask db upgrade

# Rollback migration
flask db downgrade
```

### Testing
```bash
# Test Stockfish engine integration
python test_stockfish.py
```

## Architecture

### Multi-Engine Design

The application uses **two separate chess engines** for different purposes:

1. **Lichess Stockfish AI** (`lichess_client.py`)
   - Remote engine accessed via Lichess Board API
   - Used as the opponent that the player plays against
   - Handles game creation, move execution, and game state synchronization
   - Player always plays as White

2. **Local Stockfish Engine** (`stockfish_engine.py`)
   - Local engine for analysis and move evaluation
   - Used to analyze positions and evaluate player moves in real-time
   - Provides multi-PV analysis (multiple principal variations)
   - Calculates move quality (best, excellent, good, inaccuracy, mistake, blunder)

### Core Components

**Flask Application** (`app.py`)
- Main entry point and API server
- Routes for game management (`/api/new-game`, `/api/make-move`, `/api/game-state`)
- Analysis endpoints (`/api/analyze-position`, `/api/evaluate-move`)
- Session-based game tracking with file-based persistence

**Game State Management**
- Active games stored in memory (`games` dict) for current session
- Persistent storage via `GameStorage` class (file-based in `games/` directory)
- Each game stored as JSON with FEN, moves list (UCI format), status, AI level
- Index file tracks all games with metadata (move count, timestamps, status)

**Move Evaluation Pipeline** (`stockfish_engine.py:187-320`)
- Evaluates player moves by comparing to engine's best move
- Critical evaluation logic:
  - Analyzes position BEFORE move to find best continuation
  - Analyzes position AFTER move to get resulting evaluation
  - Both evaluations converted to player's perspective (White or Black)
  - Evaluation loss = difference between best and actual move
  - Classification thresholds: <50cp=excellent, <100cp=good, <200cp=inaccuracy, <400cp=mistake, >=400cp=blunder
- Detects hanging pieces by checking if opponent can capture moved piece

**AI Commentary** (`ai_commentator.py`)
- Optional feature (requires ANTHROPIC_API_KEY)
- Generates Irving Chernev-style move commentary
- Uses Claude Haiku model for fast, educational explanations
- Considers material balance, position evaluation, and move classification
- Integrated into move evaluation workflow (`app.py:346-356`)

**Frontend Architecture** (`static/js/game.js`)
- Chess.js for game logic and move validation
- Chessboard.js for interactive board UI
- Player always controls White pieces (drag-and-drop)
- Polling mechanism (2-second intervals) checks for opponent moves via `/api/game-state`
- Automatic move evaluation on player moves with visual feedback
- Real-time position analysis available via "Analyze" button

**PGN Analysis Feature** (`templates/analyze.html`, `static/js/analyze.js`)
- Standalone page for analyzing chess games from PGN files
- PGN upload via text paste or file upload
- Full move navigation (forward/backward, first/last, click on moves)
- Keyboard shortcuts (arrow keys, Home/End)
- Save/load PGN functionality with persistent storage
- Two-phase UI: Upload section → Game analysis view
- Displays game metadata (players, event, date, opening, ratings, result)
- Non-interactive board (analysis only, no move input)

**Database and Persistence** (`models.py`, `game_storage.py`)
- PostgreSQL database for persistent storage
- SQLAlchemy ORM with three main models: `User`, `Game`, `PGN`
- Flask-Migrate for database migrations and schema updates
- User authentication via OAuth (Google, Apple)
- Games linked to users via foreign key relationships
- PGNs can be user-owned or shared (nullable user_id)

**Database Migrations** (Flask-Migrate)
- Flask-Migrate manages schema changes over time
- Migration workflow:
  1. Update `models.py` with new fields
  2. Generate migration: `flask db migrate -m "Description"`
  3. Review migration in `migrations/versions/`
  4. Apply migration: `flask db upgrade`
- Never use `Base.metadata.create_all()` after initial setup
- Always use Flask-Migrate for schema changes in production
- See `docs/MIGRATIONS.md` for detailed guide

### Data Flow

#### Play Mode
1. **New Game**: Client requests game → Flask creates Lichess AI challenge → Game ID stored in session → Board initialized
2. **Player Move**: Drag piece → Validate with Chess.js → POST to `/api/make-move` → Lichess API → Evaluate move with local Stockfish → Display evaluation
3. **Opponent Move**: Poll `/api/game-state` → Parse Lichess stream → Replay all moves → Update board position
4. **Analysis**: "Analyze" button → POST current FEN to `/api/analyze-position` → Local Stockfish multi-PV analysis → Display top variations

#### Analyze Mode
1. **Upload PGN**: User pastes/uploads PGN → POST to `/api/parse-pgn` → Parse with `chess.pgn` → Return headers and moves
2. **Navigate Game**: User clicks move/arrow key → Replay moves from start to selected position → Update board FEN → Highlight active move
3. **Save PGN**: User clicks "Save PGN" → Modal opens with auto-filled name → POST to `/api/save-pgn` → Store in `games/pgns/`
4. **Load Saved PGN**: User clicks "Saved PGNs" → GET `/api/pgns` → Display list → Click "Load" → GET `/api/pgn/<id>` → Parse and display game

### Important Implementation Details

**Stockfish Path Detection** (`stockfish_engine.py:37-49`)
- Auto-detects Stockfish in common locations: `/opt/homebrew/bin/stockfish`, `/usr/local/bin/stockfish`, `/usr/bin/stockfish`
- Requires Stockfish to be installed (Homebrew on macOS: `brew install stockfish`)

**Move Format Conversions**
- Lichess API uses UCI format (e.g., "e2e4")
- Chess.js uses both UCI and SAN
- Frontend displays SAN with Unicode pieces (♔♕♖♗♘♙)
- Stockfish engine works with UCI but returns SAN for display
- PGN parsing uses `chess.pgn.read_game()` from python-chess library

**Session and Authentication**
- Flask-Login manages user sessions
- OAuth authentication via Google and Apple
- Session stores current user ID
- Games and PGNs linked to authenticated users
- Active game state cached in memory for performance
- Database provides persistent storage across sessions

**Evaluation Perspective** (`stockfish_engine.py:246-256`)
- Stockfish always returns evaluations from White's perspective
- Code converts to player's perspective for accurate loss calculation
- Critical for correct move classification (Black wants negative scores)

## Key Files

### Backend
- `app.py` - Main Flask application and API routes (play, analyze, PGN endpoints)
- `models.py` - SQLAlchemy database models (User, Game, PGN)
- `lichess_client.py` - Lichess Board API client (opponent engine)
- `stockfish_engine.py` - Local Stockfish integration for analysis
- `ai_commentator.py` - Anthropic API integration for move commentary
- `game_storage.py` - Database persistence layer (extends SQLAlchemy models)

### Frontend - Play Mode
- `templates/play.html` - Main chess game interface
- `static/js/game.js` - Frontend game logic and board interaction
- `static/css/play.css` - Play page specific styles

### Frontend - Analyze Mode
- `templates/analyze.html` - PGN analysis interface
- `static/js/analyze.js` - PGN parsing, navigation, save/load logic
- `static/css/analyze.css` - Analyze page specific styles

### Shared
- `templates/home.html` - Landing page
- `templates/games.html` - Game history browser
- `static/css/main.css` - Shared base styles
- `static/css/board-themes.css` - Chess board theme definitions

### Database & Migrations
- `models.py` - SQLAlchemy ORM models
- `migrations/` - Flask-Migrate migration files and configuration
- `docs/MIGRATIONS.md` - Database migration guide

## Environment Variables

Required:
- `DATABASE_URL` - PostgreSQL connection string (e.g., `postgresql://user:pass@host:5432/dbname`)
- `LICHESS_API_TOKEN` - Lichess API token with `board:play` scope
- `GOOGLE_CLIENT_ID` - Google OAuth client ID
- `GOOGLE_CLIENT_SECRET` - Google OAuth client secret

Optional:
- `APPLE_CLIENT_ID` - Apple OAuth client ID (for Sign in with Apple)
- `APPLE_CLIENT_SECRET` - Apple OAuth client secret
- `ANTHROPIC_API_KEY` - Enables AI-powered move commentary
- `OPENAI_API_KEY` - Alternative AI commentary provider
- `SECRET_KEY` - Flask session secret (auto-generated if not provided)

See `docs/SETUP.md` for detailed setup instructions and `docs/AUTHENTICATION_SETUP.md` for OAuth configuration.

## Common Development Scenarios

**Adding New Analysis Features**
- Analysis logic goes in `stockfish_engine.py`
- Add API endpoint in `app.py` following pattern of `/api/analyze-position`
- Frontend calls from `game.js` and displays in analysis panel

**Modifying Move Evaluation**
- Classification thresholds in `stockfish_engine.py:266-314`
- Evaluation display in `game.js:594-667`
- Commentary prompt in `ai_commentator.py:72-87`

**Changing Game Rules**
- Player color selection: `lichess_client.py:24`
- Pawn promotion: `game.js:160` (currently auto-queens)
- Time controls: `lichess_client.py:15-26` (currently unlimited)

**Board Themes**
- Theme definitions in `static/css/board-themes.css` (classes like `board-theme-minimal`)
- Theme application logic in `game.js:435-447` and `analyze.js:388-396`
- Theme persistence via localStorage (shared between play and analyze modes)

**Working with Database Models**
- Add new fields to models in `models.py`
- Generate migration: `flask db migrate -m "Description"`
- Review migration in `migrations/versions/[generated].py`
- Apply migration: `flask db upgrade`
- Update database queries in `app.py` if needed
- See `docs/MIGRATIONS.md` for detailed workflow

**Extending PGN Analysis Features**
- Navigation logic in `analyze.js:goToMove()`, `goPreviousMove()`, `goNextMove()`
- Add new analysis tools by creating endpoints similar to `/api/parse-pgn`
- Board is non-draggable in analyze mode (set in `analyze.js:initBoard()`)
- To enable position analysis in analyze mode, integrate with `/api/analyze-position` endpoint
