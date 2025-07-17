"""
End-to-end tests for the complete job application workflow.
"""
import unittest
import os
import time
import uuid
from datetime import datetime
from unittest.mock import patch, MagicMock

from app import create_app
from models.database import db
from models.user import User
from models.job import Job
from models.application import Application, ApplicationStatus
from services.auth_service import auth_service
from services.profile_service import profile_service
from services.job_search_service import job_search_service
from services.application_service import application_service
from automation.playwright_engine.browser_manager import BrowserManager
from automation.adapters.linkedin_adapter import LinkedInAdapter
from automation.adapters.indeed_adapter import IndeedAdapter


class EndToEndJobApplicationTest(unittest.TestCase):
    """End-to-end test for the complete job application workflow."""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment once for all tests."""
        # Create test app with testing config
        cls.app = create_app('TestingConfig')
        cls.app_context = cls.app.app_context()
        cls.app_context.push()
        
        # Create database tables
        db.create_all()
        
        # Create test user with profile
        cls._create_test_user_and_profile()
        
        # Set up browser manager
        cls.browser_manager = BrowserManager(cls.app)
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
        # Close all browser contexts
        cls.browser_manager.close_all()
        
        # Clean up database
        db.session.remove()
        db.drop_all()
        cls.app_context.pop()
    
    def setUp(self):
        """Set up before each test."""
        # Create test client
        self.client = self.app.test_client()
        
        # Login to get session
        with self.client as c:
            response = c.post('/api/auth/login', json={
                'email': 'test@example.com',
                'password': 'password123'
            })
            self.csrf_token = response.json.get('csrf_token')
    
    @classmethod
    def _create_test_user_and_profile(cls):
        """Create a test user with a complete profile."""
        # Create user
        success, user_id, _ = auth_service.create_user(
            'test@example.com', 
            'password123', 
            {'first_name': 'Test', 'last_name': 'User'}
        )
        cls.user_id = user_id
        
        # Create profile
        profile_data = {
            'personal_data': {
                'first_name': 'John',
                'last_name': 'Doe',
                'phone': '555-123-4567',
                'address': '123 Main St',
                'city': 'Anytown',
                'state': 'CA',
                'zip_code': '12345',
                'country': 'USA',
                'skills': ['Python', 'JavaScript', 'React', 'SQL', 'Git'],
                'experience': [
                    {
                        'company': 'Previous Company',
                        'position': 'Software Developer',
                        'start_date': '2020-01-01',
                        'end_date': '2023-01-01',
                        'description': 'Developed web applications using Python and JavaScript'
                    }
                ],
                'education': [
                    {
                        'degree': "Bachelor's",
                        'field': 'Computer Science',
                        'institution': 'University of Technology',
                        'graduation_date': '2019-05-15'
                    }
                ]
            },
            'preferences': {
                'job_types': ['full-time', 'contract'],
                'remote_options': ['remote', 'hybrid'],
                'experience_levels': ['entry', 'mid'],
                'locations': ['San Francisco, CA', 'Remote'],
                'salary_min': 80000,
                'industries': ['Technology', 'Finance']
            }
        }
        
        # Create resume and cover letter paths
        test_resume_path = os.path.join(cls.app.config['UPLOAD_FOLDER'], f"{user_id}_resume.pdf")
        test_cover_letter_path = os.path.join(cls.app.config['UPLOAD_FOLDER'], f"{user_id}_cover_letter.pdf")
        
        # Create dummy files
        os.makedirs(os.path.dirname(test_resume_path), exist_ok=True)
        with open(test_resume_path, 'w') as f:
            f.write("Test resume content")
        with open(test_cover_letter_path, 'w') as f:
            f.write("Test cover letter content")
        
        # Add resume and cover letter to profile
        profile_data['resumes'] = [
            {
                'name': 'Software Developer Resume',
                'file_path': test_resume_path,
                'is_default': True
            }
        ]
        profile_data['cover_letters'] = [
            {
                'name': 'General Cover Letter',
                'file_path': test_cover_letter_path,
                'is_default': True
            }
        ]
        
        # Save profile
        profile_service.update_profile(user_id, profile_data)
        
        # Add website credentials
        credentials = {
            'linkedin': {
                'username': 'test@example.com',
                'password': 'linkedin_password'
            },
            'indeed': {
                'username': 'test@example.com',
                'password': 'indeed_password'
            }
        }
        profile_service.update_credentials(user_id, credentials)
    
    def _create_test_job(self):
        """Create a test job for application."""
        job = Job(
            id=str(uuid.uuid4()),
            title='Software Engineer',
            company='Test Company',
            location='San Francisco, CA',
            description='We are looking for a Software Engineer with Python and JavaScript experience.',
            source_website='linkedin',
            source_url='https://linkedin.com/jobs/test',
            job_type='full-time',
            experience_level='mid',
            remote_option='hybrid',
            discovered_at=datetime.utcnow()
        )
        job.set_salary_range(100000, 150000, 'USD')
        db.session.add(job)
        db.session.commit()
        return job
    
    @patch('automation.adapters.linkedin_adapter.LinkedInAdapter.login')
    @patch('automation.adapters.linkedin_adapter.LinkedInAdapter.search_jobs')
    def test_e2e_job_search(self, mock_search_jobs, mock_login):
        """Test end-to-end job search workflow."""
        # Mock login
        mock_login.return_value = True
        
        # Mock search results
        mock_search_jobs.return_value = [
            {
                'title': 'Software Engineer',
                'company': 'Tech Corp',
                'location': 'San Francisco, CA',
                'description': 'Python developer role with focus on backend systems.',
                'source_url': 'https://linkedin.com/jobs/1',
                'job_type': 'full-time',
                'experience_level': 'mid',
                'remote_option': 'hybrid'
            },
            {
                'title': 'Frontend Developer',
                'company': 'Web Solutions',
                'location': 'Remote',
                'description': 'Frontend role focusing on React and modern JS.',
                'source_url': 'https://linkedin.com/jobs/2',
                'job_type': 'full-time',
                'experience_level': 'entry',
                'remote_option': 'remote'
            }
        ]
        
        # Trigger job search
        search_criteria = {
            'keywords': ['developer', 'engineer'],
            'locations': ['San Francisco', 'Remote'],
            'job_types': ['full-time'],
            'sources': ['linkedin']
        }
        
        response = self.client.post(
            '/api/search',
            json=search_criteria,
            headers={'X-CSRF-Token': self.csrf_token}
        )
        self.assertEqual(response.status_code, 200)
        
        search_id = response.json.get('search_id')
        self.assertIsNotNone(search_id)
        
        # Check search results
        response = self.client.get(f'/api/search/{search_id}/results')
        self.assertEqual(response.status_code, 200)
        
        data = response.json
        self.assertEqual(data['status'], 'success')
        self.assertTrue('jobs' in data)
        
        # Verify LinkedIn adapter was called correctly
        mock_login.assert_called_once()
        mock_search_jobs.assert_called_once()
    
    @patch('automation.adapters.linkedin_adapter.LinkedInAdapter.login')
    @patch('automation.adapters.linkedin_adapter.LinkedInAdapter.apply_to_job')
    def test_e2e_job_application(self, mock_apply_to_job, mock_login):
        """Test end-to-end job application workflow."""
        # Mock login
        mock_login.return_value = True
        
        # Mock application result
        mock_apply_to_job.return_value = {
            'success': True,
            'confirmation_id': 'APP123456',
            'application_date': datetime.utcnow().isoformat(),
            'status': 'submitted'
        }
        
        # Create test job
        job = self._create_test_job()
        
        # Submit application
        response = self.client.post(
            f'/api/jobs/{job.id}/apply',
            json={},
            headers={'X-CSRF-Token': self.csrf_token}
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json
        self.assertEqual(data['status'], 'success')
        self.assertTrue('application_id' in data)
        
        application_id = data['application_id']
        
        # Check application status
        response = self.client.get(f'/api/applications/{application_id}')
        self.assertEqual(response.status_code, 200)
        
        data = response.json
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['application']['status'], ApplicationStatus.SUBMITTED.value)
        
        # Verify LinkedIn adapter was called correctly
        mock_login.assert_called_once()
        mock_apply_to_job.assert_called_once()
    
    @patch('automation.form_filler.FormFiller.detect_form_fields')
    @patch('automation.form_filler.FormFiller.fill_form')
    @patch('automation.form_filler.FormFiller.upload_file')
    @patch('automation.form_response_generator.FormResponseGenerator.generate_response')
    def test_e2e_form_filling(self, mock_generate_response, mock_upload_file, mock_fill_form, mock_detect_form_fields):
        """Test end-to-end form filling workflow."""
        from automation.form_response_generator import FormField
        
        # Mock form fields detection
        mock_detect_form_fields.return_value = [
            FormField("first_name", FormField.TEXT, "First Name", required=True),
            FormField("last_name", FormField.TEXT, "Last Name", required=True),
            FormField("email", FormField.TEXT, "Email Address", required=True),
            FormField("resume", FormField.FILE, "Resume", required=True),
            FormField("cover_letter", FormField.FILE, "Cover Letter"),
            FormField("experience", FormField.SELECT, "Years of Experience", options=["0-1", "1-3", "3-5", "5+"]),
            FormField("why_join", FormField.TEXTAREA, "Why do you want to join our company?", required=True)
        ]
        
        # Mock form filling
        mock_fill_form.return_value = True
        
        # Mock file upload
        mock_upload_file.return_value = True
        
        # Mock response generation
        mock_generate_response.return_value = "I am excited about the opportunity to join your company because..."
        
        # Create test job
        job = self._create_test_job()
        
        # Create application service instance
        with patch('services.application_service.ApplicationService.get_adapter_for_job') as mock_get_adapter:
            # Mock adapter
            mock_adapter = MagicMock()
            mock_adapter.navigate.return_value = True
            mock_adapter.get_page.return_value = MagicMock()
            mock_get_adapter.return_value = mock_adapter
            
            # Submit application
            result = application_service.submit_application(job.id, self.user_id)
            
            # Verify result
            self.assertTrue(result['success'])
            
            # Verify form detection and filling were called
            mock_detect_form_fields.assert_called_once()
            mock_fill_form.assert_called_once()
            mock_upload_file.assert_called()
            mock_generate_response.assert_called()
    
    def test_e2e_application_tracking(self):
        """Test end-to-end application tracking workflow."""
        # Create test job
        job = self._create_test_job()
        
        # Create test application
        application = Application(
            id=str(uuid.uuid4()),
            job_id=job.id,
            user_id=self.user_id,
            status=ApplicationStatus.SUBMITTED.value,
            submitted_at=datetime.utcnow(),
            materials_used={"resume_id": "default", "cover_letter_id": "default"},
            custom_responses={"why_join": "I am excited about the opportunity..."},
            confirmation_details={"confirmation_id": "APP123456"}
        )
        db.session.add(application)
        db.session.commit()
        
        # Get application from dashboard
        response = self.client.get('/api/applications')
        self.assertEqual(response.status_code, 200)
        
        data = response.json
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['applications']), 1)
        self.assertEqual(data['applications'][0]['job_id'], job.id)
        
        # Get application details
        response = self.client.get(f'/api/applications/{application.id}')
        self.assertEqual(response.status_code, 200)
        
        data = response.json
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['application']['id'], application.id)
        self.assertEqual(data['application']['status'], ApplicationStatus.SUBMITTED.value)
        
        # Update application status
        response = self.client.put(
            f'/api/applications/{application.id}',
            json={"status": ApplicationStatus.INTERVIEW.value},
            headers={'X-CSRF-Token': self.csrf_token}
        )
        self.assertEqual(response.status_code, 200)
        
        # Verify status was updated
        response = self.client.get(f'/api/applications/{application.id}')
        self.assertEqual(response.status_code, 200)
        
        data = response.json
        self.assertEqual(data['application']['status'], ApplicationStatus.INTERVIEW.value)
    
    def test_e2e_error_recovery(self):
        """Test end-to-end error recovery workflow."""
        # Create test job
        job = self._create_test_job()
        
        # Create failed application
        application = Application(
            id=str(uuid.uuid4()),
            job_id=job.id,
            user_id=self.user_id,
            status=ApplicationStatus.FAILED.value,
            error_log="Network error occurred during submission"
        )
        db.session.add(application)
        db.session.commit()
        
        # Mock application service retry
        with patch('services.application_service.ApplicationService.retry_failed_application') as mock_retry:
            mock_retry.return_value = {
                'success': True,
                'application_id': application.id,
                'status': ApplicationStatus.SUBMITTED.value
            }
            
            # Retry application
            response = self.client.post(
                f'/api/applications/{application.id}/retry',
                headers={'X-CSRF-Token': self.csrf_token}
            )
            self.assertEqual(response.status_code, 200)
            
            data = response.json
            self.assertEqual(data['status'], 'success')
            self.assertEqual(data['application']['status'], ApplicationStatus.SUBMITTED.value)
            
            # Verify retry was called
            mock_retry.assert_called_once_with(application.id)
    
    def test_e2e_performance(self):
        """Test end-to-end performance metrics."""
        # Create multiple test jobs
        jobs = []
        for i in range(5):
            job = Job(
                id=str(uuid.uuid4()),
                title=f'Software Engineer {i}',
                company=f'Test Company {i}',
                location='San Francisco, CA',
                description=f'Job description {i}',
                source_website='linkedin' if i % 2 == 0 else 'indeed',
                source_url=f'https://example.com/jobs/{i}',
                job_type='full-time',
                experience_level='mid',
                remote_option='hybrid',
                discovered_at=datetime.utcnow()
            )
            db.session.add(job)
            jobs.append(job)
        
        # Create multiple applications
        for i, job in enumerate(jobs):
            status = ApplicationStatus.SUBMITTED.value if i % 3 == 0 else \
                    ApplicationStatus.INTERVIEW.value if i % 3 == 1 else \
                    ApplicationStatus.REJECTED.value
            
            application = Application(
                id=str(uuid.uuid4()),
                job_id=job.id,
                user_id=self.user_id,
                status=status,
                submitted_at=datetime.utcnow()
            )
            db.session.add(application)
        
        db.session.commit()
        
        # Measure time to load applications dashboard
        start_time = time.time()
        response = self.client.get('/api/applications')
        end_time = time.time()
        
        self.assertEqual(response.status_code, 200)
        
        # Verify response time is acceptable (under 500ms)
        response_time = (end_time - start_time) * 1000  # Convert to milliseconds
        self.assertLess(response_time, 500)
        
        # Verify all applications were returned
        data = response.json
        self.assertEqual(len(data['applications']), 5)
        
        # Get application statistics
        response = self.client.get('/api/applications/stats')
        self.assertEqual(response.status_code, 200)
        
        data = response.json
        self.assertEqual(data['stats']['total'], 5)
        self.assertEqual(data['stats']['by_status'][ApplicationStatus.SUBMITTED.value], 2)
        self.assertEqual(data['stats']['by_status'][ApplicationStatus.INTERVIEW.value], 2)
        self.assertEqual(data['stats']['by_status'][ApplicationStatus.REJECTED.value], 1)


if __name__ == '__main__':
    unittest.main()