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
import time
import json
from typing import Dict, Optional, Tuple, Union, List, Any
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
        self._auth_log_path = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the authentication service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        
        # Set up authentication logging
        log_dir = os.path.join(app.instance_path, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        self._auth_log_path = os.path.join(log_dir, 'auth.log')
    
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
                # Log failed authentication attempt
                self.log_auth_attempt(False, 'login', email, {'reason': 'user_not_found'})
                return False, None, "Invalid email or password"
            
            if not user.is_active:
                # Log failed authentication attempt
                self.log_auth_attempt(False, 'login', email, {'reason': 'account_inactive', 'user_id': user.id})
                return False, None, "Account is inactive"
            
            # Get user credentials from encrypted personal data
            try:
                personal_data = user.personal_data or {}
                stored_password = personal_data.get('password')
            except Exception as e:
                logger.error(f"Error retrieving personal data: {str(e)}")
                self.log_auth_attempt(False, 'login', email, {'reason': 'personal_data_error', 'user_id': user.id})
                return False, None, "Authentication error: Unable to retrieve user data"
            
            if not stored_password:
                # If this is the first login and no password is set, set the provided password
                # This is useful for accounts created by admins or imported from other systems
                if self.set_password(user.id, password):
                    # Log successful authentication after setting password
                    self.log_auth_attempt(True, 'login', email, {'user_id': user.id, 'note': 'password_set_on_first_login'})
                    return True, user.to_dict(), "Authentication successful"
                else:
                    # Log failed authentication attempt
                    self.log_auth_attempt(False, 'login', email, {'reason': 'password_set_failed', 'user_id': user.id})
                    return False, None, "Failed to set password for this account"
            
            # Verify password
            if not self.verify_password(password, stored_password):
                # Log failed authentication attempt
                self.log_auth_attempt(False, 'login', email, {'reason': 'invalid_password', 'user_id': user.id})
                return False, None, "Invalid email or password"
            
            # Log successful authentication
            self.log_auth_attempt(True, 'login', email, {'user_id': user.id})
            
            # Return user data without sensitive information
            return True, user.to_dict(), "Authentication successful"
            
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            # Log error
            self.log_auth_attempt(False, 'login', email, {'reason': 'error', 'error': str(e)})
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
            
            # Initialize roles if not already set
            if 'roles' not in user_personal_data:
                user_personal_data['roles'] = ['user']  # Default role
            
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
            
            # Log user creation
            self.log_auth_attempt(True, 'user_creation', email, {'user_id': user_id})
            
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
    
    def set_password(self, user_id: str, password: str) -> bool:
        """Set a user's password without requiring the current password.
        
        This is useful for setting a password for the first time or for admin resets.
        
        Args:
            user_id: The user's ID
            password: The new password
            
        Returns:
            bool: True if successful, False otherwise
        """
        from models.user import User
        
        try:
            # Find user
            user = User.query.get(user_id)
            if not user:
                return False
            
            # Get user data
            try:
                personal_data = user.personal_data or {}
            except Exception as e:
                logger.error(f"Error retrieving personal data: {str(e)}")
                return False
            
            # Hash and set password
            hashed_password = self.hash_password(password)
            personal_data['password'] = hashed_password
            
            # Update user data
            user.personal_data = personal_data
            db.session.commit()
            
            return True
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Password set error: {str(e)}")
            return False
    
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
            try:
                personal_data = user.personal_data or {}
                stored_password = personal_data.get('password')
            except Exception as e:
                logger.error(f"Error retrieving personal data: {str(e)}")
                return False, "Authentication error: Unable to retrieve user data"
            
            if not stored_password:
                return False, "Password not set for this account"
            
            # Verify current password
            if not self.verify_password(current_password, stored_password):
                # Log failed password update
                self.log_auth_attempt(False, 'password_update', user.email, 
                                     {'user_id': user_id, 'reason': 'invalid_current_password'})
                return False, "Current password is incorrect"
            
            # Update password
            personal_data['password'] = self.hash_password(new_password)
            user.personal_data = personal_data
            
            # Save to database
            db.session.commit()
            
            # Log successful password update
            self.log_auth_attempt(True, 'password_update', user.email, {'user_id': user_id})
            
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
        session['login_time'] = time.time()
        session['created_at'] = datetime.datetime.utcnow().isoformat()
        session.permanent = True
        
        # Generate CSRF token if not already present
        if 'csrf_token' not in session:
            session['csrf_token'] = secrets.token_hex(16)
    
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
    
    def generate_api_key(self, user_id: str, description: str = None, permissions: List[str] = None, 
                         expires_at: Optional[datetime.datetime] = None) -> Tuple[bool, Optional[str], str]:
        """Generate a new API key for a user.
        
        Args:
            user_id: The user's ID
            description: Optional description of the API key
            permissions: Optional list of specific permissions for this API key
            expires_at: Optional expiration date for the API key
            
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
            try:
                personal_data = user.personal_data or {}
            except Exception as e:
                logger.error(f"Error retrieving personal data: {str(e)}")
                return False, None, "Error retrieving user data"
            
            # Initialize API keys if not present
            if 'api_keys' not in personal_data:
                personal_data['api_keys'] = {}
            
            # Add new API key with metadata
            personal_data['api_keys'][api_key] = {
                'created_at': datetime.datetime.utcnow().isoformat(),
                'description': description or "API Key",
                'last_used': None,
                'permissions': permissions or [],
                'expires_at': expires_at.isoformat() if expires_at else None
            }
            
            # Update user data
            user.personal_data = personal_data
            db.session.commit()
            
            # Log API key generation
            self.log_auth_attempt(True, 'api_key_generation', user.email, 
                                 {'user_id': user_id, 'api_key': api_key[:8] + '...'})
            
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
            try:
                personal_data = user.personal_data or {}
            except Exception as e:
                logger.error(f"Error retrieving personal data: {str(e)}")
                return False, "Error retrieving user data"
            
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
            
            # Log API key revocation
            self.log_auth_attempt(True, 'api_key_revocation', user.email, 
                                 {'user_id': user_id, 'api_key': api_key[:8] + '...'})
            
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
        valid, user_id, _ = self.validate_api_key_with_metadata(api_key)
        return valid, user_id
    
    def validate_api_key_with_metadata(self, api_key: str) -> Tuple[bool, Optional[str], Optional[Dict]]:
        """Validate an API key and return the associated user ID and metadata.
        
        Args:
            api_key: The API key to validate
            
        Returns:
            Tuple[bool, Optional[str], Optional[Dict]]: (valid, user_id, metadata)
        """
        from models.user import User
        
        try:
            # Check API key format
            if not api_key or not api_key.startswith('jaa_'):
                return False, None, None
            
            # Query all users (not efficient for large systems, but works for small user base)
            users = User.query.filter_by(is_active=True).all()
            
            for user in users:
                try:
                    personal_data = user.personal_data or {}
                except Exception as e:
                    logger.error(f"Error retrieving personal data: {str(e)}")
                    continue
                
                # Check if user has API keys
                if 'api_keys' not in personal_data:
                    continue
                
                # Check if this API key exists for the user
                if api_key in personal_data['api_keys']:
                    api_key_data = personal_data['api_keys'][api_key]
                    
                    # Check if API key has expired
                    if api_key_data.get('expires_at'):
                        expires_at = datetime.datetime.fromisoformat(api_key_data['expires_at'])
                        if expires_at < datetime.datetime.utcnow():
                            # Log expired API key attempt
                            self.log_auth_attempt(False, 'api_key_validation', api_key[:8] + '...', 
                                                {'user_id': user.id, 'reason': 'expired'})
                            return False, None, None
                    
                    # Update last used timestamp
                    api_key_data['last_used'] = datetime.datetime.utcnow().isoformat()
                    personal_data['api_keys'][api_key] = api_key_data
                    user.personal_data = personal_data
                    db.session.commit()
                    
                    # Log successful API key validation
                    self.log_auth_attempt(True, 'api_key_validation', api_key[:8] + '...', 
                                         {'user_id': user.id})
                    
                    return True, user.id, api_key_data
            
            # Log failed API key validation
            self.log_auth_attempt(False, 'api_key_validation', api_key[:8] + '...', 
                                 {'reason': 'invalid_key'})
            
            return False, None, None
            
        except Exception as e:
            logger.error(f"API key validation error: {str(e)}")
            return False, None, None
    
    def get_user_roles(self, user_id: str) -> List[str]:
        """Get the roles assigned to a user.
        
        Args:
            user_id: The user's ID
            
        Returns:
            List[str]: List of role names
        """
        from models.user import User
        
        try:
            user = User.query.get(user_id)
            if not user:
                return []
            
            # Get roles from user data
            try:
                personal_data = user.personal_data or {}
                return personal_data.get('roles', ['user'])  # Default to 'user' role
            except Exception as e:
                logger.error(f"Error retrieving personal data: {str(e)}")
                return ['user']  # Default to 'user' role on error
            
        except Exception as e:
            logger.error(f"Error getting user roles: {str(e)}")
            return []
    
    def assign_role(self, user_id: str, role: str) -> Tuple[bool, str]:
        """Assign a role to a user.
        
        Args:
            user_id: The user's ID
            role: The role to assign
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        from models.user import User
        
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            # Get user data
            try:
                personal_data = user.personal_data or {}
            except Exception as e:
                logger.error(f"Error retrieving personal data: {str(e)}")
                return False, "Error retrieving user data"
            
            # Initialize roles if not present
            if 'roles' not in personal_data:
                personal_data['roles'] = ['user']
            
            # Add role if not already assigned
            if role not in personal_data['roles']:
                personal_data['roles'].append(role)
                user.personal_data = personal_data
                db.session.commit()
            
            return True, f"Role '{role}' assigned successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error assigning role: {str(e)}")
            return False, f"Error assigning role: {str(e)}"
    
    def remove_role(self, user_id: str, role: str) -> Tuple[bool, str]:
        """Remove a role from a user.
        
        Args:
            user_id: The user's ID
            role: The role to remove
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        from models.user import User
        
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            # Get user data
            try:
                personal_data = user.personal_data or {}
            except Exception as e:
                logger.error(f"Error retrieving personal data: {str(e)}")
                return False, "Error retrieving user data"
            
            # Check if roles exist
            if 'roles' not in personal_data:
                return True, "User has no roles to remove"
            
            # Remove role if present
            if role in personal_data['roles']:
                personal_data['roles'].remove(role)
                user.personal_data = personal_data
                db.session.commit()
            
            return True, f"Role '{role}' removed successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error removing role: {str(e)}")
            return False, f"Error removing role: {str(e)}"
    
    def log_auth_attempt(self, success: bool, auth_type: str, identifier: str, details: Dict[str, Any] = None) -> None:
        """Log an authentication attempt.
        
        Args:
            success: Whether the authentication was successful
            auth_type: The type of authentication (e.g., 'login', 'api_key')
            identifier: The identifier used (e.g., email, API key)
            details: Additional details about the attempt
        """
        if not self._auth_log_path:
            return
        
        try:
            # Create log entry
            log_entry = {
                'timestamp': datetime.datetime.utcnow().isoformat(),
                'success': success,
                'auth_type': auth_type,
                'identifier': identifier,
                'details': details or {}
            }
            
            # Write to log file
            with open(self._auth_log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
                
        except Exception as e:
            logger.error(f"Error logging authentication attempt: {str(e)}")


# Create a singleton instance
auth_service = AuthService()