"""
CSRF protection middleware for Flask routes.

This module provides functions and decorators for protecting API routes
against Cross-Site Request Forgery (CSRF) attacks.
"""
import functools
from typing import Callable
from flask import request, jsonify, session, abort


def csrf_token_required(f: Callable) -> Callable:
    """Decorator to require CSRF token validation for state-changing routes.
    
    This decorator should be applied to routes that modify data (POST, PUT, DELETE)
    to protect against CSRF attacks.
    
    Args:
        f: The route function to protect
        
    Returns:
        Callable: The wrapped function
    """
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        # Only check CSRF token for state-changing methods
        if request.method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            # Get CSRF token from session
            csrf_token = session.get('csrf_token')
            
            if not csrf_token:
                return jsonify({
                    'status': 'error',
                    'message': 'CSRF token missing from session'
                }), 403
            
            # Check for token in headers
            token_header = request.headers.get('X-CSRF-Token')
            
            # Check for token in form data or JSON
            token_form = None
            if request.form:
                token_form = request.form.get('csrf_token')
            
            token_json = None
            if request.is_json:
                token_json = request.json.get('csrf_token')
            
            # Validate token
            provided_token = token_header or token_form or token_json
            
            if not provided_token:
                return jsonify({
                    'status': 'error',
                    'message': 'CSRF token not provided'
                }), 403
            
            if provided_token != csrf_token:
                return jsonify({
                    'status': 'error',
                    'message': 'Invalid CSRF token'
                }), 403
        
        return f(*args, **kwargs)
    
    return decorated_function


def get_csrf_token() -> str:
    """Get the current CSRF token from the session.
    
    Returns:
        str: The CSRF token
    
    Raises:
        RuntimeError: If no CSRF token exists in the session
    """
    csrf_token = session.get('csrf_token')
    if not csrf_token:
        raise RuntimeError("No CSRF token in session")
    return csrf_token