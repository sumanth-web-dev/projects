"""
Integration tests for job-related API endpoints.
"""
import json
import unittest
import uuid
from datetime import datetime, timedelta


class JobAPITestCase(unittest.TestCase):
    """Test case for job-related API endpoints."""
    
    def setUp(self):
        """Set up test environment."""
        # Import here to avoid circular imports
        from app import create_app
        from models.database import db
        from models.job import Job
        from services.auth_service import auth_service
        
        self.db = db
        self.Job = Job
        self.auth_service = auth_service
        
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
    
    def test_get_jobs(self):
        """Test GET /api/jobs endpoint."""
        response = self.client.get('/api/jobs')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['jobs']), 3)
    
    def test_get_jobs_with_filters(self):
        """Test GET /api/jobs with query parameters."""
        # Test filtering by source
        response = self.client.get('/api/jobs?sources=linkedin')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['jobs']), 2)
        
        # Test filtering by job type
        response = self.client.get('/api/jobs?job_types=contract')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['jobs']), 1)
        self.assertEqual(data['jobs'][0]['job_type'], 'contract')
    
    def test_get_job_details(self):
        """Test GET /api/jobs/<job_id> endpoint."""
        job_id = self.job_ids[0]
        response = self.client.get(f'/api/jobs/{job_id}')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['job']['id'], job_id)
        self.assertTrue('description' in data['job'])
        self.assertTrue('similar_jobs' in data)
    
    def test_create_job(self):
        """Test POST /api/jobs endpoint."""
        new_job = {
            'title': 'DevOps Engineer',
            'company': 'Cloud Corp',
            'location': 'Chicago, IL',
            'description': 'DevOps role with focus on AWS.',
            'source_website': 'linkedin',
            'source_url': 'https://linkedin.com/jobs/4',
            'job_type': 'full-time',
            'experience_level': 'mid',
            'remote_option': 'hybrid'
        }
        
        response = self.client.post(
            '/api/jobs',
            json=new_job,
            headers={'X-CSRF-Token': self.csrf_token}
        )
        self.assertEqual(response.status_code, 201)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['job']['title'], 'DevOps Engineer')
    
    def test_update_job(self):
        """Test PUT /api/jobs/<job_id> endpoint."""
        job_id = self.job_ids[0]
        update_data = {
            'title': 'Senior Software Engineer',
            'salary_min': 120000,
            'salary_max': 170000
        }
        
        response = self.client.put(
            f'/api/jobs/{job_id}',
            json=update_data,
            headers={'X-CSRF-Token': self.csrf_token}
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['job']['title'], 'Senior Software Engineer')
        self.assertEqual(data['job']['salary_range']['min'], 120000)
    
    def test_delete_job(self):
        """Test DELETE /api/jobs/<job_id> endpoint."""
        from services.job_search_service import job_search_service
        
        job_id = self.job_ids[2]
        
        response = self.client.delete(
            f'/api/jobs/{job_id}',
            headers={'X-CSRF-Token': self.csrf_token}
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        
        # Verify job is marked inactive
        job = job_search_service.get_job_by_id(job_id)
        self.assertFalse(job.is_active)
    
    def test_filter_jobs(self):
        """Test POST /api/jobs/filter endpoint."""
        request_data = {
            'job_ids': self.job_ids,
            'preferences': {
                'remote_options': ['remote', 'hybrid'],
                'experience_levels': ['mid', 'senior']
            }
        }
        
        response = self.client.post('/api/jobs/filter', json=request_data)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['jobs']), 2)  # Should exclude the onsite entry-level job
    
    def test_sort_jobs(self):
        """Test POST /api/jobs/sort endpoint."""
        request_data = {
            'job_ids': self.job_ids,
            'sort_by': 'salary',
            'sort_order': 'desc'
        }
        
        response = self.client.post('/api/jobs/sort', json=request_data)
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['jobs']), 3)
        
        # Verify sorting order (highest salary first)
        self.assertEqual(data['jobs'][0]['salary_range']['max'], 180000)
    
    def test_trigger_search(self):
        """Test POST /api/search endpoint."""
        search_criteria = {
            'keywords': ['developer', 'engineer'],
            'locations': ['San Francisco', 'Remote'],
            'job_types': ['full-time'],
            'sources': ['linkedin', 'indeed']
        }
        
        response = self.client.post(
            '/api/search',
            json=search_criteria,
            headers={'X-CSRF-Token': self.csrf_token}
        )
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue('search_id' in data)
        
        # Store search ID for next test
        self.search_id = data['search_id']
    
    def test_get_search_status(self):
        """Test GET /api/search/<search_id> endpoint."""
        # First trigger a search
        self.test_trigger_search()
        
        # Then check its status
        response = self.client.get(f'/api/search/{self.search_id}')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['search']['search_id'], self.search_id)
    
    def test_get_search_results(self):
        """Test GET /api/search/<search_id>/results endpoint."""
        # First trigger a search
        self.test_trigger_search()
        
        # Then get results
        response = self.client.get(f'/api/search/{self.search_id}/results')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue('jobs' in data)
    
    def test_get_job_stats(self):
        """Test GET /api/jobs/stats endpoint."""
        response = self.client.get('/api/jobs/stats')
        self.assertEqual(response.status_code, 200)
        
        data = json.loads(response.data)
        self.assertEqual(data['status'], 'success')
        self.assertTrue('stats' in data)
        self.assertEqual(data['stats']['total_jobs'], 3)
        self.assertEqual(data['stats']['by_source']['linkedin'], 2)


if __name__ == '__main__':
    unittest.main()