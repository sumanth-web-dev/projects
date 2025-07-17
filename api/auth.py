"""
Authentication middleware for Flask routes.

This module provides decorators and functions for protecting API routes
with session-based authentication and API key authentication.
"""
import functools
import time
from typing import Callable, Optional, Dict, Any, Tuple
from flask import request, jsonify, session, g, current_app
from services.auth_service import auth_service


def get_api_key_from_request() -> Optional[str]:
    """Extract API key from request headers or query parameters.
    
    Returns:
        Optional[str]: The API key if found, None otherwise
    """
    # Check Authorization header (Bearer token)
    auth_header = request.headers.get('Authorization')
    if auth_header and auth_header.startswith('Bearer '):
        return auth_header.split(' ')[1]
    
    # Check X-API-Key header
    api_key = request.headers.get('X-API-Key')
    if api_key:
        return api_key
    
    # Check query parameter
    api_key = request.args.get('api_key')
    if api_key:
        return api_key
    
    return None


def login_required(f: Callable) -> Callable:
    """Decorator to require session-based authentication for a route.
    
    Args:
        f: The route function to protect
        
    Returns:
        Callable: The wrapped function
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is authenticated via session
        if not session.get('authenticated'):
            return jsonify({
                'status': 'error',
                'message': 'Authentication required'
            }), 401
        
        # Store user ID in g for access in the route
        g.user_id = session.get('user_id')
        g.auth_method = 'session'
        
        # Check session expiration if configured
        if 'login_time' in session:
            login_time = session.get('login_time')
            current_time = time.time()
            max_age = current_app.config.get('SESSION_MAX_AGE', 86400)  # Default 24 hours
            
            if current_time - login_time > max_age:
                auth_service.end_session()
                return jsonify({
                    'status': 'error',
                    'message': 'Session expired, please login again'
                }), 401
        
        # Refresh session if needed
        if current_app.config.get('SESSION_REFRESH_EACH_REQUEST', True):
            session.modified = True
        
        return f(*args, **kwargs)
    
    return decorated_function


def api_key_required(f: Callable) -> Callable:
    """Decorator to require API key authentication for a route.
    
    Args:
        f: The route function to protect
        
    Returns:
        Callable: The wrapped function
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Get API key from request
        api_key = get_api_key_from_request()
        
        if not api_key:
            return jsonify({
                'status': 'error',
                'message': 'API key required'
            }), 401
        
        # Validate API key
        valid, user_id, metadata = auth_service.validate_api_key_with_metadata(api_key)
        
        if not valid or not user_id:
            return jsonify({
                'status': 'error',
                'message': 'Invalid API key'
            }), 401
        
        # Store user ID and API key info in g for access in the route
        g.user_id = user_id
        g.api_key = api_key
        g.auth_method = 'api_key'
        g.api_key_metadata = metadata
        
        return f(*args, **kwargs)
    
    return decorated_function


def auth_required(f: Callable) -> Callable:
    """Decorator to require either session or API key authentication.
    
    This decorator allows both session-based and API key authentication,
    making it suitable for routes that can be accessed by both web users
    and automation processes.
    
    Args:
        f: The route function to protect
        
    Returns:
        Callable: The wrapped function
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # First check for API key
        api_key = get_api_key_from_request()
        
        if api_key:
            # Validate API key
            valid, user_id, metadata = auth_service.validate_api_key_with_metadata(api_key)
            
            if valid and user_id:
                # Store user ID and authentication method in g
                g.user_id = user_id
                g.auth_method = 'api_key'
                g.api_key = api_key
                g.api_key_metadata = metadata
                return f(*args, **kwargs)
        
        # If no valid API key, check for session authentication
        if session.get('authenticated'):
            # Check session expiration if configured
            if 'login_time' in session:
                login_time = session.get('login_time')
                current_time = time.time()
                max_age = current_app.config.get('SESSION_MAX_AGE', 86400)  # Default 24 hours
                
                if current_time - login_time > max_age:
                    auth_service.end_session()
                    return jsonify({
                        'status': 'error',
                        'message': 'Session expired, please login again'
                    }), 401
            
            # Store user ID and authentication method in g
            g.user_id = session.get('user_id')
            g.auth_method = 'session'
            
            # Refresh session if needed
            if current_app.config.get('SESSION_REFRESH_EACH_REQUEST', True):
                session.modified = True
                
            return f(*args, **kwargs)
        
        # If neither authentication method is valid, return 401
        return jsonify({
            'status': 'error',
            'message': 'Authentication required'
        }), 401
    
    return decorated_function


def role_required(roles: list) -> Callable:
    """Decorator to require specific roles for a route.
    
    This decorator must be used after login_required, api_key_required,
    or auth_required to ensure g.user_id is set.
    
    Args:
        roles: List of roles required to access the route
        
    Returns:
        Callable: The decorator function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Ensure user is authenticated
            if not hasattr(g, 'user_id'):
                return jsonify({
                    'status': 'error',
                    'message': 'Authentication required'
                }), 401
            
            # Check user roles
            user_roles = auth_service.get_user_roles(g.user_id)
            
            # Check if user has any of the required roles
            if not any(role in user_roles for role in roles):
                return jsonify({
                    'status': 'error',
                    'message': 'Insufficient permissions'
                }), 403
            
            return f(*args, **kwargs)
        
        return decorated_function
    
    return decorator


def get_request_ip() -> str:
    """Get the client IP address from the request.
    
    Returns:
        str: The client IP address
    """
    # Check X-Forwarded-For header first (for proxies)
    if request.headers.get('X-Forwarded-For'):
        ip = request.headers.get('X-Forwarded-For').split(',')[0].strip()
    else:
        ip = request.remote_addr or 'unknown'
    
    return ip


def log_auth_attempt(success: bool, auth_type: str, identifier: str, details: Dict[str, Any] = None) -> None:
    """Log an authentication attempt.
    
    Args:
        success: Whether the authentication was successful
        auth_type: The type of authentication (e.g., 'login', 'api_key')
        identifier: The identifier used (e.g., email, API key)
        details: Additional details about the attempt
    """
    if details is None:
        details = {}
    
    # Add request information
    details['ip'] = get_request_ip()
    details['user_agent'] = request.user_agent.string if request.user_agent else 'unknown'
    details['path'] = request.path
    details['method'] = request.method
    
    # Log the attempt
    auth_service.log_auth_attempt(success, auth_type, identifier, details)