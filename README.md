# Chess Elegante ♟️

A beautifully designed Flask-based web application for playing chess against AI opponents and analyzing games.

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
├── app.py                    # Main Flask application
├── models.py                 # Database models (User, Game, PGN)
├── lichess_client.py         # Lichess API integration
├── stockfish_engine.py       # Local Stockfish for analysis
├── ai_commentator.py         # AI-powered move commentary
├── auth.py                   # OAuth authentication
├── game_storage.py           # Database operations
├── templates/                # HTML templates
│   ├── home.html            # Landing page
│   ├── play.html            # Play mode
│   ├── analyze.html         # PGN analysis mode
│   └── games.html           # Game history
└── static/
    ├── js/
    │   ├── game.js          # Play mode logic
    │   └── analyze.js       # Analysis mode logic
    └── css/
        ├── main.css         # Shared styles
        ├── play.css         # Play mode styles
        └── board-themes.css # Chess board themes
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

### Game Management
- `POST /api/new-game` - Start a new game against AI
- `POST /api/make-move` - Make a move
- `GET /api/game-state` - Get current game state
- `POST /api/resign` - Resign current game

### Analysis
- `POST /api/analyze-position` - Analyze a chess position
- `POST /api/evaluate-move` - Evaluate move quality

### PGN
- `POST /api/parse-pgn` - Parse PGN file
- `POST /api/save-pgn` - Save PGN to database
- `GET /api/pgns` - List saved PGNs
- `GET /api/pgn/<id>` - Load specific PGN

---

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## Acknowledgments

- **Lichess** - For the excellent Board API and Stockfish integration
- **chessboard.js** & **chess.js** - For the chess UI components
- **Stockfish** - For the powerful chess engine
- **OpenAI/Anthropic** - For AI commentary capabilities

---

## Support

- 📖 **Documentation:** See `docs/` folder
- 🐛 **Issues:** [GitHub Issues](https://github.com/yourusername/chess-elegante/issues)
- 💬 **Discussions:** [GitHub Discussions](https://github.com/yourusername/chess-elegante/discussions)

---

**Built with ♟️ and Flask**
