"""
Logging service for centralized logging configuration and management.

This module provides functionality for setting up and managing application-wide
logging with different handlers and formatters.
"""
import os
import logging
import logging.handlers
import time
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from flask import Flask, request, g, has_request_context

# Create custom formatter for structured logging
class StructuredLogFormatter(logging.Formatter):
    """Custom formatter for structured logging with JSON output."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add exception info if available
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # Add request context if available
        if has_request_context():
            log_data['request'] = {
                'id': getattr(g, 'request_id', None),
                'method': request.method,
                'path': request.path,
                'remote_addr': request.remote_addr,
                'user_agent': request.user_agent.string if request.user_agent else None
            }
            
            # Add user ID if available
            if hasattr(g, 'user_id'):
                log_data['user_id'] = g.user_id
        
        # Add extra fields from record
        for key, value in record.__dict__.items():
            if key.startswith('_') and not key.startswith('__'):
                clean_key = key[1:]  # Remove leading underscore
                log_data[clean_key] = value
        
        return json.dumps(log_data)


class LoggingService:
    """Service for managing application logging."""
    
    def __init__(self, app=None):
        """Initialize the logging service.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self.log_level = logging.INFO
        self.log_dir = 'logs'
        self.max_log_size = 10 * 1024 * 1024  # 10 MB
        self.backup_count = 10
        self.console_logging = True
        self.file_logging = True
        self.json_logging = True
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize the logging service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        
        # Load configuration
        self.log_level = self._get_log_level(app.config.get('LOG_LEVEL', 'INFO'))
        self.log_dir = app.config.get('LOG_DIR', 'logs')
        self.max_log_size = app.config.get('MAX_LOG_SIZE', 10 * 1024 * 1024)  # 10 MB
        self.backup_count = app.config.get('LOG_BACKUP_COUNT', 10)
        self.console_logging = app.config.get('CONSOLE_LOGGING', True)
        self.file_logging = app.config.get('FILE_LOGGING', True)
        self.json_logging = app.config.get('JSON_LOGGING', True)
        
        # Create log directory if it doesn't exist
        if self.file_logging and not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
        
        # Configure root logger
        self._configure_root_logger()
        
        # Configure Flask app logger
        self._configure_app_logger(app)
        
        # Add request logging
        self._setup_request_logging(app)
        
        # Log startup message
        app.logger.info(f"Application logging initialized at level {logging.getLevelName(self.log_level)}")
    
    def _get_log_level(self, level_name: str) -> int:
        """Convert log level name to logging level.
        
        Args:
            level_name: Name of log level
            
        Returns:
            int: Logging level
        """
        levels = {
            'DEBUG': logging.DEBUG,
            'INFO': logging.INFO,
            'WARNING': logging.WARNING,
            'ERROR': logging.ERROR,
            'CRITICAL': logging.CRITICAL
        }
        return levels.get(level_name.upper(), logging.INFO)
    
    def _configure_root_logger(self):
        """Configure the root logger."""
        root_logger = logging.getLogger()
        root_logger.setLevel(self.log_level)
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Add console handler if enabled
        if self.console_logging:
            console_handler = logging.StreamHandler()
            console_handler.setLevel(self.log_level)
            
            if self.json_logging:
                formatter = StructuredLogFormatter()
            else:
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
        
        # Add file handler if enabled
        if self.file_logging:
            # Main log file
            main_log_file = os.path.join(self.log_dir, 'application.log')
            file_handler = logging.handlers.RotatingFileHandler(
                main_log_file,
                maxBytes=self.max_log_size,
                backupCount=self.backup_count
            )
            file_handler.setLevel(self.log_level)
            
            if self.json_logging:
                formatter = StructuredLogFormatter()
            else:
                formatter = logging.Formatter(
                    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
            # Error log file (ERROR and above)
            error_log_file = os.path.join(self.log_dir, 'error.log')
            error_handler = logging.handlers.RotatingFileHandler(
                error_log_file,
                maxBytes=self.max_log_size,
                backupCount=self.backup_count
            )
            error_handler.setLevel(logging.ERROR)
            error_handler.setFormatter(formatter)
            root_logger.addHandler(error_handler)
    
    def _configure_app_logger(self, app: Flask):
        """Configure the Flask app logger.
        
        Args:
            app: Flask application instance
        """
        # Set app logger level
        app.logger.setLevel(self.log_level)
        
        # Remove default Flask handlers
        for handler in app.logger.handlers[:]:
            app.logger.removeHandler(handler)
        
        # App logger will use the root logger's handlers
        app.logger.propagate = True
    
    def _setup_request_logging(self, app: Flask):
        """Set up request logging middleware.
        
        Args:
            app: Flask application instance
        """
        @app.before_request
        def before_request():
            """Log request information and add request ID."""
            # Generate request ID
            g.request_id = f"{int(time.time())}-{os.urandom(4).hex()}"
            g.request_start_time = time.time()
            
            # Log request
            app.logger.debug(f"Request started: {request.method} {request.path}",
                           extra={
                               '_request_id': g.request_id,
                               '_method': request.method,
                               '_path': request.path,
                               '_remote_addr': request.remote_addr,
                               '_user_agent': request.user_agent.string if request.user_agent else None
                           })
        
        @app.after_request
        def after_request(response):
            """Log response information."""
            # Calculate request duration
            duration = time.time() - g.request_start_time
            
            # Log response
            app.logger.debug(
                f"Request completed: {request.method} {request.path} - {response.status_code} ({duration:.3f}s)",
                extra={
                    '_request_id': g.request_id,
                    '_method': request.method,
                    '_path': request.path,
                    '_status_code': response.status_code,
                    '_duration': duration
                }
            )
            
            return response
        
        @app.teardown_request
        def teardown_request(exception):
            """Log exceptions during request handling."""
            if exception:
                app.logger.error(
                    f"Request failed: {request.method} {request.path} - {str(exception)}",
                    exc_info=exception,
                    extra={
                        '_request_id': getattr(g, 'request_id', None),
                        '_method': request.method,
                        '_path': request.path
                    }
                )
    
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with the specified name.
        
        Args:
            name: Logger name
            
        Returns:
            logging.Logger: Logger instance
        """
        return logging.getLogger(name)
    
    def log_to_file(self, message: str, level: str = 'INFO', logger_name: str = None):
        """Log a message to a file.
        
        Args:
            message: Message to log
            level: Log level
            logger_name: Name of logger to use
        """
        logger = logging.getLogger(logger_name) if logger_name else self.app.logger
        log_level = self._get_log_level(level)
        logger.log(log_level, message)


# Create a singleton instance
logging_service = LoggingService()