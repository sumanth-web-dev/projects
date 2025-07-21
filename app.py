"""
Main Flask application entry point for the Job Application Agent.
"""
import os
import logging
import secrets
import uuid
from datetime import datetime
from flask import Flask, session
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from configuration import Config, DevelopmentConfig, ProductionConfig, TestingConfig
from api import api_bp
from api.auth_routes import auth_bp
from api.error_handlers import register_error_handlers
from api.rate_limiter import apply_default_rate_limits
from routes import main_bp
from models.database import init_db
from models.migrations import migration_manager
from services.encryption_service import encryption_service
from services.auth_service import auth_service
from services.logging_service import logging_service
from services.monitoring_service import monitoring_service
from services.notification_service import notification_service
from services.security_audit_service import security_audit_service
from services.otp_service import otp_service
from services.recommendation_service import recommendation_service
from services.resume_parser_service import resume_parser_service
from services.analytics_service import analytics_service
from services.job_search_service import job_search_service
from services.campus_drive_service import campus_drive_service
from services.admin_service import admin_service


def create_app(config_name='Config'):
    """Application factory pattern for creating Flask app."""
    # Ensure instance directory exists
    import os
    from datetime import datetime
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    
    # Create Flask app with explicit static folder
    static_folder = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static')
    app = Flask(__name__, 
                static_folder=static_folder, 
                static_url_path='/static')
    
    # Function to create default admin user
    def create_default_admin():
        from services.auth_service import auth_service
        from models.user import User
        
        # Check if admin user exists
        admin_email = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
        admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
        admin_role = os.environ.get('ADMIN_ROLE', 'admin')
        admin_id = os.environ.get('ADMIN_USER_ID', str(uuid.uuid4()))

        # Check if user exists
        admin_user = User.query.filter_by(email=admin_email).first()
        if not admin_user:
            # Create admin user with specific ID
            success, user_id, message = auth_service.create_user(
                email=admin_email,
                password=admin_password,
                personal_data={'roles': ['admin', 'user', 'hr']},
                user_id=admin_id
            )
            if success:
                print(f"Created admin user: {admin_email} with ID: {user_id}")
                # Set the admin user ID in app config
                app.config['ADMIN_USER_ID'] = user_id
            else:
                print(f"Failed to create admin user: {message}")
        else:
            # Set the admin user ID in app config
            app.config['ADMIN_USER_ID'] = admin_user.id
    
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
    
    # Set up secure session configuration
    app.config['SESSION_COOKIE_SECURE'] = app.config.get('SESSION_COOKIE_SECURE', True)
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['PERMANENT_SESSION_LIFETIME'] = app.config.get('PERMANENT_SESSION_LIFETIME', 86400)  # 24 hours
    
    # Generate a secure secret key if not provided
    if not app.config.get('SECRET_KEY'):
        app.config['SECRET_KEY'] = secrets.token_hex(32)
    
    # Initialize logging service first
    logging_service.init_app(app)
    
    # Initialize security audit service
    security_audit_service.init_app(app)
    
    # Initialize database
    init_db(app)
    
    # Initialize migration manager
    migration_manager.init_app(app)
    
    # Create all database tables before creating default admin user
    from models.database import create_tables
    with app.app_context():
        create_tables(app)
        create_default_admin()
        
        # Set admin email in config for error notifications
        app.config['ADMIN_EMAIL'] = os.environ.get('ADMIN_EMAIL', 'admin@example.com')
    
    # Initialize encryption service
    # Ensure we're using the correct encryption key from environment
    encryption_key = os.environ.get('ENCRYPTION_KEY')
    if not encryption_key:
        app.logger.warning("ENCRYPTION_KEY not found in environment, using fallback from config")
        encryption_key = app.config.get('ENCRYPTION_KEY', 'development_encryption_key_123456789')
    
    app.config['ENCRYPTION_KEY'] = encryption_key
    app.logger.info(f"Initializing encryption service with key: {encryption_key[:5]}...")
    encryption_service.init_app(app)
    
    # Initialize authentication service
    auth_service.init_app(app)
    
    # Initialize notification service
    notification_service.init_app(app)
    
    # Initialize monitoring service
    monitoring_service.init_app(app)
    
    # Initialize OTP service
    otp_service.init_app(app)
    
    # Initialize recommendation service
    recommendation_service.init_app(app)
    
    # Initialize resume parser service
    resume_parser_service.init_app(app)
    
    # Initialize analytics service
    analytics_service.init_app(app)
    
    # Initialize job search service
    job_search_service.init_app(app)
    
    # Initialize campus drive service
    campus_drive_service.init_app(app)
    
    # Initialize admin service
    admin_service.init_app(app)
    
    # Register error handlers
    register_error_handlers(app)
    
    # Import role-based blueprints
    from api.user_routes import user_bp
    try:
        from api.hr_routes_enhanced import hr_bp
    except ImportError:
        from api.hr_routes import hr_bp
    from api.admin_routes import admin_bp
    try:
        from api.student_routes_enhanced import student_bp
    except ImportError:
        from api.student_routes import student_bp
    from api.job_routes import job_bp
    from api.campus_drive_routes import campus_drive_bp
    
    # Import API endpoints
    from api.user_role import get_current_user_role
    
    # Register blueprints
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(hr_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(student_bp)
    app.register_blueprint(job_bp)
    app.register_blueprint(campus_drive_bp)
    
    # Apply rate limiting to API endpoints
    apply_default_rate_limits(app)
    
    # Register custom Jinja2 filters
    @app.template_filter('date')
    def format_date(value, format='%b %d, %Y'):
        """Format a date using this filter"""
        if value is None:
            return ""
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d')
            except ValueError:
                try:
                    value = datetime.strptime(value, '%Y-%m-%dT%H:%M:%S')
                except ValueError:
                    return value
        return value.strftime(format)
    
    # Generate CSRF token on session creation
    @app.before_request
    def ensure_csrf_token():
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(32)
    
    # Add security headers to all responses
    @app.after_request
    def add_security_headers(response):
        # Prevent browsers from performing MIME type sniffing
        response.headers['X-Content-Type-Options'] = 'nosniff'
        
        # Prevent clickjacking by restricting framing
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        
        # Enable browser XSS protection
        response.headers['X-XSS-Protection'] = '1; mode=block'
        
        # Set Content Security Policy
        csp = "default-src 'self'; script-src 'self' https://code.jquery.com https://cdn.jsdelivr.net https://stackpath.bootstrapcdn.com; style-src 'self' 'unsafe-inline' https://stackpath.bootstrapcdn.com https://cdnjs.cloudflare.com; font-src 'self' https://cdnjs.cloudflare.com; img-src 'self' data:;"
        response.headers['Content-Security-Policy'] = csp
        
        # Set referrer policy
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        
        return response
        
    # Add context processor for template variables
    @app.context_processor
    def inject_template_vars():
        return {
            'now': datetime.now(),
            'csrf_token': lambda: session.get('csrf_token', '')
        }
    


    
    return app




if __name__ == '__main__':
    app = create_app()
    
    # Set up more detailed logging for debugging
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
    # Log all routes for debugging
    print("Available routes:")
    for rule in app.url_map.iter_rules():
        print(f"{rule.endpoint}: {rule.rule}")
    
    # Run the application on localhost:5000
    print("Starting application on http://localhost:5000/")
    app.run(debug=True, host='localhost', port=5000,use_reloader=False)