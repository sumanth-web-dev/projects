"""
Error handler for browser automation errors.

This module provides functionality for handling and recovering from errors
that occur during browser automation.
"""
import time
import logging
import traceback
from typing import Dict, List, Optional, Tuple, Any, Union, Callable
from playwright.sync_api import Page, TimeoutError as PlaywrightTimeoutError

# Set up logging
logger = logging.getLogger(__name__)


class AutomationError(Exception):
    """Base class for automation errors."""
    
    def __init__(self, message: str, error_type: str, 
                recoverable: bool = True, context: Optional[Dict] = None):
        """Initialize AutomationError instance.
        
        Args:
            message: Error message
            error_type: Type of error
            recoverable: Whether the error is recoverable
            context: Additional context information
        """
        super().__init__(message)
        self.error_type = error_type
        self.recoverable = recoverable
        self.context = context or {}
        self.timestamp = time.time()


class NetworkError(AutomationError):
    """Error for network-related issues."""
    
    def __init__(self, message: str, context: Optional[Dict] = None):
        """Initialize NetworkError instance.
        
        Args:
            message: Error message
            context: Additional context information
        """
        super().__init__(message, "network", True, context)


class AuthenticationError(AutomationError):
    """Error for authentication-related issues."""
    
    def __init__(self, message: str, context: Optional[Dict] = None):
        """Initialize AuthenticationError instance.
        
        Args:
            message: Error message
            context: Additional context information
        """
        super().__init__(message, "authentication", False, context)


class NavigationError(AutomationError):
    """Error for navigation-related issues."""
    
    def __init__(self, message: str, context: Optional[Dict] = None):
        """Initialize NavigationError instance.
        
        Args:
            message: Error message
            context: Additional context information
        """
        super().__init__(message, "navigation", True, context)


class ElementError(AutomationError):
    """Error for element-related issues."""
    
    def __init__(self, message: str, context: Optional[Dict] = None):
        """Initialize ElementError instance.
        
        Args:
            message: Error message
            context: Additional context information
        """
        super().__init__(message, "element", True, context)


class RateLimitError(AutomationError):
    """Error for rate limiting issues."""
    
    def __init__(self, message: str, retry_after: Optional[int] = None, 
                context: Optional[Dict] = None):
        """Initialize RateLimitError instance.
        
        Args:
            message: Error message
            retry_after: Seconds to wait before retrying
            context: Additional context information
        """
        context = context or {}
        context["retry_after"] = retry_after
        super().__init__(message, "rate_limit", True, context)
        self.retry_after = retry_after


class ErrorHandler:
    """Handler for browser automation errors."""
    
    def __init__(self, app=None):
        """Initialize ErrorHandler instance.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self._max_retries = 3
        self._retry_delay = 2000  # ms
        self._error_callbacks = {}
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the error handler with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self._max_retries = app.config.get('ERROR_MAX_RETRIES', 3)
        self._retry_delay = app.config.get('ERROR_RETRY_DELAY_MS', 2000)
    
    def handle_error(self, error: Exception, context: Optional[Dict] = None) -> AutomationError:
        """Handle an error and convert it to an AutomationError.
        
        Args:
            error: Exception that occurred
            context: Additional context information
            
        Returns:
            AutomationError: Converted error
        """
        context = context or {}
        
        # Log the error
        logger.error(f"Automation error: {str(error)}")
        logger.debug(f"Error context: {context}")
        logger.debug(f"Error traceback: {traceback.format_exc()}")
        
        # Convert to AutomationError
        if isinstance(error, PlaywrightTimeoutError):
            return NavigationError(f"Navigation timeout: {str(error)}", context)
        elif "net::" in str(error).lower():
            return NetworkError(f"Network error: {str(error)}", context)
        elif "authentication" in str(error).lower() or "login" in str(error).lower():
            return AuthenticationError(f"Authentication error: {str(error)}", context)
        elif "element" in str(error).lower() or "selector" in str(error).lower():
            return ElementError(f"Element error: {str(error)}", context)
        elif "rate" in str(error).lower() or "limit" in str(error).lower():
            retry_after = None
            if "retry-after" in str(error).lower():
                try:
                    # Try to extract retry-after value
                    retry_after_str = str(error).lower().split("retry-after:")[1].strip().split()[0]
                    retry_after = int(retry_after_str)
                except (IndexError, ValueError):
                    pass
            return RateLimitError(f"Rate limit error: {str(error)}", retry_after, context)
        elif isinstance(error, AutomationError):
            return error
        else:
            return AutomationError(f"Automation error: {str(error)}", "unknown", False, context)
    
    def retry_operation(self, operation: Callable, max_retries: Optional[int] = None, 
                       retry_delay: Optional[int] = None, 
                       error_types: Optional[List[str]] = None) -> Any:
        """Retry an operation with exponential backoff.
        
        Args:
            operation: Function to retry
            max_retries: Maximum number of retries
            retry_delay: Base delay between retries in ms
            error_types: List of error types to retry
            
        Returns:
            Any: Result of the operation
            
        Raises:
            AutomationError: If all retries fail
        """
        max_retries = max_retries if max_retries is not None else self._max_retries
        retry_delay = retry_delay if retry_delay is not None else self._retry_delay
        error_types = error_types or ["network", "navigation", "element", "rate_limit"]
        
        last_error = None
        
        for attempt in range(max_retries + 1):
            try:
                return operation()
            except Exception as e:
                # Convert to AutomationError
                error = self.handle_error(e)
                last_error = error
                
                # Check if we should retry
                if attempt < max_retries and error.error_type in error_types and error.recoverable:
                    # Calculate delay with exponential backoff
                    current_delay = retry_delay * (2 ** attempt)
                    
                    # Use retry_after if available for rate limit errors
                    if isinstance(error, RateLimitError) and error.retry_after:
                        current_delay = max(current_delay, error.retry_after * 1000)
                    
                    logger.info(f"Retrying operation after error: {str(error)} (attempt {attempt + 1}/{max_retries}, delay {current_delay}ms)")
                    time.sleep(current_delay / 1000)
                    continue
                else:
                    # No more retries or error not recoverable
                    break
        
        # If we get here, all retries failed
        if last_error:
            raise last_error
        else:
            raise AutomationError("Operation failed after retries", "unknown", False)
    
    def detect_rate_limiting(self, page: Page) -> bool:
        """Detect if a page shows rate limiting or blocking.
        
        Args:
            page: Playwright page
            
        Returns:
            bool: True if rate limiting detected, False otherwise
        """
        try:
            # Check for common rate limiting indicators
            rate_limit_selectors = [
                "text=rate limit",
                "text=too many requests",
                "text=try again later",
                "text=blocked",
                "text=captcha",
                "text=429",
                "text=automated"
            ]
            
            for selector in rate_limit_selectors:
                if page.query_selector(selector):
                    logger.warning(f"Rate limiting detected: {selector}")
                    return True
            
            # Check for CAPTCHA
            captcha_selectors = [
                "iframe[src*='captcha']",
                "iframe[src*='recaptcha']",
                "iframe[src*='hcaptcha']",
                "div.g-recaptcha",
                "div.h-captcha"
            ]
            
            for selector in captcha_selectors:
                if page.query_selector(selector):
                    logger.warning(f"CAPTCHA detected: {selector}")
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error detecting rate limiting: {str(e)}")
            return False
    
    def register_error_callback(self, error_type: str, callback: Callable[[AutomationError], None]) -> None:
        """Register a callback for a specific error type.
        
        Args:
            error_type: Type of error to register for
            callback: Function to call when error occurs
        """
        if error_type not in self._error_callbacks:
            self._error_callbacks[error_type] = []
        
        self._error_callbacks[error_type].append(callback)
    
    def trigger_callbacks(self, error: AutomationError) -> None:
        """Trigger callbacks for an error.
        
        Args:
            error: Error that occurred
        """
        # Trigger callbacks for specific error type
        if error.error_type in self._error_callbacks:
            for callback in self._error_callbacks[error.error_type]:
                try:
                    callback(error)
                except Exception as e:
                    logger.error(f"Error in error callback: {str(e)}")
        
        # Trigger callbacks for all errors
        if "all" in self._error_callbacks:
            for callback in self._error_callbacks["all"]:
                try:
                    callback(error)
                except Exception as e:
                    logger.error(f"Error in error callback: {str(e)}")


# Create a singleton instance
error_handler = ErrorHandler()