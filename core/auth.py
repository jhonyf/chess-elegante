"""
Authentication module for Chess Elegante
Supports Google and Apple OAuth
"""
import os
import uuid
from datetime import datetime
from flask import Blueprint, redirect, url_for, request, session
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from authlib.integrations.flask_client import OAuth
from sqlalchemy.orm import sessionmaker
from database.models import User, Base
from sqlalchemy import create_engine
import logging

logger = logging.getLogger(__name__)

# Create authentication blueprint
auth_bp = Blueprint('auth', __name__)

# Initialize OAuth
oauth = OAuth()

# Google OAuth Configuration
google = oauth.register(
    name='google',
    client_id=os.getenv('GOOGLE_CLIENT_ID'),
    client_secret=os.getenv('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid email profile'}
)

# Apple OAuth Configuration
apple = oauth.register(
    name='apple',
    client_id=os.getenv('APPLE_CLIENT_ID'),
    client_secret=os.getenv('APPLE_CLIENT_SECRET'),
    authorize_url='https://appleid.apple.com/auth/authorize',
    authorize_params={'response_mode': 'form_post'},
    access_token_url='https://appleid.apple.com/auth/token',
    client_kwargs={'scope': 'email name'}
)


def init_auth(app, db_session_factory):
    """
    Initialize authentication for Flask app

    Args:
        app: Flask application instance
        db_session_factory: SQLAlchemy session factory for database access
    """
    # Initialize OAuth with app
    oauth.init_app(app)

    # Initialize Flask-Login
    login_manager = LoginManager()
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'

    # Store session factory for use in routes
    auth_bp.db_session_factory = db_session_factory

    @login_manager.user_loader
    def load_user(user_id):
        """Load user by ID for Flask-Login"""
        db_session = db_session_factory()
        try:
            user = db_session.query(User).filter_by(id=user_id).first()
            return user
        finally:
            db_session.close()

    # Register auth blueprint
    app.register_blueprint(auth_bp)

    logger.info("Authentication initialized successfully")


# ==================== ROUTES ====================

@auth_bp.route('/login')
def login():
    """Login page - shows OAuth options"""
    from flask import render_template
    return render_template('login.html')


@auth_bp.route('/login/google')
def login_google():
    """Initiate Google OAuth flow"""
    redirect_uri = url_for('auth.google_callback', _external=True)
    return google.authorize_redirect(redirect_uri)


@auth_bp.route('/login/apple')
def login_apple():
    """Initiate Apple OAuth flow"""
    redirect_uri = url_for('auth.apple_callback', _external=True)
    return apple.authorize_redirect(redirect_uri)


@auth_bp.route('/auth/google/callback')
def google_callback():
    """Handle Google OAuth callback"""
    try:
        token = google.authorize_access_token()
        user_info = token.get('userinfo')

        if not user_info:
            logger.error("No user info returned from Google")
            return redirect(url_for('auth.login') + '?error=no_user_info')

        # Get or create user
        user = get_or_create_user(
            provider='google',
            provider_id=user_info['sub'],
            email=user_info['email'],
            name=user_info.get('name'),
            picture=user_info.get('picture')
        )

        # Log in user
        login_user(user, remember=True)
        logger.info(f"User logged in via Google: {user.email}")

        # Redirect to original page or home
        next_page = session.get('next')
        session.pop('next', None)

        # If next_page is an API endpoint or not set, redirect to /games
        if not next_page or next_page.startswith('/api/'):
            next_page = url_for('games')

        return redirect(next_page)

    except Exception as e:
        logger.error(f"Google OAuth error: {e}", exc_info=True)
        return redirect(url_for('auth.login') + '?error=oauth_failed')


@auth_bp.route('/auth/apple/callback', methods=['GET', 'POST'])
def apple_callback():
    """Handle Apple OAuth callback"""
    try:
        token = apple.authorize_access_token()

        # Apple returns user info in ID token
        user_info = token.get('userinfo')
        if not user_info:
            logger.error("No user info returned from Apple")
            return redirect(url_for('auth.login') + '?error=no_user_info')

        # Get or create user
        user = get_or_create_user(
            provider='apple',
            provider_id=user_info['sub'],
            email=user_info.get('email'),
            name=user_info.get('name'),
            picture=None  # Apple doesn't provide profile pictures
        )

        # Log in user
        login_user(user, remember=True)
        logger.info(f"User logged in via Apple: {user.email}")

        # Redirect to original page or home
        next_page = session.get('next')
        session.pop('next', None)

        # If next_page is an API endpoint or not set, redirect to /games
        if not next_page or next_page.startswith('/api/'):
            next_page = url_for('games')

        return redirect(next_page)

    except Exception as e:
        logger.error(f"Apple OAuth error: {e}", exc_info=True)
        return redirect(url_for('auth.login') + '?error=oauth_failed')


@auth_bp.route('/logout')
@login_required
def logout():
    """Log out current user"""
    logger.info(f"User logged out: {current_user.email}")
    logout_user()
    return redirect(url_for('index'))


# ==================== HELPER FUNCTIONS ====================

def get_or_create_user(provider, provider_id, email, name=None, picture=None):
    """
    Get existing user or create new user from OAuth data

    Args:
        provider: OAuth provider name ('google' or 'apple')
        provider_id: Unique ID from OAuth provider
        email: User email
        name: User display name (optional)
        picture: Profile picture URL (optional)

    Returns:
        User object
    """
    db_session = auth_bp.db_session_factory()
    try:
        # Check if user exists by provider_id
        user = db_session.query(User).filter_by(provider_id=provider_id).first()

        if user:
            # Update last login and potentially updated info
            user.last_login = datetime.utcnow()
            if name:
                user.name = name
            if picture:
                user.picture = picture
            db_session.commit()
            logger.debug(f"Existing user found: {user.email}")
        else:
            # Create new user
            user_id = str(uuid.uuid4())
            user = User(
                id=user_id,
                provider=provider,
                provider_id=provider_id,
                email=email,
                name=name or email.split('@')[0],  # Default name from email
                picture=picture,
                created_at=datetime.utcnow(),
                last_login=datetime.utcnow()
            )
            db_session.add(user)
            db_session.commit()
            logger.info(f"New user created: {user.email} (provider: {provider})")

        # Refresh to get updated data
        db_session.refresh(user)
        return user

    except Exception as e:
        db_session.rollback()
        logger.error(f"Error getting/creating user: {e}", exc_info=True)
        raise
    finally:
        db_session.close()
