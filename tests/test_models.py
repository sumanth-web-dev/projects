"""
Unit tests for database models.
"""
import pytest
import json
import uuid
from datetime import datetime, timedelta
from sqlalchemy.exc import IntegrityError
from models import db, User, Job, Application, ApplicationStatus
from models.database import init_db


class TestUser:
    """Test cases for User model."""
    
    def test_user_creation(self):
        """Test basic user creation."""
        user_id = str(uuid.uuid4())
        email = "test@example.com"
        
        user = User(id=user_id, email=email)
        
        assert user.id == user_id
        assert user.email == email
        assert user.is_active is True
        assert user.created_at is not None
        assert user.updated_at is not None
    
    def test_user_email_validation(self):
        """Test email validation."""
        user_id = str(uuid.uuid4())
        
        # Valid email
        user = User(id=user_id, email="valid@example.com")
        assert user.email == "valid@example.com"
        
        # Invalid email format
        with pytest.raises(ValueError, match="Invalid email format"):
            User(id=user_id, email="invalid-email")
        
        # Empty email
        with pytest.raises(ValueError, match="Email is required"):
            User(id=user_id, email="")
        
        # Email normalization
        user = User(id=user_id, email="  TEST@EXAMPLE.COM  ")
        assert user.email == "test@example.com"
    
    def test_user_id_validation(self):
        """Test user ID validation."""
        # Valid ID
        user = User(id="valid-id", email="test@example.com")
        assert user.id == "valid-id"
        
        # Empty ID
        with pytest.raises(ValueError, match="User ID is required"):
            User(id="", email="test@example.com")
        
        # ID too long
        long_id = "a" * 37
        with pytest.raises(ValueError, match="User ID must be 36 characters or less"):
            User(id=long_id, email="test@example.com")
    
    def test_personal_data_encryption(self):
        """Test personal data encryption and decryption."""
        user = User(id=str(uuid.uuid4()), email="test@example.com")
        
        personal_data = {
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+1234567890",
            "address": "123 Main St"
        }
        
        # Set personal data
        user.personal_data = personal_data
        
        # Verify encryption occurred
        assert user.encrypted_personal_data is not None
        assert "John" not in user.encrypted_personal_data  # Data should be encrypted
        
        # Verify decryption works
        decrypted_data = user.personal_data
        assert decrypted_data == personal_data
    
    def test_preferences_json_handling(self):
        """Test job preferences JSON serialization."""
        user = User(id=str(uuid.uuid4()), email="test@example.com")
        
        preferences = {
            "job_titles": ["Software Engineer", "Developer"],
            "locations": ["New York", "Remote"],
            "salary_min": 80000,
            "salary_max": 120000
        }
        
        # Set preferences
        user.preferences = preferences
        
        # Verify JSON storage
        assert user.job_preferences is not None
        stored_prefs = json.loads(user.job_preferences)
        assert stored_prefs == preferences
        
        # Verify retrieval
        retrieved_prefs = user.preferences
        assert retrieved_prefs == preferences
    
    def test_personal_data_validation(self):
        """Test personal data validation."""
        user = User(id=str(uuid.uuid4()), email="test@example.com")
        
        # Valid personal data
        valid_data = {
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+1234567890",
            "address": "123 Main St"
        }
        assert user.validate_personal_data(valid_data) is True
        
        # Missing required field
        invalid_data = {
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+1234567890"
            # Missing address
        }
        with pytest.raises(ValueError, match="Required field 'address' is missing"):
            user.validate_personal_data(invalid_data)
        
        # Invalid phone format
        invalid_phone_data = {
            "first_name": "John",
            "last_name": "Doe",
            "phone": "123",  # Too short
            "address": "123 Main St"
        }
        with pytest.raises(ValueError, match="Invalid phone number format"):
            user.validate_personal_data(invalid_phone_data)
    
    def test_preferences_validation(self):
        """Test preferences validation."""
        user = User(id=str(uuid.uuid4()), email="test@example.com")
        
        # Valid preferences
        valid_prefs = {
            "salary_min": 50000,
            "salary_max": 100000,
            "locations": ["New York", "Remote"]
        }
        assert user.validate_preferences(valid_prefs) is True
        
        # Invalid salary range
        invalid_salary_prefs = {
            "salary_min": 100000,
            "salary_max": 50000  # Max less than min
        }
        with pytest.raises(ValueError, match="Minimum salary cannot be greater than maximum salary"):
            user.validate_preferences(invalid_salary_prefs)
        
        # Invalid locations type
        invalid_locations_prefs = {
            "locations": "New York"  # Should be list
        }
        with pytest.raises(ValueError, match="Locations must be a list"):
            user.validate_preferences(invalid_locations_prefs)
    
    def test_profile_completeness(self):
        """Test profile completeness check."""
        user = User(id=str(uuid.uuid4()), email="test@example.com")
        
        # Incomplete profile
        assert user.is_profile_complete() is False
        
        # Set personal data
        user.personal_data = {
            "first_name": "John",
            "last_name": "Doe",
            "phone": "+1234567890",
            "address": "123 Main St"
        }
        
        # Still incomplete without preferences
        assert user.is_profile_complete() is False
        
        # Set preferences
        user.preferences = {
            "job_titles": ["Software Engineer"],
            "locations": ["New York"]
        }
        
        # Now complete
        assert user.is_profile_complete() is True
    
    def test_user_to_dict(self):
        """Test user dictionary conversion."""
        user = User(id=str(uuid.uuid4()), email="test@example.com")
        
        # Basic dict without sensitive data
        user_dict = user.to_dict()
        assert "id" in user_dict
        assert "email" in user_dict
        assert "personal_data" not in user_dict
        assert "preferences" not in user_dict
        
        # Dict with sensitive data
        user.personal_data = {"first_name": "John", "last_name": "Doe", "phone": "+1234567890", "address": "123 Main St"}
        user_dict_sensitive = user.to_dict(include_sensitive=True)
        assert "personal_data" in user_dict_sensitive
        assert user_dict_sensitive["personal_data"]["first_name"] == "John"


class TestJob:
    """Test cases for Job model."""
    
    def test_job_creation(self):
        """Test basic job creation."""
        job_id = str(uuid.uuid4())
        title = "Software Engineer"
        company = "Tech Corp"
        source_website = "linkedin"
        source_url = "https://linkedin.com/jobs/123"
        
        job = Job(
            id=job_id,
            title=title,
            company=company,
            source_website=source_website,
            source_url=source_url
        )
        
        assert job.id == job_id
        assert job.title == title
        assert job.company == company
        assert job.source_website == source_website
        assert job.source_url == source_url
        assert job.is_active is True
        assert job.application_count == 0
    
    def test_job_validation(self):
        """Test job field validation."""
        job_id = str(uuid.uuid4())
        
        # Valid job
        job = Job(
            id=job_id,
            title="Software Engineer",
            company="Tech Corp",
            source_website="linkedin",
            source_url="https://linkedin.com/jobs/123"
        )
        assert job.title == "Software Engineer"
        
        # Empty title
        with pytest.raises(ValueError, match="Job title is required"):
            Job(
                id=job_id,
                title="",
                company="Tech Corp",
                source_website="linkedin",
                source_url="https://linkedin.com/jobs/123"
            )
        
        # Invalid source website
        with pytest.raises(ValueError, match="Source website must be one of"):
            Job(
                id=job_id,
                title="Software Engineer",
                company="Tech Corp",
                source_website="invalid_source",
                source_url="https://linkedin.com/jobs/123"
            )
        
        # Invalid URL
        with pytest.raises(ValueError, match="Source URL must be a valid HTTP/HTTPS URL"):
            Job(
                id=job_id,
                title="Software Engineer",
                company="Tech Corp",
                source_website="linkedin",
                source_url="not-a-url"
            )
    
    def test_salary_validation(self):
        """Test salary validation."""
        job_id = str(uuid.uuid4())
        
        job = Job(
            id=job_id,
            title="Software Engineer",
            company="Tech Corp",
            source_website="linkedin",
            source_url="https://linkedin.com/jobs/123"
        )
        
        # Valid salary range
        job.set_salary_range(80000, 120000, "USD")
        assert job.salary_min == 80000
        assert job.salary_max == 120000
        assert job.salary_currency == "USD"
        
        # Invalid salary range (min > max)
        with pytest.raises(ValueError, match="Minimum salary cannot be greater than maximum salary"):
            job.set_salary_range(120000, 80000)
        
        # Negative salary
        with pytest.raises(ValueError, match="Salary values must be positive"):
            job.salary_min = -1000
    
    def test_requirements_json_handling(self):
        """Test requirements JSON serialization."""
        job = Job(
            id=str(uuid.uuid4()),
            title="Software Engineer",
            company="Tech Corp",
            source_website="linkedin",
            source_url="https://linkedin.com/jobs/123"
        )
        
        requirements = ["Python", "Django", "PostgreSQL", "5+ years experience"]
        
        # Set requirements
        job.requirements = requirements
        
        # Verify JSON storage
        assert job.requirements_json is not None
        stored_reqs = json.loads(job.requirements_json)
        assert stored_reqs == requirements
        
        # Verify retrieval
        retrieved_reqs = job.requirements
        assert retrieved_reqs == requirements
    
    def test_job_matching_criteria(self):
        """Test job matching against search criteria."""
        job = Job(
            id=str(uuid.uuid4()),
            title="Senior Python Developer",
            company="Tech Corp",
            source_website="linkedin",
            source_url="https://linkedin.com/jobs/123",
            location="New York, NY",
            description="Looking for a senior Python developer with Django experience",
            salary_min=90000,
            salary_max=130000,
            experience_level="senior",
            remote_option="hybrid"
        )
        
        # Keyword matching
        criteria = {"keywords": ["Python", "Django"]}
        assert job.matches_criteria(criteria) is True
        
        criteria = {"keywords": ["Java"]}
        assert job.matches_criteria(criteria) is False
        
        # Location matching
        criteria = {"locations": ["New York"]}
        assert job.matches_criteria(criteria) is True
        
        criteria = {"locations": ["San Francisco"]}
        assert job.matches_criteria(criteria) is False
        
        # Salary matching
        criteria = {"salary_min": 80000}
        assert job.matches_criteria(criteria) is True
        
        criteria = {"salary_min": 140000}
        assert job.matches_criteria(criteria) is False
        
        # Experience level matching
        criteria = {"experience_levels": ["senior", "lead"]}
        assert job.matches_criteria(criteria) is True
        
        criteria = {"experience_levels": ["entry", "mid"]}
        assert job.matches_criteria(criteria) is False
    
    def test_job_expiration(self):
        """Test job expiration logic."""
        job = Job(
            id=str(uuid.uuid4()),
            title="Software Engineer",
            company="Tech Corp",
            source_website="linkedin",
            source_url="https://linkedin.com/jobs/123"
        )
        
        # No expiration date
        assert job.is_expired() is False
        
        # Future expiration
        job.expires_at = datetime.utcnow() + timedelta(days=7)
        assert job.is_expired() is False
        
        # Past expiration
        job.expires_at = datetime.utcnow() - timedelta(days=1)
        assert job.is_expired() is True
    
    def test_days_since_posted(self):
        """Test days since posted calculation."""
        job = Job(
            id=str(uuid.uuid4()),
            title="Software Engineer",
            company="Tech Corp",
            source_website="linkedin",
            source_url="https://linkedin.com/jobs/123"
        )
        
        # No posted date
        assert job.days_since_posted() is None
        
        # Posted 5 days ago
        job.posted_date = datetime.utcnow() - timedelta(days=5)
        assert job.days_since_posted() == 5
    
    def test_job_to_dict(self):
        """Test job dictionary conversion."""
        job = Job(
            id=str(uuid.uuid4()),
            title="Software Engineer",
            company="Tech Corp",
            source_website="linkedin",
            source_url="https://linkedin.com/jobs/123",
            description="Great job opportunity"
        )
        
        # With description
        job_dict = job.to_dict()
        assert "description" in job_dict
        assert job_dict["description"] == "Great job opportunity"
        
        # Without description
        job_dict_no_desc = job.to_dict(include_description=False)
        assert "description" not in job_dict_no_desc


class TestApplication:
    """Test cases for Application model."""
    
    def test_application_creation(self):
        """Test basic application creation."""
        app_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        application = Application(
            id=app_id,
            job_id=job_id,
            user_id=user_id
        )
        
        assert application.id == app_id
        assert application.job_id == job_id
        assert application.user_id == user_id
        assert application.status == ApplicationStatus.PENDING
        assert application.is_active is True
        assert application.retry_count == "0"
        assert application.error_count == "0"
    
    def test_application_validation(self):
        """Test application field validation."""
        app_id = str(uuid.uuid4())
        job_id = str(uuid.uuid4())
        user_id = str(uuid.uuid4())
        
        # Valid application
        application = Application(
            id=app_id,
            job_id=job_id,
            user_id=user_id
        )
        assert application.job_id == job_id
        
        # Empty job ID
        with pytest.raises(ValueError, match="Job ID is required"):
            Application(
                id=app_id,
                job_id="",
                user_id=user_id
            )
        
        # Empty user ID
        with pytest.raises(ValueError, match="User ID is required"):
            Application(
                id=app_id,
                job_id=job_id,
                user_id=""
            )
    
    def test_status_validation_and_transitions(self):
        """Test application status validation and transitions."""
        application = Application(
            id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4())
        )
        
        # Valid status transition: PENDING -> SUBMITTED
        application.update_status(ApplicationStatus.SUBMITTED)
        assert application.status == ApplicationStatus.SUBMITTED
        assert application.submitted_at is not None
        
        # Valid transition: SUBMITTED -> IN_REVIEW
        application.update_status(ApplicationStatus.IN_REVIEW)
        assert application.status == ApplicationStatus.IN_REVIEW
        
        # Invalid transition: IN_REVIEW -> PENDING
        with pytest.raises(ValueError, match="Invalid status transition"):
            application.update_status(ApplicationStatus.PENDING)
        
        # Valid terminal transition: IN_REVIEW -> REJECTED
        application.update_status(ApplicationStatus.REJECTED)
        assert application.status == ApplicationStatus.REJECTED
        assert application.is_terminal_status() is True
    
    def test_materials_used_json_handling(self):
        """Test materials used JSON serialization."""
        application = Application(
            id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4())
        )
        
        materials = {
            "resume_version": "software_engineer_v2.pdf",
            "cover_letter_version": "tech_company_template.pdf"
        }
        
        # Set materials
        application.materials_used = materials
        
        # Verify JSON storage
        assert application.materials_used_json is not None
        stored_materials = json.loads(application.materials_used_json)
        assert stored_materials == materials
        
        # Verify retrieval
        retrieved_materials = application.materials_used
        assert retrieved_materials == materials
    
    def test_custom_responses_handling(self):
        """Test custom responses JSON handling."""
        application = Application(
            id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4())
        )
        
        # Add custom responses
        application.add_custom_response("Why do you want to work here?", "I'm passionate about the company's mission.")
        application.add_custom_response("What's your greatest strength?", "Problem-solving and teamwork.")
        
        responses = application.custom_responses
        assert len(responses) == 2
        assert "Why do you want to work here?" in responses
        
        # Invalid responses
        with pytest.raises(ValueError, match="Question cannot be empty"):
            application.add_custom_response("", "Some answer")
        
        with pytest.raises(ValueError, match="Answer cannot be empty"):
            application.add_custom_response("Some question", "")
    
    def test_confirmation_details(self):
        """Test confirmation details handling."""
        application = Application(
            id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4())
        )
        
        # Set confirmation details
        application.set_confirmation(
            confirmation_id="CONF123456",
            confirmation_url="https://company.com/applications/123",
            additional_info="Application received successfully"
        )
        
        details = application.confirmation_details
        assert details["confirmation_id"] == "CONF123456"
        assert details["confirmation_url"] == "https://company.com/applications/123"
        assert details["additional_info"] == "Application received successfully"
        assert "confirmed_at" in details
    
    def test_retry_logic(self):
        """Test application retry logic."""
        application = Application(
            id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4())
        )
        
        # Initially can't retry (not failed)
        assert application.can_retry() is False
        
        # Set to failed status
        application.update_status(ApplicationStatus.FAILED, "Network error")
        assert application.can_retry() is True
        assert application.error_log == "Network error"
        
        # Increment retry count
        application.increment_retry_count()
        assert application.retry_count == "1"
        
        # After max retries
        application.retry_count = "3"
        assert application.can_retry() is False
    
    def test_days_since_submission(self):
        """Test days since submission calculation."""
        application = Application(
            id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4())
        )
        
        # No submission date
        assert application.days_since_submission() is None
        
        # Set submission date
        application.submitted_at = datetime.utcnow() - timedelta(days=3)
        assert application.days_since_submission() == 3
    
    def test_application_to_dict(self):
        """Test application dictionary conversion."""
        application = Application(
            id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            user_id=str(uuid.uuid4())
        )
        
        # Basic dict
        app_dict = application.to_dict()
        assert "id" in app_dict
        assert "status" in app_dict
        assert app_dict["status"] == "pending"
        assert "materials_used" in app_dict
        assert "custom_responses" in app_dict
        
        # Dict without details
        app_dict_no_details = application.to_dict(include_details=False)
        assert "materials_used" not in app_dict_no_details
        assert "custom_responses" not in app_dict_no_details


class TestModelRelationships:
    """Test cases for model relationships."""
    
    def test_user_application_relationship(self):
        """Test User-Application relationship."""
        # This test would require database setup
        # For now, we'll test the relationship definition exists
        user = User(id=str(uuid.uuid4()), email="test@example.com")
        assert hasattr(user, 'applications')
        
        application = Application(
            id=str(uuid.uuid4()),
            job_id=str(uuid.uuid4()),
            user_id=user.id
        )
        assert hasattr(application, 'user')
    
    def test_job_application_relationship(self):
        """Test Job-Application relationship."""
        job = Job(
            id=str(uuid.uuid4()),
            title="Software Engineer",
            company="Tech Corp",
            source_website="linkedin",
            source_url="https://linkedin.com/jobs/123"
        )
        assert hasattr(job, 'applications')
        
        application = Application(
            id=str(uuid.uuid4()),
            job_id=job.id,
            user_id=str(uuid.uuid4())
        )
        assert hasattr(application, 'job')


if __name__ == "__main__":
    pytest.main([__file__])