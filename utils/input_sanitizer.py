"""
Input sanitization utilities for preventing injection attacks.

This module provides functions for sanitizing user input to prevent
various injection attacks, including SQL injection, XSS, and command injection.
"""
import re
import html
import json
from typing import Any, Dict, List, Union, Optional
from flask import request
from sqlalchemy.sql import text


def sanitize_string(input_str: Optional[str]) -> Optional[str]:
    """Sanitize a string input to prevent XSS attacks.
    
    Args:
        input_str: String to sanitize
        
    Returns:
        Optional[str]: Sanitized string or None if input is None
    """
    if input_str is None:
        return None
    
    # Escape HTML special characters
    return html.escape(input_str)


def sanitize_dict(input_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively sanitize all string values in a dictionary.
    
    Args:
        input_dict: Dictionary to sanitize
        
    Returns:
        Dict[str, Any]: Sanitized dictionary
    """
    result = {}
    
    for key, value in input_dict.items():
        if isinstance(value, str):
            result[key] = sanitize_string(value)
        elif isinstance(value, dict):
            result[key] = sanitize_dict(value)
        elif isinstance(value, list):
            result[key] = sanitize_list(value)
        else:
            result[key] = value
    
    return result


def sanitize_list(input_list: List[Any]) -> List[Any]:
    """Recursively sanitize all string values in a list.
    
    Args:
        input_list: List to sanitize
        
    Returns:
        List[Any]: Sanitized list
    """
    result = []
    
    for item in input_list:
        if isinstance(item, str):
            result.append(sanitize_string(item))
        elif isinstance(item, dict):
            result.append(sanitize_dict(item))
        elif isinstance(item, list):
            result.append(sanitize_list(item))
        else:
            result.append(item)
    
    return result


def sanitize_request_data() -> Dict[str, Any]:
    """Sanitize all data from the current request.
    
    Returns:
        Dict[str, Any]: Sanitized request data
    """
    data = {}
    
    # Sanitize form data
    if request.form:
        data['form'] = sanitize_dict(request.form.to_dict())
    
    # Sanitize JSON data
    if request.is_json:
        data['json'] = sanitize_dict(request.get_json(silent=True) or {})
    
    # Sanitize query parameters
    if request.args:
        data['args'] = sanitize_dict(request.args.to_dict())
    
    return data


def validate_sql_params(params: Dict[str, Any]) -> bool:
    """Validate SQL parameters to prevent SQL injection.
    
    This function checks for common SQL injection patterns in parameter values.
    
    Args:
        params: SQL parameters
        
    Returns:
        bool: True if parameters are safe, False otherwise
    """
    # SQL injection patterns to check for
    sql_patterns = [
        r';\s*SELECT',
        r';\s*INSERT',
        r';\s*UPDATE',
        r';\s*DELETE',
        r';\s*DROP',
        r';\s*ALTER',
        r';\s*CREATE',
        r'--',
        r'/\*.*\*/',
        r'UNION\s+SELECT',
        r'UNION\s+ALL\s+SELECT'
    ]
    
    # Check each parameter value
    for key, value in params.items():
        if not isinstance(value, str):
            continue
        
        # Check for SQL injection patterns
        for pattern in sql_patterns:
            if re.search(pattern, value, re.IGNORECASE):
                return False
    
    return True


def safe_sql_query(query: str, params: Dict[str, Any]) -> text:
    """Create a safe SQL query using SQLAlchemy's text() function.
    
    Args:
        query: SQL query with named parameters
        params: Parameter values
        
    Returns:
        text: SQLAlchemy text object
        
    Raises:
        ValueError: If parameters contain potential SQL injection
    """
    # Validate parameters
    if not validate_sql_params(params):
        raise ValueError("SQL parameters contain potential SQL injection")
    
    # Create SQLAlchemy text object
    return text(query).bindparams(**params)


def validate_email(email: str) -> bool:
    """Validate an email address.
    
    Args:
        email: Email address to validate
        
    Returns:
        bool: True if email is valid, False otherwise
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))


def validate_url(url: str) -> bool:
    """Validate a URL.
    
    Args:
        url: URL to validate
        
    Returns:
        bool: True if URL is valid, False otherwise
    """
    pattern = r'^https?://(?:[-\w.]|(?:%[\da-fA-F]{2}))+(/[-\w%!$&\'()*+,;=:]+)*(?:\?[-\w%!$&\'()*+,;=:/?]*)?$'
    return bool(re.match(pattern, url))


def sanitize_filename(filename: str) -> str:
    """Sanitize a filename to prevent path traversal attacks.
    
    Args:
        filename: Filename to sanitize
        
    Returns:
        str: Sanitized filename
    """
    # Remove path components
    filename = re.sub(r'[/\\]', '', filename)
    
    # Remove null bytes
    filename = filename.replace('\0', '')
    
    # Limit to alphanumeric characters, dots, hyphens, and underscores
    filename = re.sub(r'[^a-zA-Z0-9._-]', '', filename)
    
    # Ensure filename is not empty
    if not filename:
        filename = 'unnamed_file'
    
    return filename