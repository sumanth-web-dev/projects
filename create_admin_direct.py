"""
Script to directly create an admin user in the database.
"""
import os
import uuid
import bcrypt
import json
from flask import Flask
from models.database import db, init_db
from services.encryption_service import encryption_service

def create_app():
    """Create a minimal Flask app for database operations."""
    app = Flask(__name__)
    
    # Ensure instance directory exists
    instance_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'instance')
    if not os.path.exists(instance_path):
        os.makedirs(instance_path)
    
    # Configure the app
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///instance/job_agent.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['ENCRYPTION_KEY'] = os.environ.get('ENCRYPTION_KEY', 'development_encryption_key_123456789')
    
    # Initialize services
    init_db(app)
    encryption_service.init_app(app)
    
    return app

def create_admin_user(app, email, password):
    """Create an admin user directly in the database."""
    from models.user import User
    
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter_by(email=email.lower()).first()
        if existing_user:
            print(f"User {email} already exists.")
            return
        
        # Create user ID
        user_id = str(uuid.uuid4())
        
        # Hash password
        salt = bcrypt.gensalt()
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
        # Create personal data with password and roles
        personal_data = {
            'password': hashed_password,
            'roles': ['admin', 'user'],
            'first_name': 'Admin',
            'last_name': 'User'
        }
        
        # Create new user
        new_user = User(
            id=user_id,
            email=email
        )
        
        # Encrypt and set personal data
        encrypted_data = encryption_service.encrypt(personal_data, user_id)
        new_user.encrypted_personal_data = encrypted_data
        
        # Save to database
        db.session.add(new_user)
        db.session.commit()
        
        print(f"Admin user created successfully: {email}")
        print(f"User ID: {user_id}")
        print(f"Password: {password}")

if __name__ == '__main__':
    app = create_app()
    
    # Default credentials
    email = 'admin@example.com'
    password = 'admin123'
    
    create_admin_user(app, email, password)