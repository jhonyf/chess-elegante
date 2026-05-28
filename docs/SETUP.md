# Setup Guide

Quick guide for local development and deployment.

---

## Local Development

### Prerequisites
- Python 3.12+
- Docker & Docker Compose
- Stockfish chess engine (for analysis)

### 1. Clone and Install

```bash
# Clone repository
git clone https://github.com/yourusername/chess-elegante.git
cd chess-elegante

# Create virtual environment
python -m venv venv
source venv/bin/activate  # macOS/Linux
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Install Stockfish
brew install stockfish  # macOS
# or
sudo apt-get install stockfish  # Ubuntu/Debian
```

### 2. Start PostgreSQL

```bash
# Start local PostgreSQL database
docker-compose -f docker-compose.local.yml up -d

# Verify it's running
docker ps

# Connect locally
psql -h localhost -U chess chess_elegante
```

### 3. Configure Environment

```bash
# Copy example env file
cp .env.example .env

# Edit .env with your credentials
```

**Minimum required for local development:**
```env
DATABASE_URL=postgresql://chess:chess@localhost:5432/chess_elegante
SECRET_KEY=your_secret_key_here
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
LICHESS_API_TOKEN=your_lichess_token
OPENAI_API_KEY=your_openai_key
```

See [Authentication Setup](AUTHENTICATION_SETUP.md) for OAuth configuration.

### 4. Initialize Database

```bash
# Initialize Flask-Migrate
flask db init

# Create and apply first migration
flask db migrate -m "Initial migration"
flask db upgrade
```

See [Migrations Guide](MIGRATIONS.md) for detailed instructions.

### 5. Run Application

```bash
# Development mode
python app.py

# Access at http://localhost:5000
```

### 6. Stop Services

```bash
# Stop PostgreSQL
docker-compose -f docker-compose.local.yml down

# Stop and remove data
docker-compose -f docker-compose.local.yml down -v
```

---

## Testing Production Build

Before deploying to AWS, test the production Docker image locally:

```bash
# Build and run full stack (app + DB)
docker-compose up --build

# Access at http://localhost:5001 (note: 5001, not 5000)

# Stop
docker-compose down
```

---

## Deployment Options

### Heroku (Easiest)

**Best for:** Quick deployments, minimal DevOps

- Managed PostgreSQL included
- Automatic HTTPS
- **Cost:** ~$10/month

See [Heroku Deployment Guide](HEROKU_DEPLOYMENT.md)

### AWS ECS Fargate (Most Flexible)

**Best for:** Cost control, scalability

- RDS PostgreSQL
- ECS Fargate containers
- **Cost:** ~$35-50/month

See [AWS Deployment Guide](AWS_DEPLOYMENT.md)

---

## Environment Variables

### Required

| Variable | Description | How to Get |
|----------|-------------|------------|
| `DATABASE_URL` | PostgreSQL connection string | Local: `postgresql://chess:chess@localhost:5432/chess_elegante` |
| `SECRET_KEY` | Flask session secret | Generate: `python -c 'import secrets; print(secrets.token_hex(32))'` |
| `GOOGLE_CLIENT_ID` | Google OAuth client ID | [Google Cloud Console](https://console.cloud.google.com) |
| `GOOGLE_CLIENT_SECRET` | Google OAuth secret | Same as above |
| `LICHESS_API_TOKEN` | Lichess API token | [Lichess Token Page](https://lichess.org/account/oauth/token) |
| `OPENAI_API_KEY` | OpenAI API key | [OpenAI Platform](https://platform.openai.com) |

### Optional

| Variable | Description |
|----------|-------------|
| `APPLE_CLIENT_ID` | Apple OAuth client ID |
| `APPLE_CLIENT_SECRET` | Apple OAuth secret (JWT) |
| `ANTHROPIC_API_KEY` | Anthropic API key (alternative to OpenAI) |

---

## Daily Development Workflow

```bash
# Start PostgreSQL
docker-compose -f docker-compose.local.yml up -d

# Activate virtual environment
source venv/bin/activate

# Run application
python app.py

# Make changes and test

# Stop PostgreSQL when done
docker-compose -f docker-compose.local.yml down
```

---

## Troubleshooting

### PostgreSQL connection refused

```bash
# Check if container is running
docker ps

# Restart PostgreSQL
docker-compose -f docker-compose.local.yml restart
```

### Port already in use

```bash
# Kill process on port 5000
lsof -ti:5000 | xargs kill -9

# Or use different port in app.py
```

### OAuth redirect URI mismatch

- Check Google Console redirect URIs include exact URL
- Add both `http://localhost:5000` and `http://127.0.0.1:5000`
- See [Authentication Setup](AUTHENTICATION_SETUP.md)

### Database tables missing

```bash
# Apply migrations
flask db upgrade
```

See [Migrations Guide](MIGRATIONS.md) for troubleshooting.

---

## Next Steps

- **Configure OAuth:** See [Authentication Setup](AUTHENTICATION_SETUP.md)
- **Database Management:** See [Migrations Guide](MIGRATIONS.md)
- **Deploy to Production:** See [AWS Deployment](AWS_DEPLOYMENT.md) or [Heroku Deployment](HEROKU_DEPLOYMENT.md)
- **AI Features:** See [AI Setup](AI_SETUP.md)
