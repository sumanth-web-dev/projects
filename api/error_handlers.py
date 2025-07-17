"""
Error handlers for the API.

This module provides centralized error handling for the API endpoints.
"""
import logging
import traceback
import json
from typing import Dict, Any, Tuple, Optional
from flask import Flask, request, jsonify, g, current_app
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from services.notification_service import notification_service

# Set up logging
logger = logging.getLogger(__name__)


class APIError(Exception):
    """Base class for API errors."""
    
    def __init__(self, message: str, status_code: int = 400, 
                error_code: str = None, details: Optional[Dict[str, Any]] = None):
        """Initialize APIError instance.
        
        Args:
            message: Error message
            status_code: HTTP status code
            error_code: Application-specific error code
            details: Additional error details
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or 'api_error'
        self.details = details or {}


class ValidationError(APIError):
    """Error for validation failures."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize ValidationError instance.
        
        Args:
            message: Error message
            details: Validation error details
        """
        super().__init__(
            message=message,
            status_code=400,
            error_code='validation_error',
            details=details
        )


class AuthenticationError(APIError):
    """Error for authentication failures."""
    
    def __init__(self, message: str = "Authentication required"):
        """Initialize AuthenticationError instance.
        
        Args:
            message: Error message
        """
        super().__init__(
            message=message,
            status_code=401,
            error_code='authentication_error'
        )


class AuthorizationError(APIError):
    """Error for authorization failures."""
    
    def __init__(self, message: str = "Permission denied"):
        """Initialize AuthorizationError instance.
        
        Args:
            message: Error message
        """
        super().__init__(
            message=message,
            status_code=403,
            error_code='authorization_error'
        )


class ResourceNotFoundError(APIError):
    """Error for resource not found."""
    
    def __init__(self, resource_type: str, resource_id: str):
        """Initialize ResourceNotFoundError instance.
        
        Args:
            resource_type: Type of resource
            resource_id: ID of resource
        """
        super().__init__(
            message=f"{resource_type} not found: {resource_id}",
            status_code=404,
            error_code='resource_not_found',
            details={
                'resource_type': resource_type,
                'resource_id': resource_id
            }
        )


class RateLimitError(APIError):
    """Error for rate limiting."""
    
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None):
        """Initialize RateLimitError instance.
        
        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
        """
        details = {}
        if retry_after is not None:
            details['retry_after'] = retry_after
        
        super().__init__(
            message=message,
            status_code=429,
            error_code='rate_limit_exceeded',
            details=details
        )


class DatabaseError(APIError):
    """Error for database operations."""
    
    def __init__(self, message: str = "Database error"):
        """Initialize DatabaseError instance.
        
        Args:
            message: Error message
        """
        super().__init__(
            message=message,
            status_code=500,
            error_code='database_error'
        )


class ServerError(APIError):
    """Error for server errors."""
    
    def __init__(self, message: str = "Internal server error"):
        """Initialize ServerError instance.
        
        Args:
            message: Error message
        """
        super().__init__(
            message=message,
            status_code=500,
            error_code='server_error'
        )


def handle_api_error(error: APIError) -> Tuple[Dict[str, Any], int]:
    """Handle API error.
    
    Args:
        error: APIError instance
        
    Returns:
        Tuple[Dict[str, Any], int]: Error response and status code
    """
    response = {
        'error': {
            'code': error.error_code,
            'message': error.message
        }
    }
    
    # Add details if available
    if error.details:
        response['error']['details'] = error.details
    
    # Add request ID if available
    if hasattr(g, 'request_id'):
        response['request_id'] = g.request_id
    
    # Log the error
    log_level = logging.ERROR if error.status_code >= 500 else logging.WARNING
    logger.log(log_level, f"API Error: {error.error_code} - {error.message}")
    
    return response, error.status_code


def handle_http_exception(error: HTTPException) -> Tuple[Dict[str, Any], int]:
    """Handle HTTP exception.
    
    Args:
        error: HTTPException instance
        
    Returns:
        Tuple[Dict[str, Any], int]: Error response and status code
    """
    response = {
        'error': {
            'code': f'http_{error.code}',
            'message': error.description
        }
    }
    
    # Add request ID if available
    if hasattr(g, 'request_id'):
        response['request_id'] = g.request_id
    
    # Log the error
    log_level = logging.ERROR if error.code >= 500 else logging.WARNING
    logger.log(log_level, f"HTTP Error {error.code}: {error.description}")
    
    return response, error.code


def handle_sqlalchemy_error(error: SQLAlchemyError) -> Tuple[Dict[str, Any], int]:
    """Handle SQLAlchemy error.
    
    Args:
        error: SQLAlchemyError instance
        
    Returns:
        Tuple[Dict[str, Any], int]: Error response and status code
    """
    # Create a generic database error response
    response = {
        'error': {
            'code': 'database_error',
            'message': "A database error occurred"
        }
    }
    
    # Add request ID if available
    if hasattr(g, 'request_id'):
        response['request_id'] = g.request_id
    
    # Log the detailed error
    logger.error(f"Database Error: {str(error)}")
    logger.debug(f"Database Error Details: {traceback.format_exc()}")
    
    return response, 500


def handle_generic_exception(error: Exception) -> Tuple[Dict[str, Any], int]:
    """Handle generic exception.
    
    Args:
        error: Exception instance
        
    Returns:
        Tuple[Dict[str, Any], int]: Error response and status code
    """
    # Create a generic server error response
    response = {
        'error': {
            'code': 'server_error',
            'message': "An unexpected error occurred"
        }
    }
    
    # Add request ID if available
    if hasattr(g, 'request_id'):
        response['request_id'] = g.request_id
    
    # Log the detailed error
    logger.error(f"Unhandled Exception: {str(error)}")
    logger.error(f"Exception Details: {traceback.format_exc()}")
    
    # Notify admin about unhandled exceptions
    try:
        if current_app.config.get('ADMIN_USER_ID'):
            notification_service.notify_system_alert(
                user_id=current_app.config['ADMIN_USER_ID'],
                alert_type='error',
                message=f"Unhandled server exception: {str(error)}"
            )
    except Exception as e:
        logger.error(f"Failed to send admin notification: {str(e)}")
    
    return response, 500


def register_error_handlers(app: Flask):
    """Register error handlers with Flask app.
    
    Args:
        app: Flask application instance
    """
    # Register handler for API errors
    @app.errorhandler(APIError)
    def handle_api_error_handler(error):
        response, status_code = handle_api_error(error)
        return jsonify(response), status_code
    
    # Register handler for HTTP exceptions
    @app.errorhandler(HTTPException)
    def handle_http_exception_handler(error):
        response, status_code = handle_http_exception(error)
        return jsonify(response), status_code
    
    # Register handler for SQLAlchemy errors
    @app.errorhandler(SQLAlchemyError)
    def handle_sqlalchemy_error_handler(error):
        response, status_code = handle_sqlalchemy_error(error)
        return jsonify(response), status_code
    
    # Register handler for generic exceptions
    @app.errorhandler(Exception)
    def handle_generic_exception_handler(error):
        response, status_code = handle_generic_exception(error)
        return jsonify(response), status_code
    
    # Log registration
    logger.info("Registered API error handlers")