"""
Tests for the logging service.
"""
import unittest
import os
import json
import logging
import tempfile
from unittest.mock import patch, MagicMock
from flask import Flask, request, g
from services.logging_service import LoggingService, StructuredLogFormatter


class TestStructuredLogFormatter(unittest.TestCase):
    """Test cases for the StructuredLogFormatter."""
    
    def setUp(self):
        """Set up test environment."""
        self.formatter = StructuredLogFormatter()
    
    def test_format_basic_record(self):
        """Test formatting a basic log record."""
        # Create a log record
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='test_file.py',
            lineno=42,
            msg='Test message',
            args=(),
            exc_info=None
        )
        
        # Format the record
        formatted = self.formatter.format(record)
        
        # Parse the JSON
        log_data = json.loads(formatted)
        
        # Verify the formatted data
        self.assertEqual(log_data['level'], 'INFO')
        self.assertEqual(log_data['logger'], 'test_logger')
        self.assertEqual(log_data['message'], 'Test message')
        self.assertEqual(log_data['module'], 'test_file')
        self.assertEqual(log_data['line'], 42)
    
    def test_format_with_exception(self):
        """Test formatting a log record with exception info."""
        try:
            # Raise an exception
            raise ValueError("Test exception")
        except ValueError as e:
            # Create a log record with exception info
            record = logging.LogRecord(
                name='test_logger',
                level=logging.ERROR,
                pathname='test_file.py',
                lineno=42,
                msg='Exception occurred: %s',
                args=(str(e),),
                exc_info=(ValueError, e, e.__traceback__)
            )
            
            # Format the record
            formatted = self.formatter.format(record)
            
            # Parse the JSON
            log_data = json.loads(formatted)
            
            # Verify the formatted data
            self.assertEqual(log_data['level'], 'ERROR')
            self.assertEqual(log_data['message'], 'Exception occurred: Test exception')
            self.assertIn('exception', log_data)
            self.assertEqual(log_data['exception']['type'], 'ValueError')
            self.assertEqual(log_data['exception']['message'], 'Test exception')
            self.assertIn('traceback', log_data['exception'])
    
    def test_format_with_extra_fields(self):
        """Test formatting a log record with extra fields."""
        # Create a log record with extra fields
        record = logging.LogRecord(
            name='test_logger',
            level=logging.INFO,
            pathname='test_file.py',
            lineno=42,
            msg='Test message with extra fields',
            args=(),
            exc_info=None
        )
        
        # Add extra fields
        record._user_id = 'test_user'
        record._request_id = '123456'
        
        # Format the record
        formatted = self.formatter.format(record)
        
        # Parse the JSON
        log_data = json.loads(formatted)
        
        # Verify the formatted data
        self.assertEqual(log_data['message'], 'Test message with extra fields')
        self.assertEqual(log_data['user_id'], 'test_user')
        self.assertEqual(log_data['request_id'], '123456')


class TestLoggingService(unittest.TestCase):
    """Test cases for the LoggingService."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a temporary directory for logs
        self.log_dir = tempfile.mkdtemp()
        
        # Create a test Flask app
        self.app = Flask(__name__)
        self.app.config['TESTING'] = True
        self.app.config['LOG_DIR'] = self.log_dir
        self.app.config['LOG_LEVEL'] = 'DEBUG'
        
        # Create logging service
        self.logging_service = LoggingService()
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove log files
        for filename in os.listdir(self.log_dir):
            os.remove(os.path.join(self.log_dir, filename))
        
        # Remove log directory
        os.rmdir(self.log_dir)
    
    def test_init_app(self):
        """Test initializing the logging service with a Flask app."""
        # Initialize the logging service
        self.logging_service.init_app(self.app)
        
        # Verify configuration was loaded
        self.assertEqual(self.logging_service.log_level, logging.DEBUG)
        self.assertEqual(self.logging_service.log_dir, self.log_dir)
        self.assertTrue(self.logging_service.console_logging)
        self.assertTrue(self.logging_service.file_logging)
        
        # Verify log directory was created
        self.assertTrue(os.path.exists(self.log_dir))
    
    def test_get_log_level(self):
        """Test converting log level names to logging levels."""
        self.assertEqual(self.logging_service._get_log_level('DEBUG'), logging.DEBUG)
        self.assertEqual(self.logging_service._get_log_level('INFO'), logging.INFO)
        self.assertEqual(self.logging_service._get_log_level('WARNING'), logging.WARNING)
        self.assertEqual(self.logging_service._get_log_level('ERROR'), logging.ERROR)
        self.assertEqual(self.logging_service._get_log_level('CRITICAL'), logging.CRITICAL)
        self.assertEqual(self.logging_service._get_log_level('INVALID'), logging.INFO)  # Default
    
    def test_configure_root_logger(self):
        """Test configuring the root logger."""
        # Initialize the logging service
        self.logging_service.init_app(self.app)
        
        # Get the root logger
        root_logger = logging.getLogger()
        
        # Verify the root logger was configured
        self.assertEqual(root_logger.level, logging.DEBUG)
        self.assertTrue(len(root_logger.handlers) > 0)
    
    def test_configure_app_logger(self):
        """Test configuring the Flask app logger."""
        # Initialize the logging service
        self.logging_service.init_app(self.app)
        
        # Verify the app logger was configured
        self.assertEqual(self.app.logger.level, logging.DEBUG)
        self.assertTrue(self.app.logger.propagate)
    
    def test_request_logging(self):
        """Test request logging middleware."""
        # Initialize the logging service
        self.logging_service.init_app(self.app)
        
        # Add a test route
        @self.app.route('/test')
        def test_route():
            return 'Test response'
        
        # Create a test client
        client = self.app.test_client()
        
        # Make a request
        with self.app.app_context():
            with patch.object(self.app.logger, 'debug') as mock_debug:
                response = client.get('/test')
                
                # Verify the response
                self.assertEqual(response.status_code, 200)
                
                # Verify request logging
                mock_debug.assert_called()
    
    def test_get_logger(self):
        """Test getting a logger."""
        # Initialize the logging service
        self.logging_service.init_app(self.app)
        
        # Get a logger
        logger = self.logging_service.get_logger('test_logger')
        
        # Verify the logger
        self.assertEqual(logger.name, 'test_logger')
        self.assertEqual(logger.level, 0)  # Inherits from parent
    
    def test_log_to_file(self):
        """Test logging to a file."""
        # Initialize the logging service
        self.logging_service.init_app(self.app)
        
        # Log a message
        with self.app.app_context():
            with patch.object(self.app.logger, 'log') as mock_log:
                self.logging_service.log_to_file('Test message', 'INFO')
                
                # Verify logging
                mock_log.assert_called_once_with(logging.INFO, 'Test message')


if __name__ == '__main__':
    unittest.main()