"""
Tests for the notification service.
"""
import unittest
from unittest.mock import patch, MagicMock, Mock
from datetime import datetime
from services.notification_service import Notification, NotificationService


class TestNotification(unittest.TestCase):
    """Test cases for the Notification class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a sample notification for testing
        self.sample_notification = Notification(
            id='test-notification-id',
            user_id='test-user-id',
            title='Test Notification',
            message='This is a test notification',
            notification_type='test',
            related_entity_id='test-entity-id',
            is_read=False,
            created_at=datetime.utcnow()
        )
    
    def test_notification_to_dict(self):
        """Test converting a notification to dictionary."""
        notification_dict = self.sample_notification.to_dict()
        
        self.assertEqual(notification_dict['id'], 'test-notification-id')
        self.assertEqual(notification_dict['user_id'], 'test-user-id')
        self.assertEqual(notification_dict['title'], 'Test Notification')
        self.assertEqual(notification_dict['message'], 'This is a test notification')
        self.assertEqual(notification_dict['notification_type'], 'test')
        self.assertEqual(notification_dict['related_entity_id'], 'test-entity-id')
        self.assertFalse(notification_dict['is_read'])
        self.assertIsNotNone(notification_dict['created_at'])


@patch('services.notification_service.db')
class TestNotificationService(unittest.TestCase):
    """Test cases for the NotificationService class."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a mock Flask app
        self.mock_app = MagicMock()
        self.mock_app.config = {
            'NOTIFICATIONS_ENABLED': True,
            'EMAIL_NOTIFICATIONS_ENABLED': True,
            'SMTP_SERVER': 'smtp.example.com',
            'SMTP_PORT': 587,
            'SMTP_USERNAME': 'test@example.com',
            'SMTP_PASSWORD': 'password123',
            'SENDER_EMAIL': 'noreply@example.com'
        }
        
        # Create a mock app context
        self.mock_app_context = MagicMock()
        self.mock_app.app_context.return_value = self.mock_app_context
        self.mock_app_context.__enter__.return_value = None
        self.mock_app_context.__exit__.return_value = None
    
    def test_init_app(self, mock_db):
        """Test initializing the notification service with a Flask app."""
        # Mock the database engine
        mock_db.engine.has_table.return_value = True
        
        # Create notification service and initialize with app
        notification_service = NotificationService()
        notification_service.init_app(self.mock_app)
        
        # Verify configuration was loaded
        self.assertTrue(notification_service.notifications_enabled)
        self.assertTrue(notification_service.email_notifications_enabled)
        self.assertEqual(notification_service.smtp_server, 'smtp.example.com')
        self.assertEqual(notification_service.smtp_port, 587)
        self.assertEqual(notification_service.smtp_username, 'test@example.com')
        self.assertEqual(notification_service.smtp_password, 'password123')
        self.assertEqual(notification_service.sender_email, 'noreply@example.com')
    
    def test_create_notifications_table(self, mock_db):
        """Test creating the notifications table."""
        # Reset the mock to clear any previous calls
        mock_db.reset_mock()
        
        # Mock the database engine
        mock_db.engine.has_table.return_value = False
        
        # Create notification service without initializing with app
        notification_service = NotificationService()
        
        # Call the method to create the table directly
        notification_service._create_notifications_table()
        
        # Verify the SQL execution was called
        mock_db.engine.execute.assert_called_once()
        self.assertTrue('CREATE TABLE IF NOT EXISTS notifications' in 
                       str(mock_db.engine.execute.call_args[0][0]))
    
    @patch('uuid.uuid4')
    def test_create_notification(self, mock_uuid, mock_db):
        """Test creating a notification."""
        # Mock UUID generation
        mock_uuid.return_value = 'test-notification-id'
        
        # Create notification service and initialize with app
        notification_service = NotificationService()
        notification_service.init_app(self.mock_app)
        
        # Call the method to create a notification
        result = notification_service.create_notification(
            user_id='test-user-id',
            title='Test Notification',
            message='This is a test notification',
            notification_type='test',
            related_entity_id='test-entity-id'
        )
        
        # Verify the result and SQL execution
        self.assertEqual(result, 'test-notification-id')
        mock_db.engine.execute.assert_called_once()
        self.assertEqual(mock_db.engine.execute.call_args[0][1], 'test-notification-id')
        self.assertEqual(mock_db.engine.execute.call_args[0][2], 'test-user-id')
        self.assertEqual(mock_db.engine.execute.call_args[0][3], 'Test Notification')
    
    def test_get_notifications(self, mock_db):
        """Test retrieving notifications."""
        # Mock the database result
        mock_result = MagicMock()
        mock_result.__iter__.return_value = [
            ('test-id', 'test-user-id', 'Test Title', 'Test Message', 
             'test_type', 'test-entity-id', False, datetime.utcnow())
        ]
        mock_db.engine.execute.return_value = mock_result
        
        # Create notification service and initialize with app
        notification_service = NotificationService()
        notification_service.init_app(self.mock_app)
        
        # Call the method to get notifications
        notifications = notification_service.get_notifications(
            user_id='test-user-id',
            unread_only=True,
            limit=10,
            offset=0
        )
        
        # Verify the result
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]['title'], 'Test Title')
        self.assertEqual(notifications[0]['user_id'], 'test-user-id')
        mock_db.engine.execute.assert_called_once()
    
    def test_mark_notification_read(self, mock_db):
        """Test marking a notification as read."""
        # Create notification service and initialize with app
        notification_service = NotificationService()
        notification_service.init_app(self.mock_app)
        
        # Call the method to mark notification as read
        result = notification_service.mark_notification_read(
            notification_id='test-notification-id',
            is_read=True
        )
        
        # Verify the result and SQL execution
        self.assertTrue(result)
        mock_db.engine.execute.assert_called_once_with(
            "UPDATE notifications SET is_read = ? WHERE id = ?",
            True, 'test-notification-id'
        )
    
    def test_mark_all_read(self, mock_db):
        """Test marking all notifications as read."""
        # Create notification service and initialize with app
        notification_service = NotificationService()
        notification_service.init_app(self.mock_app)
        
        # Call the method to mark all notifications as read
        result = notification_service.mark_all_read(user_id='test-user-id')
        
        # Verify the result and SQL execution
        self.assertTrue(result)
        mock_db.engine.execute.assert_called_once_with(
            "UPDATE notifications SET is_read = TRUE WHERE user_id = ?",
            'test-user-id'
        )
    
    def test_delete_notification(self, mock_db):
        """Test deleting a notification."""
        # Create notification service and initialize with app
        notification_service = NotificationService()
        notification_service.init_app(self.mock_app)
        
        # Call the method to delete a notification
        result = notification_service.delete_notification(
            notification_id='test-notification-id'
        )
        
        # Verify the result and SQL execution
        self.assertTrue(result)
        mock_db.engine.execute.assert_called_once_with(
            "DELETE FROM notifications WHERE id = ?",
            'test-notification-id'
        )
    
    def test_delete_all_notifications(self, mock_db):
        """Test deleting all notifications for a user."""
        # Create notification service and initialize with app
        notification_service = NotificationService()
        notification_service.init_app(self.mock_app)
        
        # Call the method to delete all notifications
        result = notification_service.delete_all_notifications(
            user_id='test-user-id'
        )
        
        # Verify the result and SQL execution
        self.assertTrue(result)
        mock_db.engine.execute.assert_called_once_with(
            "DELETE FROM notifications WHERE user_id = ?",
            'test-user-id'
        )
    
    def test_get_unread_count(self, mock_db):
        """Test getting unread notification count."""
        # Mock the database result
        mock_result = MagicMock()
        mock_result.scalar.return_value = 5
        mock_db.engine.execute.return_value = mock_result
        
        # Create notification service and initialize with app
        notification_service = NotificationService()
        notification_service.init_app(self.mock_app)
        
        # Call the method to get unread count
        count = notification_service.get_unread_count(user_id='test-user-id')
        
        # Verify the result
        self.assertEqual(count, 5)
        mock_db.engine.execute.assert_called_once()
    
    @patch('smtplib.SMTP')
    @patch('services.notification_service.User')
    def test_send_email_notification(self, mock_user_model, mock_smtp, mock_db):
        """Test sending email notifications."""
        # Mock the user query
        mock_user = MagicMock()
        mock_user.email = 'user@example.com'
        mock_user_query = MagicMock()
        mock_user_query.get.return_value = mock_user
        mock_user_model.query = mock_user_query
        
        # Mock SMTP server
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Create notification service and initialize with app
        notification_service = NotificationService()
        notification_service.init_app(self.mock_app)
        
        # Call the method to send email notification
        result = notification_service.send_email_notification(
            user_id='test-user-id',
            subject='Test Email',
            message='This is a test email',
            html_message='<p>This is a test email</p>'
        )
        
        # Verify the result and SMTP operations
        self.assertTrue(result)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('test@example.com', 'password123')
        mock_server.send_message.assert_called_once()
    
    @patch('services.notification_service.ApplicationStatus')
    def test_notify_application_status_change(self, mock_application_status, mock_db):
        """Test notification for application status changes."""
        # Create mock statuses
        mock_old_status = MagicMock()
        mock_old_status.value = "APPLIED"
        mock_new_status = MagicMock()
        mock_new_status.value = "INTERVIEW_SCHEDULED"
        
        # Mock important statuses list
        mock_application_status.SUBMITTED = mock_new_status
        mock_application_status.INTERVIEW_SCHEDULED = mock_new_status
        mock_application_status.OFFER_RECEIVED = mock_new_status
        mock_application_status.REJECTED = mock_new_status
        mock_application_status.ACCEPTED = mock_new_status
        
        # Create notification service with mocked dependencies
        with patch('services.notification_service.Application') as mock_application_model:
            with patch('services.notification_service.NotificationService.create_notification') as mock_create_notification:
                with patch('services.notification_service.NotificationService.send_email_notification') as mock_send_email:
                    # Mock application query
                    mock_application = MagicMock()
                    mock_application.user_id = 'test-user-id'
                    mock_job = MagicMock()
                    mock_job.title = 'Software Engineer'
                    mock_job.company = 'Test Company'
                    mock_application.job = mock_job
                    
                    mock_application_query = MagicMock()
                    mock_application_query.get.return_value = mock_application
                    mock_application_model.query = mock_application_query
                    
                    # Mock notification creation
                    mock_create_notification.return_value = 'new-notification-id'
                    mock_send_email.return_value = True
                    
                    # Create notification service and initialize with app
                    notification_service = NotificationService()
                    notification_service.init_app(self.mock_app)
                    
                    # Call the method to notify about application status change
                    result = notification_service.notify_application_status_change(
                        application_id='test-application-id',
                        old_status=mock_old_status,
                        new_status=mock_new_status
                    )
                    
                    # Verify the result and notification creation
                    self.assertTrue(result)
                    mock_create_notification.assert_called_once()
                    mock_send_email.assert_called
    
    @patch('services.notification_service.NotificationService.create_notification')
    @patch('services.notification_service.NotificationService.send_email_notification')
    def test_notify_system_alert(self, mock_send_email, mock_create_notification, mock_db):
        """Test system alert notifications."""
        # Mock notification creation
        mock_create_notification.return_value = 'new-notification-id'
        
        # Create notification service and initialize with app
        notification_service = NotificationService()
        notification_service.init_app(self.mock_app)
        
        # Call the method to notify about system alert
        result = notification_service.notify_system_alert(
            user_id='test-user-id',
            alert_type='error',
            message='Test error message'
        )
        
        # Verify the result and notification creation
        self.assertTrue(result)
        mock_create_notification.assert_called_once()
        mock_send_email.assert_called_once()
    
    @patch('services.notification_service.NotificationService.create_notification')
    @patch('services.notification_service.NotificationService.send_email_notification')
    def test_notify_automation_status(self, mock_send_email, mock_create_notification, mock_db):
        """Test automation status notifications."""
        # Mock notification creation
        mock_create_notification.return_value = 'new-notification-id'
        
        # Create notification service and initialize with app
        notification_service = NotificationService()
        notification_service.init_app(self.mock_app)
        
        # Prepare test data
        details = {
            'jobs_found': 10,
            'applications_submitted': 5,
            'errors': ['Error 1', 'Error 2']
        }
        
        # Call the method to notify about automation status
        result = notification_service.notify_automation_status(
            user_id='test-user-id',
            status='completed',
            details=details
        )
        
        # Verify the result and notification creation
        self.assertTrue(result)
        mock_create_notification.assert_called_once()
        mock_send_email.assert_called_once()


if __name__ == '__main__':
    unittest.main()