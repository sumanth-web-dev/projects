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
    
    # File upload settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    
    # Encryption settings
    ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
    
    # AI service settings
    AI_API_KEY = os.environ.get('AI_API_KEY')
    
    # Rate limiting settings
    RATELIMIT_STORAGE_URL = "memory://"


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