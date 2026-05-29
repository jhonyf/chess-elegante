# Chess Elegante ♟️

A beautifully designed Flask-based web application for playing chess against AI opponents and analyzing games.

https://chesselegante.com/

![Python](https://img.shields.io/badge/python-3.12+-blue.svg)
![Flask](https://img.shields.io/badge/flask-3.0+-green.svg)
![PostgreSQL](https://img.shields.io/badge/postgresql-16+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)

---

## Features

### 🎮 Play Mode
- **AI Opponents** - Play against Lichess Stockfish AI (8 difficulty levels)
- **Interactive Board** - Drag-and-drop interface with beautiful chess pieces
- **Real-time Analysis** - Move evaluation and position analysis powered by Stockfish
- **AI Commentary** - Get educational explanations for each move (Irving Chernev style)
- **Move History** - Track and review all moves with timestamps

### 📊 Analyze Mode
- **PGN Import** - Upload and analyze chess games from PGN files
- **Full Navigation** - Step through games move by move with keyboard shortcuts
- **Save & Load** - Store favorite games and analysis for later review
- **Game Metadata** - View player names, ratings, opening, and results

### 🎨 Design
- **Elegant UI** - Modern, minimalist design with customizable board themes
- **Responsive** - Works on desktop and mobile devices
- **Dark/Light Themes** - Multiple chess board color schemes

### 🔐 User Features
- **OAuth Authentication** - Sign in with Google or Apple
- **Game History** - Browse all your past games
- **Persistent Storage** - PostgreSQL database for users, games, and PGNs

---

## Quick Start

### Prerequisites
- Python 3.12+
- Docker & Docker Compose
- Stockfish chess engine

### Installation

```bash
# Clone repository
git clone https://github.com/yourusername/chess-elegante.git
cd chess-elegante

# Start PostgreSQL
docker-compose -f docker-compose.local.yml up -d

# Set up Python environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Initialize database
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# Run application
python app.py
```

Visit http://localhost:5000 to start playing!

**👉 See [Setup Guide](docs/SETUP.md) for detailed instructions**

---

## Documentation

### Getting Started
- **[Setup Guide](docs/SETUP.md)** - Complete local development setup
- **[Authentication Setup](docs/AUTHENTICATION_SETUP.md)** - Configure Google/Apple OAuth
- **[AI Setup](docs/AI_SETUP.md)** - Configure AI commentary (OpenAI/Anthropic)

### Database
- **[Migrations Guide](docs/MIGRATIONS.md)** - Database schema management with Flask-Migrate
- **[Database Setup](docs/DATABASE_SETUP.md)** - PostgreSQL configuration (local & RDS)

### Deployment
- **[Heroku Deployment](docs/HEROKU_DEPLOYMENT.md)** - Deploy to Heroku (~$10/month)
- **[AWS Deployment](docs/AWS_DEPLOYMENT.md)** - Deploy to AWS ECS Fargate (~$35-50/month)
- **[Vercel Deployment](docs/VERCEL_DEPLOYMENT.md)** - Deploy to Vercel serverless with managed PostgreSQL
- **[CI/CD Setup](.github/SETUP_CI.md)** - GitHub Actions automated deployment

### Development
- **[CLAUDE.md](CLAUDE.md)** - Project overview and architecture (for Claude Code)

---

## Tech Stack

### Backend
- **Flask** - Web framework
- **PostgreSQL** - Database
- **SQLAlchemy + Flask-Migrate** - ORM and migrations
- **python-chess** - Chess logic and validation
- **Stockfish** - Chess engine for analysis
- **Lichess API** - AI opponent integration

### Frontend
- **chessboard.js** - Interactive chess board
- **chess.js** - Client-side chess logic
- **Vanilla JavaScript** - No heavy frameworks

### AI & APIs
- **OpenAI GPT** or **Anthropic Claude** - Move commentary
- **Lichess Board API** - Play against Stockfish AI

---

## Architecture

Chess Elegante uses a **dual-engine architecture**:

1. **Lichess Stockfish** (Remote)
   - AI opponent that you play against
   - Accessed via Lichess Board API
   - Player always plays as White

2. **Local Stockfish** (Analysis)
   - Real-time position evaluation
   - Move quality classification (excellent, good, inaccuracy, mistake, blunder)
   - Multi-PV analysis showing top variations

### Key Components

```
chess-elegante/
├── app.py                         # Main Flask application and route wiring
├── core/                          # Shared app utilities
│   └── auth, admin, and move-format helpers
├── database/                      # SQLAlchemy database models and setup
├── services/                      # Domain integrations and persistence services
│   └── Lichess, Stockfish, AI commentary, analysis, and storage
├── templates/                     # HTML templates
│   └── pages plus reusable component partials
├── static/                        # Frontend JavaScript and CSS assets
├── seed_data/                     # Curated game data and import helpers
├── scripts/                       # Maintenance and seeding scripts
├── migrations/                    # Alembic/Flask-Migrate migration files
└── docs/                          # Setup, deployment, and architecture docs
```

---

## Development

### Running Tests

```bash
# Test Stockfish integration
python test_stockfish.py

# Test Docker build
docker-compose up --build
```

### Database Migrations

```bash
# After changing models.py
flask db migrate -m "Add new field"
flask db upgrade
```

See [Migrations Guide](docs/MIGRATIONS.md) for details.

### Deployment

**Local testing:**
```bash
docker-compose up --build
# Test at http://localhost:5001
```

---

## Environment Variables

Create a `.env` file with these variables:

```env
# Required
DATABASE_URL=postgresql://user:pass@host:5432/chess_elegante
SECRET_KEY=your_secret_key
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
LICHESS_API_TOKEN=your_lichess_token
OPENAI_API_KEY=your_openai_key

# Optional
APPLE_CLIENT_ID=your_apple_client_id
APPLE_CLIENT_SECRET=your_apple_client_secret
ANTHROPIC_API_KEY=your_anthropic_key
```

See [Setup Guide](docs/SETUP.md) for how to obtain these values.

---

## API Endpoints

### System
- `GET /health` - Health check
- `GET /api/version` - Current deployed version metadata

### Game Management
- `GET /api/games` - List the current user's games
- `GET /api/game/<game_id>` - Load a specific game
- `POST /api/resume-game/<game_id>` - Resume a saved live game
- `DELETE /api/delete-game/<game_id>` - Delete a saved game
- `POST /api/new-game` - Start a new game against AI
- `POST /api/make-move` - Make a move
- `GET /api/game-state` - Get current game state
- `GET /api/game-stream` - Stream live game updates via Server-Sent Events
- `POST /api/resign` - Resign current game

### Analysis
- `POST /api/analyze-position` - Analyze a chess position
- `POST /api/analyze-best-move` - Get the best move with AI commentary
- `POST /api/evaluate-move` - Evaluate move quality
- `POST /api/evaluate-move-ai` - Generate AI commentary for a move

### PGN & Saved Analysis
- `POST /api/parse-pgn` - Parse PGN file
- `POST /api/save-pgn` - Save PGN to database
- `GET /api/pgns` - List saved PGNs
- `GET /api/game/<game_id>/data` - Load saved or curated game data for analysis
- `POST /api/generate-commentary/<game_id>` - Generate commentary for a saved game

### Curated Games
- `GET /api/curated-games` - List public curated games, optionally filtered by opening

### Admin
- `GET /admin/api/curated-games` - List curated games with commentary status
- `POST /admin/api/upload-curated-game` - Upload a curated game from PGN
- `POST /admin/api/generate-commentary/<game_id>` - Start curated-game commentary generation
- `GET /admin/api/commentary-status/<game_id>` - Check commentary generation status
- `PATCH /admin/api/curated-game/<game_id>` - Update curated game metadata
- `DELETE /admin/api/curated-game/<game_id>` - Delete a curated game

---

## Acknowledgments

- **Lichess** - For the excellent Board API and Stockfish integration
- **chessboard.js** & **chess.js** - For the chess UI components
- **Stockfish** - For the powerful chess engine
- **OpenAI/Anthropic** - For AI commentary capabilities

---

**Built with ♟️ and Flask**
