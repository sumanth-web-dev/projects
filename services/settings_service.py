"""
Settings Service for managing system configuration and user preferences.
"""
import json
import os
import secrets
import psutil
import datetime
from typing import Dict, Any, Optional, List, Tuple
from models.database import db
from models.user import User
from services.encryption_service import encryption_service
from sqlalchemy import text


class SettingsService:
    """Service for managing system settings and user preferences."""
    
    def __init__(self):
        self.default_settings = {
            'general': {
                'default_search_radius': 25,
                'job_refresh_interval': 6,
                'job_sources': ['linkedin', 'indeed'],
                'theme': 'light'
            },
            'automation': {
                'auto_apply_enabled': False,
                'daily_application_limit': 10,
                'schedule_days': [],
                'schedule_times': {},
                'browser_type': 'chromium',
                'headless_mode': True
            },
            'security': {
                'enable_2fa': False,
                'session_timeout': 30,
                'enable_api_access': False,
                'api_key': None
            }
        }
    
    def get_user_settings(self, user_id: str) -> Dict[str, Any]:
        """Get all settings for a user."""
        try:
            user = User.query.filter_by(id=user_id).first()
            if not user:
                return self.default_settings
            
            # Decrypt and parse settings
            if user.settings_data:
                decrypted_data = encryption_service.decrypt_data(user.settings_data)
                settings = json.loads(decrypted_data)
                
                # Merge with defaults to ensure all keys exist
                merged_settings = self._merge_settings(self.default_settings, settings)
                return merged_settings
            else:
                return self.default_settings
                
        except Exception as e:
            print(f"Error getting user settings: {e}")
            return self.default_settings
    
    def update_user_settings(self, user_id: str, settings_category: str, settings_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Update specific category of user settings."""
        try:
            user = User.query.filter_by(id=user_id).first()
            if not user:
                return False, "User not found"
            
            # Get current settings
            current_settings = self.get_user_settings(user_id)
            
            # Update the specific category
            if settings_category in current_settings:
                current_settings[settings_category].update(settings_data)
            else:
                current_settings[settings_category] = settings_data
            
            # Encrypt and save
            settings_json = json.dumps(current_settings)
            encrypted_settings = encryption_service.encrypt_data(settings_json)
            
            user.settings_data = encrypted_settings
            user.updated_at = datetime.datetime.utcnow()
            
            db.session.commit()
            
            return True, "Settings updated successfully"
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating user settings: {e}")
            return False, f"Failed to update settings: {str(e)}"
    
    def get_credentials(self, user_id: str) -> Dict[str, bool]:
        """Get credential status for all services."""
        try:
            user = User.query.filter_by(id=user_id).first()
            if not user:
                return {}
            
            credentials_status = {}
            
            # Check if credentials exist for each service
            if user.credentials_data:
                decrypted_data = encryption_service.decrypt_data(user.credentials_data)
                credentials = json.loads(decrypted_data)
                
                for service in ['linkedin', 'indeed', 'glassdoor']:
                    credentials_status[service] = service in credentials and credentials[service].get('username') and credentials[service].get('password')
            else:
                for service in ['linkedin', 'indeed', 'glassdoor']:
                    credentials_status[service] = False
            
            return credentials_status
            
        except Exception as e:
            print(f"Error getting credentials status: {e}")
            return {}
    
    def update_credentials(self, user_id: str, service: str, username: str, password: str) -> Tuple[bool, str]:
        """Update credentials for a specific service."""
        try:
            user = User.query.filter_by(id=user_id).first()
            if not user:
                return False, "User not found"
            
            # Get current credentials
            credentials = {}
            if user.credentials_data:
                decrypted_data = encryption_service.decrypt_data(user.credentials_data)
                credentials = json.loads(decrypted_data)
            
            # Update credentials for the service
            credentials[service] = {
                'username': username,
                'password': password,
                'updated_at': datetime.datetime.utcnow().isoformat()
            }
            
            # Encrypt and save
            credentials_json = json.dumps(credentials)
            encrypted_credentials = encryption_service.encrypt_data(credentials_json)
            
            user.credentials_data = encrypted_credentials
            user.updated_at = datetime.datetime.utcnow()
            
            db.session.commit()
            
            return True, f"{service.capitalize()} credentials updated successfully"
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating credentials: {e}")
            return False, f"Failed to update credentials: {str(e)}"
    
    def delete_credentials(self, user_id: str, service: str) -> Tuple[bool, str]:
        """Delete credentials for a specific service."""
        try:
            user = User.query.filter_by(id=user_id).first()
            if not user:
                return False, "User not found"
            
            if not user.credentials_data:
                return True, "No credentials to delete"
            
            # Get current credentials
            decrypted_data = encryption_service.decrypt_data(user.credentials_data)
            credentials = json.loads(decrypted_data)
            
            # Remove credentials for the service
            if service in credentials:
                del credentials[service]
                
                # Encrypt and save
                credentials_json = json.dumps(credentials)
                encrypted_credentials = encryption_service.encrypt_data(credentials_json)
                
                user.credentials_data = encrypted_credentials
                user.updated_at = datetime.datetime.utcnow()
                
                db.session.commit()
            
            return True, f"{service.capitalize()} credentials removed successfully"
            
        except Exception as e:
            db.session.rollback()
            print(f"Error deleting credentials: {e}")
            return False, f"Failed to delete credentials: {str(e)}"
    
    def get_credential_info(self, user_id: str, service: str) -> Tuple[bool, Dict[str, Any]]:
        """Get credential info (username only) for a specific service."""
        try:
            user = User.query.filter_by(id=user_id).first()
            if not user or not user.credentials_data:
                return False, {}
            
            decrypted_data = encryption_service.decrypt_data(user.credentials_data)
            credentials = json.loads(decrypted_data)
            
            if service in credentials:
                return True, {
                    'username': credentials[service].get('username', ''),
                    'updated_at': credentials[service].get('updated_at', '')
                }
            else:
                return False, {}
                
        except Exception as e:
            print(f"Error getting credential info: {e}")
            return False, {}
    
    def generate_api_key(self, user_id: str) -> Tuple[bool, str, str]:
        """Generate a new API key for the user."""
        try:
            api_key = secrets.token_urlsafe(32)
            
            # Update user settings with new API key
            success, message = self.update_user_settings(user_id, 'security', {
                'api_key': api_key,
                'enable_api_access': True
            })
            
            if success:
                return True, api_key, "API key generated successfully"
            else:
                return False, "", message
                
        except Exception as e:
            print(f"Error generating API key: {e}")
            return False, "", f"Failed to generate API key: {str(e)}"
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get current system status and metrics."""
        try:
            # Get system resource usage
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            # Get automation status (placeholder - would integrate with actual automation service)
            automation_active = False  # This would check actual automation status
            
            # Get recent logs (placeholder - would integrate with actual logging system)
            recent_logs = [
                {
                    'timestamp': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S'),
                    'event': 'System started',
                    'status': 'success'
                },
                {
                    'timestamp': (datetime.datetime.utcnow() - datetime.timedelta(minutes=5)).strftime('%Y-%m-%d %H:%M:%S'),
                    'event': 'Job search completed',
                    'status': 'success'
                },
                {
                    'timestamp': (datetime.datetime.utcnow() - datetime.timedelta(minutes=10)).strftime('%Y-%m-%d %H:%M:%S'),
                    'event': 'Application submitted',
                    'status': 'success'
                }
            ]
            
            return {
                'automation_active': automation_active,
                'last_automation_run': 'Never',
                'next_automation_run': 'Not scheduled',
                'applications_today': 0,
                'cpu_usage': round(cpu_usage, 1),
                'memory_usage': round(memory.percent, 1),
                'disk_usage': round(disk.percent, 1),
                'recent_logs': recent_logs
            }
            
        except Exception as e:
            print(f"Error getting system status: {e}")
            return {
                'automation_active': False,
                'last_automation_run': 'Error',
                'next_automation_run': 'Error',
                'applications_today': 0,
                'cpu_usage': 0,
                'memory_usage': 0,
                'disk_usage': 0,
                'recent_logs': []
            }
    
    def run_diagnostics(self) -> Dict[str, Any]:
        """Run system diagnostics and return results."""
        try:
            diagnostics = {
                'database_connection': False,
                'encryption_service': False,
                'browser_availability': False,
                'disk_space': False,
                'memory_available': False,
                'errors': []
            }
            
            # Test database connection
            try:
                result = db.session.execute(text("SELECT 1 as test")).fetchone()
                diagnostics['database_connection'] = result and result[0] == 1
            except Exception as e:
                diagnostics['errors'].append(f"Database connection failed: {str(e)}")
            
            # Test encryption service
            try:
                test_data = "test_encryption"
                encrypted = encryption_service.encrypt_data(test_data)
                decrypted = encryption_service.decrypt_data(encrypted)
                diagnostics['encryption_service'] = decrypted == test_data
            except Exception as e:
                diagnostics['errors'].append(f"Encryption service failed: {str(e)}")
            
            # Check disk space (at least 1GB free)
            try:
                disk = psutil.disk_usage('/')
                free_gb = disk.free / (1024**3)
                diagnostics['disk_space'] = free_gb > 1.0
                if not diagnostics['disk_space']:
                    diagnostics['errors'].append(f"Low disk space: {free_gb:.1f}GB free")
            except Exception as e:
                diagnostics['errors'].append(f"Disk space check failed: {str(e)}")
            
            # Check available memory (at least 500MB free)
            try:
                memory = psutil.virtual_memory()
                free_mb = memory.available / (1024**2)
                diagnostics['memory_available'] = free_mb > 500
                if not diagnostics['memory_available']:
                    diagnostics['errors'].append(f"Low memory: {free_mb:.0f}MB available")
            except Exception as e:
                diagnostics['errors'].append(f"Memory check failed: {str(e)}")
            
            # Browser availability would be checked here
            diagnostics['browser_availability'] = True  # Placeholder
            
            return diagnostics
            
        except Exception as e:
            return {
                'database_connection': False,
                'encryption_service': False,
                'browser_availability': False,
                'disk_space': False,
                'memory_available': False,
                'errors': [f"Diagnostics failed: {str(e)}"]
            }
    
    def _merge_settings(self, defaults: Dict[str, Any], user_settings: Dict[str, Any]) -> Dict[str, Any]:
        """Merge user settings with defaults to ensure all keys exist."""
        merged = defaults.copy()
        
        for category, settings in user_settings.items():
            if category in merged:
                merged[category].update(settings)
            else:
                merged[category] = settings
        
        return merged


# Create global instance
settings_service = SettingsService()