"""
Script to reset a user's password.
This can be useful when encryption keys have changed or when users forget their passwords.
"""
import os
import sys
from dotenv import load_dotenv
from flask import Flask
from services.auth_service import auth_service
from models.user import User
from models.database import db

# Load environment variables
load_dotenv()

def create_app():
    """Create a minimal Flask app for the script."""
    app = Flask(__name__)
    
    # Configure the app
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///instance/job_agent.db')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['ENCRYPTION_KEY'] = os.environ.get('ENCRYPTION_KEY', 'development_encryption_key_123456789')
    
    # Initialize database
    db.init_app(app)
    
    return app

def reset_password(email, new_password):
    """Reset a user's password."""
    app = create_app()
    
    with app.app_context():
        # Find user by email
        user = User.query.filter_by(email=email.lower()).first()
        
        if not user:
            print(f"User with email {email} not found.")
            return False
        
        # Reset password
        success = auth_service.set_password(user.id, new_password)
        
        if success:
            print(f"Password for {email} has been reset successfully.")
        else:
            print(f"Failed to reset password for {email}.")
        
        return success

def list_users():
    """List all users in the database."""
    app = create_app()
    
    with app.app_context():
        users = User.query.all()
        
        if not users:
            print("No users found in the database.")
            return
        
        print(f"Found {len(users)} users:")
        for user in users:
            print(f"- {user.email} (ID: {user.id})")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  List all users: python reset_user_password.py list")
        print("  Reset password: python reset_user_password.py reset <email> <new_password>")
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == "list":
        list_users()
    elif command == "reset" and len(sys.argv) == 4:
        email = sys.argv[2]
        new_password = sys.argv[3]
        reset_password(email, new_password)
    else:
        print("Invalid command or missing arguments.")
        print("Usage:")
        print("  List all users: python reset_user_password.py list")
        print("  Reset password: python reset_user_password.py reset <email> <new_password>")