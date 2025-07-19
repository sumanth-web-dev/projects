"""
Notification service for managing application status updates and alerts.

This module provides functionality for sending notifications to users through
various channels including in-app notifications and email.
"""

from flask import session
import logging
import json
import uuid
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from sqlalchemy.exc import SQLAlchemyError
from models.database import db
from models.user import User
from models.application import Application, ApplicationStatus
import os

# Set up logging
logger = logging.getLogger(__name__)


class Notification:
    """Model for storing notification data."""
    
    def __init__(self, id: str, user_id: str, title: str, message: str, 
                 notification_type: str, related_entity_id: Optional[str] = None,
                 is_read: bool = False, created_at: Optional[datetime] = None):
        """Initialize a notification.
        
        Args:
            id: Unique notification ID
            user_id: ID of the user this notification is for
            title: Notification title
            message: Notification message content
            notification_type: Type of notification (e.g., 'application_status', 'system_alert')
            related_entity_id: Optional ID of related entity (e.g., application_id)
            is_read: Whether the notification has been read
            created_at: Timestamp when the notification was created
        """
        self.id = id
        self.user_id = user_id
        self.title = title
        self.message = message
        self.notification_type = notification_type
        self.related_entity_id = related_entity_id
        self.is_read = is_read
        self.created_at = created_at or datetime.utcnow()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert notification to dictionary."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'title': self.title,
            'message': self.message,
            'notification_type': self.notification_type,
            'related_entity_id': self.related_entity_id,
            'is_read': self.is_read,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class NotificationService:
    """Service for managing user notifications."""
    
    def __init__(self, app=None):
        """Initialize the notification service.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self.smtp_server = os.environ.get('SMTP_SERVER')
        self.smtp_port = os.environ.get('SMTP_PORT')
        self.smtp_username = os.environ.get('SMTP_USERNAME')
        self.smtp_password = os.environ.get('SMTP_PASSWORD')
        self.sender_email = os.environ.get('SENDER_EMAIL')
        self.notifications_enabled = True
        self.email_notifications_enabled = True # os.environ.get('EMAIL_NOTIFICATIONS_ENABLED', 'true').lower() == 'true'
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the notification service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self.notifications_enabled = app.config.get('NOTIFICATIONS_ENABLED', True)
        self.email_notifications_enabled = app.config.get('EMAIL_NOTIFICATIONS_ENABLED', True)
        
        # Email configuration
        self.smtp_server = app.config.get('SMTP_SERVER')
        self.smtp_port = app.config.get('SMTP_PORT')
        self.smtp_username = app.config.get('SMTP_USERNAME')
        self.smtp_password = app.config.get('SMTP_PASSWORD')
        self.sender_email = app.config.get('SENDER_EMAIL')
        
        # Create notifications table if it doesn't exist
        with app.app_context():
            from sqlalchemy import inspect
            inspector = inspect(db.engine)
            if 'notifications' not in inspector.get_table_names():
                self._create_notifications_table()
    
    def _create_notifications_table(self):
        """Create the notifications table if it doesn't exist."""
        try:
            from sqlalchemy import text
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS notifications (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    title TEXT NOT NULL,
                    message TEXT NOT NULL,
                    notification_type TEXT NOT NULL,
                    related_entity_id TEXT,
                    is_read BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (user_id) REFERENCES users (id)
                )
            """))
            db.session.commit()
            logger.info("Notifications table created successfully")
        except Exception as e:
            logger.error(f"Error creating notifications table: {str(e)}")
    
    def create_notification(self, user_id: str, title: str, message: str, 
                           notification_type: str, related_entity_id: Optional[str] = None) -> Optional[str]:
        """Create a new notification for a user.
        
        Args:
            user_id: ID of the user to notify
            title: Notification title
            message: Notification message content
            notification_type: Type of notification (e.g., 'application_status', 'system_alert')
            related_entity_id: Optional ID of related entity (e.g., application_id)
            
        Returns:
            Optional[str]: The notification ID if successful, None otherwise
        """
        if not self.notifications_enabled:
            logger.info("Notifications are disabled, skipping notification creation")
            return None
        
        try:
            from sqlalchemy import text
            notification_id = str(uuid.uuid4())
            
            # Insert notification into database
            db.session.execute(text(
                """
                INSERT INTO notifications (id, user_id, title, message, notification_type, related_entity_id)
                VALUES (:id, :user_id, :title, :message, :notification_type, :related_entity_id)
                """
            ), {
                "id": notification_id,
                "user_id": user_id,
                "title": title,
                "message": message,
                "notification_type": notification_type,
                "related_entity_id": related_entity_id
            })
            db.session.commit()
            
            logger.info(f"Created notification {notification_id} for user {user_id}")
            return notification_id
        except Exception as e:
            logger.error(f"Error creating notification: {str(e)}")
            return None
    
    def get_notifications(self, user_id: str, unread_only: bool = False, 
                         limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Get notifications for a user.
        
        Args:
            user_id: ID of the user
            unread_only: Whether to only return unread notifications
            limit: Maximum number of notifications to return
            offset: Offset for pagination
            
        Returns:
            List[Dict[str, Any]]: List of notification dictionaries
        """
        try:
            from sqlalchemy import text
            query = """
                SELECT id, user_id, title, message, notification_type, related_entity_id, is_read, created_at
                FROM notifications
                WHERE user_id = :user_id
            """
            
            params = {"user_id": user_id}
            
            if unread_only:
                query += " AND is_read = FALSE"
            
            query += " ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
            params.update({"limit": limit, "offset": offset})
            
            result = db.session.execute(text(query), params)
            
            notifications = []
            for row in result:
                notification = Notification(
                    id=row[0],
                    user_id=row[1],
                    title=row[2],
                    message=row[3],
                    notification_type=row[4],
                    related_entity_id=row[5],
                    is_read=bool(row[6]),
                    created_at=row[7]
                )
                notifications.append(notification.to_dict())
            
            return notifications
        except Exception as e:
            logger.error(f"Error retrieving notifications: {str(e)}")
            return []
    
    def mark_notification_read(self, notification_id: str, is_read: bool = True) -> bool:
        """Mark a notification as read or unread.
        
        Args:
            notification_id: ID of the notification
            is_read: Whether to mark as read (True) or unread (False)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from sqlalchemy import text
            db.session.execute(text(
                "UPDATE notifications SET is_read = :is_read WHERE id = :id"
            ), {
                "is_read": is_read,
                "id": notification_id
            })
            db.session.commit()
            
            logger.info(f"Marked notification {notification_id} as {'read' if is_read else 'unread'}")
            return True
        except Exception as e:
            logger.error(f"Error marking notification as read: {str(e)}")
            return False
    
    def mark_all_read(self, user_id: str) -> bool:
        """Mark all notifications for a user as read.
        
        Args:
            user_id: ID of the user
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from sqlalchemy import text
            db.session.execute(text(
                "UPDATE notifications SET is_read = TRUE WHERE user_id = :user_id"
            ), {
                "user_id": user_id
            })
            db.session.commit()
            
            logger.info(f"Marked all notifications as read for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error marking all notifications as read: {str(e)}")
            return False
    
    def delete_notification(self, notification_id: str) -> bool:
        """Delete a notification.
        
        Args:
            notification_id: ID of the notification
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from sqlalchemy import text
            db.session.execute(text(
                "DELETE FROM notifications WHERE id = :id"
            ), {
                "id": notification_id
            })
            db.session.commit()
            
            logger.info(f"Deleted notification {notification_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting notification: {str(e)}")
            return False
    
    def delete_all_notifications(self, user_id: str) -> bool:
        """Delete all notifications for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from sqlalchemy import text
            db.session.execute(text(
                "DELETE FROM notifications WHERE user_id = :user_id"
            ), {
                "user_id": user_id
            })
            db.session.commit()
            
            logger.info(f"Deleted all notifications for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error deleting all notifications: {str(e)}")
            return False
    
    def get_unread_count(self, user_id: str) -> int:
        """Get the count of unread notifications for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            int: Count of unread notifications
        """
        try:
            from sqlalchemy import text
            result = db.session.execute(text(
                "SELECT COUNT(*) FROM notifications WHERE user_id = :user_id AND is_read = FALSE"
            ), {
                "user_id": user_id
            })
            
            count = result.scalar()
            return count or 0
        except Exception as e:
            logger.error(f"Error getting unread notification count: {str(e)}")
            return 0
    
    def send_email_notification(self, user_id: str, subject: str, 
                              message: str, html_message: Optional[str] = None) -> bool:
        """Send an email notification to a user.
        
        Args:
            user_id: ID of the user to email
            subject: Email subject
            message: Plain text email message
            html_message: Optional HTML version of the message
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self.email_notifications_enabled:
            logger.info("Email notifications are disabled, skipping email")
            return False
        print("#"*20)
        print(f"{self.smtp_server}, {self.smtp_port}, {self.smtp_username}, {self.smtp_password}, {self.sender_email}")
        if not all([self.smtp_server, self.smtp_port, self.smtp_username, 
                   self.smtp_password, self.sender_email]):
            logger.error("Email configuration is incomplete, cannot send email")
            return False
        
        try:
            # Get user email
            # user = User.query.get(user_id)
            # if not user or not user.email:
            #     logger.error(f"User {user_id} not found or has no email")
            #     return False
            
            # recipient_email = user.email
            recipient_email = session['registration_email'] 
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.sender_email
            msg['To'] = recipient_email
            
            # Attach plain text and HTML parts
            msg.attach(MIMEText(message, 'plain'))
            if html_message:
                msg.attach(MIMEText(html_message, 'html'))
            
            # Send email
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
            
            logger.info(f"Sent email notification to user {user_id} ({recipient_email})")
            return True
        except Exception as e:
            logger.error(f"Error sending email notification: {str(e)}")
            return False
    
    def notify_application_status_change(self, application_id: str, 
                                       old_status: ApplicationStatus, 
                                       new_status: ApplicationStatus) -> bool:
        """Notify a user about an application status change.
        
        Args:
            application_id: ID of the application
            old_status: Previous application status
            new_status: New application status
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Get application and user details
            application = Application.query.get(application_id)
            if not application:
                logger.error(f"Application {application_id} not found")
                return False
            
            user_id = application.user_id
            job = application.job
            
            if not job:
                logger.error(f"Job not found for application {application_id}")
                return False
            
            # Create notification title and message
            title = f"Application Status Update: {job.title} at {job.company}"
            message = f"Your application for {job.title} at {job.company} has changed status from {old_status.value} to {new_status.value}."
            
            # Create in-app notification
            notification_id = self.create_notification(
                user_id=user_id,
                title=title,
                message=message,
                notification_type="application_status",
                related_entity_id=application_id
            )
            
            # Send email notification for important status changes
            important_statuses = [
                ApplicationStatus.SUBMITTED,
                ApplicationStatus.INTERVIEW_SCHEDULED,
                ApplicationStatus.OFFER_RECEIVED,
                ApplicationStatus.REJECTED,
                ApplicationStatus.ACCEPTED
            ]
            
            if new_status in important_statuses:
                html_message = f"""
                <h2>Application Status Update</h2>
                <p>Your application for <strong>{job.title}</strong> at <strong>{job.company}</strong> 
                has been updated.</p>
                <p>Status: <strong>{old_status.value}</strong> → <strong>{new_status.value}</strong></p>
                <p>View your application details in the dashboard for more information.</p>
                """
                
                self.send_email_notification(
                    user_id=user_id,
                    subject=title,
                    message=message,
                    html_message=html_message
                )
            
            return notification_id is not None
        except Exception as e:
            logger.error(f"Error creating application status notification: {str(e)}")
            return False
    
    def notify_system_alert(self, user_id: str, alert_type: str, message: str) -> bool:
        """Send a system alert notification to a user.
        
        Args:
            user_id: ID of the user to notify
            alert_type: Type of alert (e.g., 'error', 'warning', 'info')
            message: Alert message
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            title = f"System Alert: {alert_type.capitalize()}"
            
            notification_id = self.create_notification(
                user_id=user_id,
                title=title,
                message=message,
                notification_type=f"system_{alert_type}",
                related_entity_id=None
            )
            
            # Send email for critical alerts
            if alert_type in ['error', 'security']:
                html_message = f"""
                <h2>System Alert: {alert_type.capitalize()}</h2>
                <p>{message}</p>
                <p>Please check your dashboard for more information.</p>
                """
                
                self.send_email_notification(
                    user_id=user_id,
                    subject=title,
                    message=message,
                    html_message=html_message
                )
            
            return notification_id is not None
        except Exception as e:
            logger.error(f"Error creating system alert notification: {str(e)}")
            return False
    
    def notify_job_match(self, user_id: str, job_id: str, match_score: float, 
                       match_reasons: List[str]) -> bool:
        """Notify a user about a high-match job opportunity.
        
        Args:
            user_id: ID of the user to notify
            job_id: ID of the matching job
            match_score: Job match score (0-1)
            match_reasons: List of reasons for the match
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from models.job import Job
            job = Job.query.get(job_id)
            
            if not job:
                logger.error(f"Job {job_id} not found")
                return False
            
            # Format match score as percentage
            score_percent = int(match_score * 100)
            
            title = f"New Job Match: {job.title} at {job.company} ({score_percent}% match)"
            
            # Create message with match reasons
            message = f"We found a new job that matches your profile: {job.title} at {job.company}.\n\n"
            message += f"Match score: {score_percent}%\n\n"
            message += "Why this job matches your profile:\n"
            for reason in match_reasons:
                message += f"- {reason}\n"
            
            notification_id = self.create_notification(
                user_id=user_id,
                title=title,
                message=message,
                notification_type="job_match",
                related_entity_id=job_id
            )
            
            # Send email for high-match jobs (>80%)
            if match_score > 0.8:
                html_message = f"""
                <h2>High-Match Job Opportunity</h2>
                <p>We found a new job that matches your profile: <strong>{job.title}</strong> at <strong>{job.company}</strong>.</p>
                <p>Match score: <strong>{score_percent}%</strong></p>
                <h3>Why this job matches your profile:</h3>
                <ul>
                """
                
                for reason in match_reasons:
                    html_message += f"<li>{reason}</li>"
                
                html_message += """
                </ul>
                <p>View your dashboard to apply for this job.</p>
                """
                
                self.send_email_notification(
                    user_id=user_id,
                    subject=title,
                    message=message,
                    html_message=html_message
                )
            
            return notification_id is not None
        except Exception as e:
            logger.error(f"Error creating job match notification: {str(e)}")
            return False
    
    def notify_automation_status(self, user_id: str, status: str, details: Dict[str, Any]) -> bool:
        """Notify a user about automation status changes.
        
        Args:
            user_id: ID of the user to notify
            status: Automation status (e.g., 'started', 'completed', 'failed')
            details: Dictionary of status details
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            title = f"Automation {status.capitalize()}"
            
            # Create message with details
            message = f"Automation {status} at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}.\n\n"
            
            if 'jobs_found' in details:
                message += f"Jobs found: {details['jobs_found']}\n"
            
            if 'applications_submitted' in details:
                message += f"Applications submitted: {details['applications_submitted']}\n"
            
            if 'errors' in details and details['errors']:
                message += f"\nErrors encountered: {len(details['errors'])}\n"
                for error in details['errors'][:3]:  # Show first 3 errors
                    message += f"- {error}\n"
                
                if len(details['errors']) > 3:
                    message += f"... and {len(details['errors']) - 3} more errors\n"
            
            notification_id = self.create_notification(
                user_id=user_id,
                title=title,
                message=message,
                notification_type=f"automation_{status}",
                related_entity_id=None
            )
            
            # Send email for failed automation or completed with errors
            if status == 'failed' or (status == 'completed' and details.get('errors')):
                html_message = f"""
                <h2>Automation {status.capitalize()}</h2>
                <p>Your automated job application process has {status} at {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')}.</p>
                """
                
                if 'jobs_found' in details:
                    html_message += f"<p>Jobs found: <strong>{details['jobs_found']}</strong></p>"
                
                if 'applications_submitted' in details:
                    html_message += f"<p>Applications submitted: <strong>{details['applications_submitted']}</strong></p>"
                
                if 'errors' in details and details['errors']:
                    html_message += f"<h3>Errors encountered ({len(details['errors'])}):</h3><ul>"
                    for error in details['errors'][:5]:  # Show first 5 errors in email
                        html_message += f"<li>{error}</li>"
                    
                    if len(details['errors']) > 5:
                        html_message += f"<li>... and {len(details['errors']) - 5} more errors</li>"
                    
                    html_message += "</ul>"
                
                html_message += "<p>Check your dashboard for complete details.</p>"
                
                self.send_email_notification(
                    user_id=user_id,
                    subject=title,
                    message=message,
                    html_message=html_message
                )
            
            return notification_id is not None
        except Exception as e:
            logger.error(f"Error creating automation status notification: {str(e)}")
            return False


# Create a singleton instance
notification_service = NotificationService()