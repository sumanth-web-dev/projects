"""
Tests for the job search service.
"""
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
import uuid

from models.database import db
from models.job import Job
from services.job_search_service import JobSearchService


class TestJobSearchService(unittest.TestCase):
    """Test cases for JobSearchService."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a mock Flask app
        self.app = MagicMock()
        self.app.config = {
            'DEBUG': True
        }
        
        # Initialize service
        self.job_search_service = JobSearchService(self.app)
        
        # Mock database session
        self.db_session_mock = MagicMock()
        db.session = self.db_session_mock
    
    def test_search_jobs(self):
        """Test searching for jobs with various criteria."""
        # Create mock jobs
        mock_job1 = MagicMock(spec=Job)
        mock_job1.id = str(uuid.uuid4())
        mock_job1.title = "Senior Python Developer"
        mock_job1.company = "Tech Corp"
        mock_job1.location = "New York, NY"
        mock_job1.is_active = True
        mock_job1.discovered_at = datetime.utcnow()
        
        mock_job2 = MagicMock(spec=Job)
        mock_job2.id = str(uuid.uuid4())
        mock_job2.title = "Junior Python Developer"
        mock_job2.company = "Startup Inc"
        mock_job2.location = "Remote"
        mock_job2.is_active = True
        mock_job2.discovered_at = datetime.utcnow() - timedelta(days=5)
        
        # Mock query results
        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.order_by.return_value = mock_query
        mock_query.limit.return_value = mock_query
        mock_query.offset.return_value = mock_query
        mock_query.all.return_value = [mock_job1, mock_job2]
        
        # Mock Job.query
        with patch('models.job.Job.query', mock_query):
            # Test basic search
            success, jobs, message = self.job_search_service.search_jobs({})
            
            self.assertTrue(success)
            self.assertEqual(len(jobs), 2)
            self.assertIn("Found 2 jobs", message)
            
            # Test with keywords
            mock_query.all.return_value = [mock_job1]
            success, jobs, message = self.job_search_service.search_jobs({
                'keywords': 'Senior'
            })
            
            self.assertTrue(success)
            self.assertEqual(len(jobs), 1)
            self.assertIn("Found 1 jobs", message)
    
    def test_filter_jobs(self):
        """Test filtering jobs based on user preferences."""
        # Create mock jobs
        mock_job1 = MagicMock(spec=Job)
        mock_job1.matches_criteria.return_value = True
        
        mock_job2 = MagicMock(spec=Job)
        mock_job2.matches_criteria.return_value = False
        
        mock_job3 = MagicMock(spec=Job)
        mock_job3.matches_criteria.return_value = True
        
        # Test filtering
        filtered_jobs = self.job_search_service.filter_jobs(
            [mock_job1, mock_job2, mock_job3],
            {'keywords': ['python'], 'locations': ['remote']}
        )
        
        self.assertEqual(len(filtered_jobs), 2)
        self.assertIn(mock_job1, filtered_jobs)
        self.assertIn(mock_job3, filtered_jobs)
        self.assertNotIn(mock_job2, filtered_jobs)
        
        # Test with empty preferences
        all_jobs = self.job_search_service.filter_jobs(
            [mock_job1, mock_job2, mock_job3],
            {}
        )
        
        self.assertEqual(len(all_jobs), 3)
    
    def test_detect_duplicates(self):
        """Test detecting and consolidating duplicate jobs."""
        # Create mock jobs with same company and title but different details
        job_id1 = str(uuid.uuid4())
        job_id2 = str(uuid.uuid4())
        job_id3 = str(uuid.uuid4())
        
        mock_job1 = MagicMock(spec=Job)
        mock_job1.id = job_id1
        mock_job1.company = "Tech Corp"
        mock_job1.title = "Python Developer"
        mock_job1.description = "A detailed job description"
        mock_job1.salary_min = 80000
        mock_job1.salary_max = 100000
        mock_job1.discovered_at = datetime.utcnow() - timedelta(days=2)
        
        mock_job2 = MagicMock(spec=Job)
        mock_job2.id = job_id2
        mock_job2.company = "Tech Corp"
        mock_job2.title = "Python Developer"
        mock_job2.description = None
        mock_job2.salary_min = None
        mock_job2.salary_max = None
        mock_job2.discovered_at = datetime.utcnow() - timedelta(days=1)
        
        mock_job3 = MagicMock(spec=Job)
        mock_job3.id = job_id3
        mock_job3.company = "Different Corp"
        mock_job3.title = "Python Developer"
        mock_job3.description = "Another job description"
        mock_job3.discovered_at = datetime.utcnow()
        
        # Test deduplication
        unique_jobs = self.job_search_service.detect_duplicates([mock_job1, mock_job2, mock_job3])
        
        self.assertEqual(len(unique_jobs), 2)
        
        # Check that we kept the job with more information
        job_ids = [job.id for job in unique_jobs]
        self.assertIn(job_id1, job_ids)  # Should keep job1 over job2
        self.assertIn(job_id3, job_ids)
    
    def test_get_job_by_id(self):
        """Test getting a job by ID."""
        # Mock Job.query
        mock_job = MagicMock(spec=Job)
        mock_job.id = "test_job_id"
        
        with patch('models.job.Job.query') as mock_query:
            mock_query.get.return_value = mock_job
            
            # Test successful retrieval
            job = self.job_search_service.get_job_by_id("test_job_id")
            self.assertEqual(job.id, "test_job_id")
            
            # Test job not found
            mock_query.get.return_value = None
            job = self.job_search_service.get_job_by_id("nonexistent_id")
            self.assertIsNone(job)
    
    def test_get_job_by_url(self):
        """Test getting a job by source URL."""
        # Mock Job.query
        mock_job = MagicMock(spec=Job)
        mock_job.source_url = "https://example.com/job/123"
        
        with patch('models.job.Job.query') as mock_query:
            mock_query.filter_by.return_value.first.return_value = mock_job
            
            # Test successful retrieval
            job = self.job_search_service.get_job_by_url("https://example.com/job/123")
            self.assertEqual(job.source_url, "https://example.com/job/123")
            
            # Test job not found
            mock_query.filter_by.return_value.first.return_value = None
            job = self.job_search_service.get_job_by_url("https://example.com/job/nonexistent")
            self.assertIsNone(job)
    
    def test_save_job(self):
        """Test saving a new job and updating an existing one."""
        # Mock get_job_by_url
        with patch.object(self.job_search_service, 'get_job_by_url') as mock_get_job:
            # Test creating a new job
            mock_get_job.return_value = None
            
            job_data = {
                'title': 'Software Engineer',
                'company': 'Tech Company',
                'source_website': 'linkedin',
                'source_url': 'https://linkedin.com/jobs/123'
            }
            
            success, job, message = self.job_search_service.save_job(job_data)
            
            self.assertTrue(success)
            self.assertIsNotNone(job)
            self.assertIn("created successfully", message)
            self.db_session_mock.add.assert_called_once()
            self.db_session_mock.commit.assert_called_once()
            
            # Test updating an existing job
            self.db_session_mock.reset_mock()
            mock_existing_job = MagicMock(spec=Job)
            mock_get_job.return_value = mock_existing_job
            
            updated_data = {
                'title': 'Senior Software Engineer',
                'description': 'Updated description'
            }
            
            success, job, message = self.job_search_service.save_job(updated_data)
            
            self.assertTrue(success)
            self.assertEqual(job, mock_existing_job)
            self.assertIn("updated successfully", message)
            self.db_session_mock.add.assert_not_called()
            self.db_session_mock.commit.assert_called_once()
            
            # Verify attributes were updated
            self.assertEqual(mock_existing_job.title, 'Senior Software Engineer')
            self.assertEqual(mock_existing_job.description, 'Updated description')
    
    def test_mark_job_inactive(self):
        """Test marking a job as inactive."""
        # Mock get_job_by_id
        mock_job = MagicMock(spec=Job)
        mock_job.is_active = True
        
        with patch.object(self.job_search_service, 'get_job_by_id') as mock_get_job:
            # Test successful update
            mock_get_job.return_value = mock_job
            
            success, message = self.job_search_service.mark_job_inactive("test_job_id")
            
            self.assertTrue(success)
            self.assertIn("marked as inactive", message)
            self.assertFalse(mock_job.is_active)
            self.db_session_mock.commit.assert_called_once()
            
            # Test job not found
            self.db_session_mock.reset_mock()
            mock_get_job.return_value = None
            
            success, message = self.job_search_service.mark_job_inactive("nonexistent_id")
            
            self.assertFalse(success)
            self.assertIn("not found", message)
            self.db_session_mock.commit.assert_not_called()
    
    def test_get_similar_jobs(self):
        """Test finding similar jobs."""
        # Create mock jobs
        mock_job = MagicMock(spec=Job)
        mock_job.id = "test_job_id"
        mock_job.title = "Python Developer"
        mock_job.company = "Tech Corp"
        mock_job.extract_keywords.return_value = ["python", "developer", "backend"]
        
        similar_job1 = MagicMock(spec=Job)
        similar_job1.id = "similar1"
        similar_job1.title = "Senior Python Developer"
        similar_job1.company = "Tech Corp"
        
        similar_job2 = MagicMock(spec=Job)
        similar_job2.id = "similar2"
        similar_job2.title = "Python Backend Engineer"
        similar_job2.company = "Tech Corp"
        
        # Mock get_job_by_id
        with patch.object(self.job_search_service, 'get_job_by_id') as mock_get_job:
            mock_get_job.return_value = mock_job
            
            # Mock query results
            mock_query = MagicMock()
            mock_query.filter.return_value = mock_query
            mock_query.limit.return_value = mock_query
            mock_query.all.return_value = [similar_job1, similar_job2]
            
            # Mock Job.query
            with patch('models.job.Job.query', mock_query):
                # Test finding similar jobs
                similar_jobs = self.job_search_service.get_similar_jobs("test_job_id")
                
                self.assertEqual(len(similar_jobs), 2)
                self.assertIn(similar_job1, similar_jobs)
                self.assertIn(similar_job2, similar_jobs)
                
                # Test with job not found
                mock_get_job.return_value = None
                similar_jobs = self.job_search_service.get_similar_jobs("nonexistent_id")
                self.assertEqual(len(similar_jobs), 0)
                
                # Test with no keywords
                mock_get_job.return_value = mock_job
                mock_job.extract_keywords.return_value = []
                similar_jobs = self.job_search_service.get_similar_jobs("test_job_id")
                self.assertEqual(len(similar_jobs), 0)


if __name__ == '__main__':
    unittest.main()