"""
Authentication middleware for Flask routes.

This module provides decorators and functions for protecting API routes
with session-based authentication and API key authentication.
"""
import functools
from typing import Callable, Optional
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
        valid, user_id = auth_service.validate_api_key(api_key)
        
        if not valid or not user_id:
            return jsonify({
                'status': 'error',
                'message': 'Invalid API key'
            }), 401
        
        # Store user ID in g for access in the route
        g.user_id = user_id
        g.api_key = api_key
        
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
            valid, user_id = auth_service.validate_api_key(api_key)
            
            if valid and user_id:
                # Store user ID and authentication method in g
                g.user_id = user_id
                g.auth_method = 'api_key'
                g.api_key = api_key
                return f(*args, **kwargs)
        
        # If no valid API key, check for session authentication
        if session.get('authenticated'):
            # Store user ID and authentication method in g
            g.user_id = session.get('user_id')
            g.auth_method = 'session'
            return f(*args, **kwargs)
        
        # If neither authentication method is valid, return 401
        return jsonify({
            'status': 'error',
            'message': 'Authentication required'
        }), 401
    
    return decorated_function