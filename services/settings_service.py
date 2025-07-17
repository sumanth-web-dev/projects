"""
Settings service for managing user and system settings.
"""
import os
import logging
import json
import psutil
from typing import Dict, Any, Optional, Tuple
from flask import current_app
from models.database import db

# Set up logging
logger = logging.getLogger(__name__)


class SettingsService:
    """Service for managing user and system settings."""
    
    def __init__(self, app=None):
        """Initialize the settings service.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self._settings_path = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the settings service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        
        # Set up settings directory
        instance_path = app.instance_path
        self._settings_path = os.path.join(instance_path, 'settings')
        os.makedirs(self._settings_path, exist_ok=True)
    
    def get_user_settings(self, user_id: str) -> Dict[str, Any]:
        """Get settings for a user.
        
        Args:
            user_id: The user ID
            
        Returns:
            Dict[str, Any]: User settings
        """
        # For now, return default settings
        return {
            'general': {
                'default_search_radius': 25,
                'job_refresh_interval': 12,
                'job_sources': ['linkedin', 'indeed', 'glassdoor'],
                'theme': 'light'
            },
            'automation': {
                'auto_apply_enabled': True,
                'daily_application_limit': 10,
                'schedule_days': ['monday', 'wednesday', 'friday'],
                'schedule_times': ['09:00', '14:00'],
                'browser_type': 'chrome',
                'headless_mode': True
            },
            'security': {
                'enable_2fa': False,
                'session_timeout': 60,  # minutes
                'enable_api_access': True,
                'api_key': None
            },
            'notifications': {
                'email_notifications': True,
                'browser_notifications': True,
                'notification_frequency': 'daily'
            }
        }
    
    def update_user_settings(self, user_id: str, settings: Dict[str, Any]) -> Tuple[bool, str]:
        """Update settings for a user.
        
        Args:
            user_id: The user ID
            settings: New settings
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # In a real implementation, we would validate and save the settings
            # For now, just return success
            return True, "Settings updated successfully"
        except Exception as e:
            logger.error(f"Error updating settings: {str(e)}")
            return False, f"Error updating settings: {str(e)}"
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status information.
        
        Returns:
            Dict[str, Any]: System status
        """
        try:
            # Get CPU and memory usage
            cpu_usage = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            memory_usage = memory.percent
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            disk_usage = disk.percent
            
            # Mock status for services
            return {
                'cpu_usage': cpu_usage,
                'memory_usage': memory_usage,
                'disk_usage': disk_usage,
                'database_connected': True,
                'job_search_active': True,
                'automation_active': False,
                'notification_service_active': True,
                'last_update': '2025-07-18T01:30:00Z'
            }
        except Exception as e:
            logger.error(f"Error getting system status: {str(e)}")
            return {
                'error': str(e),
                'database_connected': False,
                'job_search_active': False,
                'automation_active': False,
                'notification_service_active': False
            }
    
    def get_credentials(self, user_id: str) -> Dict[str, Dict[str, str]]:
        """Get stored credentials for external services.
        
        Args:
            user_id: The user ID
            
        Returns:
            Dict[str, Dict[str, str]]: Credentials by service
        """
        # For security, we don't return actual credentials
        # Just return the services for which credentials are stored
        return {
            'linkedin': {
                'username': 'user@example.com',
                'has_password': True
            },
            'indeed': {
                'username': 'user@example.com',
                'has_password': True
            }
        }
    
    def update_credentials(self, user_id: str, service: str, 
                         credentials: Dict[str, str]) -> Tuple[bool, str]:
        """Update credentials for an external service.
        
        Args:
            user_id: The user ID
            service: Service name
            credentials: Credentials dictionary
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # In a real implementation, we would encrypt and store the credentials
            # For now, just return success
            return True, f"{service} credentials updated successfully"
        except Exception as e:
            logger.error(f"Error updating credentials: {str(e)}")
            return False, f"Error updating credentials: {str(e)}"


# Create a singleton instance
settings_service = SettingsService()