# Heroku Deployment Guide

This guide covers deploying Chess Elegante to Heroku with managed PostgreSQL - a simpler, zero-ops alternative to AWS ECS.

---

## Architecture Overview

**Components:**
- **Heroku Dyno** - Runs the Flask application (web process)
- **Heroku Postgres** - Managed PostgreSQL database
- **Heroku Container Registry** - Docker image hosting
- **Config Vars** - Environment variables (secrets)
- **Heroku SSL** - Automatic HTTPS on custom domains

**Why Heroku:**
- ✅ Zero infrastructure management
- ✅ Automatic HTTPS
- ✅ Built-in PostgreSQL
- ✅ Easy deployments (git push)
- ✅ Free SSL certificates
- ⚠️ Higher cost than AWS for same resources
- ⚠️ Dyno sleeps after 30min inactivity (on free/hobby tier)

---

## Cost Estimate

### Hobby/Production Setup

| Service | Configuration | Cost |
|---------|--------------|------|
| Eco Dyno | 1 dyno (sleeps after 30min) | $5/month |
| Mini Postgres | 10GB database, 20 connections | $5/month |
| **Total** | Basic setup | **$10/month** |

### Production Setup

| Service | Configuration | Cost |
|---------|--------------|------|
| Basic Dyno | 1 dyno (no sleep, 512MB RAM) | $7/month |
| Standard-0 Postgres | 64GB database, 120 connections | $50/month |
| **Total** | | **$57/month** |

### Professional Setup

| Service | Configuration | Cost |
|---------|--------------|------|
| Standard-1X Dyno | 1 dyno (512MB RAM) | $25/month |
| Standard-2 Postgres | 256GB database, 480 connections | $200/month |
| **Total** | | **$225/month** |

**Comparison to AWS:**
- Hobby: $10/month (Heroku) vs $35/month (AWS) - **Heroku wins**
- Production: $57/month (Heroku) vs $35/month (AWS) - **AWS wins**

---

## Prerequisites

1. Heroku account (free tier available)
2. Heroku CLI installed
3. Git installed
4. Docker installed (for container deployment)
5. Domain name (optional)

---

## Step 1: Install Heroku CLI

### macOS
```bash
brew tap heroku/brew && brew install heroku
```

### Linux
```bash
curl https://cli-assets.heroku.com/install.sh | sh
```

### Windows
Download from: https://devcenter.heroku.com/articles/heroku-cli

### Verify Installation
```bash
heroku --version
heroku login
```

---

## Step 2: Prepare Application

### 2.1 Create Procfile

Heroku needs a Procfile to know how to run your app:

```bash
cat > Procfile <<EOF
web: gunicorn --bind 0.0.0.0:\$PORT --workers 2 --threads 4 --timeout 120 app:app
EOF
```

**Note:** Heroku assigns `$PORT` dynamically - don't hardcode 5000.

### 2.2 Update requirements.txt

Ensure gunicorn is included:

```bash
# Already in requirements.txt from AWS setup
grep gunicorn requirements.txt || echo "gunicorn>=21.2.0" >> requirements.txt
```

### 2.3 Create runtime.txt (Optional)

Specify Python version:

```bash
echo "python-3.12.0" > runtime.txt
```

### 2.4 Update app.py for Heroku Port

Heroku provides `PORT` environment variable:

```python
# In app.py, change:
if __name__ == '__main__':
    app.run(debug=True)

# To:
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
```

---

## Step 3: Create Heroku App

### 3.1 Create App

```bash
# Create app (Heroku assigns random name)
heroku create

# Or create with custom name
heroku create chess-elegante

# Verify
heroku apps:info
```

### 3.2 Add PostgreSQL

```bash
# Add Mini Postgres ($5/month)
heroku addons:create heroku-postgresql:mini

# Or use Eco (free tier - limited)
# heroku addons:create heroku-postgresql:essential-0

# Or use Standard-0 for production ($50/month)
# heroku addons:create heroku-postgresql:standard-0

# Wait for database to be ready
heroku pg:wait

# Get database info
heroku pg:info

# Get DATABASE_URL (automatically set as config var)
heroku config:get DATABASE_URL
```

---

## Step 4: Configure Environment Variables

### 4.1 Set Config Vars

```bash
# Google OAuth
heroku config:set GOOGLE_CLIENT_ID="your_google_client_id.apps.googleusercontent.com"
heroku config:set GOOGLE_CLIENT_SECRET="your_google_client_secret"

# Apple OAuth (optional)
heroku config:set APPLE_CLIENT_ID="com.yourcompany.chesselegante"
heroku config:set APPLE_CLIENT_SECRET="your_apple_jwt_token"

# Flask Secret Key
heroku config:set SECRET_KEY="$(python -c 'import secrets; print(secrets.token_hex(32))')"

# Lichess API Token
heroku config:set LICHESS_API_TOKEN="your_lichess_token"

# OpenAI API Key
heroku config:set OPENAI_API_KEY="your_openai_api_key"

# Anthropic API Key (optional)
heroku config:set ANTHROPIC_API_KEY="your_anthropic_api_key"

# Verify all config vars
heroku config
```

**Note:** `DATABASE_URL` is automatically set when you add Heroku Postgres.

---

## Step 5: Deploy Application

### Method A: Git Deployment (Recommended for Python apps)

This is simpler but requires a `requirements.txt` and Heroku buildpack.

```bash
# Initialize git if not already
git init
git add .
git commit -m "Initial commit for Heroku deployment"

# Add Heroku remote
heroku git:remote -a your-app-name

# Deploy
git push heroku main

# If your branch is named differently
git push heroku master:main
```

### Method B: Container Deployment (Using Docker)

Use this if you want to use the same Dockerfile as AWS.

```bash
# Login to Heroku Container Registry
heroku container:login

# Build and push container
heroku container:push web

# Release the container
heroku container:release web

# Check logs
heroku logs --tail
```

---

## Step 6: Run Database Migration

### 6.1 Run Database Migrations

```bash
# Apply migrations as one-off dyno
heroku run flask db upgrade

# Or connect to dyno and run manually
heroku run bash
flask db upgrade
exit
```

See [Migrations Guide](MIGRATIONS.md) for detailed migration workflow.

### 6.2 Verify Database

```bash
# Connect to PostgreSQL
heroku pg:psql

# Inside psql:
\dt                                    # List tables
SELECT * FROM users;                    # Check users table
SELECT * FROM games LIMIT 5;            # Check games table
\q                                      # Exit
```

---

## Step 7: Configure Domain and SSL

### 7.1 Add Custom Domain

```bash
# Add domain
heroku domains:add chesselegante.com

# Get DNS target (Heroku provides this)
heroku domains

# Output will show something like:
# DNS Target: your-app-name-12345.herokudns.com
```

### 7.2 Update DNS Records

In your DNS provider (Cloudflare, Route 53, etc.):

**Option A: CNAME (Recommended)**
```
Type: CNAME
Name: chess
Value: your-app-name-12345.herokudns.com
TTL: Auto or 300
```

**Option B: Subdomain with ALIAS/ANAME**
```
Type: ALIAS (or ANAME on some providers)
Name: chess
Value: your-app-name-12345.herokudns.com
```

### 7.3 Enable SSL (Automatic & Free)

Heroku automatically provisions SSL certificates for custom domains:

```bash
# SSL is automatic on paid dynos
# For free/hobby dynos, upgrade:
heroku certs:auto:enable

# Check SSL status
heroku certs:auto

# Verify HTTPS
curl https://chesselegante.com
```

**Note:** SSL provisioning takes 5-60 minutes after DNS propagation.

---

## Step 8: Update OAuth Redirect URIs

### Google OAuth Console

1. Go to https://console.cloud.google.com/apis/credentials
2. Edit OAuth 2.0 Client ID
3. Add Authorized Redirect URIs:
   ```
   https://your-app-name.herokuapp.com/auth/google/callback
   https://chesselegante.com/auth/google/callback
   ```

### Apple Developer Console

1. Go to https://developer.apple.com/account/resources/identifiers/list/serviceId
2. Edit your Service ID
3. Add Return URLs:
   ```
   https://your-app-name.herokuapp.com/auth/apple/callback
   https://chesselegante.com/auth/apple/callback
   ```

---

## Step 9: Scale and Monitor

### 9.1 Scale Dynos

```bash
# Check current scale
heroku ps

# Scale to 1 web dyno (default)
heroku ps:scale web=1

# Scale to 2 dynos for high availability
heroku ps:scale web=2

# Downscale to 0 (stop app, still charged for database)
heroku ps:scale web=0
```

### 9.2 View Logs

```bash
# Stream logs
heroku logs --tail

# Filter for errors
heroku logs --tail | grep ERROR

# View last 200 lines
heroku logs -n 200

# View specific dyno logs
heroku logs --dyno web.1 --tail
```

### 9.3 Monitor Performance

```bash
# Check app info
heroku apps:info

# Check dyno metrics (requires paid tier)
heroku ps:metrics

# Check database metrics
heroku pg:info
heroku pg:diagnose
```

---

## Step 10: Backups and Maintenance

### 10.1 Database Backups

```bash
# Manual backup
heroku pg:backups:capture

# Schedule daily backups (Standard tier and above)
heroku pg:backups:schedule DATABASE_URL --at '02:00 America/Los_Angeles'

# List backups
heroku pg:backups

# Download backup
heroku pg:backups:download

# Restore from backup
heroku pg:backups:restore b001 DATABASE_URL
```

### 10.2 Maintenance Mode

```bash
# Enable maintenance mode (shows static page)
heroku maintenance:on

# Run migrations during maintenance
heroku run flask db upgrade

# Disable maintenance mode
heroku maintenance:off
```

---

## Heroku-Specific Files

Your project should have these files for Heroku:

```
.
├── Procfile                 # Tells Heroku how to run app
├── runtime.txt              # Python version
├── requirements.txt         # Python dependencies
├── app.py                   # Main application
├── Dockerfile               # For container deployment (optional)
└── .gitignore              # Don't commit .env, venv, etc.
```

**Procfile:**
```
web: gunicorn --bind 0.0.0.0:$PORT --workers 2 --threads 4 --timeout 120 app:app
```

**runtime.txt:**
```
python-3.12.0
```

**.gitignore:**
```
venv/
__pycache__/
*.pyc
.env
.DS_Store
games/
*.db
```

---

## Environment Comparison

### Local Development
```bash
# Start local PostgreSQL
docker-compose -f docker-compose.local.yml up -d

# Activate venv
source venv/bin/activate

# Run app
python app.py

# Access at http://localhost:5000
```

### Heroku Staging
```bash
# Deploy to staging app
git push heroku-staging main

# Access at https://your-app-staging.herokuapp.com
```

### Heroku Production
```bash
# Deploy to production
git push heroku main

# Access at https://your-app-name.herokuapp.com
```

---

## Deployment Workflow

### Initial Deployment
```bash
# 1. Create and configure app
heroku create chess-elegante
heroku addons:create heroku-postgresql:mini
heroku config:set GOOGLE_CLIENT_ID="..." GOOGLE_CLIENT_SECRET="..."
# ... set other config vars

# 2. Deploy code
git push heroku main

# 3. Run migration
heroku run flask db upgrade

# 4. Open app
heroku open
```

### Update Deployment
```bash
# 1. Make changes locally
# ... edit code ...

# 2. Test locally
python app.py

# 3. Commit changes
git add .
git commit -m "Update feature X"

# 4. Deploy to Heroku
git push heroku main

# 5. Check logs
heroku logs --tail
```

### Rollback Deployment
```bash
# View releases
heroku releases

# Rollback to previous release
heroku rollback

# Or rollback to specific version
heroku rollback v23
```

---

## Troubleshooting

### App Crashes on Boot

```bash
# Check logs
heroku logs --tail

# Common issues:
# - Missing config vars (check: heroku config)
# - Database not ready (check: heroku pg:info)
# - Port binding error (ensure app uses $PORT)
# - Missing dependencies (check requirements.txt)
```

### Database Connection Errors

```bash
# Verify DATABASE_URL is set
heroku config:get DATABASE_URL

# Check database status
heroku pg:info

# Test connection
heroku pg:psql
```

### H10 App Crashed Error

```bash
# View crash logs
heroku logs --tail | grep "Error R10"

# Common causes:
# - App not binding to $PORT
# - Missing Procfile
# - Crash during startup
# - Out of memory

# Check dyno status
heroku ps
```

### OAuth Redirect Mismatch

```bash
# Get your app URL
heroku apps:info

# Ensure OAuth redirect URIs match exactly:
# https://your-app-name.herokuapp.com/auth/google/callback

# Check config vars
heroku config:get GOOGLE_CLIENT_ID
```

### Stockfish Not Found

If using buildpack deployment (not Docker), Stockfish won't be available by default:

**Option 1: Use Docker deployment**
```bash
heroku container:push web
heroku container:release web
```

**Option 2: Use Heroku Buildpack with APT**
```bash
# Create Aptfile
echo "stockfish" > Aptfile

# Add buildpack
heroku buildpacks:add --index 1 heroku-community/apt
heroku buildpacks:add --index 2 heroku/python

# Deploy
git add Aptfile
git commit -m "Add Stockfish via APT buildpack"
git push heroku main
```

---

## Performance Optimization

### 1. Enable HTTP/2
Heroku automatically supports HTTP/2 on HTTPS connections.

### 2. Use CDN for Static Assets
```bash
# Serve static files through Heroku's CDN
# Already configured in Flask app
```

### 3. Database Connection Pooling
Already configured in `game_storage_db.py` with SQLAlchemy connection pooling.

### 4. Enable Dyno Metadata
```bash
heroku labs:enable runtime-dyno-metadata

# Access in code via:
# os.environ.get('HEROKU_RELEASE_VERSION')
# os.environ.get('HEROKU_SLUG_COMMIT')
```

### 5. Preboot (Standard/Performance Dynos)
```bash
# Enable preboot for zero-downtime deploys
heroku features:enable preboot
```

---

## Advanced: Review Apps (Staging Environments)

### Set Up Pipelines

```bash
# Create pipeline
heroku pipelines:create chess-elegante-pipeline

# Add apps to pipeline
heroku pipelines:add chess-elegante-pipeline -a chess-elegante-staging --stage staging
heroku pipelines:add chess-elegante-pipeline -a chess-elegante-prod --stage production

# Enable review apps (creates temporary app for each PR)
# Configure in Heroku Dashboard -> Pipeline -> Enable Review Apps
```

---

## Advanced: Auto-Deploy from GitHub

1. **Connect GitHub Repo:**
   - Go to Heroku Dashboard
   - Select your app
   - Deploy tab → Deployment method → GitHub
   - Connect repository

2. **Enable Automatic Deploys:**
   - Choose branch (e.g., `main`)
   - Enable "Wait for CI to pass" (optional)
   - Click "Enable Automatic Deploys"

Now every push to `main` automatically deploys to Heroku.

---

## Security Checklist

- [x] All secrets in Config Vars (not committed to git)
- [x] `.env` in `.gitignore`
- [x] HTTPS enforced (automatic on custom domains)
- [x] Database uses SSL (automatic with Heroku Postgres)
- [x] OAuth redirect URIs use HTTPS
- [x] Database backups enabled
- [x] Config vars include SECRET_KEY
- [x] No hardcoded credentials in code
- [ ] Enable Heroku Shield (for HIPAA/PCI compliance - extra cost)
- [ ] Review app permissions regularly

---

## Useful Heroku Commands

```bash
# App Management
heroku apps:info                        # App info
heroku apps:rename new-name             # Rename app
heroku apps:destroy --app app-name      # Delete app

# Logs & Debugging
heroku logs --tail                      # Stream logs
heroku logs --tail --dyno web.1         # Specific dyno
heroku run bash                         # Open shell in dyno

# Database
heroku pg:info                          # Database info
heroku pg:psql                          # Connect to database
heroku pg:backups:capture               # Create backup
heroku pg:credentials:url DATABASE      # Get credentials

# Config
heroku config                           # List all config vars
heroku config:set KEY=value             # Set config var
heroku config:unset KEY                 # Remove config var

# Releases
heroku releases                         # List releases
heroku releases:info v123               # Release details
heroku rollback                         # Rollback to previous

# Scaling
heroku ps                               # List dynos
heroku ps:scale web=2                   # Scale to 2 dynos
heroku ps:restart                       # Restart all dynos

# Add-ons
heroku addons                           # List add-ons
heroku addons:create addon-name         # Add add-on
heroku addons:destroy addon-name        # Remove add-on
```

---

## Cost Optimization Tips

### 1. Use Eco Dynos ($5/month)
- Good for hobby projects
- Sleeps after 30min inactivity
- Shared compute resources

### 2. Downgrade Database When Not Needed
```bash
# Development: Use Essential-0 (free tier - limited)
heroku addons:create heroku-postgresql:essential-0

# Production: Use Mini ($5/month)
heroku addons:create heroku-postgresql:mini
```

### 3. Scale Down During Off-Hours
```bash
# Stop dynos at night (use Heroku Scheduler add-on)
heroku addons:create scheduler:standard

# Configure job: `heroku ps:scale web=0` at 11 PM
# Configure job: `heroku ps:scale web=1` at 7 AM
```

### 4. Use Free Tier (Limited)
- Free tier includes 1000 dyno hours/month
- Database limited to 10k rows
- Good for development/testing

---

## Migration from Local to Heroku

```bash
# 1. Export local database
pg_dump -h localhost -U chess -d chess_elegante > local_backup.sql

# 2. Import to Heroku
heroku pg:psql < local_backup.sql

# Or use Heroku's tool
heroku pg:push chess_elegante DATABASE_URL --app your-app-name
```

---

## Next Steps

1. ✅ Install Heroku CLI
2. ✅ Create Heroku app
3. ✅ Add PostgreSQL add-on
4. ✅ Set config vars (secrets)
5. ✅ Deploy application
6. ✅ Run database migration
7. ✅ Configure custom domain (optional)
8. ✅ Enable SSL (automatic)
9. ✅ Update OAuth redirect URIs
10. ✅ Monitor logs and performance

---

## Support Resources

- **Heroku Docs:** https://devcenter.heroku.com/
- **Heroku Status:** https://status.heroku.com/
- **Heroku Support:** https://help.heroku.com/
- **PostgreSQL Docs:** https://devcenter.heroku.com/categories/postgres-basics
- **Pricing:** https://www.heroku.com/pricing

---

## Conclusion

Heroku provides the simplest deployment option:
- **Pros:** Zero infrastructure, automatic SSL, easy deploys, built-in PostgreSQL
- **Cons:** Higher cost at scale, less control, dyno sleeping on free/eco tier

**Best for:**
- Quick deployments
- Hobby projects
- Low-traffic applications
- Teams wanting zero DevOps overhead

**Consider AWS ECS if:**
- You need fine-grained cost control
- You expect high traffic
- You need custom infrastructure
- You want maximum configurability
