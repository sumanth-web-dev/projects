"""
Script to create an admin user for the Job Application Agent.
"""
import os
import sys
from flask import Flask
from models.database import init_db
from services.auth_service import auth_service
from models.user import User

def create_app():
    """Create a minimal Flask app for database operations."""
    app = Flask(__name__)
    
    # Ensure instance directory exists
    import os
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/job_agent.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    init_db(app)
    return app

def create_admin_user(app, email, password):
    """Create an admin user."""
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(email=email.lower()).first()
        if existing_user:
            print(f"User {email} already exists.")
            return
        
        # Create user
        success, user_id, message = auth_service.create_user(
            email=email,
            password=password,
            personal_data={'roles': ['admin', 'user']}
        )
        
        if success:
            print(f"Admin user created successfully: {email}")
        else:
            print(f"Failed to create admin user: {message}")

if __name__ == '__main__':
    app = create_app()
    
    # Default credentials
    email = 'admin@example.com'
    password = 'admin123'
    
    # Use command line arguments if provided
    if len(sys.argv) > 1:
        email = sys.argv[1]
    if len(sys.argv) > 2:
        password = sys.argv[2]
    
    create_admin_user(app, email, password)