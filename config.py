"""
Configuration settings for the Job Application Agent.
"""
import os
from datetime import timedelta


class Config:
    """Base configuration class."""
    
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database settings
    def __init__(self):
        """Initialize database URI with proper path resolution."""
        if os.environ.get('DATABASE_URL'):
            self.SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
        else:
            # Use absolute path for SQLite database
            base_dir = os.path.abspath(os.path.dirname(__file__))
            db_path = os.path.join(base_dir, 'instance', 'job_agent.db')
            self.SQLALCHEMY_DATABASE_URI = f'sqlite:///{db_path}'
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Ensure instance directory exists
    @staticmethod
    def init_app(app):
        """Initialize configuration-specific settings."""
        # Create instance directory if it doesn't exist
        instance_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
        os.makedirs(instance_dir, exist_ok=True)
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = True  # Only send cookies over HTTPS
    SESSION_COOKIE_HTTPONLY = True  # Prevent JavaScript access to cookies
    SESSION_COOKIE_SAMESITE = 'Lax'  # CSRF protection
    SESSION_REFRESH_EACH_REQUEST = True  # Refresh session on each request
    SESSION_MAX_AGE = 86400  # 24 hours in seconds
    
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    
    # Encryption settings
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
    
    # AI service settings
    AI_API_KEY = os.environ.get('AI_API_KEY')
    
    # Rate limiting settings
    RATELIMIT_STORAGE_URL = "memory://"
    
    # Logging settings
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
    CONSOLE_LOGGING = True
    FILE_LOGGING = True
    JSON_LOGGING = True
    LOG_BACKUP_COUNT = 10
    MAX_LOG_SIZE = 10 * 1024 * 1024  # 10 MB
    
    # Monitoring settings
    MONITORING_ENABLED = True
    METRICS_INTERVAL = 60  # seconds
    METRICS_RETENTION_DAYS = 7  # days
    ALERT_THRESHOLDS = {
        'cpu_usage': 80.0,  # percentage
        'memory_usage': 80.0,  # percentage
        'disk_usage': 80.0,  # percentage
        'error_rate': 5.0,  # percentage
        'response_time': 1000.0  # milliseconds
    }
    
    # Admin settings
    ADMIN_USER_ID = os.environ.get('ADMIN_USER_ID')


class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    @staticmethod
    def init_app(app):
        """Initialize testing-specific settings."""
        # For testing, we don't need to create instance directory
        pass