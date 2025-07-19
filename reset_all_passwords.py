"""
Script to reset all user passwords to a default value.
This can be useful after changing encryption keys.
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
    app.config['ENCRYPTION_KEY'] = os.environ.get('ENCRYPTION_KEY')
    
    # Initialize database
    db.init_app(app)
    
    return app

def reset_all_passwords(default_password):
    """Reset all user passwords to a default value."""
    app = create_app()
    
    with app.app_context():
        # Get all users
        users = User.query.all()
        
        if not users:
            print("No users found in the database.")
            return
        
        print(f"Found {len(users)} users. Resetting passwords...")
        
        success_count = 0
        fail_count = 0
        
        for user in users:
            # Reset password
            success = auth_service.set_password(user.id, default_password)
            
            if success:
                success_count += 1
                print(f"✓ Reset password for {user.email}")
            else:
                fail_count += 1
                print(f"✗ Failed to reset password for {user.email}")
        
        print(f"\nSummary: {success_count} passwords reset successfully, {fail_count} failed.")

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python reset_all_passwords.py <default_password>")
        sys.exit(1)
    
    default_password = sys.argv[1]
    
    # Confirm before proceeding
    print("WARNING: This will reset ALL user passwords to the specified default.")
    print("Users will need to change their passwords after logging in.")
    confirmation = input("Are you sure you want to proceed? (yes/no): ")
    
    if confirmation.lower() == "yes":
        reset_all_passwords(default_password)
    else:
        print("Operation cancelled.")