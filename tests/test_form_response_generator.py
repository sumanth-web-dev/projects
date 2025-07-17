"""
Unit tests for the form response generator.
"""
import unittest
from unittest.mock import patch, MagicMock
import flask
from automation.form_response_generator import FormResponseGenerator, FormField
from services.ai_service import JobContext, ResponseQuality


class MockJob:
    """Mock Job class for testing."""
    
    def __init__(self, id, title, company, description):
        self.id = id
        self.title = title
        self.company = company
        self.description = description
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'company': self.company,
            'description': self.description,
            'location': 'Remote',
            'salary_range': {'min': 80000, 'max': 120000, 'currency': 'USD'}
        }


class TestFormResponseGenerator(unittest.TestCase):
    """Test cases for FormResponseGenerator."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a test Flask app
        self.app = flask.Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create mock AI service
        self.mock_ai_service = MagicMock()
        self.mock_ai_service.generate_response.return_value = "This is a test response."
        self.mock_ai_service.validate_response_quality.return_value = ResponseQuality(
            ResponseQuality.HIGH, 0.9, []
        )
        
        # Create form response generator with mock AI service
        self.form_generator = FormResponseGenerator(self.mock_ai_service)
        
        # Create a mock job
        self.mock_job = MockJob(
            id="test-job-id",
            title="Software Engineer",
            company="Test Company",
            description="We are looking for a Software Engineer with Python and JavaScript experience."
        )
        
        # Create job context
        self.job_context = JobContext(self.mock_job)
        
        # Create a mock user profile
        self.user_profile = {
            'email': 'john.doe@example.com',
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
                        'position': 'Junior Developer',
                        'description': 'Developed web applications using Python and JavaScript'
                    },
                    {
                        'company': 'Another Company',
                        'position': 'Software Engineer',
                        'description': 'Built RESTful APIs and React frontends'
                    }
                ],
                'education': [
                    {
                        'degree': "Bachelor's",
                        'field': 'Computer Science',
                        'institution': 'University of Technology'
                    }
                ]
            },
            'preferences': {
                'job_titles': ['Software Engineer', 'Full Stack Developer'],
                'locations': ['Remote', 'New York'],
                'salary_min': 90000,
                'salary_max': 130000,
                'notice_period': '2 weeks'
            }
        }
    
    def test_generate_field_response(self):
        """Test generating responses for form fields."""
        # Test text field
        text_field = FormField(
            field_id="name",
            field_type=FormField.TEXT,
            label="Full Name",
            required=True
        )
        
        response, quality = self.form_generator.generate_field_response(
            text_field, self.job_context, self.user_profile
        )
        
        self.assertEqual(response, "This is a test response.")
        self.assertEqual(quality.quality, ResponseQuality.HIGH)
        
        # Test textarea field
        textarea_field = FormField(
            field_id="experience",
            field_type=FormField.TEXTAREA,
            label="Describe your experience",
            required=True
        )
        
        response, quality = self.form_generator.generate_field_response(
            textarea_field, self.job_context, self.user_profile
        )
        
        self.assertEqual(response, "This is a test response.")
        self.assertEqual(quality.quality, ResponseQuality.HIGH)
        
        # Test select field with options
        select_field = FormField(
            field_id="education",
            field_type=FormField.SELECT,
            label="Highest Education",
            options=["High School", "Bachelor's", "Master's", "PhD"],
            required=True
        )
        
        # Mock AI service to return a response that matches an option
        self.mock_ai_service.generate_response.return_value = "I have a Bachelor's degree in Computer Science."
        
        response, quality = self.form_generator.generate_field_response(
            select_field, self.job_context, self.user_profile
        )
        
        self.assertEqual(response, "Bachelor's")
        self.assertEqual(quality.quality, ResponseQuality.HIGH)
    
    def test_generate_form_responses(self):
        """Test generating responses for multiple form fields."""
        fields = [
            FormField(
                field_id="name",
                field_type=FormField.TEXT,
                label="Full Name",
                required=True
            ),
            FormField(
                field_id="email",
                field_type=FormField.TEXT,
                label="Email Address",
                required=True
            ),
            FormField(
                field_id="experience",
                field_type=FormField.TEXTAREA,
                label="Describe your experience",
                required=True
            )
        ]
        
        responses = self.form_generator.generate_form_responses(
            fields, self.job_context, self.user_profile
        )
        
        self.assertEqual(len(responses), 3)
        self.assertIn("name", responses)
        self.assertIn("email", responses)
        self.assertIn("experience", responses)
        
        for field_id, (response, quality) in responses.items():
            self.assertEqual(response, "This is a test response.")
            self.assertEqual(quality.quality, ResponseQuality.HIGH)
    
    def test_detect_field_type(self):
        """Test field type detection."""
        # The detect_field_type method returns semantic field types, not HTML element types
        # These are the semantic types defined in _common_field_patterns
        self.assertEqual(
            self.form_generator.detect_field_type("first_name", "First Name"),
            "name"
        )
        self.assertEqual(
            self.form_generator.detect_field_type("email", "Email Address"),
            "email"
        )
        self.assertEqual(
            self.form_generator.detect_field_type("experience", "Describe your experience"),
            "experience"
        )
    
    def test_map_user_data_to_field(self):
        """Test mapping user data to form fields."""
        # Test name field
        name_field = FormField(
            field_id="full_name",
            field_type=FormField.TEXT,
            label="Full Name",
            required=True
        )
        
        name_value = self.form_generator.map_user_data_to_field(name_field, self.user_profile)
        self.assertEqual(name_value, "John Doe")
        
        # Test email field
        email_field = FormField(
            field_id="email",
            field_type=FormField.TEXT,
            label="Email Address",
            required=True
        )
        
        email_value = self.form_generator.map_user_data_to_field(email_field, self.user_profile)
        self.assertEqual(email_value, "john.doe@example.com")
        
        # Test phone field
        phone_field = FormField(
            field_id="phone",
            field_type=FormField.TEXT,
            label="Phone Number",
            required=True
        )
        
        phone_value = self.form_generator.map_user_data_to_field(phone_field, self.user_profile)
        self.assertEqual(phone_value, "555-123-4567")
        
        # Test address field
        address_field = FormField(
            field_id="address",
            field_type=FormField.TEXT,
            label="Address",
            required=True
        )
        
        address_value = self.form_generator.map_user_data_to_field(address_field, self.user_profile)
        self.assertEqual(address_value, "123 Main St")
        
        # Test skills field
        skills_field = FormField(
            field_id="skills",
            field_type=FormField.TEXTAREA,
            label="Skills",
            required=True
        )
        
        skills_value = self.form_generator.map_user_data_to_field(skills_field, self.user_profile)
        self.assertEqual(skills_value, "Python, JavaScript, React, SQL, Git")
    
    def test_convert_field_to_question(self):
        """Test converting fields to questions."""
        # Test name field
        name_field = FormField(
            field_id="name",
            field_type=FormField.TEXT,
            label="Full Name",
            required=True
        )
        
        name_question = self.form_generator._convert_field_to_question(name_field)
        self.assertEqual(name_question, "What is your Full Name?")
        
        # Test experience field
        exp_field = FormField(
            field_id="experience",
            field_type=FormField.TEXTAREA,
            label="Work Experience",
            required=True
        )
        
        exp_question = self.form_generator._convert_field_to_question(exp_field)
        self.assertEqual(exp_question, "Describe your Work Experience.")
        
        # Test field with question mark
        question_field = FormField(
            field_id="why",
            field_type=FormField.TEXTAREA,
            label="Why do you want to work here?",
            required=True
        )
        
        question = self.form_generator._convert_field_to_question(question_field)
        self.assertEqual(question, "Why do you want to work here?")
    
    def test_format_response_for_field_type(self):
        """Test response formatting based on field type."""
        # Test text field formatting
        text_field = FormField(
            field_id="name",
            field_type=FormField.TEXT,
            label="Full Name",
            required=True
        )
        
        text_response = self.form_generator._format_response_for_field_type(
            "John Doe is my name. I am a software engineer.", text_field
        )
        self.assertEqual(text_response, "John Doe is my name")
        
        # Test textarea field formatting
        textarea_field = FormField(
            field_id="experience",
            field_type=FormField.TEXTAREA,
            label="Work Experience",
            required=True
        )
        
        long_text = "This is a very long response. " * 100
        textarea_response = self.form_generator._format_response_for_field_type(
            long_text, textarea_field
        )
        self.assertTrue(len(textarea_response) <= 500)
        
        # Test select field formatting
        select_field = FormField(
            field_id="education",
            field_type=FormField.SELECT,
            label="Highest Education",
            options=["High School", "Bachelor's", "Master's", "PhD"],
            required=True
        )
        
        select_response = self.form_generator._format_response_for_field_type(
            "I have a Bachelor's degree in Computer Science.", select_field
        )
        self.assertEqual(select_response, "Bachelor's")
        
        # Test select field with no match
        select_response_no_match = self.form_generator._format_response_for_field_type(
            "I completed my education.", select_field
        )
        self.assertEqual(select_response_no_match, "High School")  # First option for required field
    
    def test_generate_fallback_response(self):
        """Test fallback response generation."""
        # Test name field fallback
        name_field = FormField(
            field_id="full_name",
            field_type=FormField.TEXT,
            label="Full Name",
            required=True
        )
        
        name_fallback = self.form_generator._generate_fallback_response(name_field, self.user_profile)
        self.assertEqual(name_fallback, "John Doe")
        
        # Test unknown field fallback
        unknown_field = FormField(
            field_id="unknown",
            field_type=FormField.TEXT,
            label="Unknown Field",
            required=True
        )
        
        unknown_fallback = self.form_generator._generate_fallback_response(unknown_field, self.user_profile)
        self.assertEqual(unknown_fallback, "Information available upon request")
        
        # Test textarea fallback
        textarea_field = FormField(
            field_id="unknown_textarea",
            field_type=FormField.TEXTAREA,
            label="Unknown Textarea",
            required=True
        )
        
        textarea_fallback = self.form_generator._generate_fallback_response(textarea_field, self.user_profile)
        self.assertEqual(textarea_fallback, "I would be happy to discuss this further in an interview.")
    
    def tearDown(self):
        """Clean up after tests."""
        self.app_context.pop()


if __name__ == '__main__':
    unittest.main()