"""
Tests for the API error handlers.
"""
import unittest
from unittest.mock import patch, MagicMock
import json
from flask import Flask, jsonify
from werkzeug.exceptions import NotFound, Unauthorized
from sqlalchemy.exc import SQLAlchemyError
from api.error_handlers import (
    APIError, ValidationError, AuthenticationError, AuthorizationError,
    ResourceNotFoundError, RateLimitError, DatabaseError, ServerError,
    register_error_handlers
)


class TestErrorHandlers(unittest.TestCase):
    """Test cases for API error handlers."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a test Flask app
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        
        # Register error handlers
        register_error_handlers(self.app)
        
        # Add test routes
        @self.app.route('/test/api-error')
        def test_api_error():
            raise APIError("Test API error", 400, "test_error")
        
        @self.app.route('/test/validation-error')
        def test_validation_error():
            raise ValidationError("Invalid input", {"field": "This field is required"})
        
        @self.app.route('/test/auth-error')
        def test_auth_error():
            raise AuthenticationError()
        
        @self.app.route('/test/permission-error')
        def test_permission_error():
            raise AuthorizationError()
        
        @self.app.route('/test/not-found-error')
        def test_not_found_error():
            raise ResourceNotFoundError("User", "123")
        
        @self.app.route('/test/rate-limit-error')
        def test_rate_limit_error():
            raise RateLimitError("Too many requests", 60)
        
        @self.app.route('/test/database-error')
        def test_database_error():
            raise DatabaseError("Database connection failed")
        
        @self.app.route('/test/server-error')
        def test_server_error():
            raise ServerError("Internal server error")
        
        @self.app.route('/test/http-error')
        def test_http_error():
            raise NotFound()
        
        @self.app.route('/test/sqlalchemy-error')
        def test_sqlalchemy_error():
            raise SQLAlchemyError("Database error")
        
        @self.app.route('/test/generic-error')
        def test_generic_error():
            raise Exception("Unexpected error")
        
        # Create test client
        self.client = self.app.test_client()
    
    def test_api_error_handler(self):
        """Test handling of APIError."""
        response = self.client.get('/test/api-error')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error']['code'], 'test_error')
        self.assertEqual(data['error']['message'], 'Test API error')
    
    def test_validation_error_handler(self):
        """Test handling of ValidationError."""
        response = self.client.get('/test/validation-error')
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error']['code'], 'validation_error')
        self.assertEqual(data['error']['message'], 'Invalid input')
        self.assertIn('details', data['error'])
        self.assertEqual(data['error']['details']['field'], 'This field is required')
    
    def test_authentication_error_handler(self):
        """Test handling of AuthenticationError."""
        response = self.client.get('/test/auth-error')
        self.assertEqual(response.status_code, 401)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error']['code'], 'authentication_error')
        self.assertEqual(data['error']['message'], 'Authentication required')
    
    def test_authorization_error_handler(self):
        """Test handling of AuthorizationError."""
        response = self.client.get('/test/permission-error')
        self.assertEqual(response.status_code, 403)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error']['code'], 'authorization_error')
        self.assertEqual(data['error']['message'], 'Permission denied')
    
    def test_resource_not_found_error_handler(self):
        """Test handling of ResourceNotFoundError."""
        response = self.client.get('/test/not-found-error')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error']['code'], 'resource_not_found')
        self.assertEqual(data['error']['message'], 'User not found: 123')
        self.assertIn('details', data['error'])
        self.assertEqual(data['error']['details']['resource_type'], 'User')
        self.assertEqual(data['error']['details']['resource_id'], '123')
    
    def test_rate_limit_error_handler(self):
        """Test handling of RateLimitError."""
        response = self.client.get('/test/rate-limit-error')
        self.assertEqual(response.status_code, 429)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error']['code'], 'rate_limit_exceeded')
        self.assertEqual(data['error']['message'], 'Too many requests')
        self.assertIn('details', data['error'])
        self.assertEqual(data['error']['details']['retry_after'], 60)
    
    def test_database_error_handler(self):
        """Test handling of DatabaseError."""
        response = self.client.get('/test/database-error')
        self.assertEqual(response.status_code, 500)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error']['code'], 'database_error')
        self.assertEqual(data['error']['message'], 'Database connection failed')
    
    def test_server_error_handler(self):
        """Test handling of ServerError."""
        response = self.client.get('/test/server-error')
        self.assertEqual(response.status_code, 500)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error']['code'], 'server_error')
        self.assertEqual(data['error']['message'], 'Internal server error')
    
    def test_http_error_handler(self):
        """Test handling of HTTP exceptions."""
        response = self.client.get('/test/http-error')
        self.assertEqual(response.status_code, 404)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error']['code'], 'http_404')
    
    @patch('api.error_handlers.logger')
    def test_sqlalchemy_error_handler(self, mock_logger):
        """Test handling of SQLAlchemy errors."""
        response = self.client.get('/test/sqlalchemy-error')
        self.assertEqual(response.status_code, 500)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error']['code'], 'database_error')
        self.assertEqual(data['error']['message'], 'A database error occurred')
        
        # Verify logging
        mock_logger.error.assert_called()
    
    @patch('api.error_handlers.logger')
    @patch('api.error_handlers.notification_service')
    @patch('api.error_handlers.current_app')
    def test_generic_exception_handler(self, mock_app, mock_notification, mock_logger):
        """Test handling of generic exceptions."""
        # Configure mock app
        mock_app.config = {'ADMIN_USER_ID': 'admin123'}
        
        response = self.client.get('/test/generic-error')
        self.assertEqual(response.status_code, 500)
        
        data = json.loads(response.data)
        self.assertIn('error', data)
        self.assertEqual(data['error']['code'], 'server_error')
        self.assertEqual(data['error']['message'], 'An unexpected error occurred')
        
        # Verify logging
        mock_logger.error.assert_called()
        
        # Verify admin notification
        mock_notification.notify_system_alert.assert_called_once_with(
            user_id='admin123',
            alert_type='error',
            message='Unhandled server exception: Unexpected error'
        )


if __name__ == '__main__':
    unittest.main()