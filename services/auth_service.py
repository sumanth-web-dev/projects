"""
Authentication service for user authentication and session management.

This module provides functionality for user authentication, password hashing,
session management, and API key generation and validation.
"""
import os
import uuid
import secrets
import logging
import datetime
from typing import Dict, Optional, Tuple, Union
from flask import current_app, session, request
import bcrypt
from sqlalchemy.exc import SQLAlchemyError
from models.database import db
from services.encryption_service import encryption_service

# Set up logging
logger = logging.getLogger(__name__)


class AuthService:
    """Service for user authentication and session management."""
    
    def __init__(self, app=None):
        """Initialize the authentication service.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the authentication service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
    
    def hash_password(self, password: str) -> str:
        """Hash a password using bcrypt.
        
        Args:
            password: The plain text password to hash
            
        Returns:
            str: The hashed password
        """
        # Generate a salt and hash the password
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed_password: str) -> bool:
        """Verify a password against a hash.
        
        Args:
            password: The plain text password to verify
            hashed_password: The hashed password to check against
            
        Returns:
            bool: True if the password matches, False otherwise
        """
        try:
            return bcrypt.checkpw(
                password.encode('utf-8'),
                hashed_password.encode('utf-8')
            )
        except Exception as e:
            logger.error(f"Password verification error: {str(e)}")
            return False
    
    def authenticate_user(self, email: str, password: str) -> Tuple[bool, Optional[Dict], str]:
        """Authenticate a user with email and password.
        
        Args:
            email: The user's email
            password: The user's password
            
        Returns:
            Tuple[bool, Optional[Dict], str]: (success, user_data, message)
        """
        from models.user import User
        
        try:
            # Find user by email
            user = User.query.filter_by(email=email.lower()).first()
            
            if not user:
                return False, None, "Invalid email or password"
            
            if not user.is_active:
                return False, None, "Account is inactive"
            
            # Get user credentials from encrypted personal data
            personal_data = user.personal_data
            stored_password = personal_data.get('password')
            
            if not stored_password:
                return False, None, "Password not set for this account"
            
            # Verify password
            if not self.verify_password(password, stored_password):
                return False, None, "Invalid email or password"
            
            # Return user data without sensitive information
            return True, user.to_dict(), "Authentication successful"
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False, None, f"Authentication error: {str(e)}"
    
    def create_user(self, email: str, password: str, personal_data: Dict = None) -> Tuple[bool, Optional[str], str]:
        """Create a new user account.
        
        Args:
            email: The user's email
            password: The user's password
            personal_data: Optional personal data for the user
            
        Returns:
            Tuple[bool, Optional[str], str]: (success, user_id, message)
        """
        from models.user import User
        
        try:
            # Check if user already exists
            existing_user = User.query.filter_by(email=email.lower()).first()
            if existing_user:
                return False, None, "Email already registered"
            
            # Create user ID
            user_id = str(uuid.uuid4())
            
            # Initialize personal data
            user_personal_data = personal_data or {}
            
            # Hash password and store in personal data
            hashed_password = self.hash_password(password)
            user_personal_data['password'] = hashed_password
            
            # Create new user
            new_user = User(
                id=user_id,
                email=email
            )
            
            # Set personal data with encrypted password
            new_user.personal_data = user_personal_data
            
            # Save to database
            db.session.add(new_user)
            db.session.commit()
            
            return True, user_id, "User created successfully"
            
        except ValueError as e:
            # Validation error
            db.session.rollback()
            return False, None, str(e)
        except SQLAlchemyError as e:
            # Database error
            db.session.rollback()
            logger.error(f"Database error creating user: {str(e)}")
            return False, None, "Database error creating user"
        except Exception as e:
            # Other errors
            db.session.rollback()
            logger.error(f"Error creating user: {str(e)}")
            return False, None, f"Error creating user: {str(e)}"
    
    def update_password(self, user_id: str, current_password: str, new_password: str) -> Tuple[bool, str]:
        """Update a user's password.
        
        Args:
            user_id: The user's ID
            current_password: The current password
            new_password: The new password
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        from models.user import User
        
        try:
            # Find user
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            # Get user credentials from encrypted personal data
            personal_data = user.personal_data
            stored_password = personal_data.get('password')
            
            if not stored_password:
                return False, "Password not set for this account"
            
            # Verify current password
            if not self.verify_password(current_password, stored_password):
                return False, "Current password is incorrect"
            
            # Update password
            personal_data['password'] = self.hash_password(new_password)
            user.personal_data = personal_data
            
            # Save to database
            db.session.commit()
            
            return True, "Password updated successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Password update error: {str(e)}")
            return False, f"Password update error: {str(e)}"
    
    def create_session(self, user_id: str) -> None:
        """Create a new session for a user.
        
        Args:
            user_id: The user's ID
        """
        # Set session data
        session['user_id'] = user_id
        session['authenticated'] = True
        session['login_time'] = datetime.datetime.utcnow().isoformat()
        session.permanent = True
    
    def end_session(self) -> None:
        """End the current user session."""
        # Clear session data
        session.clear()
    
    def get_current_user_id(self) -> Optional[str]:
        """Get the current user ID from the session.
        
        Returns:
            Optional[str]: The user ID if authenticated, None otherwise
        """
        if session.get('authenticated'):
            return session.get('user_id')
        return None
    
    def generate_api_key(self, user_id: str, description: str = None) -> Tuple[bool, Optional[str], str]:
        """Generate a new API key for a user.
        
        Args:
            user_id: The user's ID
            description: Optional description of the API key
            
        Returns:
            Tuple[bool, Optional[str], str]: (success, api_key, message)
        """
        from models.user import User
        
        try:
            # Find user
            user = User.query.get(user_id)
            if not user:
                return False, None, "User not found"
            
            # Generate API key
            api_key = f"jaa_{secrets.token_urlsafe(32)}"
            
            # Get user personal data
            personal_data = user.personal_data
            
            # Initialize API keys if not present
            if 'api_keys' not in personal_data:
                personal_data['api_keys'] = {}
            
            # Add new API key with metadata
            personal_data['api_keys'][api_key] = {
                'created_at': datetime.datetime.utcnow().isoformat(),
                'description': description or "API Key",
                'last_used': None
            }
            
            # Update user data
            user.personal_data = personal_data
            db.session.commit()
            
            return True, api_key, "API key generated successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"API key generation error: {str(e)}")
            return False, None, f"API key generation error: {str(e)}"
    
    def revoke_api_key(self, user_id: str, api_key: str) -> Tuple[bool, str]:
        """Revoke an API key.
        
        Args:
            user_id: The user's ID
            api_key: The API key to revoke
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        from models.user import User
        
        try:
            # Find user
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            # Get user personal data
            personal_data = user.personal_data
            
            # Check if API keys exist
            if 'api_keys' not in personal_data:
                return False, "No API keys found"
            
            # Check if the specific API key exists
            if api_key not in personal_data['api_keys']:
                return False, "API key not found"
            
            # Remove the API key
            del personal_data['api_keys'][api_key]
            
            # Update user data
            user.personal_data = personal_data
            db.session.commit()
            
            return True, "API key revoked successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"API key revocation error: {str(e)}")
            return False, f"API key revocation error: {str(e)}"
    
    def validate_api_key(self, api_key: str) -> Tuple[bool, Optional[str]]:
        """Validate an API key and return the associated user ID.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            Tuple[bool, Optional[str]]: (valid, user_id)
        """
        from models.user import User
        
        try:
            # Check API key format
            if not api_key or not api_key.startswith('jaa_'):
                return False, None
            
            # Query all users (not efficient for large systems, but works for small user base)
            users = User.query.filter_by(is_active=True).all()
            
            for user in users:
                personal_data = user.personal_data
                
                # Check if user has API keys
                if 'api_keys' not in personal_data:
                    continue
                
                # Check if this API key exists for the user
                if api_key in personal_data['api_keys']:
                    # Update last used timestamp
                    personal_data['api_keys'][api_key]['last_used'] = datetime.datetime.utcnow().isoformat()
                    user.personal_data = personal_data
                    db.session.commit()
                    
                    return True, user.id
            
            return False, None
            
        except Exception as e:
            logger.error(f"API key validation error: {str(e)}")
            return False, None


# Create a singleton instance
auth_service = AuthService()