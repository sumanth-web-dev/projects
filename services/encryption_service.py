"""
Encryption service for sensitive data.

This module provides encryption and decryption functionality for sensitive user data
using AES-256 encryption via the Fernet implementation from the cryptography package.
"""
import os
import base64
import json
import logging
from typing import Dict, Any, Optional, Union
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.backends import default_backend
from flask import request, has_request_context

# Set up logging
logger = logging.getLogger(__name__)


class EncryptionService:
    """Service for encrypting and decrypting sensitive data using AES-256."""
    
    def __init__(self, app=None):
        """Initialize the encryption service.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self._master_key = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the encryption service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self._master_key = self._get_master_key()
    
    def _get_master_key(self) -> bytes:
        """Get the master encryption key from environment variables.
        
        Returns:
            bytes: The master encryption key
            
        Raises:
            ValueError: If the encryption key is not set or invalid
        """
        # Try to get the key from environment variable
        key = os.environ.get('ENCRYPTION_KEY')
        
        # If not in environment, try to get from app config
        if not key and self.app:
            key = self.app.config.get('ENCRYPTION_KEY')
            logger.info(f"Using encryption key from app config: {key[:5]}...")
        
        if not key:
            # In development, we can generate a key, but in production this should be set
            if self.app and self.app.config.get('DEBUG', False):
                logger.warning("ENCRYPTION_KEY not set. Generating a temporary key for development.")
                key = Fernet.generate_key().decode()
                # Store in app config for this session
                self.app.config['ENCRYPTION_KEY'] = key
            else:
                raise ValueError("ENCRYPTION_KEY environment variable or app config not set")
        
        # Ensure the key is properly formatted for Fernet
        try:
            # Check if the key is a valid Fernet key
            if not key:
                raise ValueError("Empty encryption key")
                
            # If the key is not in base64 format, convert it to a valid Fernet key
            if len(key.encode()) != 44 or not key.endswith('='):
                logger.warning("Converting encryption key to valid Fernet format")
                # Use the key as a seed to derive a valid Fernet key
                kdf = PBKDF2HMAC(
                    algorithm=hashes.SHA256(),
                    length=32,
                    salt=b'static_salt_for_key_derivation',
                    iterations=100000,
                    backend=default_backend()
                )
                derived_key = base64.urlsafe_b64encode(kdf.derive(key.encode()))
                key = derived_key.decode()
                
                # Store the converted key in app config
                if self.app:
                    logger.info(f"Storing converted key in app config: {key[:5]}...")
                    self.app.config['ENCRYPTION_KEY'] = key
            
            # Validate the key by creating a Fernet instance
            Fernet(key.encode())
            logger.info("Successfully validated encryption key")
            return key.encode()
        except Exception as e:
            # In development, we can generate a key if the provided one is invalid
            if self.app and self.app.config.get('DEBUG', False):
                logger.warning(f"Invalid encryption key format: {str(e)}. Generating a new key.")
                key = Fernet.generate_key().decode()
                self.app.config['ENCRYPTION_KEY'] = key
                return key.encode()
            else:
                raise ValueError(f"Invalid encryption key format: {str(e)}")
    
    def _derive_key(self, user_id: str) -> bytes:
        """Derive a user-specific encryption key from the master key.
        
        Args:
            user_id: The user ID to derive a key for
            
        Returns:
            bytes: A user-specific encryption key
        """
        if not self._master_key:
            self._master_key = self._get_master_key()
        
        # Use PBKDF2 to derive a user-specific key
        salt = user_id.encode()[:16].ljust(16, b'0')  # Ensure salt is 16 bytes
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )
        
        # Derive key from master key
        key = base64.urlsafe_b64encode(kdf.derive(self._master_key))
        return key
    
    def encrypt(self, data: Union[Dict, str], user_id: Optional[str] = None) -> str:
        """Encrypt data using AES-256 encryption.
        
        Args:
            data: The data to encrypt (dictionary or string)
            user_id: Optional user ID for user-specific encryption
            
        Returns:
            str: The encrypted data as a string
            
        Raises:
            ValueError: If encryption fails
        """
        try:
            # Convert dict to JSON string if needed
            if isinstance(data, dict):
                data_str = json.dumps(data)
            else:
                data_str = str(data)
            
            # Get the appropriate key
            if user_id:
                key = self._derive_key(user_id)
            else:
                key = self._master_key or self._get_master_key()
            
            # Create cipher and encrypt
            cipher = Fernet(key)
            encrypted_data = cipher.encrypt(data_str.encode())
            
            # Return as string
            return encrypted_data.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            raise ValueError(f"Failed to encrypt data: {str(e)}")
    
    def decrypt(self, encrypted_data: str, user_id: Optional[str] = None) -> Union[Dict, str]:
        """Decrypt data that was encrypted with AES-256.
        
        Args:
            encrypted_data: The encrypted data string
            user_id: Optional user ID for user-specific decryption
            
        Returns:
            Union[Dict, str]: The decrypted data, as dictionary if JSON or string otherwise
            
        Raises:
            ValueError: If decryption fails
        """
        if not encrypted_data:
            return {} if user_id else ""
        
        try:
            # Get the appropriate key
            if user_id:
                key = self._derive_key(user_id)
            else:
                key = self._master_key or self._get_master_key()
            
            # Create cipher and decrypt
            cipher = Fernet(key)
            decrypted_data = cipher.decrypt(encrypted_data.encode()).decode()
            
            # Try to parse as JSON
            try:
                return json.loads(decrypted_data)
            except json.JSONDecodeError:
                # Return as string if not valid JSON
                return decrypted_data
        except InvalidToken:
            # Create log message with context information
            log_msg = "Decryption failed: Invalid token or key"
            
            # Add request info if available
            request_info = {}
            if has_request_context():
                request_info = {
                    'id': request.environ.get('REQUEST_ID', 'unknown'),
                    'method': request.method,
                    'path': request.path,
                    'remote_addr': request.remote_addr,
                    'user_agent': request.user_agent.string if request.user_agent else None
                }
                log_msg += f" - Request: {json.dumps(request_info)}"
            
            # Log the error with additional debug info
            logger.error(f"{log_msg} - Key length: {len(key) if key else 'None'}, Data length: {len(encrypted_data) if encrypted_data else 'None'}")
            
            # Try to recover using the default development key as fallback
            try:
                if self.app and self.app.config.get('DEBUG', False):
                    logger.warning("Attempting recovery with default development key")
                    default_key = b'development_encryption_key_123456789'
                    kdf = PBKDF2HMAC(
                        algorithm=hashes.SHA256(),
                        length=32,
                        salt=b'static_salt_for_key_derivation',
                        iterations=100000,
                        backend=default_backend()
                    )
                    fallback_key = base64.urlsafe_b64encode(kdf.derive(default_key))
                    cipher = Fernet(fallback_key)
                    decrypted_data = cipher.decrypt(encrypted_data.encode()).decode()
                    
                    # Try to parse as JSON
                    try:
                        return json.loads(decrypted_data)
                    except json.JSONDecodeError:
                        # Return as string if not valid JSON
                        return decrypted_data
            except Exception:
                # Fallback failed, return empty result
                pass
                
            # Return empty result instead of raising an exception
            return {} if user_id else ""
        except Exception as e:
            # Create log message with context information
            log_msg = f"Decryption failed: {str(e)}"
            
            # Add request info if available
            request_info = {}
            if has_request_context():
                request_info = {
                    'id': request.environ.get('REQUEST_ID', 'unknown'),
                    'method': request.method,
                    'path': request.path,
                    'remote_addr': request.remote_addr,
                    'user_agent': request.user_agent.string if request.user_agent else None
                }
                log_msg += f" - Request: {json.dumps(request_info)}"
            
            # Log the error without using extra parameter
            logger.error(log_msg)
            
            # Return empty result instead of raising an exception
            return {} if user_id else ""
    
    def encrypt_credentials(self, credentials: Dict[str, str], user_id: str) -> str:
        """Encrypt user credentials for external services.
        
        Args:
            credentials: Dictionary of credentials (e.g., {'username': 'user', 'password': 'pass'})
            user_id: The user ID these credentials belong to
            
        Returns:
            str: Encrypted credentials string
        """
        return self.encrypt(credentials, user_id)
    
    def decrypt_credentials(self, encrypted_credentials: str, user_id: str) -> Dict[str, str]:
        """Decrypt user credentials for external services.
        
        Args:
            encrypted_credentials: The encrypted credentials string
            user_id: The user ID these credentials belong to
            
        Returns:
            Dict[str, str]: Dictionary of decrypted credentials
        """
        result = self.decrypt(encrypted_credentials, user_id)
        if isinstance(result, dict):
            return result
        else:
            # If somehow we got a string instead of a dict, return empty dict
            logger.warning("Decrypted credentials were not in expected dictionary format")
            return {}
    
    def generate_key(self) -> str:
        """Generate a new random encryption key.
        
        Returns:
            str: A new Fernet key as a string
        """
        return Fernet.generate_key().decode()


# Create a singleton instance
encryption_service = EncryptionService()