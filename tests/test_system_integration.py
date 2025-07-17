"""
System integration tests for the job application agent.
"""
import unittest
import json
import uuid
import os
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
from services.ai_service import ai_service
from automation.form_filler import FormFiller
from automation.form_response_generator import FormResponseGenerator


class SystemIntegrationTest(unittest.TestCase):
    """System integration tests for the job application agent."""
    
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
    
    @classmethod
    def tearDownClass(cls):
        """Clean up after all tests."""
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
    
    def test_api_frontend_integration(self):
        """Test integration between API and frontend."""
        # Create test job
        job = self._create_test_job()
        
        # Test that job appears in API response
        response = self.client.get('/api/jobs')
        self.assertEqual(response.status_code, 200)
        
        data = response.json
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['jobs']), 1)
        self.assertEqual(data['jobs'][0]['id'], job.id)
        
        # Test job details endpoint
        response = self.client.get(f'/api/jobs/{job.id}')
        self.assertEqual(response.status_code, 200)
        
        data = response.json
        self.assertEqual(data['status'], 'success')
        self.assertEqual(data['job']['id'], job.id)
        
        # Test job filtering endpoint
        response = self.client.post(
            '/api/jobs/filter',
            json={
                'job_ids': [job.id],
                'preferences': {
                    'remote_options': ['remote', 'hybrid'],
                    'experience_levels': ['mid']
                }
            }
        )
        self.assertEqual(response.status_code, 200)
        
        data = response.json
        self.assertEqual(data['status'], 'success')
        self.assertEqual(len(data['jobs']), 1)
    
    def test_database_operations_concurrent_access(self):
        """Test database operations under concurrent access."""
        # Create multiple test jobs
        jobs = []
        for i in range(5):
            job = Job(
                id=str(uuid.uuid4()),
                title=f'Software Engineer {i}',
                company=f'Test Company {i}',
                location='San Francisco, CA',
                description=f'Job description {i}',
                source_website='linkedin',
                source_url=f'https://example.com/jobs/{i}',
                job_type='full-time',
                experience_level='mid',
                remote_option='hybrid',
                discovered_at=datetime.utcnow()
            )
            db.session.add(job)
            jobs.append(job)
        
        db.session.commit()
        
        # Simulate concurrent access by making multiple requests
        import threading
        
        def make_request(job_id):
            client = self.app.test_client()
            # Login
            response = client.post('/api/auth/login', json={
                'email': 'test@example.com',
                'password': 'password123'
            })
            csrf_token = response.json.get('csrf_token')
            
            # Get job details
            response = client.get(f'/api/jobs/{job_id}')
            self.assertEqual(response.status_code, 200)
            
            # Update job (simulating concurrent update)
            response = client.put(
                f'/api/jobs/{job_id}',
                json={'title': f'Updated Job {job_id}'},
                headers={'X-CSRF-Token': csrf_token}
            )
            self.assertEqual(response.status_code, 200)
        
        # Create threads for concurrent access
        threads = []
        for job in jobs:
            thread = threading.Thread(target=make_request, args=(job.id,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all jobs were updated correctly
        for job in jobs:
            db_job = Job.query.get(job.id)
            self.assertTrue(db_job.title.startswith('Updated Job'))
    
    def test_ai_service_integration(self):
        """Test AI service integration with real and mocked responses."""
        # Create test job
        job = self._create_test_job()
        
        # Test AI service with mocked response
        with patch('services.ai_service.AIService._generate_ai_response') as mock_generate:
            mock_generate.return_value = "I am excited about the opportunity to join your company because of your innovative products and collaborative culture."
            
            # Generate response to a custom question
            question = "Why do you want to work for our company?"
            response = ai_service.generate_response(
                question=question,
                job_context={"job_id": job.id, "job_title": job.title, "company": job.company, "job_description": job.description},
                user_profile=profile_service.get_profile(self.user_id)
            )
            
            # Verify response
            self.assertIsNotNone(response)
            self.assertTrue(len(response) > 0)
            mock_generate.assert_called_once()
        
        # Test template selection
        templates = [
            {"id": "1", "name": "Software Engineer Resume", "keywords": ["python", "javascript", "backend"]},
            {"id": "2", "name": "Frontend Developer Resume", "keywords": ["react", "javascript", "frontend"]},
            {"id": "3", "name": "Data Scientist Resume", "keywords": ["python", "data", "machine learning"]}
        ]
        
        best_template = ai_service.select_best_template(job, templates)
        self.assertEqual(best_template["id"], "1")  # Should match Software Engineer template
    
    def test_form_filler_ai_integration(self):
        """Test integration between form filler and AI service."""
        from automation.form_response_generator import FormField
        
        # Create test job
        job = self._create_test_job()
        
        # Create form filler and response generator
        form_filler = FormFiller(self.app)
        form_response_generator = FormResponseGenerator(self.app)
        
        # Create test form field
        custom_question_field = FormField(
            "why_join", 
            FormField.TEXTAREA, 
            "Why do you want to join our company?", 
            required=True
        )
        
        # Mock AI service
        with patch('services.ai_service.AIService.generate_response') as mock_generate:
            mock_generate.return_value = "I am excited about the opportunity to join Test Company because of the innovative work you're doing in software engineering."
            
            # Generate response
            response = form_response_generator.generate_response(
                custom_question_field,
                job_context={"job_id": job.id, "job_title": job.title, "company": job.company, "job_description": job.description},
                user_profile=profile_service.get_profile(self.user_id)
            )
            
            # Verify response
            self.assertIsNotNone(response)
            self.assertTrue(len(response) > 0)
            self.assertTrue("Test Company" in response)
            mock_generate.assert_called_once()
    
    def test_api_automation_integration(self):
        """Test integration between API and automation components."""
        # Create test job
        job = self._create_test_job()
        
        # Mock application service
        with patch('services.application_service.ApplicationService.submit_application') as mock_submit:
            mock_submit.return_value = {
                'success': True,
                'application_id': str(uuid.uuid4()),
                'status': ApplicationStatus.SUBMITTED.value,
                'confirmation_details': {'confirmation_id': 'APP123456'}
            }
            
            # Submit application through API
            response = self.client.post(
                f'/api/jobs/{job.id}/apply',
                json={},
                headers={'X-CSRF-Token': self.csrf_token}
            )
            self.assertEqual(response.status_code, 200)
            
            data = response.json
            self.assertEqual(data['status'], 'success')
            self.assertTrue('application_id' in data)
            
            # Verify application service was called
            mock_submit.assert_called_once_with(job.id, self.user_id)
    
    def test_notification_service_integration(self):
        """Test integration with notification service."""
        from services.notification_service import notification_service
        
        # Create test job and application
        job = self._create_test_job()
        application = Application(
            id=str(uuid.uuid4()),
            job_id=job.id,
            user_id=self.user_id,
            status=ApplicationStatus.SUBMITTED.value,
            submitted_at=datetime.utcnow()
        )
        db.session.add(application)
        db.session.commit()
        
        # Mock email sending
        with patch('services.notification_service.NotificationService._send_email') as mock_send_email:
            mock_send_email.return_value = True
            
            # Send notification
            result = notification_service.send_application_status_notification(
                application_id=application.id,
                status=ApplicationStatus.INTERVIEW.value,
                details="Interview scheduled for next week"
            )
            
            # Verify notification was sent
            self.assertTrue(result)
            mock_send_email.assert_called_once()
            
            # Verify notification appears in API
            response = self.client.get('/api/notifications')
            self.assertEqual(response.status_code, 200)
            
            data = response.json
            self.assertEqual(data['status'], 'success')
            self.assertTrue(len(data['notifications']) > 0)
            self.assertEqual(data['notifications'][0]['application_id'], application.id)
    
    def test_load_testing(self):
        """Test system under load with multiple simultaneous sessions."""
        # Create multiple test jobs
        jobs = []
        for i in range(10):
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
        
        db.session.commit()
        
        # Simulate multiple users accessing the system simultaneously
        import threading
        import time
        
        results = {'success_count': 0, 'failure_count': 0, 'response_times': []}
        
        def simulate_user_session(user_index):
            try:
                start_time = time.time()
                
                # Create client
                client = self.app.test_client()
                
                # Login
                response = client.post('/api/auth/login', json={
                    'email': 'test@example.com',
                    'password': 'password123'
                })
                csrf_token = response.json.get('csrf_token')
                
                # Get jobs
                response = client.get('/api/jobs')
                assert response.status_code == 200
                
                # Get job details
                job_id = jobs[user_index % len(jobs)].id
                response = client.get(f'/api/jobs/{job_id}')
                assert response.status_code == 200
                
                # Filter jobs
                response = client.post(
                    '/api/jobs/filter',
                    json={
                        'job_ids': [job.id for job in jobs],
                        'preferences': {
                            'remote_options': ['remote', 'hybrid'],
                            'experience_levels': ['mid']
                        }
                    }
                )
                assert response.status_code == 200
                
                # Get profile
                response = client.get('/api/profile')
                assert response.status_code == 200
                
                # Get applications
                response = client.get('/api/applications')
                assert response.status_code == 200
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to milliseconds
                
                with results_lock:
                    results['success_count'] += 1
                    results['response_times'].append(response_time)
            
            except Exception as e:
                with results_lock:
                    results['failure_count'] += 1
                    print(f"Error in user session {user_index}: {str(e)}")
        
        # Create threads for simulating users
        threads = []
        results_lock = threading.Lock()
        num_users = 20
        
        for i in range(num_users):
            thread = threading.Thread(target=simulate_user_session, args=(i,))
            threads.append(thread)
        
        # Start all threads
        for thread in threads:
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify results
        self.assertEqual(results['success_count'], num_users)
        self.assertEqual(results['failure_count'], 0)
        
        # Calculate average response time
        avg_response_time = sum(results['response_times']) / len(results['response_times'])
        
        # Verify average response time is acceptable (under 2000ms for all operations)
        self.assertLess(avg_response_time, 2000)


    def test_database_transaction_integrity(self):
        """Test database transaction integrity with rollbacks."""
        # Create test job
        job = self._create_test_job()
        
        # Start a transaction
        try:
            # Make changes within a transaction
            job.title = "Updated Job Title"
            job.company = "Updated Company"
            
            # Create an application that will cause a constraint violation
            invalid_application = Application(
                id=str(uuid.uuid4()),
                job_id="invalid-job-id",  # This will cause a foreign key constraint violation
                user_id=self.user_id,
                status=ApplicationStatus.SUBMITTED.value
            )
            db.session.add(invalid_application)
            
            # Attempt to commit - this should fail
            db.session.commit()
            self.fail("Expected database constraint violation")
        except Exception:
            # Transaction should be rolled back
            db.session.rollback()
        
        # Verify job changes were rolled back
        db.session.refresh(job)
        self.assertEqual(job.title, "Software Engineer")  # Original title
        self.assertEqual(job.company, "Test Company")     # Original company
    
    def test_websocket_real_time_updates(self):
        """Test WebSocket real-time updates for application status changes."""
        from flask_socketio import SocketIO
        
        # Create test job and application
        job = self._create_test_job()
        application = Application(
            id=str(uuid.uuid4()),
            job_id=job.id,
            user_id=self.user_id,
            status=ApplicationStatus.SUBMITTED.value,
            submitted_at=datetime.utcnow()
        )
        db.session.add(application)
        db.session.commit()
        
        # Mock SocketIO
        with patch('services.application_service.socketio') as mock_socketio:
            # Update application status
            application_service.update_application_status(
                application.id, 
                ApplicationStatus.INTERVIEW.value,
                {"interview_date": "2025-07-25", "interview_type": "video"}
            )
            
            # Verify WebSocket event was emitted
            mock_socketio.emit.assert_called_with(
                'application_status_update',
                {
                    'application_id': application.id,
                    'status': ApplicationStatus.INTERVIEW.value,
                    'details': {"interview_date": "2025-07-25", "interview_type": "video"}
                },
                room=f'user_{self.user_id}'
            )
    
    def test_frontend_automation_integration(self):
        """Test integration between frontend, API, and automation engine."""
        # Create test job
        job = self._create_test_job()
        
        # Mock the browser manager and adapter
        with patch('automation.playwright_engine.browser_manager.BrowserManager') as mock_browser_manager:
            # Set up mock browser manager
            mock_instance = mock_browser_manager.return_value
            mock_instance.create_context.return_value = MagicMock()
            mock_instance.get_page.return_value = MagicMock()
            
            # Mock the adapter factory
            with patch('services.application_service.ApplicationService._get_adapter_for_website') as mock_get_adapter:
                # Set up mock adapter
                mock_adapter = MagicMock()
                mock_adapter.login.return_value = True
                mock_adapter.navigate.return_value = True
                mock_adapter.apply_to_job.return_value = {
                    'success': True,
                    'confirmation_id': 'APP123456',
                    'application_date': datetime.utcnow().isoformat(),
                    'status': 'submitted'
                }
                mock_get_adapter.return_value = mock_adapter
                
                # Submit application through API
                response = self.client.post(
                    f'/api/jobs/{job.id}/apply',
                    json={},
                    headers={'X-CSRF-Token': self.csrf_token}
                )
                self.assertEqual(response.status_code, 200)
                
                # Verify application was created
                data = response.json
                self.assertEqual(data['status'], 'success')
                self.assertTrue('application_id' in data)
                
                # Verify adapter methods were called
                mock_adapter.login.assert_called_once()
                mock_adapter.navigate.assert_called_once()
                mock_adapter.apply_to_job.assert_called_once()
                
                # Verify application status in database
                application = Application.query.get(data['application_id'])
                self.assertEqual(application.status, ApplicationStatus.SUBMITTED.value)
    
    def test_error_handling_and_logging_integration(self):
        """Test integration of error handling and logging across components."""
        from services.logging_service import logging_service
        
        # Create test job
        job = self._create_test_job()
        
        # Mock the application service to raise an exception
        with patch('services.application_service.ApplicationService.submit_application') as mock_submit:
            mock_submit.side_effect = Exception("Test error during application submission")
            
            # Mock the logging service
            with patch('services.logging_service.LoggingService.log_error') as mock_log_error:
                # Attempt to submit application through API
                response = self.client.post(
                    f'/api/jobs/{job.id}/apply',
                    json={},
                    headers={'X-CSRF-Token': self.csrf_token}
                )
                
                # Verify error response
                self.assertEqual(response.status_code, 500)
                data = response.json
                self.assertEqual(data['status'], 'error')
                
                # Verify error was logged
                mock_log_error.assert_called_once()
                
                # Verify error log contains relevant information
                call_args = mock_log_error.call_args[0]
                self.assertTrue("Test error during application submission" in str(call_args))
                self.assertTrue(job.id in str(call_args))


if __name__ == '__main__':
    unittest.main()