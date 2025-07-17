"""
Security middleware for protecting against common web vulnerabilities.

This module provides middleware functions for protecting against common web
vulnerabilities such as XSS, CSRF, clickjacking, and more.
"""
import re
from functools import wraps
from typing import Callable, Dict, Any, List, Optional
from flask import request, abort, current_app, g
from services.security_audit_service import security_audit_service
from utils.input_sanitizer import sanitize_string


def check_content_type(required_type: str) -> Callable:
    """Decorator to enforce specific Content-Type header.
    
    Args:
        required_type: Required Content-Type value
        
    Returns:
        Callable: The decorator function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            content_type = request.headers.get('Content-Type', '')
            if not content_type.startswith(required_type):
                security_audit_service.log_security_event(
                    event_type='invalid_content_type',
                    description=f"Invalid Content-Type: {content_type}, expected: {required_type}",
                    severity='warning'
                )
                return {
                    'error': {
                        'code': 'invalid_content_type',
                        'message': f"Invalid Content-Type. Expected: {required_type}"
                    }
                }, 415
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def validate_json_schema(schema: Dict[str, Any]) -> Callable:
    """Decorator to validate JSON request data against a schema.
    
    Args:
        schema: JSON schema for validation
        
    Returns:
        Callable: The decorator function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if request has JSON data
            if not request.is_json:
                return {
                    'error': {
                        'code': 'invalid_request',
                        'message': "Request must be JSON"
                    }
                }, 400
            
            # Get JSON data
            data = request.get_json()
            
            # Validate required fields
            errors = []
            for field, field_schema in schema.items():
                if field_schema.get('required', False) and field not in data:
                    errors.append(f"Missing required field: {field}")
                elif field in data:
                    # Validate field type
                    field_type = field_schema.get('type')
                    if field_type and not isinstance(data[field], _get_type_for_schema(field_type)):
                        errors.append(f"Invalid type for field {field}. Expected: {field_type}")
                    
                    # Validate field pattern
                    pattern = field_schema.get('pattern')
                    if pattern and isinstance(data[field], str) and not re.match(pattern, data[field]):
                        errors.append(f"Invalid format for field {field}")
                    
                    # Validate field length
                    min_length = field_schema.get('minLength')
                    if min_length is not None and isinstance(data[field], str) and len(data[field]) < min_length:
                        errors.append(f"Field {field} must be at least {min_length} characters long")
                    
                    max_length = field_schema.get('maxLength')
                    if max_length is not None and isinstance(data[field], str) and len(data[field]) > max_length:
                        errors.append(f"Field {field} must be at most {max_length} characters long")
            
            # Return errors if any
            if errors:
                security_audit_service.log_security_event(
                    event_type='schema_validation_failure',
                    description=f"JSON schema validation failed: {', '.join(errors)}",
                    severity='warning'
                )
                return {
                    'error': {
                        'code': 'validation_error',
                        'message': "Request validation failed",
                        'details': {
                            'errors': errors
                        }
                    }
                }, 400
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def _get_type_for_schema(schema_type: str) -> type:
    """Get Python type for JSON schema type.
    
    Args:
        schema_type: JSON schema type
        
    Returns:
        type: Python type
    """
    type_map = {
        'string': str,
        'number': (int, float),
        'integer': int,
        'boolean': bool,
        'array': list,
        'object': dict
    }
    
    return type_map.get(schema_type, object)


def check_origin(allowed_origins: Optional[List[str]] = None) -> Callable:
    """Decorator to check Origin header for CORS requests.
    
    Args:
        allowed_origins: List of allowed origins
        
    Returns:
        Callable: The decorator function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get Origin header
            origin = request.headers.get('Origin')
            
            # Skip check if no Origin header (not a CORS request)
            if not origin:
                return f(*args, **kwargs)
            
            # Get allowed origins from config if not provided
            origins = allowed_origins or current_app.config.get('ALLOWED_ORIGINS', [])
            
            # Check if origin is allowed
            if origins and origin not in origins:
                security_audit_service.log_security_event(
                    event_type='invalid_origin',
                    description=f"Invalid Origin: {origin}",
                    severity='warning'
                )
                abort(403)
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def sanitize_inputs() -> Callable:
    """Decorator to sanitize request inputs to prevent XSS.
    
    Returns:
        Callable: The decorator function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Sanitize URL parameters
            for key, value in request.args.items():
                if isinstance(value, str):
                    request.args = request.args.copy()
                    request.args[key] = sanitize_string(value)
            
            # Sanitize form data
            if request.form:
                for key, value in request.form.items():
                    if isinstance(value, str):
                        request.form = request.form.copy()
                        request.form[key] = sanitize_string(value)
            
            # Store original JSON data
            if request.is_json:
                g.original_json = request.get_json()
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def check_permissions(required_permissions: List[str]) -> Callable:
    """Decorator to check user permissions.
    
    Args:
        required_permissions: List of required permissions
        
    Returns:
        Callable: The decorator function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Skip check if no user ID in context
            if not hasattr(g, 'user_id'):
                abort(401)
            
            # Get user permissions from auth service
            from services.auth_service import auth_service
            user_permissions = auth_service.get_user_permissions(g.user_id)
            
            # Check if user has all required permissions
            missing_permissions = [p for p in required_permissions if p not in user_permissions]
            
            if missing_permissions:
                security_audit_service.log_security_event(
                    event_type='permission_denied',
                    description=f"User {g.user_id} missing permissions: {', '.join(missing_permissions)}",
                    severity='warning'
                )
                return {
                    'error': {
                        'code': 'permission_denied',
                        'message': "Insufficient permissions"
                    }
                }, 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def prevent_parameter_pollution() -> Callable:
    """Decorator to prevent HTTP parameter pollution attacks.
    
    Returns:
        Callable: The decorator function
    """
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check for duplicate parameters in query string
            query_params = request.args.keys()
            duplicate_params = [param for param in query_params if len(request.args.getlist(param)) > 1]
            
            if duplicate_params:
                security_audit_service.log_security_event(
                    event_type='parameter_pollution',
                    description=f"HTTP parameter pollution detected: {', '.join(duplicate_params)}",
                    severity='warning'
                )
                return {
                    'error': {
                        'code': 'invalid_request',
                        'message': "Duplicate query parameters are not allowed"
                    }
                }, 400
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator