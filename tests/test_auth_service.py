"""
Tests for the authentication service.
"""
import unittest
import uuid
import datetime
from flask import Flask, session
from models.database import db, init_db
from models.user import User
from services.auth_service import AuthService, auth_service
from services.encryption_service import encryption_service
from config import TestingConfig


class TestAuthService(unittest.TestCase):
    """Test cases for the AuthService class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create Flask app with testing config
        self.app = Flask(__name__)
        self.app.config.from_object(TestingConfig())
        
        # Initialize database
        init_db(self.app)
        
        # Initialize services
        encryption_service.init_app(self.app)
        auth_service.init_app(self.app)
        
        # Create application context
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create database tables
        db.create_all()
        
        # Create test user
        self.test_user_id = str(uuid.uuid4())
        self.test_email = "test@example.com"
        self.test_password = "TestPassword123!"
        
        # Create test user directly
        test_user = User(
            id=self.test_user_id,
            email=self.test_email
        )
        
        # Set password in personal data
        personal_data = {
            'password': auth_service.hash_password(self.test_password),
            'first_name': 'Test',
            'last_name': 'User',
            'phone': '+1234567890',
            'address': '123 Test St',
            'roles': ['user']
        }
        test_user.personal_data = personal_data
        
        # Save to database
        db.session.add(test_user)
        db.session.commit()
    
    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_password_hashing(self):
        """Test password hashing and verification."""
        password = "TestPassword123!"
        
        # Hash password
        hashed = auth_service.hash_password(password)
        
        # Verify password
        self.assertTrue(auth_service.verify_password(password, hashed))
        self.assertFalse(auth_service.verify_password("WrongPassword", hashed))
    
    def test_user_authentication(self):
        """Test user authentication."""
        # Test successful authentication
        success, user_data, message = auth_service.authenticate_user(
            self.test_email, self.test_password
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(user_data)
        self.assertEqual(user_data['id'], self.test_user_id)
        
        # Test failed authentication with wrong password
        success, user_data, message = auth_service.authenticate_user(
            self.test_email, "WrongPassword"
        )
        
        self.assertFalse(success)
        self.assertIsNone(user_data)
        
        # Test failed authentication with non-existent user
        success, user_data, message = auth_service.authenticate_user(
            "nonexistent@example.com", self.test_password
        )
        
        self.assertFalse(success)
        self.assertIsNone(user_data)
    
    def test_user_creation(self):
        """Test user creation."""
        # Test successful user creation
        email = "newuser@example.com"
        password = "NewUserPassword123!"
        personal_data = {
            'first_name': 'New',
            'last_name': 'User',
            'phone': '+1987654321',
            'address': '456 New St'
        }
        
        success, user_id, message = auth_service.create_user(
            email, password, personal_data
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(user_id)
        
        # Verify user was created
        user = User.query.filter_by(email=email).first()
        self.assertIsNotNone(user)
        self.assertEqual(user.id, user_id)
        
        # Verify roles were set
        roles = auth_service.get_user_roles(user_id)
        self.assertIn('user', roles)
        
        # Test duplicate email
        success, user_id, message = auth_service.create_user(
            self.test_email, password
        )
        
        self.assertFalse(success)
        self.assertIsNone(user_id)
    
    def test_api_key_management(self):
        """Test API key generation and validation."""
        # Generate API key
        success, api_key, message = auth_service.generate_api_key(
            self.test_user_id, "Test API Key"
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(api_key)
        self.assertTrue(api_key.startswith('jaa_'))
        
        # Validate API key
        valid, user_id = auth_service.validate_api_key(api_key)
        
        self.assertTrue(valid)
        self.assertEqual(user_id, self.test_user_id)
        
        # Validate API key with metadata
        valid, user_id, metadata = auth_service.validate_api_key_with_metadata(api_key)
        
        self.assertTrue(valid)
        self.assertEqual(user_id, self.test_user_id)
        self.assertEqual(metadata['description'], "Test API Key")
        
        # Revoke API key
        success, message = auth_service.revoke_api_key(
            self.test_user_id, api_key
        )
        
        self.assertTrue(success)
        
        # Validate revoked API key
        valid, user_id = auth_service.validate_api_key(api_key)
        
        self.assertFalse(valid)
        self.assertIsNone(user_id)
    
    def test_api_key_with_permissions_and_expiration(self):
        """Test API key with permissions and expiration date."""
        # Generate API key with permissions and expiration
        permissions = ['read', 'write']
        expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=30)
        
        success, api_key, message = auth_service.generate_api_key(
            self.test_user_id, "Test API Key with Permissions", permissions, expires_at
        )
        
        self.assertTrue(success)
        self.assertIsNotNone(api_key)
        
        # Validate API key with metadata
        valid, user_id, metadata = auth_service.validate_api_key_with_metadata(api_key)
        
        self.assertTrue(valid)
        self.assertEqual(user_id, self.test_user_id)
        self.assertEqual(metadata['description'], "Test API Key with Permissions")
        self.assertEqual(metadata['permissions'], permissions)
        self.assertIsNotNone(metadata['expires_at'])
        
        # Generate expired API key
        expired_at = datetime.datetime.utcnow() - datetime.timedelta(days=1)
        
        success, expired_api_key, message = auth_service.generate_api_key(
            self.test_user_id, "Expired API Key", permissions, expired_at
        )
        
        self.assertTrue(success)
        
        # Validate expired API key
        valid, user_id, metadata = auth_service.validate_api_key_with_metadata(expired_api_key)
        
        self.assertFalse(valid)
        self.assertIsNone(user_id)
        self.assertIsNone(metadata)
    
    def test_session_management(self):
        """Test session management."""
        with self.app.test_request_context():
            # Create session
            auth_service.create_session(self.test_user_id)
            
            # Check session data
            self.assertEqual(session.get('user_id'), self.test_user_id)
            self.assertTrue(session.get('authenticated'))
            self.assertIsNotNone(session.get('login_time'))
            self.assertIsNotNone(session.get('created_at'))
            self.assertIsNotNone(session.get('csrf_token'))
            
            # Get current user ID
            user_id = auth_service.get_current_user_id()
            self.assertEqual(user_id, self.test_user_id)
            
            # End session
            auth_service.end_session()
            
            # Check session data is cleared
            self.assertIsNone(session.get('user_id'))
            self.assertIsNone(session.get('authenticated'))
            
            # Get current user ID after logout
            user_id = auth_service.get_current_user_id()
            self.assertIsNone(user_id)
    
    def test_user_roles(self):
        """Test user role management."""
        # Test getting roles
        roles = auth_service.get_user_roles(self.test_user_id)
        self.assertIn('user', roles)
        
        # Test assigning a new role
        success, message = auth_service.assign_role(self.test_user_id, 'admin')
        self.assertTrue(success)
        
        # Verify role was assigned
        roles = auth_service.get_user_roles(self.test_user_id)
        self.assertIn('user', roles)
        self.assertIn('admin', roles)
        
        # Test removing a role
        success, message = auth_service.remove_role(self.test_user_id, 'admin')
        self.assertTrue(success)
        
        # Verify role was removed
        roles = auth_service.get_user_roles(self.test_user_id)
        self.assertIn('user', roles)
        self.assertNotIn('admin', roles)
        
        # Test with non-existent user
        roles = auth_service.get_user_roles('non-existent-id')
        self.assertEqual(roles, [])
    
    def test_password_update(self):
        """Test password update functionality."""
        new_password = "NewPassword456!"
        
        # Test successful password update
        success, message = auth_service.update_password(
            self.test_user_id, self.test_password, new_password
        )
        
        self.assertTrue(success)
        
        # Verify new password works for authentication
        success, user_data, message = auth_service.authenticate_user(
            self.test_email, new_password
        )
        
        self.assertTrue(success)
        
        # Test with incorrect current password
        success, message = auth_service.update_password(
            self.test_user_id, "WrongPassword", "AnotherPassword789!"
        )
        
        self.assertFalse(success)
        
        # Test with non-existent user
        success, message = auth_service.update_password(
            'non-existent-id', self.test_password, new_password
        )
        
        self.assertFalse(success)


if __name__ == '__main__':
    unittest.main()