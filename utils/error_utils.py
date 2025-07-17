"""
Error handling utilities for the application.

This module provides functions for standardized error handling and reporting.
"""
import logging
import traceback
import sys
from typing import Dict, Any, Optional, Tuple, List
from flask import jsonify, current_app
from services.security_audit_service import security_audit_service

# Set up logging
logger = logging.getLogger(__name__)


def log_exception(exc: Exception, context: Optional[Dict[str, Any]] = None) -> None:
    """Log an exception with context information.
    
    Args:
        exc: Exception to log
        context: Additional context information
    """
    exc_type, exc_value, exc_traceback = sys.exc_info()
    
    # Format traceback
    tb_lines = traceback.format_exception(exc_type, exc_value, exc_traceback)
    tb_text = ''.join(tb_lines)
    
    # Log exception
    logger.error(f"Exception: {str(exc)}")
    logger.error(f"Traceback: {tb_text}")
    
    # Log context if provided
    if context:
        logger.error(f"Context: {context}")
    
    # Log security event for certain exception types
    if any(err_type in exc.__class__.__name__ for err_type in ['Security', 'Auth', 'Permission', 'Access']):
        security_audit_service.log_security_event(
            event_type='security_exception',
            description=f"Security-related exception: {exc.__class__.__name__}",
            severity='error',
            details={
                'exception_type': exc.__class__.__name__,
                'exception_message': str(exc),
                'context': context
            }
        )


def format_validation_errors(errors: Dict[str, List[str]]) -> Dict[str, Any]:
    """Format validation errors for API response.
    
    Args:
        errors: Dictionary of field errors
        
    Returns:
        Dict[str, Any]: Formatted error response
    """
    return {
        'error': {
            'code': 'validation_error',
            'message': 'Validation failed',
            'details': {
                'fields': errors
            }
        }
    }


def create_error_response(error_code: str, message: str, status_code: int = 400, 
                         details: Optional[Dict[str, Any]] = None) -> Tuple[Dict[str, Any], int]:
    """Create a standardized error response.
    
    Args:
        error_code: Error code
        message: Error message
        status_code: HTTP status code
        details: Additional error details
        
    Returns:
        Tuple[Dict[str, Any], int]: Error response and status code
    """
    response = {
        'error': {
            'code': error_code,
            'message': message
        }
    }
    
    if details:
        response['error']['details'] = details
    
    return response, status_code


def handle_request_validation(func):
    """Decorator to handle request validation.
    
    This decorator catches validation errors and returns a standardized error response.
    
    Args:
        func: Function to decorate
        
    Returns:
        Function: Decorated function
    """
    from functools import wraps
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            logger.warning(f"Validation error: {str(e)}")
            return jsonify(format_validation_errors({'general': [str(e)]})), 400
    
    return wrapper