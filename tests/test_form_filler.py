"""
Unit tests for the form filler.
"""
import unittest
from unittest.mock import patch, MagicMock
import flask
import os
from automation.form_filler import FormFiller
from automation.form_response_generator import FormField
from services.ai_service import JobContext


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


class TestFormFiller(unittest.TestCase):
    """Test cases for FormFiller."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a test Flask app
        self.app = flask.Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create form filler
        self.form_filler = FormFiller(self.app)
        
        # Mock page and elements
        self.page_mock = MagicMock()
        self.element_mock = MagicMock()
        
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
                    }
                ],
                'education': [
                    {
                        'degree': "Bachelor's",
                        'field': 'Computer Science',
                        'institution': 'University of Technology'
                    }
                ]
            }
        }
        
        # Create a mock job context
        self.mock_job = MockJob(
            id="test-job-id",
            title="Software Engineer",
            company="Test Company",
            description="We are looking for a Software Engineer with Python and JavaScript experience."
        )
        self.job_context = JobContext(self.mock_job)
    
    def test_detect_form_fields(self):
        """Test detecting form fields."""
        # Mock query_selector_all to return elements
        self.page_mock.query_selector_all.side_effect = lambda selector: {
            "input:not([type='hidden']):not([type='submit']):not([type='button']):not([type='reset'])": [
                self._create_mock_element("text", "first_name", "First Name"),
                self._create_mock_element("email", "email", "Email Address"),
                self._create_mock_element("checkbox", "subscribe", "Subscribe to newsletter")
            ],
            "textarea": [
                self._create_mock_element("textarea", "comments", "Comments")
            ],
            "select": [
                self._create_mock_element("select", "country", "Country")
            ]
        }.get(selector, [])
        
        # Mock _process_* methods
        with patch.object(self.form_filler, '_process_input_element') as mock_process_input:
            with patch.object(self.form_filler, '_process_textarea_element') as mock_process_textarea:
                with patch.object(self.form_filler, '_process_select_element') as mock_process_select:
                    # Set up mock returns
                    mock_process_input.side_effect = [
                        FormField("first_name", FormField.TEXT, "First Name", required=True),
                        FormField("email", FormField.TEXT, "Email Address", required=True),
                        FormField("subscribe", FormField.CHECKBOX, "Subscribe to newsletter")
                    ]
                    mock_process_textarea.return_value = FormField("comments", FormField.TEXTAREA, "Comments")
                    mock_process_select.return_value = FormField("country", FormField.SELECT, "Country", options=["USA", "Canada"])
                    
                    # Detect form fields
                    fields = self.form_filler.detect_form_fields(self.page_mock)
                    
                    # Verify fields were detected
                    self.assertEqual(len(fields), 5)
                    self.assertEqual(fields[0].field_id, "first_name")
                    self.assertEqual(fields[1].field_id, "email")
                    self.assertEqual(fields[2].field_id, "subscribe")
                    self.assertEqual(fields[3].field_id, "comments")
                    self.assertEqual(fields[4].field_id, "country")
    
    def test_fill_form(self):
        """Test filling a form."""
        # Create test form fields
        form_fields = [
            FormField("first_name", FormField.TEXT, "First Name", required=True),
            FormField("last_name", FormField.TEXT, "Last Name", required=True),
            FormField("email", FormField.TEXT, "Email Address", required=True),
            FormField("comments", FormField.TEXTAREA, "Comments"),
            FormField("country", FormField.SELECT, "Country", options=["USA", "Canada"])
        ]
        
        # Mock _fill_field method
        with patch.object(self.form_filler, '_fill_field') as mock_fill_field:
            # Set up mock returns
            mock_fill_field.return_value = True
            
            # Fill form
            result = self.form_filler.fill_form(self.page_mock, form_fields, self.user_profile, self.job_context)
            
            # Verify form was filled
            self.assertTrue(result)
            self.assertEqual(mock_fill_field.call_count, 5)
    
    def test_upload_file(self):
        """Test uploading a file."""
        # Mock os.path.exists
        with patch('os.path.exists') as mock_exists:
            mock_exists.return_value = True
            
            # Test upload
            result = self.form_filler.upload_file(self.page_mock, "#resume", "path/to/resume.pdf")
            
            # Verify file was uploaded
            self.assertTrue(result)
            self.page_mock.set_input_files.assert_called_with("#resume", "path/to/resume.pdf")
    
    def test_process_input_element(self):
        """Test processing an input element."""
        # Mock element attributes
        element = self._create_mock_element("text", "first_name", "First Name", required=True)
        
        # Mock _find_label_for_element
        with patch.object(self.form_filler, '_find_label_for_element') as mock_find_label:
            mock_find_label.return_value = "First Name"
            
            # Process element
            field = self.form_filler._process_input_element(self.page_mock, element)
            
            # Verify field was created
            self.assertIsNotNone(field)
            self.assertEqual(field.field_id, "first_name")
            self.assertEqual(field.field_type, FormField.TEXT)
            self.assertEqual(field.label, "First Name")
            self.assertTrue(field.required)
    
    def test_process_textarea_element(self):
        """Test processing a textarea element."""
        # Mock element attributes
        element = self._create_mock_element("textarea", "comments", "Comments")
        
        # Mock _find_label_for_element
        with patch.object(self.form_filler, '_find_label_for_element') as mock_find_label:
            mock_find_label.return_value = "Comments"
            
            # Process element
            field = self.form_filler._process_textarea_element(self.page_mock, element)
            
            # Verify field was created
            self.assertIsNotNone(field)
            self.assertEqual(field.field_id, "comments")
            self.assertEqual(field.field_type, FormField.TEXTAREA)
            self.assertEqual(field.label, "Comments")
    
    def test_process_select_element(self):
        """Test processing a select element."""
        # Mock element attributes
        element = self._create_mock_element("select", "country", "Country")
        
        # Mock _find_label_for_element and _get_select_options
        with patch.object(self.form_filler, '_find_label_for_element') as mock_find_label:
            with patch.object(self.form_filler, '_get_select_options') as mock_get_options:
                mock_find_label.return_value = "Country"
                mock_get_options.return_value = ["USA", "Canada"]
                
                # Process element
                field = self.form_filler._process_select_element(self.page_mock, element)
                
                # Verify field was created
                self.assertIsNotNone(field)
                self.assertEqual(field.field_id, "country")
                self.assertEqual(field.field_type, FormField.SELECT)
                self.assertEqual(field.label, "Country")
                self.assertEqual(field.options, ["USA", "Canada"])
    
    def test_find_label_for_element(self):
        """Test finding a label for an element."""
        # Mock query_selector
        self.page_mock.query_selector.return_value = self._create_mock_element("label", "first_name_label", "First Name")
        
        # Find label
        label = self.form_filler._find_label_for_element(self.page_mock, "first_name", "first_name")
        
        # Verify label was found
        self.assertEqual(label, "First Name")
        self.page_mock.query_selector.assert_called_with("label[for='first_name']")
    
    def test_get_select_options(self):
        """Test getting select options."""
        # Mock element evaluate
        element = MagicMock()
        element.evaluate.return_value = ["USA", "Canada", "UK"]
        
        # Get options
        options = self.form_filler._get_select_options(self.page_mock, element)
        
        # Verify options were retrieved
        self.assertEqual(options, ["USA", "Canada", "UK"])
        element.evaluate.assert_called_once()
    
    def test_fill_field(self):
        """Test filling a field."""
        # Create test field
        field = FormField("first_name", FormField.TEXT, "First Name", required=True)
        
        # Mock interaction_handler
        with patch('automation.form_filler.interaction_handler') as mock_interaction_handler:
            mock_interaction_handler.human_type.return_value = True
            
            # Fill field
            result = self.form_filler._fill_field(self.page_mock, field, self.user_profile)
            
            # Verify field was filled
            self.assertTrue(result)
            mock_interaction_handler.human_type.assert_called_once()
    
    def test_get_fallback_value(self):
        """Test getting fallback values."""
        # Test various field types
        first_name_field = FormField("first_name", FormField.TEXT, "First Name")
        email_field = FormField("email", FormField.TEXT, "Email Address")
        comments_field = FormField("comments", FormField.TEXTAREA, "Comments")
        country_field = FormField("country", FormField.SELECT, "Country", options=["USA", "Canada"])
        subscribe_field = FormField("subscribe", FormField.CHECKBOX, "Subscribe", required=True)
        
        # Get fallback values
        first_name_value = self.form_filler._get_fallback_value(first_name_field)
        email_value = self.form_filler._get_fallback_value(email_field)
        comments_value = self.form_filler._get_fallback_value(comments_field)
        country_value = self.form_filler._get_fallback_value(country_field)
        subscribe_value = self.form_filler._get_fallback_value(subscribe_field)
        
        # Verify fallback values
        self.assertEqual(first_name_value, "John")
        self.assertEqual(email_value, "john.doe@example.com")
        self.assertEqual(comments_value, "Please see my attached resume for details.")
        self.assertEqual(country_value, "USA")
        self.assertTrue(subscribe_value)
    
    def _create_mock_element(self, element_type, element_id, label_text, required=False):
        """Create a mock element with attributes."""
        element = MagicMock()
        
        # Set up get_attribute method
        element.get_attribute.side_effect = lambda attr: {
            'id': element_id,
            'name': element_id,
            'type': element_type,
            'required': 'required' if required else None,
            'placeholder': f"Enter {label_text}",
            'maxlength': None
        }.get(attr)
        
        # Set up inner_text method
        element.inner_text.return_value = label_text
        
        return element
    
    def tearDown(self):
        """Clean up after tests."""
        self.app_context.pop()


if __name__ == '__main__':
    unittest.main()