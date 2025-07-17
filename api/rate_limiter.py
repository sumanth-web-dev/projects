"""
Rate limiting middleware for API endpoints.

This module provides functions and decorators for rate limiting API requests
to prevent abuse and ensure fair usage of resources.
"""
import time
import functools
from typing import Callable, Dict, Tuple, Optional
from flask import request, jsonify, g, current_app
from api.error_handlers import RateLimitError
from services.security_audit_service import security_audit_service

# Store rate limit data in memory
# Format: {key: {'count': int, 'reset_time': float}}
_rate_limit_store: Dict[str, Dict[str, float]] = {}


def _get_rate_limit_key() -> str:
    """Generate a key for rate limiting based on user ID or IP address.
    
    Returns:
        str: Rate limit key
    """
    # Use user ID if authenticated
    if hasattr(g, 'user_id'):
        return f"user:{g.user_id}"
    
    # Otherwise use IP address
    ip = request.remote_addr
    if not ip:
        ip = 'unknown'
    
    return f"ip:{ip}"


def _check_rate_limit(key: str, limit: int, window: int) -> Tuple[bool, int, float]:
    """Check if a request exceeds the rate limit.
    
    Args:
        key: Rate limit key
        limit: Maximum number of requests allowed
        window: Time window in seconds
        
    Returns:
        Tuple[bool, int, float]: (allowed, current_count, reset_time)
    """
    current_time = time.time()
    
    # Initialize or get rate limit data for key
    if key not in _rate_limit_store or _rate_limit_store[key]['reset_time'] <= current_time:
        _rate_limit_store[key] = {
            'count': 1,
            'reset_time': current_time + window
        }
        return True, 1, _rate_limit_store[key]['reset_time']
    
    # Increment count
    _rate_limit_store[key]['count'] += 1
    
    # Check if limit exceeded
    if _rate_limit_store[key]['count'] > limit:
        return False, _rate_limit_store[key]['count'], _rate_limit_store[key]['reset_time']
    
    return True, _rate_limit_store[key]['count'], _rate_limit_store[key]['reset_time']


def rate_limit(limit: int, window: int = 60, by_endpoint: bool = True) -> Callable:
    """Decorator to apply rate limiting to a route.
    
    Args:
        limit: Maximum number of requests allowed in the time window
        window: Time window in seconds
        by_endpoint: Whether to apply rate limit per endpoint or globally
        
    Returns:
        Callable: The decorator function
    """
    def decorator(f: Callable) -> Callable:
        @functools.wraps(f)
        def decorated_function(*args, **kwargs):
            # Get rate limit key
            base_key = _get_rate_limit_key()
            
            # Add endpoint to key if rate limiting by endpoint
            if by_endpoint:
                key = f"{base_key}:{request.endpoint}"
            else:
                key = base_key
            
            # Check rate limit
            allowed, count, reset_time = _check_rate_limit(key, limit, window)
            
            # Set rate limit headers
            response_headers = {
                'X-RateLimit-Limit': str(limit),
                'X-RateLimit-Remaining': str(max(0, limit - count)),
                'X-RateLimit-Reset': str(int(reset_time))
            }
            
            # If rate limit exceeded, return error
            if not allowed:
                # Calculate retry after time
                retry_after = int(reset_time - time.time())
                response_headers['Retry-After'] = str(retry_after)
                
                # Log rate limit event
                security_audit_service.log_security_event(
                    event_type='rate_limit_exceeded',
                    description=f"Rate limit exceeded for {key}",
                    severity='warning',
                    details={
                        'limit': limit,
                        'window': window,
                        'count': count,
                        'endpoint': request.endpoint
                    }
                )
                
                # Raise rate limit error
                raise RateLimitError(
                    message="Rate limit exceeded. Please try again later.",
                    retry_after=retry_after
                )
            
            # Execute route function
            response = f(*args, **kwargs)
            
            # Add rate limit headers to response
            if hasattr(response, 'headers'):
                for header, value in response_headers.items():
                    response.headers[header] = value
            
            return response
        
        return decorated_function
    
    return decorator


def get_rate_limit_config(endpoint: Optional[str] = None, app=None) -> Tuple[int, int]:
    """Get rate limit configuration for an endpoint.
    
    Args:
        endpoint: API endpoint
        app: Flask application instance
        
    Returns:
        Tuple[int, int]: (limit, window)
    """
    # Use provided app or current_app
    config = app.config if app else current_app.config
    
    # Default rate limits
    default_limit = config.get('DEFAULT_RATE_LIMIT', 60)
    default_window = config.get('DEFAULT_RATE_LIMIT_WINDOW', 60)
    
    # Check for endpoint-specific rate limits
    if endpoint:
        endpoint_limits = config.get('ENDPOINT_RATE_LIMITS', {})
        if endpoint in endpoint_limits:
            return endpoint_limits[endpoint]
    
    return default_limit, default_window


def apply_default_rate_limits(app):
    """Apply default rate limits to all API routes.
    
    Args:
        app: Flask application instance
    """
    # Get all API routes
    for rule in app.url_map.iter_rules():
        if rule.endpoint.startswith('api.'):
            # Get rate limit config for endpoint
            limit, window = get_rate_limit_config(rule.endpoint, app)
            
            # Apply rate limit decorator to view function
            view_func = app.view_functions[rule.endpoint]
            app.view_functions[rule.endpoint] = rate_limit(limit, window)(view_func)
    
    app.logger.info("Applied default rate limits to API routes")