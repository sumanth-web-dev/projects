"""
Production configuration settings for the Job Application Agent.
This file extends the base Config class with production-specific settings.
"""
import os
import logging
from config import Config


class ProductionConfig(Config):
    """Production configuration with enhanced security and performance settings."""
    
    DEBUG = False
    TESTING = False
    
    # Enhanced security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Rate limiting settings - more restrictive in production
    RATELIMIT_DEFAULT = "100 per hour"
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', "memory://")
    
    # Logging settings - more structured in production
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'WARNING')
    CONSOLE_LOGGING = False  # Disable console logging in production
    FILE_LOGGING = True
    JSON_LOGGING = True
    
    @staticmethod
    def init_app(app):
        """Initialize production-specific settings."""
        Config.init_app(app)
        
        # Use gunicorn logger when available
        gunicorn_logger = logging.getLogger('gunicorn.error')
        if gunicorn_logger.handlers:
            app.logger.handlers = gunicorn_logger.handlers
            app.logger.setLevel(gunicorn_logger.level)
        
        # Create log directory if it doesn't exist
        if not os.path.exists(app.config['LOG_DIR']):
            os.makedirs(app.config['LOG_DIR'], exist_ok=True)
        
        # Create uploads directory if it doesn't exist
        if not os.path.exists(app.config['UPLOAD_FOLDER']):
            os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        
        # Verify that required environment variables are set
        required_env_vars = [
            'SECRET_KEY',
            'ENCRYPTION_KEY',
            'DATABASE_URL',
            'AI_API_KEY'
        ]
        
        missing_vars = [var for var in required_env_vars if not os.environ.get(var)]
        if missing_vars:
            raise RuntimeError(f"Missing required environment variables: {', '.join(missing_vars)}")