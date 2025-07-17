"""
Tests for the profile service.
"""
import os
import uuid
import unittest
import tempfile
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

from models.database import db
from models.user import User
from services.profile_service import ProfileService
from services.encryption_service import encryption_service


class TestProfileService(unittest.TestCase):
    """Test cases for ProfileService."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a mock Flask app
        self.app = MagicMock()
        self.app.config = {
            'UPLOAD_FOLDER': tempfile.mkdtemp(),
            'DEBUG': True
        }
        
        # Create test directories
        os.makedirs(os.path.join(self.app.config['UPLOAD_FOLDER'], 'resumes'), exist_ok=True)
        os.makedirs(os.path.join(self.app.config['UPLOAD_FOLDER'], 'cover_letters'), exist_ok=True)
        
        # Initialize service
        self.profile_service = ProfileService(self.app)
        
        # Mock database session
        self.db_session_mock = MagicMock()
        db.session = self.db_session_mock
    
    def tearDown(self):
        """Clean up after tests."""
        # Remove test directories
        import shutil
        shutil.rmtree(self.app.config['UPLOAD_FOLDER'], ignore_errors=True)
    
    def test_get_user_by_id(self):
        """Test getting a user by ID."""
        # Mock User.query
        mock_user = MagicMock(spec=User)
        mock_user.id = "test_user_id"
        mock_user.email = "test@example.com"
        
        with patch('models.user.User.query') as mock_query:
            mock_query.get.return_value = mock_user
            
            # Test successful retrieval
            user = self.profile_service.get_user_by_id("test_user_id")
            self.assertEqual(user.id, "test_user_id")
            
            # Test user not found
            mock_query.get.return_value = None
            user = self.profile_service.get_user_by_id("nonexistent_id")
            self.assertIsNone(user)
    
    def test_get_user_by_email(self):
        """Test getting a user by email."""
        # Mock User.query
        mock_user = MagicMock(spec=User)
        mock_user.id = "test_user_id"
        mock_user.email = "test@example.com"
        
        with patch('models.user.User.query') as mock_query:
            mock_query.filter_by.return_value.first.return_value = mock_user
            
            # Test successful retrieval
            user = self.profile_service.get_user_by_email("test@example.com")
            self.assertEqual(user.email, "test@example.com")
            
            # Test user not found
            mock_query.filter_by.return_value.first.return_value = None
            user = self.profile_service.get_user_by_email("nonexistent@example.com")
            self.assertIsNone(user)
    
    def test_get_profile(self):
        """Test getting a user's profile."""
        # Mock User
        mock_user = MagicMock(spec=User)
        mock_user.id = "test_user_id"
        mock_user.email = "test@example.com"
        mock_user.to_dict.return_value = {
            'id': "test_user_id",
            'email': "test@example.com",
            'personal_data': {'first_name': 'Test', 'last_name': 'User'},
            'preferences': {'job_titles': ['Developer']}
        }
        
        # Mock get_user_by_id
        with patch.object(self.profile_service, 'get_user_by_id', return_value=mock_user):
            # Mock resume and cover letter lists
            with patch.object(self.profile_service, 'get_resume_list', return_value=[{'id': 'resume1'}]):
                with patch.object(self.profile_service, 'get_cover_letter_list', return_value=[{'id': 'letter1'}]):
                    # Test successful retrieval
                    success, profile, message = self.profile_service.get_profile("test_user_id")
                    
                    self.assertTrue(success)
                    self.assertEqual(profile['id'], "test_user_id")
                    self.assertEqual(profile['email'], "test@example.com")
                    self.assertEqual(len(profile['resumes']), 1)
                    self.assertEqual(len(profile['cover_letters']), 1)
    
    def test_update_personal_info(self):
        """Test updating personal information."""
        # Mock User
        mock_user = MagicMock(spec=User)
        mock_user.id = "test_user_id"
        mock_user.personal_data = {
            'password': 'hashed_password',
            'first_name': 'Old',
            'last_name': 'Name'
        }
        
        # Mock get_user_by_id
        with patch.object(self.profile_service, 'get_user_by_id', return_value=mock_user):
            # Test successful update
            success, message = self.profile_service.update_personal_info(
                "test_user_id",
                {
                    'first_name': 'New',
                    'last_name': 'Name',
                    'phone': '123-456-7890',
                    'address': '123 Main St'
                }
            )
            
            self.assertTrue(success)
            self.assertIn("updated successfully", message)
            
            # Verify password was preserved
            self.assertEqual(mock_user.personal_data['password'], 'hashed_password')
            
            # Verify new fields were added
            self.assertEqual(mock_user.personal_data['first_name'], 'New')
            self.assertEqual(mock_user.personal_data['phone'], '123-456-7890')
            
            # Test validation error
            mock_user.validate_personal_data.side_effect = ValueError("Invalid data")
            success, message = self.profile_service.update_personal_info(
                "test_user_id",
                {'first_name': ''}
            )
            
            self.assertFalse(success)
            self.assertEqual(message, "Invalid data")
    
    def test_update_preferences(self):
        """Test updating job preferences."""
        # Mock User
        mock_user = MagicMock(spec=User)
        mock_user.id = "test_user_id"
        mock_user.preferences = {
            'job_titles': ['Developer'],
            'locations': ['New York']
        }
        
        # Mock get_user_by_id
        with patch.object(self.profile_service, 'get_user_by_id', return_value=mock_user):
            # Test successful update
            success, message = self.profile_service.update_preferences(
                "test_user_id",
                {
                    'job_titles': ['Senior Developer', 'Team Lead'],
                    'locations': ['San Francisco', 'Remote'],
                    'salary_min': 100000,
                    'salary_max': 150000
                }
            )
            
            self.assertTrue(success)
            self.assertIn("updated successfully", message)
            
            # Test validation error
            mock_user.validate_preferences.side_effect = ValueError("Invalid preferences")
            success, message = self.profile_service.update_preferences(
                "test_user_id",
                {'salary_min': 200000, 'salary_max': 100000}  # Invalid range
            )
            
            self.assertFalse(success)
            self.assertEqual(message, "Invalid preferences")
    
    def test_resume_operations(self):
        """Test resume CRUD operations."""
        # Mock User
        mock_user = MagicMock(spec=User)
        mock_user.id = "test_user_id"
        mock_user.personal_data = {'resumes': []}
        
        # Create a temporary resume file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(b"Test resume content")
            resume_path = temp_file.name
        
        try:
            # Mock get_user_by_id
            with patch.object(self.profile_service, 'get_user_by_id', return_value=mock_user):
                # Test add resume
                success, resume_id, message = self.profile_service.add_resume(
                    "test_user_id",
                    resume_path,
                    "My Resume",
                    "Technical resume"
                )
                
                self.assertTrue(success)
                self.assertIsNotNone(resume_id)
                self.assertIn("added successfully", message)
                
                # Verify resume was added to user data
                self.assertEqual(len(mock_user.personal_data['resumes']), 1)
                self.assertEqual(mock_user.personal_data['resumes'][0]['name'], "My Resume")
                self.assertEqual(mock_user.personal_data['resumes'][0]['description'], "Technical resume")
                
                # Test update resume
                mock_user.personal_data['resumes'][0]['id'] = resume_id
                success, message = self.profile_service.update_resume(
                    "test_user_id",
                    resume_id,
                    "Updated Resume",
                    "Updated description"
                )
                
                self.assertTrue(success)
                self.assertIn("updated successfully", message)
                self.assertEqual(mock_user.personal_data['resumes'][0]['name'], "Updated Resume")
                
                # Test get resume file path
                with patch('os.path.exists', return_value=True):
                    success, path, message = self.profile_service.get_resume_file_path(
                        "test_user_id",
                        resume_id
                    )
                    
                    self.assertTrue(success)
                    self.assertIsNotNone(path)
                
                # Test delete resume
                with patch('os.path.exists', return_value=True), patch('os.remove') as mock_remove:
                    success, message = self.profile_service.delete_resume(
                        "test_user_id",
                        resume_id
                    )
                    
                    self.assertTrue(success)
                    self.assertIn("deleted successfully", message)
                    self.assertEqual(len(mock_user.personal_data['resumes']), 0)
                    mock_remove.assert_called_once()
        finally:
            # Clean up
            if os.path.exists(resume_path):
                os.unlink(resume_path)
    
    def test_cover_letter_operations(self):
        """Test cover letter CRUD operations."""
        # Mock User
        mock_user = MagicMock(spec=User)
        mock_user.id = "test_user_id"
        mock_user.personal_data = {'cover_letters': []}
        
        # Create a temporary cover letter file
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as temp_file:
            temp_file.write(b"Test cover letter content")
            cover_letter_path = temp_file.name
        
        try:
            # Mock get_user_by_id
            with patch.object(self.profile_service, 'get_user_by_id', return_value=mock_user):
                # Test add cover letter
                success, cover_letter_id, message = self.profile_service.add_cover_letter(
                    "test_user_id",
                    cover_letter_path,
                    "My Cover Letter",
                    "General cover letter"
                )
                
                self.assertTrue(success)
                self.assertIsNotNone(cover_letter_id)
                self.assertIn("added successfully", message)
                
                # Verify cover letter was added to user data
                self.assertEqual(len(mock_user.personal_data['cover_letters']), 1)
                self.assertEqual(mock_user.personal_data['cover_letters'][0]['name'], "My Cover Letter")
                self.assertEqual(mock_user.personal_data['cover_letters'][0]['description'], "General cover letter")
                
                # Test update cover letter
                mock_user.personal_data['cover_letters'][0]['id'] = cover_letter_id
                success, message = self.profile_service.update_cover_letter(
                    "test_user_id",
                    cover_letter_id,
                    "Updated Cover Letter",
                    "Updated description"
                )
                
                self.assertTrue(success)
                self.assertIn("updated successfully", message)
                self.assertEqual(mock_user.personal_data['cover_letters'][0]['name'], "Updated Cover Letter")
                
                # Test get cover letter file path
                with patch('os.path.exists', return_value=True):
                    success, path, message = self.profile_service.get_cover_letter_file_path(
                        "test_user_id",
                        cover_letter_id
                    )
                    
                    self.assertTrue(success)
                    self.assertIsNotNone(path)
                
                # Test delete cover letter
                with patch('os.path.exists', return_value=True), patch('os.remove') as mock_remove:
                    success, message = self.profile_service.delete_cover_letter(
                        "test_user_id",
                        cover_letter_id
                    )
                    
                    self.assertTrue(success)
                    self.assertIn("deleted successfully", message)
                    self.assertEqual(len(mock_user.personal_data['cover_letters']), 0)
                    mock_remove.assert_called_once()
        finally:
            # Clean up
            if os.path.exists(cover_letter_path):
                os.unlink(cover_letter_path)
    
    def test_sanitize_personal_info(self):
        """Test sanitization of personal information."""
        # Test with valid data
        raw_data = {
            'first_name': ' John ',
            'last_name': ' Doe ',
            'phone': '123-456-7890',
            'address': '123 Main St',
            'unexpected_field': 'should be removed'
        }
        
        sanitized = self.profile_service._sanitize_personal_info(raw_data)
        
        self.assertEqual(sanitized['first_name'], 'John')
        self.assertEqual(sanitized['last_name'], 'Doe')
        self.assertNotIn('unexpected_field', sanitized)
    
    def test_sanitize_preferences(self):
        """Test sanitization of job preferences."""
        # Test with valid data
        raw_prefs = {
            'job_titles': [' Developer ', 'Engineer'],
            'locations': ['New York', ' Remote '],
            'remote_only': True,
            'salary_min': '80000',
            'salary_max': 120000,
            'job_types': ['Full-time'],
            'unexpected_field': 'should be removed'
        }
        
        sanitized = self.profile_service._sanitize_preferences(raw_prefs)
        
        self.assertEqual(sanitized['job_titles'][0], 'Developer')
        self.assertEqual(sanitized['locations'][1], 'Remote')
        self.assertTrue(sanitized['remote_only'])
        self.assertEqual(sanitized['salary_min'], 80000.0)
        self.assertEqual(sanitized['salary_max'], 120000.0)
        self.assertNotIn('unexpected_field', sanitized)
        
        # Test with invalid data
        invalid_prefs = {
            'job_titles': 'Not a list',
            'salary_min': 'not a number',
            'excluded_keywords': 'not a list'
        }
        
        sanitized = self.profile_service._sanitize_preferences(invalid_prefs)
        
        self.assertEqual(sanitized['job_titles'], [])
        self.assertNotIn('salary_min', sanitized)
        self.assertEqual(sanitized['excluded_keywords'], [])


if __name__ == '__main__':
    unittest.main()