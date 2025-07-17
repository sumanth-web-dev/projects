"""
Tests for the authentication middleware.
"""
import unittest
import uuid
import datetime
from flask import Flask, jsonify, request, g, session
from models.database import db, init_db
from models.user import User
from services.auth_service import auth_service
from services.encryption_service import encryption_service
from api.auth import login_required, api_key_required, auth_required, role_required
from config import TestingConfig


class TestAuthMiddleware(unittest.TestCase):
    """Test cases for the authentication middleware."""
    
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
        
        # Set password and roles in personal data
        personal_data = {
            'password': auth_service.hash_password(self.test_password),
            'first_name': 'Test',
            'last_name': 'User',
            'phone': '+1234567890',
            'address': '123 Test St',
            'roles': ['user', 'tester']
        }
        test_user.personal_data = personal_data
        
        # Save to database
        db.session.add(test_user)
        db.session.commit()
        
        # Generate API key for testing
        success, self.api_key, _ = auth_service.generate_api_key(self.test_user_id, "Test API Key")
        
        # Set up test routes
        @self.app.route('/test/login_required')
        @login_required
        def test_login_required():
            return jsonify({
                'user_id': g.user_id,
                'auth_method': g.auth_method
            })
        
        @self.app.route('/test/api_key_required')
        @api_key_required
        def test_api_key_required():
            return jsonify({
                'user_id': g.user_id,
                'auth_method': g.auth_method,
                'api_key': g.api_key
            })
        
        @self.app.route('/test/auth_required')
        @auth_required
        def test_auth_required():
            return jsonify({
                'user_id': g.user_id,
                'auth_method': g.auth_method
            })
        
        @self.app.route('/test/role_required')
        @auth_required
        @role_required(['admin', 'tester'])
        def test_role_required():
            return jsonify({
                'user_id': g.user_id,
                'roles': auth_service.get_user_roles(g.user_id)
            })
        
        @self.app.route('/test/admin_role_required')
        @auth_required
        @role_required(['admin'])
        def test_admin_role_required():
            return jsonify({
                'user_id': g.user_id,
                'roles': auth_service.get_user_roles(g.user_id)
            })
    
    def tearDown(self):
        """Clean up after tests."""
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_login_required_middleware(self):
        """Test login_required middleware."""
        with self.app.test_client() as client:
            # Test without session
            response = client.get('/test/login_required')
            self.assertEqual(response.status_code, 401)
            
            # Test with session
            with client.session_transaction() as sess:
                auth_service.create_session(self.test_user_id)
            
            response = client.get('/test/login_required')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['user_id'], self.test_user_id)
            self.assertEqual(data['auth_method'], 'session')
    
    def test_api_key_required_middleware(self):
        """Test api_key_required middleware."""
        with self.app.test_client() as client:
            # Test without API key
            response = client.get('/test/api_key_required')
            self.assertEqual(response.status_code, 401)
            
            # Test with invalid API key
            response = client.get('/test/api_key_required', headers={
                'Authorization': 'Bearer invalid_key'
            })
            self.assertEqual(response.status_code, 401)
            
            # Test with valid API key in Authorization header
            response = client.get('/test/api_key_required', headers={
                'Authorization': f'Bearer {self.api_key}'
            })
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['user_id'], self.test_user_id)
            self.assertEqual(data['auth_method'], 'api_key')
            
            # Test with valid API key in X-API-Key header
            response = client.get('/test/api_key_required', headers={
                'X-API-Key': self.api_key
            })
            self.assertEqual(response.status_code, 200)
            
            # Test with valid API key in query parameter
            response = client.get(f'/test/api_key_required?api_key={self.api_key}')
            self.assertEqual(response.status_code, 200)
    
    def test_auth_required_middleware(self):
        """Test auth_required middleware."""
        with self.app.test_client() as client:
            # Test without authentication
            response = client.get('/test/auth_required')
            self.assertEqual(response.status_code, 401)
            
            # Test with session
            with client.session_transaction() as sess:
                auth_service.create_session(self.test_user_id)
            
            response = client.get('/test/auth_required')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['user_id'], self.test_user_id)
            self.assertEqual(data['auth_method'], 'session')
            
            # Test with API key
            client.cookie_jar.clear()  # Clear session
            response = client.get('/test/auth_required', headers={
                'Authorization': f'Bearer {self.api_key}'
            })
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['user_id'], self.test_user_id)
            self.assertEqual(data['auth_method'], 'api_key')
    
    def test_role_required_middleware(self):
        """Test role_required middleware."""
        with self.app.test_client() as client:
            # Set up session
            with client.session_transaction() as sess:
                auth_service.create_session(self.test_user_id)
            
            # Test with required role
            response = client.get('/test/role_required')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertEqual(data['user_id'], self.test_user_id)
            self.assertIn('tester', data['roles'])
            
            # Test without required role
            response = client.get('/test/admin_role_required')
            self.assertEqual(response.status_code, 403)
            
            # Assign admin role and test again
            auth_service.assign_role(self.test_user_id, 'admin')
            response = client.get('/test/admin_role_required')
            self.assertEqual(response.status_code, 200)
            data = response.get_json()
            self.assertIn('admin', data['roles'])


if __name__ == '__main__':
    unittest.main()