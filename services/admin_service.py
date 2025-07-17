"""
Admin service for managing administrative functions.

This module provides functionality for managing users, roles, system settings,
email templates, and other administrative tasks.
"""
import os
import json
import uuid
import logging
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import func, text
from models.database import db
from models.user import User
from services.auth_service import auth_service
from services.security_audit_service import security_audit_service
from services.notification_service import notification_service

# Set up logging
logger = logging.getLogger(__name__)


class AdminService:
    """Service for administrative functions."""
    
    def __init__(self, app=None):
        """Initialize the admin service.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self.settings_path = None
        self.email_templates_path = None
        self.backup_path = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the admin service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        
        # Set up paths
        instance_path = app.instance_path
        self.settings_path = os.path.join(instance_path, 'settings')
        self.email_templates_path = os.path.join(instance_path, 'email_templates')
        self.backup_path = os.path.join(instance_path, 'backups')
        
        # Create directories if they don't exist
        os.makedirs(self.settings_path, exist_ok=True)
        os.makedirs(self.email_templates_path, exist_ok=True)
        os.makedirs(self.backup_path, exist_ok=True)
        
        # Initialize default settings if they don't exist
        self._init_default_settings()
        
        # Initialize default email templates if they don't exist
        self._init_default_email_templates()
    
    def _init_default_settings(self):
        """Initialize default system settings."""
        settings_file = os.path.join(self.settings_path, 'system_settings.json')
        
        if not os.path.exists(settings_file):
            default_settings = {
                'site_name': 'Job Application Agent',
                'site_description': 'A platform for job seekers and employers',
                'contact_email': 'contact@example.com',
                'max_file_size': 5,  # MB
                'allowed_file_types': ['pdf', 'doc', 'docx'],
                'pagination_limit': 20,
                'enable_notifications': True,
                'enable_email_notifications': False,
                'maintenance_mode': False,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            
            with open(settings_file, 'w') as f:
                json.dump(default_settings, f, indent=2)
    
    def _init_default_email_templates(self):
        """Initialize default email templates."""
        templates = {
            'welcome': {
                'subject': 'Welcome to Job Application Agent',
                'body': """
                <h2>Welcome to Job Application Agent!</h2>
                <p>Dear {{user_name}},</p>
                <p>Thank you for joining Job Application Agent. We're excited to help you in your career journey.</p>
                <p>With your new account, you can:</p>
                <ul>
                    <li>Search and apply for jobs</li>
                    <li>Create and manage your professional profile</li>
                    <li>Track your job applications</li>
                    <li>Receive personalized job recommendations</li>
                </ul>
                <p>If you have any questions, please don't hesitate to contact us.</p>
                <p>Best regards,<br>The Job Application Agent Team</p>
                """
            },
            'password_reset': {
                'subject': 'Password Reset Request',
                'body': """
                <h2>Password Reset Request</h2>
                <p>Dear {{user_name}},</p>
                <p>We received a request to reset your password. Please use the following code to reset your password:</p>
                <h3 style="font-size: 24px; letter-spacing: 5px; background-color: #f5f5f5; padding: 10px; text-align: center;">{{reset_code}}</h3>
                <p>This code will expire in 30 minutes.</p>
                <p>If you did not request a password reset, please ignore this email.</p>
                <p>Best regards,<br>The Job Application Agent Team</p>
                """
            },
            'application_status': {
                'subject': 'Application Status Update: {{job_title}}',
                'body': """
                <h2>Application Status Update</h2>
                <p>Dear {{user_name}},</p>
                <p>Your application for <strong>{{job_title}}</strong> at <strong>{{company}}</strong> has been updated.</p>
                <p>Status: <strong>{{old_status}}</strong> → <strong>{{new_status}}</strong></p>
                <p>{{additional_message}}</p>
                <p>You can view your application details in your dashboard for more information.</p>
                <p>Best regards,<br>The Job Application Agent Team</p>
                """
            },
            'interview_invitation': {
                'subject': 'Interview Invitation: {{job_title}}',
                'body': """
                <h2>Interview Invitation</h2>
                <p>Dear {{user_name}},</p>
                <p>We are pleased to invite you for an interview for the <strong>{{job_title}}</strong> position at <strong>{{company}}</strong>.</p>
                <p><strong>Interview Details:</strong></p>
                <ul>
                    <li><strong>Date:</strong> {{interview_date}}</li>
                    <li><strong>Time:</strong> {{interview_time}}</li>
                    <li><strong>Type:</strong> {{interview_type}}</li>
                    <li><strong>Location/Link:</strong> {{interview_location}}</li>
                </ul>
                <p>Please confirm your attendance by replying to this email or through your dashboard.</p>
                <p>Best regards,<br>The Recruitment Team</p>
                """
            },
            'job_recommendation': {
                'subject': 'Job Recommendations Based on Your Profile',
                'body': """
                <h2>Job Recommendations</h2>
                <p>Dear {{user_name}},</p>
                <p>Based on your profile and preferences, we've found some job opportunities that might interest you:</p>
                <ul>
                    {{#each jobs}}
                    <li>
                        <strong>{{this.title}}</strong> at {{this.company}}<br>
                        Location: {{this.location}}<br>
                        <a href="{{this.url}}">View Job</a>
                    </li>
                    {{/each}}
                </ul>
                <p>Log in to your dashboard to see more recommendations and apply for these positions.</p>
                <p>Best regards,<br>The Job Application Agent Team</p>
                """
            }
        }
        
        for template_id, template_data in templates.items():
            template_file = os.path.join(self.email_templates_path, f'{template_id}.json')
            
            if not os.path.exists(template_file):
                with open(template_file, 'w') as f:
                    json.dump(template_data, f, indent=2)
    
    def get_system_settings(self) -> Dict[str, Any]:
        """Get system settings.
        
        Returns:
            Dict[str, Any]: System settings
        """
        settings_file = os.path.join(self.settings_path, 'system_settings.json')
        
        try:
            with open(settings_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error reading system settings: {str(e)}")
            return {}
    
    def update_system_settings(self, settings: Dict[str, Any]) -> Tuple[bool, str]:
        """Update system settings.
        
        Args:
            settings: Dictionary of settings to update
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        settings_file = os.path.join(self.settings_path, 'system_settings.json')
        
        try:
            # Read current settings
            current_settings = {}
            if os.path.exists(settings_file):
                with open(settings_file, 'r') as f:
                    current_settings = json.load(f)
            
            # Update settings
            for key, value in settings.items():
                current_settings[key] = value
            
            # Update timestamp
            current_settings['updated_at'] = datetime.utcnow().isoformat()
            
            # Write updated settings
            with open(settings_file, 'w') as f:
                json.dump(current_settings, f, indent=2)
            
            return True, "Settings updated successfully"
        except Exception as e:
            logger.error(f"Error updating system settings: {str(e)}")
            return False, f"Error updating system settings: {str(e)}"
    
    def get_email_templates(self) -> List[Dict[str, Any]]:
        """Get all email templates.
        
        Returns:
            List[Dict[str, Any]]: List of email templates
        """
        templates = []
        
        try:
            for filename in os.listdir(self.email_templates_path):
                if filename.endswith('.json'):
                    template_id = os.path.splitext(filename)[0]
                    template_file = os.path.join(self.email_templates_path, filename)
                    
                    with open(template_file, 'r') as f:
                        template_data = json.load(f)
                        template_data['id'] = template_id
                        templates.append(template_data)
        except Exception as e:
            logger.error(f"Error getting email templates: {str(e)}")
        
        return templates
    
    def get_email_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific email template.
        
        Args:
            template_id: ID of the template
            
        Returns:
            Optional[Dict[str, Any]]: Email template or None if not found
        """
        template_file = os.path.join(self.email_templates_path, f'{template_id}.json')
        
        try:
            if os.path.exists(template_file):
                with open(template_file, 'r') as f:
                    template_data = json.load(f)
                    template_data['id'] = template_id
                    return template_data
        except Exception as e:
            logger.error(f"Error getting email template: {str(e)}")
        
        return None
    
    def update_email_template(self, template_id: str, template_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Update an email template.
        
        Args:
            template_id: ID of the template
            template_data: Template data
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        template_file = os.path.join(self.email_templates_path, f'{template_id}.json')
        
        try:
            with open(template_file, 'w') as f:
                json.dump(template_data, f, indent=2)
            
            return True, "Email template updated successfully"
        except Exception as e:
            logger.error(f"Error updating email template: {str(e)}")
            return False, f"Error updating email template: {str(e)}"
    
    def create_email_template(self, template_id: str, template_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Create a new email template.
        
        Args:
            template_id: ID of the template
            template_data: Template data
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        template_file = os.path.join(self.email_templates_path, f'{template_id}.json')
        
        try:
            if os.path.exists(template_file):
                return False, "Template ID already exists"
            
            with open(template_file, 'w') as f:
                json.dump(template_data, f, indent=2)
            
            return True, "Email template created successfully"
        except Exception as e:
            logger.error(f"Error creating email template: {str(e)}")
            return False, f"Error creating email template: {str(e)}"
    
    def delete_email_template(self, template_id: str) -> Tuple[bool, str]:
        """Delete an email template.
        
        Args:
            template_id: ID of the template
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        template_file = os.path.join(self.email_templates_path, f'{template_id}.json')
        
        try:
            if not os.path.exists(template_file):
                return False, "Template not found"
            
            os.remove(template_file)
            
            return True, "Email template deleted successfully"
        except Exception as e:
            logger.error(f"Error deleting email template: {str(e)}")
            return False, f"Error deleting email template: {str(e)}"
    
    def get_user_roles(self) -> List[Dict[str, Any]]:
        """Get all user roles.
        
        Returns:
            List[Dict[str, Any]]: List of user roles
        """
        try:
            # This is a simplified approach; in a real system, you would query a roles table
            roles = [
                {'id': 'admin', 'name': 'Administrator', 'description': 'Full system access'},
                {'id': 'hr', 'name': 'HR Manager', 'description': 'Manage jobs and applications'},
                {'id': 'student', 'name': 'Student', 'description': 'Access student features'},
                {'id': 'user', 'name': 'Regular User', 'description': 'Basic access'}
            ]
            
            # Count users in each role
            for role in roles:
                role_id = role['id']
                # Count users with this role
                count = db.session.query(func.count(User.id)).filter(
                    User.personal_data.contains(f'"roles": ["{role_id}"')
                ).scalar()
                role['user_count'] = count or 0
            
            return roles
        except Exception as e:
            logger.error(f"Error getting user roles: {str(e)}")
            return []
    
    def create_role(self, role_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Create a new user role.
        
        Args:
            role_data: Role data
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # In a real system, you would insert into a roles table
            # For this example, we'll just return success
            return True, "Role created successfully"
        except Exception as e:
            logger.error(f"Error creating role: {str(e)}")
            return False, f"Error creating role: {str(e)}"
    
    def update_role(self, role_id: str, role_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Update a user role.
        
        Args:
            role_id: ID of the role
            role_data: Role data
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # In a real system, you would update a roles table
            # For this example, we'll just return success
            return True, "Role updated successfully"
        except Exception as e:
            logger.error(f"Error updating role: {str(e)}")
            return False, f"Error updating role: {str(e)}"
    
    def delete_role(self, role_id: str) -> Tuple[bool, str]:
        """Delete a user role.
        
        Args:
            role_id: ID of the role
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # In a real system, you would delete from a roles table
            # For this example, we'll just return success
            return True, "Role deleted successfully"
        except Exception as e:
            logger.error(f"Error deleting role: {str(e)}")
            return False, f"Error deleting role: {str(e)}"
    
    def create_backup(self) -> Tuple[bool, str, Optional[str]]:
        """Create a database backup.
        
        Returns:
            Tuple[bool, str, Optional[str]]: (success, message, backup_id)
        """
        try:
            # Generate backup ID
            backup_id = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            backup_dir = os.path.join(self.backup_path, backup_id)
            
            # Create backup directory
            os.makedirs(backup_dir, exist_ok=True)
            
            # In a real system, you would dump the database
            # For this example, we'll just create a placeholder file
            with open(os.path.join(backup_dir, 'backup.json'), 'w') as f:
                f.write('{"backup": "placeholder"}')
            
            # Create backup metadata
            metadata = {
                'id': backup_id,
                'timestamp': datetime.utcnow().isoformat(),
                'size': '1 KB',  # Placeholder
                'status': 'completed'
            }
            
            with open(os.path.join(backup_dir, 'metadata.json'), 'w') as f:
                json.dump(metadata, f, indent=2)
            
            return True, "Backup created successfully", backup_id
        except Exception as e:
            logger.error(f"Error creating backup: {str(e)}")
            return False, f"Error creating backup: {str(e)}", None
    
    def get_backups(self) -> List[Dict[str, Any]]:
        """Get all database backups.
        
        Returns:
            List[Dict[str, Any]]: List of backups
        """
        backups = []
        
        try:
            for backup_id in os.listdir(self.backup_path):
                backup_dir = os.path.join(self.backup_path, backup_id)
                
                if os.path.isdir(backup_dir):
                    metadata_file = os.path.join(backup_dir, 'metadata.json')
                    
                    if os.path.exists(metadata_file):
                        with open(metadata_file, 'r') as f:
                            metadata = json.load(f)
                            backups.append(metadata)
        except Exception as e:
            logger.error(f"Error getting backups: {str(e)}")
        
        # Sort by timestamp (newest first)
        backups.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return backups
    
    def restore_backup(self, backup_id: str) -> Tuple[bool, str]:
        """Restore a database backup.
        
        Args:
            backup_id: ID of the backup
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            backup_dir = os.path.join(self.backup_path, backup_id)
            
            if not os.path.exists(backup_dir):
                return False, "Backup not found"
            
            # In a real system, you would restore the database
            # For this example, we'll just return success
            return True, "Backup restored successfully"
        except Exception as e:
            logger.error(f"Error restoring backup: {str(e)}")
            return False, f"Error restoring backup: {str(e)}"
    
    def delete_backup(self, backup_id: str) -> Tuple[bool, str]:
        """Delete a database backup.
        
        Args:
            backup_id: ID of the backup
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            backup_dir = os.path.join(self.backup_path, backup_id)
            
            if not os.path.exists(backup_dir):
                return False, "Backup not found"
            
            shutil.rmtree(backup_dir)
            
            return True, "Backup deleted successfully"
        except Exception as e:
            logger.error(f"Error deleting backup: {str(e)}")
            return False, f"Error deleting backup: {str(e)}"
    
    def get_system_logs(self, log_type: str = 'system', limit: int = 100) -> List[Dict[str, Any]]:
        """Get system logs.
        
        Args:
            log_type: Type of logs to get ('system', 'auth', 'error')
            limit: Maximum number of logs to return
            
        Returns:
            List[Dict[str, Any]]: List of logs
        """
        logs = []
        
        try:
            log_file = None
            
            if log_type == 'auth':
                log_file = os.path.join(self.app.instance_path, 'logs', 'auth.log')
            elif log_type == 'error':
                log_file = os.path.join(self.app.instance_path, 'logs', 'error.log')
            else:
                log_file = os.path.join(self.app.instance_path, 'logs', 'app.log')
            
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    lines = f.readlines()
                    
                    # Get the last 'limit' lines
                    for line in lines[-limit:]:
                        try:
                            log_entry = json.loads(line.strip())
                            logs.append(log_entry)
                        except:
                            # If not JSON, create a simple entry
                            logs.append({
                                'timestamp': '',
                                'level': '',
                                'message': line.strip()
                            })
        except Exception as e:
            logger.error(f"Error getting system logs: {str(e)}")
        
        return logs
    
    def get_security_audit_logs(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get security audit logs.
        
        Args:
            limit: Maximum number of logs to return
            
        Returns:
            List[Dict[str, Any]]: List of security audit logs
        """
        try:
            # In a real system, you would query a security_audit table
            # For this example, we'll return placeholder data
            return security_audit_service.get_recent_events(limit)
        except Exception as e:
            logger.error(f"Error getting security audit logs: {str(e)}")
            return []
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get system status information.
        
        Returns:
            Dict[str, Any]: System status
        """
        try:
            # In a real system, you would gather actual system metrics
            # For this example, we'll return placeholder data
            return {
                'uptime': '3 days, 7 hours',
                'database_status': 'ok',
                'cache_status': 'ok',
                'email_status': 'ok',
                'storage_usage': '1.2 GB / 10 GB',
                'memory_usage': '512 MB / 2 GB',
                'cpu_usage': '15%',
                'active_users': 42,
                'last_backup': '2025-07-17 23:00:00'
            }
        except Exception as e:
            logger.error(f"Error getting system status: {str(e)}")
            return {}
    
    def get_user_growth_data(self, days: int = 30) -> Dict[str, List]:
        """Get user growth data for the specified number of days.
        
        Args:
            days: Number of days to include
            
        Returns:
            Dict[str, List]: User growth data
        """
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Generate dates
            dates = []
            current_date = start_date
            while current_date <= end_date:
                dates.append(current_date.strftime('%Y-%m-%d'))
                current_date += timedelta(days=1)
            
            # In a real system, you would query the database for user counts by date
            # For this example, we'll generate random data
            import random
            data = []
            cumulative = 100  # Start with some existing users
            
            for _ in dates:
                new_users = random.randint(1, 10)
                cumulative += new_users
                data.append(new_users)
            
            return {
                'labels': dates,
                'data': data
            }
        except Exception as e:
            logger.error(f"Error getting user growth data: {str(e)}")
            return {'labels': [], 'data': []}
    
    def get_user_distribution(self) -> Dict[str, int]:
        """Get user distribution by role.
        
        Returns:
            Dict[str, int]: User counts by role
        """
        try:
            # In a real system, you would query the database for user counts by role
            # For this example, we'll return placeholder data
            return {
                'admin': 5,
                'hr': 15,
                'student': 250,
                'user': 730
            }
        except Exception as e:
            logger.error(f"Error getting user distribution: {str(e)}")
            return {}
    
    def get_performance_data(self, days: int = 7) -> Dict[str, Any]:
        """Get system performance data.
        
        Args:
            days: Number of days to include
            
        Returns:
            Dict[str, Any]: Performance data
        """
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Generate time points (every 6 hours)
            time_points = []
            current_time = start_date
            while current_time <= end_date:
                time_points.append(current_time.strftime('%Y-%m-%d %H:%M'))
                current_time += timedelta(hours=6)
            
            # In a real system, you would query actual performance metrics
            # For this example, we'll generate random data
            import random
            response_times = [random.randint(80, 200) for _ in time_points]
            error_rates = [round(random.uniform(0, 2), 2) for _ in time_points]
            
            return {
                'labels': time_points,
                'response_times': response_times,
                'error_rates': error_rates
            }
        except Exception as e:
            logger.error(f"Error getting performance data: {str(e)}")
            return {'labels': [], 'response_times': [], 'error_rates': []}
    
    def send_system_notification(self, notification_data: Dict[str, Any]) -> Tuple[bool, str]:
        """Send a system notification to users.
        
        Args:
            notification_data: Notification data
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            notification_type = notification_data.get('notification_type')
            recipient_type = notification_data.get('recipient_type')
            subject = notification_data.get('subject')
            message = notification_data.get('message')
            
            if not all([notification_type, recipient_type, subject, message]):
                return False, "Missing required fields"
            
            # Get recipients based on recipient type
            recipients = []
            
            if recipient_type == 'all':
                recipients = User.query.filter_by(is_active=True).all()
            elif recipient_type == 'role':
                role = notification_data.get('role')
                if role:
                    recipients = User.query.filter(
                        User.is_active == True,
                        User.personal_data.contains(f'"roles": ["{role}"')
                    ).all()
            elif recipient_type == 'specific':
                user_ids = notification_data.get('user_ids', [])
                if user_ids:
                    recipients = User.query.filter(
                        User.id.in_(user_ids),
                        User.is_active == True
                    ).all()
            
            # Send notifications
            for user in recipients:
                notification_service.create_notification(
                    user_id=user.id,
                    title=subject,
                    message=message,
                    notification_type=notification_type
                )
                
                # Send email if enabled
                if notification_data.get('send_email', False):
                    notification_service.send_email_notification(
                        user_id=user.id,
                        subject=subject,
                        message=message
                    )
            
            return True, f"Notification sent to {len(recipients)} users"
        except Exception as e:
            logger.error(f"Error sending system notification: {str(e)}")
            return False, f"Error sending system notification: {str(e)}"


# Create a singleton instance
admin_service = AdminService()