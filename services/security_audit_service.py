"""
Security audit logging service for tracking security-related events.

This module provides functionality for logging security-related events
such as authentication attempts, sensitive data access, and configuration changes.
"""
import logging
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
from flask import request, g, has_request_context
from services.logging_service import logging_service

# Create a dedicated logger for security events
security_logger = logging.getLogger('security')

class SecurityAuditService:
    """Service for security audit logging."""
    
    def __init__(self, app=None):
        """Initialize the security audit service.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self.log_dir = 'logs'
        self.enable_security_logging = True
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the security audit service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self.log_dir = app.config.get('LOG_DIR', 'logs')
        self.enable_security_logging = app.config.get('ENABLE_SECURITY_LOGGING', True)
        
        # Configure security logger
        self._configure_security_logger()
        
        app.logger.info("Security audit logging initialized")
    
    def _configure_security_logger(self):
        """Configure the security logger."""
        import os
        import logging.handlers
        
        if not self.enable_security_logging:
            return
        
        # Create security log file handler
        security_log_file = os.path.join(self.log_dir, 'security.log')
        
        # Create handler with rotation
        handler = logging.handlers.RotatingFileHandler(
            security_log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=10
        )
        
        # Create formatter
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s'
        )
        
        # Configure handler
        handler.setFormatter(formatter)
        handler.setLevel(logging.INFO)
        
        # Add handler to security logger
        security_logger.setLevel(logging.INFO)
        security_logger.addHandler(handler)
        
        # Ensure security logger doesn't propagate to root logger
        security_logger.propagate = False
    
    def _get_context_info(self) -> Dict[str, Any]:
        """Get context information from the current request.
        
        Returns:
            Dict[str, Any]: Context information
        """
        context = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_id': f"{int(time.time())}-{id(request) if has_request_context() else 'no-request'}"
        }
        
        if has_request_context():
            context.update({
                'request_id': getattr(g, 'request_id', None),
                'ip_address': request.remote_addr,
                'user_agent': request.user_agent.string if request.user_agent else None,
                'path': request.path,
                'method': request.method,
                'user_id': getattr(g, 'user_id', None),
                'auth_method': getattr(g, 'auth_method', None)
            })
        
        return context
    
    def log_auth_event(self, event_type: str, success: bool, username: str, details: Optional[Dict[str, Any]] = None):
        """Log an authentication event.
        
        Args:
            event_type: Type of authentication event (login, logout, etc.)
            success: Whether the authentication was successful
            username: Username or identifier used for authentication
            details: Additional details about the event
        """
        if not self.enable_security_logging:
            return
        
        context = self._get_context_info()
        
        # Add event-specific information
        event_data = {
            'event_type': 'authentication',
            'auth_event': event_type,
            'success': success,
            'username': username
        }
        
        # Add additional details
        if details:
            event_data.update(details)
        
        # Combine context and event data
        log_data = {**context, **event_data}
        
        # Log the event
        security_logger.info(f"Authentication event: {event_type} - {'Success' if success else 'Failure'} - User: {username}", 
                           extra={'security_event': json.dumps(log_data)})
    
    def log_data_access(self, resource_type: str, resource_id: str, action: str, details: Optional[Dict[str, Any]] = None):
        """Log a data access event.
        
        Args:
            resource_type: Type of resource being accessed
            resource_id: ID of the resource
            action: Action being performed (read, write, delete)
            details: Additional details about the access
        """
        if not self.enable_security_logging:
            return
        
        context = self._get_context_info()
        
        # Add event-specific information
        event_data = {
            'event_type': 'data_access',
            'resource_type': resource_type,
            'resource_id': resource_id,
            'action': action
        }
        
        # Add additional details
        if details:
            event_data.update(details)
        
        # Combine context and event data
        log_data = {**context, **event_data}
        
        # Log the event
        security_logger.info(f"Data access: {action} {resource_type} {resource_id}", 
                           extra={'security_event': json.dumps(log_data)})
    
    def log_config_change(self, config_type: str, change_description: str, details: Optional[Dict[str, Any]] = None):
        """Log a configuration change event.
        
        Args:
            config_type: Type of configuration being changed
            change_description: Description of the change
            details: Additional details about the change
        """
        if not self.enable_security_logging:
            return
        
        context = self._get_context_info()
        
        # Add event-specific information
        event_data = {
            'event_type': 'config_change',
            'config_type': config_type,
            'change_description': change_description
        }
        
        # Add additional details
        if details:
            event_data.update(details)
        
        # Combine context and event data
        log_data = {**context, **event_data}
        
        # Log the event
        security_logger.info(f"Configuration change: {config_type} - {change_description}", 
                           extra={'security_event': json.dumps(log_data)})
    
    def log_security_event(self, event_type: str, description: str, severity: str = 'info', details: Optional[Dict[str, Any]] = None):
        """Log a general security event.
        
        Args:
            event_type: Type of security event
            description: Description of the event
            severity: Severity level (info, warning, error, critical)
            details: Additional details about the event
        """
        if not self.enable_security_logging:
            return
        
        context = self._get_context_info()
        
        # Add event-specific information
        event_data = {
            'event_type': event_type,
            'description': description,
            'severity': severity
        }
        
        # Add additional details
        if details:
            event_data.update(details)
        
        # Combine context and event data
        log_data = {**context, **event_data}
        
        # Map severity to log level
        level_map = {
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }
        level = level_map.get(severity.lower(), logging.INFO)
        
        # Log the event
        security_logger.log(level, f"Security event: {event_type} - {description}", 
                          extra={'security_event': json.dumps(log_data)})


# Create a singleton instance
security_audit_service = SecurityAuditService()