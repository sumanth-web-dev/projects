"""
Main Flask application entry point for the Job Application Agent.
"""
from flask import Flask
from config import Config, DevelopmentConfig, ProductionConfig, TestingConfig
from api import api_bp
from models.database import init_db
from models.migrations import migration_manager
from services.encryption_service import encryption_service
from services.auth_service import auth_service


def create_app(config_name='Config'):
    """Application factory pattern for creating Flask app."""
    app = Flask(__name__)
    
    # Get the appropriate config class
    if config_name == 'TestingConfig':
        config_class = TestingConfig
    elif config_name == 'DevelopmentConfig':
        config_class = DevelopmentConfig
    elif config_name == 'ProductionConfig':
        config_class = ProductionConfig
    else:
        config_class = Config
    
    config_instance = config_class()
    app.config.from_object(config_instance)
    
    # Initialize configuration-specific settings
    config_class.init_app(app)
    
    # Initialize database
    init_db(app)
    
    # Initialize migration manager
    migration_manager.init_app(app)
    
    # Initialize encryption service
    encryption_service.init_app(app)
    
    # Initialize authentication service
    auth_service.init_app(app)
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')
    
    return app


if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, host='0.0.0.0', port=5000)