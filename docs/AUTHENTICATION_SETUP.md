# Authentication Setup Guide

Chess Elegante uses OAuth 2.0 for user authentication, supporting **Google** and **Apple** sign-in. This guide covers setup for both local development and production deployment.

---

## Overview

**Authentication Features:**
- OAuth 2.0 with Google and Apple
- User-specific game storage (My Games)
- Shared PGN analysis (all authenticated users can access)
- Persistent sessions with Flask-Login
- PostgreSQL user storage

**Protected Routes:**
- `/play` - Requires authentication
- `/games` - Requires authentication (shows only user's games)
- `/analyze` - Requires authentication (but PGNs are shared)
- `/about`, `/` - Public access

---

## Local Development Setup

### 1. Google OAuth Setup

#### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Project name: `Chess Elegante` (or any name)

#### Step 2: Enable OAuth Consent Screen

1. Navigate to **APIs & Services** → **OAuth consent screen**
2. Select **External** user type (for testing)
3. Fill in:
   - App name: `Chess Elegante`
   - User support email: Your email
   - Developer contact: Your email
4. Click **Save and Continue**
5. Scopes: Skip (default scopes are sufficient)
6. Test users: Add your email for testing
7. Click **Save and Continue**

#### Step 3: Create OAuth Client ID

1. Navigate to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **OAuth client ID**
3. Application type: **Web application**
4. Name: `Chess Elegante Local`
5. **Authorized JavaScript origins:**
   ```
   http://localhost:5000
   ```
6. **Authorized redirect URIs:**
   ```
   http://localhost:5000/auth/google/callback
   ```
7. Click **Create**
8. Copy the **Client ID** and **Client Secret**

#### Step 4: Add to .env

```env
GOOGLE_CLIENT_ID=123456789-abc123def456.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=GOCSPX-abc123def456ghi789
```

---

### 2. Apple OAuth Setup

Apple Sign In is more complex and requires an Apple Developer account ($99/year).

#### Step 1: Apple Developer Account

1. Sign up at [developer.apple.com](https://developer.apple.com/)
2. Enroll in Apple Developer Program ($99/year)

#### Step 2: Create App ID

1. Go to **Certificates, Identifiers & Profiles**
2. Click **Identifiers** → **+** (Add)
3. Select **App IDs** → Continue
4. Description: `Chess Elegante`
5. Bundle ID: `com.yourcompany.chesselegante`
6. Enable **Sign in with Apple**
7. Click **Continue** → **Register**

#### Step 3: Create Service ID

1. Go to **Identifiers** → **+** (Add)
2. Select **Services IDs** → Continue
3. Description: `Chess Elegante Web`
4. Identifier: `com.yourcompany.chesselegante.web`
5. Enable **Sign in with Apple**
6. Click **Configure** next to Sign in with Apple
7. **Primary App ID**: Select the App ID created above
8. **Web Domain**: `localhost` (for local testing)
9. **Return URLs**: `http://localhost:5000/auth/apple/callback`
10. Click **Save** → **Continue** → **Register**

#### Step 4: Create Private Key

1. Go to **Keys** → **+** (Add)
2. Key Name: `Chess Elegante Sign In Key`
3. Enable **Sign in with Apple**
4. Click **Configure** → Select your App ID → **Save**
5. Click **Continue** → **Register**
6. **Download** the key file (`.p8`) - you can only download once!
7. Note the **Key ID** shown

#### Step 5: Generate Client Secret (JWT)

Apple requires a JWT token as the client secret. Create a script:

```python
# generate_apple_secret.py
import jwt
import time

# Your values from Apple Developer account
TEAM_ID = "ABC123DEF4"  # Found in top-right of developer portal
KEY_ID = "XYZ789GHI0"   # From the key you created
CLIENT_ID = "com.yourcompany.chesselegante.web"  # Your Service ID
KEY_FILE = "AuthKey_XYZ789GHI0.p8"  # Downloaded .p8 file

# Read the private key
with open(KEY_FILE, 'r') as f:
    private_key = f.read()

# Generate JWT
headers = {
    "kid": KEY_ID,
    "alg": "ES256"
}

payload = {
    "iss": TEAM_ID,
    "iat": time.time(),
    "exp": time.time() + 86400 * 180,  # 6 months (max allowed)
    "aud": "https://appleid.apple.com",
    "sub": CLIENT_ID
}

client_secret = jwt.encode(payload, private_key, algorithm="ES256", headers=headers)
print(f"APPLE_CLIENT_SECRET={client_secret}")
```

Install dependencies and run:
```bash
pip install pyjwt cryptography
python generate_apple_secret.py
```

#### Step 6: Add to .env

```env
APPLE_CLIENT_ID=com.yourcompany.chesselegante.web
APPLE_CLIENT_SECRET=eyJhbGciOiJFUzI1NiIsImtpZCI6IlhZWjc4OUdISTAifQ...
```

**Note:** Regenerate the secret every 6 months (or less).

---

### 3. Environment Configuration

Update your `.env` file:

```env
# Database
DATABASE_URL=postgresql://chess:chess@localhost:5432/chess_elegante

# Google OAuth
GOOGLE_CLIENT_ID=your_google_client_id_here.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret_here

# Apple OAuth
APPLE_CLIENT_ID=com.yourcompany.chesselegante.web
APPLE_CLIENT_SECRET=your_generated_jwt_token_here

# Flask
SECRET_KEY=your_generated_secret_key_here

# Other configs...
LICHESS_API_TOKEN=your_lichess_token
OPENAI_API_KEY=your_openai_key
```

Generate a Flask secret key:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

### 4. Database Migration

Initialize the database and create the User table:

```bash
# Start PostgreSQL
docker-compose up -d

# Initialize Flask-Migrate and create tables
flask db init
flask db migrate -m "Initial migration"
flask db upgrade
```

For detailed migration instructions, see [Migrations Guide](MIGRATIONS.md).

Verify User table exists:
```bash
docker exec -it chess_elegante_db psql -U chess -d chess_elegante -c "\d users"
```

---

### 5. Test Locally

```bash
# Install dependencies
pip install -r requirements.txt

# Run app
python app.py
```

Navigate to http://localhost:5000 and click **Login**. Test both Google and Apple sign-in.

---

## Production Setup (AWS)

### 1. Google OAuth for Production

#### Update OAuth Client

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Navigate to **APIs & Services** → **Credentials**
3. Edit your OAuth 2.0 Client ID
4. **Authorized JavaScript origins:**
   ```
   https://your-domain.com
   https://www.your-domain.com
   ```
5. **Authorized redirect URIs:**
   ```
   https://your-domain.com/auth/google/callback
   https://www.your-domain.com/auth/google/callback
   ```
6. Save changes

### 2. Apple OAuth for Production

#### Update Service ID

1. Go to [Apple Developer](https://developer.apple.com/account/resources/identifiers/list/serviceId)
2. Select your Service ID
3. Edit **Sign in with Apple** configuration
4. **Web Domain**: `your-domain.com`
5. **Return URLs**: `https://your-domain.com/auth/apple/callback`
6. Save

#### Regenerate Client Secret (if needed)

Use the same script but update payload:
```python
payload = {
    "iss": TEAM_ID,
    "iat": time.time(),
    "exp": time.time() + 86400 * 180,  # 6 months
    "aud": "https://appleid.apple.com",
    "sub": CLIENT_ID  # Same Service ID
}
```

### 3. Environment Variables on AWS

#### Option A: EC2 Instance

Create `/opt/chess-elegante/.env`:
```env
DATABASE_URL=postgresql://chess:PASSWORD@your-rds-endpoint:5432/chess_elegante
GOOGLE_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=your_google_client_secret
APPLE_CLIENT_ID=com.yourcompany.chesselegante.web
APPLE_CLIENT_SECRET=your_generated_jwt_token
SECRET_KEY=your_production_secret_key
LICHESS_API_TOKEN=your_lichess_token
OPENAI_API_KEY=your_openai_key
```

Set permissions:
```bash
chmod 600 /opt/chess-elegante/.env
chown chess-app:chess-app /opt/chess-elegante/.env
```

#### Option B: AWS Elastic Beanstalk

Set environment variables in console or via CLI:
```bash
eb setenv \
  DATABASE_URL=postgresql://... \
  GOOGLE_CLIENT_ID=... \
  GOOGLE_CLIENT_SECRET=... \
  APPLE_CLIENT_ID=... \
  APPLE_CLIENT_SECRET=... \
  SECRET_KEY=... \
  LICHESS_API_TOKEN=... \
  OPENAI_API_KEY=...
```

#### Option C: AWS Secrets Manager (Recommended)

Store secrets in AWS Secrets Manager and retrieve them in `app.py`:

```python
import boto3
import json

def get_secret(secret_name):
    client = boto3.client('secretsmanager', region_name='us-east-1')
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response['SecretString'])

# In app.py
if os.getenv('ENV') == 'production':
    secrets = get_secret('chess-elegante/prod')
    os.environ.update(secrets)
```

### 4. HTTPS Requirement

**Important:** OAuth providers require HTTPS in production.

#### Option A: AWS Application Load Balancer

1. Create ALB with SSL certificate (AWS Certificate Manager)
2. Configure HTTPS listener (port 443)
3. HTTP → HTTPS redirect

#### Option B: Nginx with Let's Encrypt

```nginx
server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

---

## Troubleshooting

### Google OAuth Errors

**Error: redirect_uri_mismatch**
- Check that redirect URI exactly matches in Google Console
- Ensure protocol (http/https) matches
- Check for trailing slashes

**Error: invalid_client**
- Verify `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET` in `.env`
- Ensure OAuth consent screen is configured

### Apple OAuth Errors

**Error: invalid_client**
- Regenerate client secret JWT (may have expired)
- Verify Team ID, Key ID, and Client ID are correct

**Error: invalid_request**
- Check redirect URI in Apple Developer portal
- Ensure domain is verified

### Database Errors

**User table doesn't exist**
```bash
python -c "from models import Base; from sqlalchemy import create_engine; import os; from dotenv import load_dotenv; load_dotenv(); engine = create_engine(os.getenv('DATABASE_URL')); Base.metadata.create_all(engine)"
```

**Foreign key constraint error**
- Ensure user exists before creating games
- Check `user_id` is being passed correctly

### Session Errors

**User not staying logged in**
- Verify `SECRET_KEY` is set and consistent
- Check Flask session configuration
- Ensure cookies are enabled in browser

---

## Testing

### Test OAuth Flow

1. Clear browser cookies
2. Navigate to `/login`
3. Click **Continue with Google**
4. Authorize app
5. Should redirect to homepage with "Logout" in nav
6. Check database:
```sql
SELECT * FROM users ORDER BY created_at DESC LIMIT 1;
```

### Test Protected Routes

```bash
# Should redirect to /login
curl -I http://localhost:5000/play

# After login, should return 200
curl -I -b cookies.txt http://localhost:5000/play
```

### Test Game Creation

1. Login
2. Go to `/play`
3. Start new game
4. Check database:
```sql
SELECT game_id, user_id, status FROM games ORDER BY created_at DESC LIMIT 1;
```

Should show `user_id` matching logged-in user.

---

## Security Considerations

### Production Checklist

- [ ] Use HTTPS only (no HTTP)
- [ ] Set secure session cookies:
  ```python
  app.config['SESSION_COOKIE_SECURE'] = True  # HTTPS only
  app.config['SESSION_COOKIE_HTTPONLY'] = True  # No JavaScript access
  app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'  # CSRF protection
  ```
- [ ] Store secrets in AWS Secrets Manager (not .env files)
- [ ] Enable RDS encryption at rest
- [ ] Use IAM roles for AWS services (no hardcoded credentials)
- [ ] Rotate Apple JWT secret every 6 months
- [ ] Set up CloudWatch alerts for failed logins
- [ ] Enable MFA for AWS account
- [ ] Implement rate limiting on OAuth endpoints
- [ ] Use prepared statements for all SQL queries (SQLAlchemy does this)
- [ ] Validate all user input

---

## Cost Estimates

**Free Tier:**
- Google OAuth: Free (unlimited)
- AWS RDS (PostgreSQL): Free for 12 months (db.t3.micro)
- AWS EC2: Free for 12 months (t2.micro)

**After Free Tier:**
- Apple Developer Program: $99/year
- AWS RDS (db.t4g.small): ~$26/month
- AWS EC2 (t3.small): ~$15/month
- AWS ALB: ~$16/month
- **Total: ~$57/month + $99/year**

---

## Next Steps

1. Set up Google OAuth locally
2. Test authentication flow
3. (Optional) Set up Apple OAuth
4. Deploy to AWS with HTTPS
5. Update OAuth redirect URIs for production
6. Test in production

For issues, check logs in `logs/app.log` or enable Flask debug mode locally.
