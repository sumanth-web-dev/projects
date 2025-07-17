"""
Error notification module for browser automation errors.

This module provides functionality for notifying users and administrators
about errors that occur during browser automation.
"""
import logging
import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from services.notification_service import notification_service
from automation.playwright_engine.error_handler import AutomationError, ErrorHandler

# Set up logging
logger = logging.getLogger(__name__)


class ErrorNotifier:
    """Notifier for automation errors."""
    
    def __init__(self, error_handler: Optional[ErrorHandler] = None):
        """Initialize ErrorNotifier instance.
        
        Args:
            error_handler: ErrorHandler instance to register callbacks with
        """
        self.error_handler = error_handler
        
        if error_handler:
            self._register_callbacks()
    
    def _register_callbacks(self):
        """Register error callbacks with the error handler."""
        # Register for all error types
        self.error_handler.register_error_callback("all", self.handle_error)
        
        # Register for specific error types
        self.error_handler.register_error_callback("authentication", self.handle_auth_error)
        self.error_handler.register_error_callback("rate_limit", self.handle_rate_limit_error)
    
    def handle_error(self, error: AutomationError):
        """Handle any automation error.
        
        Args:
            error: AutomationError instance
        """
        # Log the error
        logger.error(f"Automation error: {str(error)} (type: {error.error_type}, recoverable: {error.recoverable})")
        
        # Get user ID from context if available
        user_id = error.context.get('user_id') if error.context else None
        
        if not user_id:
            logger.warning("No user ID in error context, cannot send notification")
            return
        
        # Create error details
        error_details = {
            'error_type': error.error_type,
            'message': str(error),
            'recoverable': error.recoverable,
            'timestamp': datetime.fromtimestamp(error.timestamp).isoformat(),
            'context': error.context
        }
        
        # Send notification to user
        try:
            notification_service.notify_system_alert(
                user_id=user_id,
                alert_type='error',
                message=f"Automation error: {str(error)}"
            )
            logger.info(f"Sent error notification to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send error notification: {str(e)}")
    
    def handle_auth_error(self, error: AutomationError):
        """Handle authentication errors.
        
        Args:
            error: AutomationError instance
        """
        # Get user ID from context if available
        user_id = error.context.get('user_id') if error.context else None
        
        if not user_id:
            logger.warning("No user ID in error context, cannot send notification")
            return
        
        # Send specific notification for authentication errors
        try:
            notification_service.notify_system_alert(
                user_id=user_id,
                alert_type='security',
                message=(
                    "Authentication failed during job application automation. "
                    "Please check your credentials in the settings page."
                )
            )
            logger.info(f"Sent authentication error notification to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send authentication error notification: {str(e)}")
    
    def handle_rate_limit_error(self, error: AutomationError):
        """Handle rate limit errors.
        
        Args:
            error: AutomationError instance
        """
        # Get user ID from context if available
        user_id = error.context.get('user_id') if error.context else None
        
        if not user_id:
            logger.warning("No user ID in error context, cannot send notification")
            return
        
        # Get site information if available
        site = error.context.get('site', 'job site')
        
        # Send specific notification for rate limit errors
        try:
            retry_info = ""
            if hasattr(error, 'retry_after') and error.retry_after:
                retry_info = f" The system will automatically retry after {error.retry_after} seconds."
            
            notification_service.notify_system_alert(
                user_id=user_id,
                alert_type='warning',
                message=(
                    f"Rate limit detected on {site}. This may be due to too many requests "
                    f"or automated access detection.{retry_info} "
                    f"Consider pausing automation for a while."
                )
            )
            logger.info(f"Sent rate limit error notification to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send rate limit error notification: {str(e)}")
    
    def notify_automation_start(self, user_id: str, job_search_params: Dict[str, Any]):
        """Notify user about automation start.
        
        Args:
            user_id: ID of the user
            job_search_params: Job search parameters
        """
        try:
            details = {
                'search_params': job_search_params,
                'start_time': datetime.utcnow().isoformat()
            }
            
            notification_service.notify_automation_status(
                user_id=user_id,
                status='started',
                details=details
            )
            logger.info(f"Sent automation start notification to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send automation start notification: {str(e)}")
    
    def notify_automation_complete(self, user_id: str, stats: Dict[str, Any], errors: List[str] = None):
        """Notify user about automation completion.
        
        Args:
            user_id: ID of the user
            stats: Automation statistics
            errors: List of error messages
        """
        try:
            details = {
                'jobs_found': stats.get('jobs_found', 0),
                'applications_submitted': stats.get('applications_submitted', 0),
                'completion_time': datetime.utcnow().isoformat(),
                'duration_seconds': stats.get('duration_seconds', 0),
                'errors': errors or []
            }
            
            notification_service.notify_automation_status(
                user_id=user_id,
                status='completed',
                details=details
            )
            logger.info(f"Sent automation complete notification to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send automation complete notification: {str(e)}")
    
    def notify_automation_failure(self, user_id: str, reason: str, errors: List[str] = None):
        """Notify user about automation failure.
        
        Args:
            user_id: ID of the user
            reason: Reason for failure
            errors: List of error messages
        """
        try:
            details = {
                'reason': reason,
                'failure_time': datetime.utcnow().isoformat(),
                'errors': errors or []
            }
            
            notification_service.notify_automation_status(
                user_id=user_id,
                status='failed',
                details=details
            )
            logger.info(f"Sent automation failure notification to user {user_id}")
        except Exception as e:
            logger.error(f"Failed to send automation failure notification: {str(e)}")


# Create a singleton instance
from automation.playwright_engine.error_handler import error_handler
error_notifier = ErrorNotifier(error_handler)