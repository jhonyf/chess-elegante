# Vercel Deployment Guide

This guide covers deploying Chess Elegante to Vercel using Python Serverless Functions with an external PostgreSQL database.

---

## Architecture Overview

**Components:**
- **Vercel Python Runtime** - Runs the Flask application as serverless functions
- **Managed PostgreSQL** - Database for users, games, and PGNs
- **Vercel Project Settings** - Build, routing, and environment configuration
- **Environment Variables** - Secrets and API credentials
- **Vercel Domains** - Preview URLs, production domains, and automatic HTTPS

**Important limitations:**
- Vercel serverless functions are best for request/response workloads, not long-running background processes.
- Local file persistence in `games/` is not reliable on Vercel. Use PostgreSQL-backed persistence for production data.
- Local Stockfish binaries are not available by default. Analysis features need a compatible bundled binary, a remote analysis API, or a separate backend host.
- Lichess, OAuth, OpenAI, and Anthropic calls must complete within Vercel function limits.

---

## Cost Estimate

### Hobby Setup

| Service | Configuration | Cost |
|---------|--------------|------|
| Vercel Hobby | Personal projects, preview deployments | Free |
| Managed PostgreSQL | Neon, Supabase, Vercel Postgres, or similar free tier | Free-$5/month |
| **Total** | Basic setup | **$0-5/month** |

### Production Setup

| Service | Configuration | Cost |
|---------|--------------|------|
| Vercel Pro | Team/project production usage | $20/user/month |
| Managed PostgreSQL | Production database tier | $20-50+/month |
| **Total** | Typical small production setup | **$40-70+/month** |

**Comparison:**
- Hobby: Vercel can be the cheapest option for preview or low-traffic deployments.
- Production: Heroku is usually simpler for Flask apps with native dependencies.
- AWS is usually more flexible for Stockfish and long-running processes.

---

## Prerequisites

1. Vercel account
2. Vercel CLI installed
3. Git installed
4. Managed PostgreSQL database
5. Domain name (recommended for OAuth and HTTPS)

---

## Step 1: Install Vercel CLI

### macOS/Linux/Windows
```bash
npm install -g vercel
```

### Verify Installation
```bash
vercel --version
vercel login
```

---

## Step 2: Prepare Flask for Vercel

Vercel expects Python serverless entry points under the `api/` directory. Keep the existing Flask app in `app.py` and expose it from a Vercel function entry point.

### 2.1 Create `api/index.py`

```bash
mkdir -p api
cat > api/index.py <<EOF
import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from app import app
EOF
```

### 2.2 Create `vercel.json`

```bash
cat > vercel.json <<EOF
{
  "builds": [
    {
      "src": "api/index.py",
      "use": "@vercel/python"
    }
  ],
  "routes": [
    {
      "src": "/(.*)",
      "dest": "api/index.py"
    }
  ]
}
EOF
```

### 2.3 Review `requirements.txt`

Vercel installs Python dependencies from `requirements.txt`.

Make sure production dependencies are listed, including:

```text
Flask
gunicorn
psycopg2-binary
Flask-SQLAlchemy
Flask-Migrate
Flask-Login
Authlib
python-chess
requests
```

---

## Step 3: Create Vercel Project

### 3.1 Link Local Project

```bash
vercel link
```

Follow the prompts:
- Set up and deploy: `Y`
- Scope: choose your Vercel account or team
- Link to existing project: choose `N` for first setup
- Project name: `chess-elegante`
- Directory: `./`

### 3.2 Configure Project Settings

In the Vercel dashboard:

1. Open the project.
2. Go to **Settings** -> **General**.
3. Confirm the framework preset is set to **Other** if Vercel does not detect Flask correctly.
4. Leave build command empty unless custom build steps are required.

---

## Step 4: Configure Environment Variables

### 4.1 Required Variables

Set these in **Vercel Dashboard** -> **Project** -> **Settings** -> **Environment Variables**:

```bash
DATABASE_URL=postgresql://user:password@host:5432/database
LICHESS_API_TOKEN=your_lichess_token
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
SECRET_KEY=your_random_secret_key
```

### 4.2 Optional Variables

```bash
APPLE_CLIENT_ID=your_apple_client_id
APPLE_CLIENT_SECRET=your_apple_client_secret
ANTHROPIC_API_KEY=your_anthropic_api_key
OPENAI_API_KEY=your_openai_api_key
```

### 4.3 Set Variables with CLI

```bash
vercel env add DATABASE_URL production
vercel env add LICHESS_API_TOKEN production
vercel env add GOOGLE_CLIENT_ID production
vercel env add GOOGLE_CLIENT_SECRET production
vercel env add SECRET_KEY production
```

Repeat for `preview` and `development` environments if needed.

---

## Step 5: Configure Database

### 5.1 Use Managed PostgreSQL

Recommended providers:
- Vercel Postgres
- Neon
- Supabase
- Railway PostgreSQL
- AWS RDS

The database must be reachable from Vercel serverless functions over the public internet or through the provider's supported integration.

### 5.2 Apply Migrations

Vercel deployments should not run migrations automatically during request handling. Run migrations from a trusted local machine or CI job with production `DATABASE_URL`.

```bash
export DATABASE_URL="postgresql://user:password@host:5432/database"
flask db upgrade
```

### 5.3 File Storage Warning

Do not rely on `games/` for production persistence on Vercel. Serverless filesystems are ephemeral and should be treated as temporary.

Use the SQLAlchemy `Game` and `PGN` models for persistent data.

---

## Step 6: Deploy Application

### Preview Deployment

```bash
vercel
```

Vercel returns a preview URL like:

```text
https://chess-elegante-git-main-your-team.vercel.app
```

### Production Deployment

```bash
vercel --prod
```

Production deploys use the project production domain and any configured custom domains.

---

## Step 7: Configure Domain and HTTPS

### 7.1 Add Domain

In the Vercel dashboard:

1. Open the project.
2. Go to **Settings** -> **Domains**.
3. Add your domain, for example `chess.example.com`.
4. Follow the DNS instructions Vercel provides.

### 7.2 HTTPS

Vercel automatically provisions HTTPS certificates for configured domains.

---

## Step 8: Update OAuth Redirect URIs

### Google OAuth Console

Add authorized redirect URIs:

```text
https://your-project.vercel.app/auth/google/callback
https://your-custom-domain.com/auth/google/callback
```

### Apple Developer Console

Add return URLs:

```text
https://your-project.vercel.app/auth/apple/callback
https://your-custom-domain.com/auth/apple/callback
```

Make sure the URLs exactly match the Flask routes and deployed domain.

---

## Step 9: Stockfish and Analysis Options

The local Stockfish integration in `stockfish_engine.py` expects a native Stockfish binary. Vercel does not provide that binary by default.

### Option A: Disable Local Analysis on Vercel

Use Vercel for play, authentication, and PGN storage, but hide or disable analysis endpoints that require local Stockfish.

### Option B: Use a Remote Analysis Service

Host Stockfish on a platform that supports native binaries and longer-running processes:
- AWS ECS/Fargate
- Heroku with buildpack support
- Railway
- Fly.io
- A small VPS

Then update the Flask analysis endpoints to call that service.

### Option C: Bundle a Compatible Binary

Bundle a Linux-compatible Stockfish binary with the deployment and point `stockfish_engine.py` to it. This can be fragile because serverless filesystem paths, package size limits, and execution permissions must all be handled carefully.

For production, Option B is usually the most reliable.

---

## Step 10: Monitor and Debug

### View Deployments

```bash
vercel ls
```

### View Logs

```bash
vercel logs
```

For production:

```bash
vercel logs your-production-domain.com
```

### Inspect Environment Variables

```bash
vercel env ls
```

---

## Deployment Workflow

### Initial Deployment

```bash
# 1. Link project
vercel link

# 2. Add environment variables
vercel env add DATABASE_URL production
vercel env add LICHESS_API_TOKEN production
vercel env add GOOGLE_CLIENT_ID production
vercel env add GOOGLE_CLIENT_SECRET production
vercel env add SECRET_KEY production

# 3. Run database migrations from local or CI
flask db upgrade

# 4. Deploy production
vercel --prod
```

### Update Deployment

```bash
# 1. Make changes locally
# ... edit code ...

# 2. Commit changes
git add .
git commit -m "Update application"

# 3. Deploy preview
vercel

# 4. Deploy production
vercel --prod
```

### Rollback Deployment

Use the Vercel dashboard:

1. Open the project.
2. Go to **Deployments**.
3. Select a previous successful deployment.
4. Click **Promote to Production**.

---

## Troubleshooting

### 404 Not Found

Common causes:
- Missing `vercel.json` route to `api/index.py`
- Flask app not exported as `app`
- Project root configured incorrectly
- Deployment linked to the wrong directory

Check:

```bash
vercel logs
```

### Import Errors

Common causes:
- Missing dependency in `requirements.txt`
- `api/index.py` cannot import root-level `app.py`
- Native dependency incompatible with Vercel's runtime

Check the deployment build logs in the Vercel dashboard.

### Database Connection Errors

Common causes:
- `DATABASE_URL` missing in the selected environment
- Database provider blocks Vercel outbound connections
- SSL required by the database provider
- Connection pool exhaustion

For serverless deployments, keep database connections short-lived and use provider-recommended pooling when available.

### OAuth Redirect Mismatch

Make sure OAuth redirect URLs exactly match the active Vercel URL:

```text
https://your-project.vercel.app/auth/google/callback
https://your-custom-domain.com/auth/google/callback
```

Preview URLs are different from production URLs. Add preview redirect URIs only if you need OAuth on preview deployments.

### Stockfish Not Found

Expected on Vercel unless a compatible binary is bundled.

Recommended fix:
- Move analysis to a remote service, or
- Disable local Stockfish analysis for Vercel deployments.

---

## Security Checklist

- Store all secrets in Vercel environment variables.
- Never commit `.env` files.
- Use a strong `SECRET_KEY`.
- Use HTTPS-only OAuth redirect URLs.
- Restrict database access where the provider supports it.
- Rotate API keys after accidental exposure.
- Avoid logging OAuth tokens, session secrets, or API keys.

---

## Vercel-Specific Files

Minimum recommended files:

```text
api/index.py
vercel.json
requirements.txt
```

Optional files:

```text
.vercelignore
```

Use `.vercelignore` to exclude local-only files:

```text
venv/
.env
games/
__pycache__/
.pytest_cache/
```

---

## Next Steps

1. Create `api/index.py`.
2. Create `vercel.json`.
3. Move production persistence fully to PostgreSQL.
4. Decide whether Stockfish analysis should be disabled, bundled, or moved to a remote service.
5. Configure Vercel environment variables.
6. Deploy a preview with `vercel`.
7. Deploy production with `vercel --prod`.

---

## Support Resources

- [Vercel Python templates](https://vercel.com/templates/python)
- [Vercel deployment methods](https://examples.vercel.com/docs/deployments/deployment-methods)
- [Vercel deployments API](https://docs.vercel.com/docs/rest-api/reference/endpoints/deployments/create-a-new-deployment)
- [Vercel 404 troubleshooting](https://vercel.com/kb/guide/why-is-my-deployed-project-giving-404)
