"""
Tests for the job search service.
"""
import unittest
from unittest.mock import patch, MagicMock, mock_open
from datetime import datetime, timedelta
import uuid
import sys

# Create mocks for the modules to avoid circular imports
db_mock = MagicMock()
Job_mock = MagicMock()

# Mock the modules
sys.modules['models.database'] = MagicMock()
sys.modules['models.database'].db = db_mock
sys.modules['models.job'] = MagicMock()
sys.modules['models.job'].Job = Job_mock

# Now import the service
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
        # Create mock jobs with specific attributes
        mock_job1 = MagicMock(spec=Job)
        mock_job1.matches_criteria.return_value = True
        mock_job1.is_active = True
        mock_job1.is_expired.return_value = False
        mock_job1.company = "Good Company"
        mock_job1.title = "Python Developer"
        mock_job1.description = "A great job for Python developers"
        
        mock_job2 = MagicMock(spec=Job)
        mock_job2.matches_criteria.return_value = False
        mock_job2.is_active = True
        mock_job2.is_expired.return_value = False
        mock_job2.company = "Another Company"
        mock_job2.title = "Java Developer"
        mock_job2.description = "Java development position"
        
        mock_job3 = MagicMock(spec=Job)
        mock_job3.matches_criteria.return_value = True
        mock_job3.is_active = True
        mock_job3.is_expired.return_value = False
        mock_job3.company = "Tech Corp"
        mock_job3.title = "Senior Developer"
        mock_job3.description = "Senior role for experienced developers"
        
        mock_job4 = MagicMock(spec=Job)
        mock_job4.matches_criteria.return_value = True
        mock_job4.is_active = False  # Inactive job
        mock_job4.company = "Inactive Corp"
        
        mock_job5 = MagicMock(spec=Job)
        mock_job5.matches_criteria.return_value = True
        mock_job5.is_active = True
        mock_job5.is_expired.return_value = True  # Expired job
        mock_job5.company = "Expired Corp"
        
        mock_job6 = MagicMock(spec=Job)
        mock_job6.matches_criteria.return_value = True
        mock_job6.is_active = True
        mock_job6.is_expired.return_value = False
        mock_job6.company = "Blacklisted Corp"  # Company in excluded list
        mock_job6.title = "Python Developer"
        mock_job6.description = "Python development position"
        
        mock_job7 = MagicMock(spec=Job)
        mock_job7.matches_criteria.return_value = True
        mock_job7.is_active = True
        mock_job7.is_expired.return_value = False
        mock_job7.company = "Good Company"
        mock_job7.title = "Python Developer with unpaid overtime"  # Contains excluded keyword
        mock_job7.description = "Python development position"
        
        # Test basic filtering with matches_criteria
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
        
        # Test filtering inactive jobs
        active_jobs = self.job_search_service.filter_jobs(
            [mock_job1, mock_job3, mock_job4],
            {}
        )
        
        self.assertEqual(len(active_jobs), 2)
        self.assertIn(mock_job1, active_jobs)
        self.assertIn(mock_job3, active_jobs)
        self.assertNotIn(mock_job4, active_jobs)
        
        # Test filtering expired jobs
        non_expired_jobs = self.job_search_service.filter_jobs(
            [mock_job1, mock_job3, mock_job5],
            {'exclude_expired': True}
        )
        
        self.assertEqual(len(non_expired_jobs), 2)
        self.assertIn(mock_job1, non_expired_jobs)
        self.assertIn(mock_job3, non_expired_jobs)
        self.assertNotIn(mock_job5, non_expired_jobs)
        
        # Test filtering by excluded companies
        no_blacklisted_jobs = self.job_search_service.filter_jobs(
            [mock_job1, mock_job3, mock_job6],
            {'excluded_companies': ['Blacklisted Corp', 'Bad Company']}
        )
        
        self.assertEqual(len(no_blacklisted_jobs), 2)
        self.assertIn(mock_job1, no_blacklisted_jobs)
        self.assertIn(mock_job3, no_blacklisted_jobs)
        self.assertNotIn(mock_job6, no_blacklisted_jobs)
        
        # Test filtering by excluded keywords
        no_keyword_jobs = self.job_search_service.filter_jobs(
            [mock_job1, mock_job3, mock_job7],
            {'excluded_keywords': ['unpaid', 'overtime']}
        )
        
        self.assertEqual(len(no_keyword_jobs), 2)
        self.assertIn(mock_job1, no_keyword_jobs)
        self.assertIn(mock_job3, no_keyword_jobs)
        self.assertNotIn(mock_job7, no_keyword_jobs)
    
    def test_detect_duplicates(self):
        """Test detecting and consolidating duplicate jobs."""
        # Create mock jobs with same company and title but different details
        job_id1 = str(uuid.uuid4())
        job_id2 = str(uuid.uuid4())
        job_id3 = str(uuid.uuid4())
        job_id4 = str(uuid.uuid4())
        job_id5 = str(uuid.uuid4())
        
        # Two jobs with same URL (highest confidence match)
        mock_job1 = MagicMock(spec=Job)
        mock_job1.id = job_id1
        mock_job1.company = "Tech Corp"
        mock_job1.title = "Python Developer"
        mock_job1.description = "A detailed job description"
        mock_job1.salary_min = 80000
        mock_job1.salary_max = 100000
        mock_job1.source_url = "https://example.com/job/123"
        mock_job1.discovered_at = datetime.utcnow() - timedelta(days=2)
        mock_job1.requirements = ["Python", "Django", "SQL"]
        mock_job1.posted_date = datetime.utcnow() - timedelta(days=5)
        mock_job1.job_type = "Full-time"
        mock_job1.experience_level = "Mid-level"
        mock_job1.remote_option = "Remote"
        
        mock_job2 = MagicMock(spec=Job)
        mock_job2.id = job_id2
        mock_job2.company = "Tech Corp"
        mock_job2.title = "Python Developer"
        mock_job2.description = None
        mock_job2.salary_min = None
        mock_job2.salary_max = None
        mock_job2.source_url = "https://example.com/job/123"  # Same URL as job1
        mock_job2.discovered_at = datetime.utcnow() - timedelta(days=1)
        mock_job2.requirements = []
        mock_job2.posted_date = None
        mock_job2.job_type = None
        mock_job2.experience_level = None
        mock_job2.remote_option = None
        
        # Different company, different job
        mock_job3 = MagicMock(spec=Job)
        mock_job3.id = job_id3
        mock_job3.company = "Different Corp"
        mock_job3.title = "Python Developer"
        mock_job3.description = "Another job description"
        mock_job3.source_url = "https://example.com/job/456"
        mock_job3.discovered_at = datetime.utcnow()
        mock_job3.location = "New York, NY"
        
        # Same company and location, similar title (medium confidence match)
        mock_job4 = MagicMock(spec=Job)
        mock_job4.id = job_id4
        mock_job4.company = "Tech Corp"
        mock_job4.title = "Senior Python Developer"
        mock_job4.description = "Senior role description"
        mock_job4.source_url = "https://example.com/job/789"
        mock_job4.discovered_at = datetime.utcnow()
        mock_job4.location = "San Francisco, CA"
        
        mock_job5 = MagicMock(spec=Job)
        mock_job5.id = job_id5
        mock_job5.company = "Tech Corp"
        mock_job5.title = "Python Developer Lead"
        mock_job5.description = "Lead role description"
        mock_job5.source_url = "https://example.com/job/101112"
        mock_job5.discovered_at = datetime.utcnow() - timedelta(days=1)
        mock_job5.location = "San Francisco, CA"  # Same location as job4
        
        # Test deduplication
        unique_jobs = self.job_search_service.detect_duplicates([mock_job1, mock_job2, mock_job3, mock_job4, mock_job5])
        
        # We should have 3 unique jobs:
        # 1. One from the URL match (job1 or job2)
        # 2. job3 (different company)
        # 3. One from the company+location+similar title match (job4 or job5)
        self.assertEqual(len(unique_jobs), 3)
        
        # Check that we kept the job with more information for URL match
        job_ids = [job.id for job in unique_jobs]
        self.assertIn(job_id1, job_ids)  # Should keep job1 over job2 (more info)
        self.assertNotIn(job_id2, job_ids)
        self.assertIn(job_id3, job_ids)  # Different company, should be kept
        
        # Either job4 or job5 should be kept, but not both
        self.assertTrue((job_id4 in job_ids and job_id5 not in job_ids) or 
                        (job_id5 in job_ids and job_id4 not in job_ids))
    
    def test_select_best_job(self):
        """Test selecting the best job from potential duplicates."""
        # Create mock jobs with varying levels of information
        job_id1 = str(uuid.uuid4())
        job_id2 = str(uuid.uuid4())
        job_id3 = str(uuid.uuid4())
        
        # Job with complete information
        mock_job1 = MagicMock(spec=Job)
        mock_job1.id = job_id1
        mock_job1.description = "A detailed job description"
        mock_job1.salary_min = 80000
        mock_job1.salary_max = 100000
        mock_job1.requirements = ["Python", "Django", "SQL"]
        mock_job1.posted_date = datetime.utcnow() - timedelta(days=5)
        mock_job1.job_type = "Full-time"
        mock_job1.experience_level = "Mid-level"
        mock_job1.remote_option = "Remote"
        mock_job1.discovered_at = datetime.utcnow() - timedelta(days=2)
        
        # Job with partial information but more recent
        mock_job2 = MagicMock(spec=Job)
        mock_job2.id = job_id2
        mock_job2.description = "Brief description"
        mock_job2.salary_min = None
        mock_job2.salary_max = None
        mock_job2.requirements = []
        mock_job2.posted_date = None
        mock_job2.job_type = "Full-time"
        mock_job2.experience_level = None
        mock_job2.remote_option = None
        mock_job2.discovered_at = datetime.utcnow() - timedelta(days=1)
        
        # Job with minimal information but most recent
        mock_job3 = MagicMock(spec=Job)
        mock_job3.id = job_id3
        mock_job3.description = None
        mock_job3.salary_min = None
        mock_job3.salary_max = None
        mock_job3.requirements = []
        mock_job3.posted_date = None
        mock_job3.job_type = None
        mock_job3.experience_level = None
        mock_job3.remote_option = None
        mock_job3.discovered_at = datetime.utcnow()
        
        # Test with all three jobs
        best_job = self.job_search_service._select_best_job([mock_job1, mock_job2, mock_job3])
        self.assertEqual(best_job.id, job_id1)  # Should select job1 with most information
        
        # Test with just the two less complete jobs
        best_job = self.job_search_service._select_best_job([mock_job2, mock_job3])
        self.assertEqual(best_job.id, job_id2)  # Should select job2 with more information
        
        # Test with single job
        best_job = self.job_search_service._select_best_job([mock_job3])
        self.assertEqual(best_job.id, job_id3)  # Should return the only job
    
    def test_group_by_similar_titles(self):
        """Test grouping jobs by similar titles."""
        # Create mock jobs with varying title similarities
        job1 = MagicMock(spec=Job)
        job1.id = "job1"
        job1.title = "Senior Python Developer"
        
        job2 = MagicMock(spec=Job)
        job2.id = "job2"
        job2.title = "Python Developer Lead"
        
        job3 = MagicMock(spec=Job)
        job3.id = "job3"
        job3.title = "Java Engineer"
        
        job4 = MagicMock(spec=Job)
        job4.id = "job4"
        job4.title = "Senior Java Developer"
        
        job5 = MagicMock(spec=Job)
        job5.id = "job5"
        job5.title = "Frontend React Developer"
        
        # Test grouping
        groups = self.job_search_service._group_by_similar_titles([job1, job2, job3, job4, job5])
        
        # Should have 3 groups:
        # 1. Python jobs (job1, job2)
        # 2. Java jobs (job3, job4)
        # 3. Frontend job (job5)
        self.assertEqual(len(groups), 3)
        
        # Find the Python group
        python_group = next((g for g in groups if "job1" in [j.id for j in g]), None)
        self.assertIsNotNone(python_group)
        self.assertEqual(len(python_group), 2)
        self.assertIn(job1, python_group)
        self.assertIn(job2, python_group)
        
        # Find the Java group
        java_group = next((g for g in groups if "job3" in [j.id for j in g]), None)
        self.assertIsNotNone(java_group)
        self.assertEqual(len(java_group), 2)
        self.assertIn(job3, java_group)
        self.assertIn(job4, java_group)
        
        # Find the Frontend group
        frontend_group = next((g for g in groups if "job5" in [j.id for j in g]), None)
        self.assertIsNotNone(frontend_group)
        self.assertEqual(len(frontend_group), 1)
        self.assertIn(job5, frontend_group)
    
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