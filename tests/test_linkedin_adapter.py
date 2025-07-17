"""
Tests for the LinkedIn adapter.
"""
import pytest
import os
from unittest.mock import MagicMock, patch
from playwright.sync_api import Page, ElementHandle

from automation.adapters.linkedin_adapter import LinkedInAdapter
from automation.adapters.base_adapter import SelectorConfig, AdapterConfig
from services.encryption_service import encryption_service


@pytest.fixture
def mock_page():
    """Create a mock Playwright page."""
    page = MagicMock(spec=Page)
    return page


@pytest.fixture
def mock_element():
    """Create a mock Playwright element handle."""
    element = MagicMock(spec=ElementHandle)
    return element


@pytest.fixture
def linkedin_adapter():
    """Create a LinkedIn adapter instance for testing."""
    adapter = LinkedInAdapter()
    # Mock the browser context and page
    adapter._context = MagicMock()
    adapter._page = MagicMock()
    return adapter


class TestLinkedInAdapter:
    """Test suite for LinkedIn adapter."""
    
    def test_init(self):
        """Test adapter initialization."""
        adapter = LinkedInAdapter()
        
        # Check basic properties
        assert adapter.name == "linkedin"
        assert adapter.base_url == "https://www.linkedin.com"
        assert adapter.login_required is True
        
        # Check selectors
        assert isinstance(adapter.selectors, SelectorConfig)
        assert "login_button" in adapter.selectors.selectors
        assert "easy_apply_button" in adapter.selectors.selectors
    
    @patch('automation.adapters.base_adapter.browser_manager')
    def test_get_page(self, mock_browser_manager, linkedin_adapter):
        """Test get_page method."""
        # Reset page to None to test get_page
        linkedin_adapter._page = None
        
        # Setup mock
        mock_browser_manager.get_page.return_value = MagicMock()
        
        # Call method
        page = linkedin_adapter.get_page()
        
        # Verify
        assert page is not None
        mock_browser_manager.get_page.assert_called_once_with("linkedin_context")
    
    @patch('automation.adapters.linkedin_adapter.interaction_handler')
    def test_login(self, mock_interaction, linkedin_adapter, mock_page):
        """Test login method."""
        # Setup
        linkedin_adapter._page = mock_page
        linkedin_adapter._logged_in = False
        
        # Mock successful navigation
        linkedin_adapter.navigate = MagicMock(return_value=True)
        
        # Mock successful element interactions
        mock_interaction.wait_for_element.return_value = True
        mock_interaction.human_type.return_value = True
        mock_interaction.human_click.return_value = True
        mock_interaction.wait_for_navigation = MagicMock()
        
        # Mock successful login verification
        mock_page.query_selector.side_effect = lambda selector: MagicMock() if selector == "div.feed-identity-module" else None
        
        # Call method
        result = linkedin_adapter.login({"username": "test@example.com", "password": "password123"})
        
        # Verify
        assert result is True
        assert linkedin_adapter._logged_in is True
        linkedin_adapter.navigate.assert_called_once_with("https://www.linkedin.com/login")
        mock_interaction.human_type.assert_any_call(mock_page, linkedin_adapter.selectors.get("username_field"), "test@example.com")
        mock_interaction.human_type.assert_any_call(mock_page, linkedin_adapter.selectors.get("password_field"), "password123")
        mock_interaction.human_click.assert_called_once_with(mock_page, linkedin_adapter.selectors.get("submit_login"))
    
    @patch('automation.adapters.linkedin_adapter.interaction_handler')
    def test_login_failure(self, mock_interaction, linkedin_adapter, mock_page):
        """Test login failure handling."""
        # Setup
        linkedin_adapter._page = mock_page
        linkedin_adapter._logged_in = False
        
        # Mock successful navigation
        linkedin_adapter.navigate = MagicMock(return_value=True)
        
        # Mock successful element interactions
        mock_interaction.wait_for_element.return_value = True
        mock_interaction.human_type.return_value = True
        mock_interaction.human_click.return_value = True
        mock_interaction.wait_for_navigation = MagicMock()
        
        # Mock login error
        error_element = MagicMock()
        error_element.inner_text.return_value = "Incorrect password"
        mock_page.query_selector.side_effect = lambda selector: error_element if selector == linkedin_adapter.selectors.get("login_error") else None
        
        # Call method
        result = linkedin_adapter.login({"username": "test@example.com", "password": "wrong_password"})
        
        # Verify
        assert result is False
        assert linkedin_adapter._logged_in is False
    
    @patch('automation.adapters.linkedin_adapter.interaction_handler')
    def test_search_jobs(self, mock_interaction, linkedin_adapter, mock_page):
        """Test job search functionality."""
        # Setup
        linkedin_adapter._page = mock_page
        linkedin_adapter._logged_in = True
        
        # Mock successful navigation
        linkedin_adapter.navigate = MagicMock(return_value=True)
        
        # Mock successful element interactions
        mock_interaction.human_type.return_value = True
        mock_interaction.human_click.return_value = True
        mock_interaction.wait_for_navigation = MagicMock()
        
        # Mock job extraction
        linkedin_adapter._extract_job_listings = MagicMock(return_value=[
            {"id": "123", "title": "Software Engineer", "company": "Tech Co"},
            {"id": "456", "title": "Data Scientist", "company": "Data Inc"}
        ])
        
        # Call method
        results = linkedin_adapter.search_jobs({"keywords": "python developer", "location": "New York"})
        
        # Verify
        assert len(results) == 2
        assert results[0]["title"] == "Software Engineer"
        assert results[1]["company"] == "Data Inc"
        linkedin_adapter.navigate.assert_called_once_with("https://www.linkedin.com/jobs/")
        mock_interaction.human_type.assert_any_call(mock_page, linkedin_adapter.selectors.get("search_jobs_input"), "python developer")
        mock_interaction.human_type.assert_any_call(mock_page, linkedin_adapter.selectors.get("search_location_input"), "New York")
        mock_interaction.human_click.assert_called_once_with(mock_page, linkedin_adapter.selectors.get("search_submit"))
    
    @patch('automation.adapters.linkedin_adapter.interaction_handler')
    def test_extract_job_details(self, mock_interaction, linkedin_adapter, mock_page):
        """Test job details extraction."""
        # Setup
        linkedin_adapter._page = mock_page
        linkedin_adapter._logged_in = True
        
        # Mock successful navigation
        linkedin_adapter.navigate = MagicMock(return_value=True)
        
        # Mock successful element waiting
        mock_interaction.wait_for_element.return_value = True
        
        # Mock job detail elements
        def mock_query_selector(selector):
            elements = {
                linkedin_adapter.selectors.get("job_details_title"): MagicMock(inner_text=lambda: "Senior Python Developer"),
                linkedin_adapter.selectors.get("job_details_company"): MagicMock(inner_text=lambda: "Tech Company"),
                linkedin_adapter.selectors.get("job_details_location"): MagicMock(inner_text=lambda: "New York, NY"),
                linkedin_adapter.selectors.get("job_details_description"): MagicMock(inner_text=lambda: "Job description text"),
                linkedin_adapter.selectors.get("job_details_posted_date"): MagicMock(inner_text=lambda: "Posted 2 days ago"),
                linkedin_adapter.selectors.get("job_details_applicants"): MagicMock(inner_text=lambda: "25 applicants"),
                linkedin_adapter.selectors.get("easy_apply_button"): MagicMock()
            }
            return elements.get(selector)
        
        mock_page.query_selector.side_effect = mock_query_selector
        
        # Call method
        job_url = "https://www.linkedin.com/jobs/view/123456/"
        details = linkedin_adapter.extract_job_details(job_url)
        
        # Verify
        assert details["title"] == "Senior Python Developer"
        assert details["company"] == "Tech Company"
        assert details["location"] == "New York, NY"
        assert details["description"] == "Job description text"
        assert details["posted_date"] == "Posted 2 days ago"
        assert details["applicants"] == 25
        assert details["source_url"] == job_url
        assert details["source_website"] == "LinkedIn"
        assert details["easy_apply_available"] is True
    
    @patch('automation.adapters.linkedin_adapter.form_filler')
    @patch('automation.adapters.linkedin_adapter.interaction_handler')
    def test_apply_to_job(self, mock_interaction, mock_form_filler, linkedin_adapter, mock_page):
        """Test job application functionality."""
        # Setup
        linkedin_adapter._page = mock_page
        linkedin_adapter._logged_in = True
        
        # Mock successful navigation
        linkedin_adapter.navigate = MagicMock(return_value=True)
        
        # Mock Easy Apply button
        mock_page.query_selector.side_effect = lambda selector: MagicMock() if selector == linkedin_adapter.selectors.get("easy_apply_button") else None
        
        # Mock successful click
        mock_interaction.human_click.return_value = True
        
        # Mock application process
        linkedin_adapter._process_application_steps = MagicMock(return_value={
            "success": True,
            "message": "Application submitted successfully",
            "steps_completed": 3,
            "total_steps": 3,
            "fields_filled": 10
        })
        
        # Call method
        job_url = "https://www.linkedin.com/jobs/view/123456/"
        application_data = {
            "user_profile": {"name": "John Doe"},
            "job_context": MagicMock()
        }
        result = linkedin_adapter.apply_to_job(job_url, application_data)
        
        # Verify
        assert result["success"] is True
        assert result["message"] == "Application submitted successfully"
        assert result["steps_completed"] == 3
        linkedin_adapter.navigate.assert_called_once_with(job_url)
        mock_interaction.human_click.assert_called_once_with(mock_page, linkedin_adapter.selectors.get("easy_apply_button"))
        linkedin_adapter._process_application_steps.assert_called_once_with(mock_page, application_data)
    
    def test_extract_job_listings(self, linkedin_adapter, mock_page, mock_element):
        """Test job listings extraction from search results."""
        # Setup
        # Mock job cards
        job_card1 = MagicMock()
        job_link1 = MagicMock()
        job_link1.get_attribute.return_value = "/jobs/view/123/"
        job_card1.query_selector.side_effect = lambda selector: {
            "a.job-card-list__title": job_link1,
            linkedin_adapter.selectors.get("job_title"): MagicMock(inner_text=lambda: "Python Developer"),
            linkedin_adapter.selectors.get("job_company"): MagicMock(inner_text=lambda: "Tech Co"),
            linkedin_adapter.selectors.get("job_location"): MagicMock(inner_text=lambda: "New York, NY"),
            linkedin_adapter.selectors.get("job_description"): MagicMock(inner_text=lambda: "Great job opportunity"),
            linkedin_adapter.selectors.get("job_posted_date"): MagicMock(inner_text=lambda: "1 day ago")
        }.get(selector)
        
        job_card2 = MagicMock()
        job_link2 = MagicMock()
        job_link2.get_attribute.return_value = "/jobs/view/456/"
        job_card2.query_selector.side_effect = lambda selector: {
            "a.job-card-list__title": job_link2,
            linkedin_adapter.selectors.get("job_title"): MagicMock(inner_text=lambda: "Data Scientist"),
            linkedin_adapter.selectors.get("job_company"): MagicMock(inner_text=lambda: "Data Inc"),
            linkedin_adapter.selectors.get("job_location"): MagicMock(inner_text=lambda: "Remote"),
            linkedin_adapter.selectors.get("job_description"): MagicMock(inner_text=lambda: "Data science position"),
            linkedin_adapter.selectors.get("job_posted_date"): MagicMock(inner_text=lambda: "2 days ago")
        }.get(selector)
        
        mock_page.query_selector_all.return_value = [job_card1, job_card2]
        
        # Call method
        results = linkedin_adapter._extract_job_listings(mock_page)
        
        # Verify
        assert len(results) == 2
        assert results[0]["id"] == "123"
        assert results[0]["title"] == "Python Developer"
        assert results[0]["company"] == "Tech Co"
        assert results[1]["id"] == "456"
        assert results[1]["title"] == "Data Scientist"
        assert results[1]["source_website"] == "LinkedIn"


if __name__ == "__main__":
    pytest.main(["-xvs", "test_linkedin_adapter.py"])