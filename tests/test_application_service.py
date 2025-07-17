"""
Tests for the application service.
"""
import unittest
import uuid
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from models.database import db
from models.application import Application, ApplicationStatus
from models.job import Job
from models.user import User
from services.application_service import ApplicationService, ApplicationResult


class TestApplicationService(unittest.TestCase):
    """Test cases for ApplicationService."""
    
    def setUp(self):
        """Set up test environment."""
        # Create mock app
        self.mock_app = MagicMock()
        self.mock_app.config = {'MAX_APPLICATION_RETRIES': 3}
        
        # Create service instance
        self.service = ApplicationService(self.mock_app)
        
        # Mock database session
        self.db_session_patch = patch('services.application_service.db.session')
        self.mock_db_session = self.db_session_patch.start()
        
        # Create test data
        self.user_id = str(uuid.uuid4())
        self.job_id = str(uuid.uuid4())
        self.application_id = str(uuid.uuid4())
        
        # Create mock objects
        self.mock_user = MagicMock(spec=User)
        self.mock_user.id = self.user_id
        
        self.mock_job = MagicMock(spec=Job)
        self.mock_job.id = self.job_id
        
        self.mock_application = MagicMock(spec=Application)
        self.mock_application.id = self.application_id
        self.mock_application.user_id = self.user_id
        self.mock_application.job_id = self.job_id
        self.mock_application.status = ApplicationStatus.PENDING
        self.mock_application.is_active = True
        self.mock_application.retry_count = "0"
        self.mock_application.error_count = "0"
        self.mock_application.created_at = datetime.utcnow()
        self.mock_application.updated_at = datetime.utcnow()
        self.mock_application.submitted_at = None
    
    def tearDown(self):
        """Clean up after tests."""
        self.db_session_patch.stop()
    
    def test_get_application_by_id(self):
        """Test retrieving an application by ID."""
        # Mock query
        mock_query = MagicMock()
        mock_query.get.return_value = self.mock_application
        
        # Set up Application.query
        with patch('services.application_service.Application.query', mock_query):
            result = self.service.get_application_by_id(self.application_id)
            
            # Verify result
            self.assertEqual(result, self.mock_application)
            mock_query.get.assert_called_once_with(self.application_id)
    
    def test_get_application_by_id_not_found(self):
        """Test retrieving a non-existent application."""
        # Mock query
        mock_query = MagicMock()
        mock_query.get.return_value = None
        
        # Set up Application.query
        with patch('services.application_service.Application.query', mock_query):
            result = self.service.get_application_by_id(self.application_id)
            
            # Verify result
            self.assertIsNone(result)
            mock_query.get.assert_called_once_with(self.application_id)
    
    def test_get_applications_by_user(self):
        """Test retrieving applications for a user."""
        # Mock query
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.filter_by.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = [self.mock_application]
        
        # Set up Application.query
        with patch('services.application_service.Application.query', mock_query):
            result = self.service.get_applications_by_user(self.user_id)
            
            # Verify result
            self.assertEqual(result, [self.mock_application])
            mock_query.filter.assert_called()
            mock_query.order_by.assert_called()
            mock_query.limit.assert_called_with(100)
            mock_query.offset.assert_called_with(0)
            mock_query.all.assert_called_once()
    
    def test_create_application(self):
        """Test creating a new application."""
        # Mock User and Job queries
        mock_user_query = MagicMock()
        mock_user_query.get.return_value = self.mock_user
        
        mock_job_query = MagicMock()
        mock_job_query.get.return_value = self.mock_job
        
        # Mock Application query for existing application check
        mock_app_query = MagicMock()
        mock_app_query.filter.return_value = mock_app_query
        mock_app_query.first.return_value = None  # No existing application
        
        # Set up patches
        with patch('services.application_service.User.query', mock_user_query), \
             patch('services.application_service.Job.query', mock_job_query), \
             patch('services.application_service.Application.query', mock_app_query), \
             patch('services.application_service.uuid.uuid4', return_value=uuid.UUID(self.application_id)):
            
            # Test creating application
            materials = {'resume_version': 'resume1', 'cover_letter_version': 'cover1'}
            result = self.service.create_application(self.user_id, self.job_id, materials)
            
            # Verify result
            self.assertTrue(result.success)
            self.assertEqual(result.application_id, self.application_id)
            self.assertEqual(result.message, "Application created successfully")
            
            # Verify db operations
            self.mock_db_session.add.assert_called_once()
            self.mock_db_session.commit.assert_called_once()
    
    def test_create_application_existing(self):
        """Test creating an application that already exists."""
        # Mock User and Job queries
        mock_user_query = MagicMock()
        mock_user_query.get.return_value = self.mock_user
        
        mock_job_query = MagicMock()
        mock_job_query.get.return_value = self.mock_job
        
        # Mock Application query for existing application check
        mock_app_query = MagicMock()
        mock_app_query.filter.return_value = mock_app_query
        mock_app_query.first.return_value = self.mock_application  # Existing application
        
        # Set up patches
        with patch('services.application_service.User.query', mock_user_query), \
             patch('services.application_service.Job.query', mock_job_query), \
             patch('services.application_service.Application.query', mock_app_query):
            
            # Test creating application
            result = self.service.create_application(self.user_id, self.job_id)
            
            # Verify result
            self.assertFalse(result.success)
            self.assertEqual(result.application_id, self.application_id)
            self.assertEqual(result.message, "Application already exists for this job")
            
            # Verify no db operations
            self.mock_db_session.add.assert_not_called()
            self.mock_db_session.commit.assert_not_called()
    
    def test_update_application_status(self):
        """Test updating application status."""
        # Mock get_application_by_id
        with patch.object(self.service, 'get_application_by_id', return_value=self.mock_application):
            # Test updating status
            result = self.service.update_application_status(
                self.application_id, 
                ApplicationStatus.SUBMITTED
            )
            
            # Verify result
            self.assertTrue(result.success)
            self.assertEqual(result.application_id, self.application_id)
            
            # Verify application method calls
            self.mock_application.update_status.assert_called_once_with(
                ApplicationStatus.SUBMITTED, None
            )
            
            # Verify db operations
            self.mock_db_session.commit.assert_called_once()
    
    def test_update_application_status_not_found(self):
        """Test updating status for non-existent application."""
        # Mock get_application_by_id
        with patch.object(self.service, 'get_application_by_id', return_value=None):
            # Test updating status
            result = self.service.update_application_status(
                self.application_id, 
                ApplicationStatus.SUBMITTED
            )
            
            # Verify result
            self.assertFalse(result.success)
            self.assertEqual(result.message, "Application not found")
            
            # Verify no db operations
            self.mock_db_session.commit.assert_not_called()
    
    def test_retry_failed_application(self):
        """Test retrying a failed application."""
        # Set up mock application
        self.mock_application.status = ApplicationStatus.FAILED
        self.mock_application.can_retry.return_value = True
        
        # Mock get_application_by_id
        with patch.object(self.service, 'get_application_by_id', return_value=self.mock_application):
            # Test retrying application
            result = self.service.retry_failed_application(self.application_id)
            
            # Verify result
            self.assertTrue(result.success)
            self.assertEqual(result.application_id, self.application_id)
            
            # Verify application method calls
            self.mock_application.increment_retry_count.assert_called_once()
            self.mock_application.update_status.assert_called_once_with(ApplicationStatus.PENDING)
            
            # Verify db operations
            self.mock_db_session.commit.assert_called_once()
    
    def test_retry_failed_application_max_retries(self):
        """Test retrying an application that has reached max retries."""
        # Set up mock application
        self.mock_application.status = ApplicationStatus.FAILED
        self.mock_application.can_retry.return_value = False
        
        # Mock get_application_by_id
        with patch.object(self.service, 'get_application_by_id', return_value=self.mock_application):
            # Test retrying application
            result = self.service.retry_failed_application(self.application_id)
            
            # Verify result
            self.assertFalse(result.success)
            self.assertEqual(result.application_id, self.application_id)
            self.assertIn("Maximum retry attempts", result.message)
            
            # Verify no application method calls
            self.mock_application.increment_retry_count.assert_not_called()
            self.mock_application.update_status.assert_not_called()
            
            # Verify no db operations
            self.mock_db_session.commit.assert_not_called()
    
    def test_submit_application(self):
        """Test submitting an application."""
        # Mock get_application_by_id
        with patch.object(self.service, 'get_application_by_id', return_value=self.mock_application):
            # Test submitting application
            result = self.service.submit_application(self.application_id)
            
            # Verify result
            self.assertTrue(result.success)
            self.assertEqual(result.application_id, self.application_id)
            
            # Verify application method calls
            self.mock_application.update_status.assert_called_once_with(ApplicationStatus.SUBMITTED)
            
            # Verify db operations
            self.mock_db_session.commit.assert_called_once()
    
    def test_mark_application_failed(self):
        """Test marking an application as failed."""
        # Mock get_application_by_id
        with patch.object(self.service, 'get_application_by_id', return_value=self.mock_application):
            # Test marking application as failed
            error_message = "Connection timeout during form submission"
            result = self.service.mark_application_failed(self.application_id, error_message)
            
            # Verify result
            self.assertTrue(result.success)
            self.assertEqual(result.application_id, self.application_id)
            self.assertEqual(result.error, error_message)
            
            # Verify application method calls
            self.mock_application.update_status.assert_called_once_with(
                ApplicationStatus.FAILED, error_message
            )
            
            # Verify db operations
            self.mock_db_session.commit.assert_called_once()
    
    def test_get_applications_needing_followup(self):
        """Test getting applications needing follow-up."""
        # Mock query
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = [self.mock_application]
        
        # Set up Application.query
        with patch('services.application_service.Application.query', mock_query):
            # Test getting applications needing follow-up
            result = self.service.get_applications_needing_followup(days_threshold=14)
            
            # Verify result
            self.assertEqual(result, [self.mock_application])
            mock_query.filter.assert_called()
            mock_query.all.assert_called_once()
    
    def test_application_result_to_dict(self):
        """Test ApplicationResult to_dict method."""
        # Create ApplicationResult
        result = ApplicationResult(
            success=True,
            application_id=self.application_id,
            message="Test message",
            error="Test error",
            confirmation_details={"id": "conf123"}
        )
        
        # Convert to dict
        result_dict = result.to_dict()
        
        # Verify dict
        self.assertEqual(result_dict["success"], True)
        self.assertEqual(result_dict["application_id"], self.application_id)
        self.assertEqual(result_dict["message"], "Test message")
        self.assertEqual(result_dict["error"], "Test error")
        self.assertEqual(result_dict["confirmation_details"], {"id": "conf123"})


if __name__ == '__main__':
    unittest.main()