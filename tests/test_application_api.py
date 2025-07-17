"""
Integration tests for application management API endpoints.
"""
import json
import uuid
import unittest
from datetime import datetime, timedelta


class ApplicationAPITestCase(unittest.TestCase):
    """Test case for application management API endpoints."""
    
    def setUp(self):
        """Set up test environment."""
        # Import here to avoid circular imports
        from app import create_app
        from models.database import db
        from models.job import Job
        from models.application import Application
        from services.auth_service import auth_service
        from services.application_service import application_service
        
        self.db = db
        self.Job = Job
        self.Application = Application
        self.auth_service = auth_service
        self.application_service = application_service
        
        # Create test app with testing config
        self.app = create_app('TestingConfig')
        self.client = self.app.test_client()
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create database tables
        self.db.create_all()
        
        # Create test user
        success, user_id, _ = self.auth_service.create_user(
            'test@example.com', 
            'password123', 
            {'first_name': 'Test', 'last_name': 'User'}
        )
        self.user_id = user_id
        
        # Create test jobs
        self._create_test_jobs()
        
        # Create test applications
        self._create_test_applications()
        
        # Login to get session
        with self.client as c:
            response = c.post('/api/auth/login', json={
                'email': 'test@example.com',
                'password': 'password123'
            })
            data = json.loads(response.data)
            self.csrf_token = data.get('csrf_token')
    
    def tearDown(self):
        """Clean up after tests."""
        self.db.session.remove()
        self.db.drop_all()
        self.app_context.pop()
    
    def _create_test_jobs(self):
        """Create test job data."""
        # Job 1: Software Engineer at Tech Corp
        job1 = self.Job(
            id=str(uuid.uuid4()),
            title='Software Engineer',
            company='Tech Corp',
            location='San Francisco, CA',
            description='Python developer role with focus on backend systems.',
            source_website='linkedin',
            source_url='https://linkedin.com/jobs/1',
            job_type='full-time',
            experience_level='mid',
            remote_option='hybrid',
            discovered_at=datetime.utcnow() - timedelta(days=2)
        )
        job1.set_salary_range(100000, 150000, 'USD')
        
        # Job 2: Senior Developer at Code Inc
        job2 = self.Job(
            id=str(uuid.uuid4()),
            title='Senior Developer',
            company='Code Inc',
            location='Remote',
            description='Senior role working on cloud infrastructure.',
            source_website='indeed',
            source_url='https://indeed.com/jobs/2',
            job_type='full-time',
            experience_level='senior',
            remote_option='remote',
            discovered_at=datetime.utcnow() - timedelta(days=1)
        )
        job2.set_salary_range(130000, 180000, 'USD')
        
        # Job 3: Frontend Developer at Design Co
        job3 = self.Job(
            id=str(uuid.uuid4()),
            title='Frontend Developer',
            company='Design Co',
            location='New York, NY',
            description='Frontend role focusing on React and modern JS.',
            source_website='linkedin',
            source_url='https://linkedin.com/jobs/3',
            job_type='contract',
            experience_level='entry',
            remote_option='onsite',
            discovered_at=datetime.utcnow() - timedelta(days=3)
        )
        job3.set_salary_range(80000, 110000, 'USD')
        
        # Add jobs to database
        self.db.session.add_all([job1, job2, job3])
        self.db.session.commit()
        
        # Store job IDs for tests
        self.job_ids = [job1.id, job2.id, job3.id]
    
    def _create_test_applications(self):
        """Create test application data."""
        # Import ApplicationStatus here to avoid circular imports
        from models.application import ApplicationStatus
        
        # Application 1: Pending application
        app1_id = str(uuid.uuid4())
        app1 = self.Application(
            id=app1_id,
            user_id=self.user_id,
            job_id=self.job_ids[0],
            status=ApplicationStatus.PENDING,
            application_method='automated'
        )
        app1.materials_used = {
            'resume_version': 'resume1',
            'cover_letter_version': 'cover1'
        }
        
        # Application 2: Submitted application
        app2_id = str(uuid.uuid4())
        app2 = self.Application(
            id=app2_id,
            user_id=self.user_id,
            job_id=self.job_ids[1],
            status=ApplicationStatus.SUBMITTED,
            application_method='manual',
            submitted_at=datetime.utcnow() - timedelta(days=5)
        )
        app2.materials_used = {
            'resume_version': 'resume2',
            'cover_letter_version': 'cover2'
        }
        app2.custom_responses = {
            'Why do you want to work here?': 'I am passionate about cloud infrastructure.',
            'Years of experience?': '5+ years'
        }
        app2.confirmation_details = {
            'confirmation_id': 'conf123',
            'confirmation_url': 'https://example.com/confirm/123'
        }
        
        # Application 3: Failed application
        app3_id = str(uuid.uuid4())
        app3 = self.Application(
            id=app3_id,
            user_id=self.user_id,
            job_id=self.job_ids[2],
            status=ApplicationStatus.FAILED,
            application_method='automated',
            error_log='Connection timeout during form submission'
        )
        
        # Add applications to database
        self.db.session.add_all([app1, app2, app3])
        self.db.session.commit()
        
        # Store application IDs for tests
        self.application_ids = [app1_id, app2_id, app3_id]
    
    def test_get_applications(self):
        """Test GET /api/applications endpoint."""
        response = self.client.get('/api/applications')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['applications']), 3)
    
    def test_get_applications_with_filters(self):
        """Test GET /api/applications with query parameters."""
        # Test filtering by status
        response = self.client.get('/api/applications?status=submitted')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['applications']), 1)
        self.assertEqual(data['applications'][0]['status'], 'submitted')
        
        # Test filtering by active_only
        response = self.client.get('/api/applications?active_only=false')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['applications']), 3)
    
    def test_get_application_details(self):
        """Test GET /api/applications/<application_id> endpoint."""
        application_id = self.application_ids[0]
        response = self.client.get(f'/api/applications/{application_id}')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['application']['id'], application_id)
        self.assertTrue('materials_used' in data['application'])
    
    def test_create_application(self):
        """Test POST /api/applications endpoint."""
        new_application = {
            'job_id': self.job_ids[0],
            'materials': {
                'resume_version': 'resume3',
                'cover_letter_version': 'cover3'
            },
            'application_method': 'manual'
        }
        
        response = self.client.post(
            '/api/applications',
            json=new_application,
            headers={'X-CSRF-Token': self.csrf_token}
        )
        self.assertEqual(response.status_code, 201)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue('application_id' in data)
    
    def test_update_application(self):
        """Test PUT /api/applications/<application_id> endpoint."""
        application_id = self.application_ids[0]
        update_data = {
            'status': 'submitted',
            'materials': {
                'resume_version': 'resume_updated',
                'cover_letter_version': 'cover_updated'
            },
            'custom_responses': {
                'Why are you interested?': 'I am passionate about technology.'
            }
        }
        
        response = self.client.put(
            f'/api/applications/{application_id}',
            json=update_data,
            headers={'X-CSRF-Token': self.csrf_token}
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['application']['status'], 'submitted')
    
    def test_delete_application(self):
        """Test DELETE /api/applications/<application_id> endpoint."""
        application_id = self.application_ids[2]
        
        response = self.client.delete(
            f'/api/applications/{application_id}',
            headers={'X-CSRF-Token': self.csrf_token}
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        # Verify application is marked inactive
        application = self.application_service.get_application_by_id(application_id)
        self.assertFalse(application.is_active)
    
    def test_retry_application(self):
        """Test POST /api/applications/<application_id>/retry endpoint."""
        # Import ApplicationStatus here to avoid circular imports
        from models.application import ApplicationStatus
        
        application_id = self.application_ids[2]  # Failed application
        
        response = self.client.post(
            f'/api/applications/{application_id}/retry',
            headers={'X-CSRF-Token': self.csrf_token}
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        # Verify application status is reset to pending
        application = self.application_service.get_application_by_id(application_id)
        self.assertEqual(application.status, ApplicationStatus.PENDING)
    
    def test_get_application_stats(self):
        """Test GET /api/applications/stats endpoint."""
        response = self.client.get('/api/applications/stats')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue('stats' in data)
        self.assertEqual(data['stats']['total_applications'], 3)
    
    def test_get_applications_needing_followup(self):
        """Test GET /api/applications/followup endpoint."""
        response = self.client.get('/api/applications/followup?days_threshold=3')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue('applications' in data)
        # Should include the submitted application that's 5 days old
        self.assertEqual(len(data['applications']), 1)
    
    def test_get_application_status(self):
        """Test GET /api/applications/<application_id>/status endpoint."""
        application_id = self.application_ids[0]
        response = self.client.get(f'/api/applications/{application_id}/status')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue('application_status' in data)
        self.assertEqual(data['application_status']['id'], application_id)
        self.assertEqual(data['application_status']['status'], 'pending')
    
    def test_get_automation_status(self):
        """Test GET /api/automation/status endpoint."""
        # First create an API key for authentication
        with self.client as c:
            response = c.post(
                '/api/auth/api-key',
                json={'description': 'Test API Key'},
                headers={'X-CSRF-Token': self.csrf_token}
            )
            api_key_data = json.loads(response.data)
            api_key = api_key_data.get('api_key')
        
        # Test automation status endpoint
        response = self.client.get(
            '/api/automation/status',
            headers={'Authorization': f'Bearer {api_key}'}
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue('automation_status' in data)
    
    def test_start_automation(self):
        """Test POST /api/automation/start endpoint."""
        # First create an API key for authentication
        with self.client as c:
            response = c.post(
                '/api/auth/api-key',
                json={'description': 'Test API Key'},
                headers={'X-CSRF-Token': self.csrf_token}
            )
            api_key_data = json.loads(response.data)
            api_key = api_key_data.get('api_key')
        
        # Test start automation endpoint
        automation_data = {
            'job_ids': [self.job_ids[0]],
            'application_ids': [self.application_ids[0]]
        }
        
        response = self.client.post(
            '/api/automation/start',
            json=automation_data,
            headers={'Authorization': f'Bearer {api_key}'}
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue('automation_id' in data)
    
    def test_stop_automation(self):
        """Test POST /api/automation/stop endpoint."""
        # First create an API key for authentication
        with self.client as c:
            response = c.post(
                '/api/auth/api-key',
                json={'description': 'Test API Key'},
                headers={'X-CSRF-Token': self.csrf_token}
            )
            api_key_data = json.loads(response.data)
            api_key = api_key_data.get('api_key')
        
        # First start automation to get an ID
        automation_data = {
            'job_ids': [self.job_ids[0]]
        }
        
        start_response = self.client.post(
            '/api/automation/start',
            json=automation_data,
            headers={'Authorization': f'Bearer {api_key}'}
        )
        start_data = json.loads(start_response.data)
        automation_id = start_data.get('automation_id')
        
        # Test stop automation endpoint
        stop_data = {
            'automation_id': automation_id
        }
        
        response = self.client.post(
            '/api/automation/stop',
            json=stop_data,
            headers={'Authorization': f'Bearer {api_key}'}
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['automation_id'], automation_id)
    
    def test_get_automation_logs(self):
        """Test GET /api/automation/logs endpoint."""
        # First create an API key for authentication
        with self.client as c:
            response = c.post(
                '/api/auth/api-key',
                json={'description': 'Test API Key'},
                headers={'X-CSRF-Token': self.csrf_token}
            )
            api_key_data = json.loads(response.data)
            api_key = api_key_data.get('api_key')
        
        # Test get automation logs endpoint
        response = self.client.get(
            '/api/automation/logs',
            headers={'Authorization': f'Bearer {api_key}'}
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue('logs' in data)


if __name__ == '__main__':
    unittest.main()