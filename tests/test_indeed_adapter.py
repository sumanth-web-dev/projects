"""
Tests for the Indeed adapter.
"""
import pytest
import os
from unittest.mock import MagicMock, patch
from playwright.sync_api import Page, ElementHandle

from automation.adapters.indeed_adapter import IndeedAdapter
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
def indeed_adapter():
    """Create an Indeed adapter instance for testing."""
    adapter = IndeedAdapter()
    # Mock the browser context and page
    adapter._context = MagicMock()
    adapter._page = MagicMock()
    return adapter


class TestIndeedAdapter:
    """Test suite for Indeed adapter."""
    
    def test_init(self):
        """Test adapter initialization."""
        adapter = IndeedAdapter()
        
        # Check basic properties
        assert adapter.name == "indeed"
        assert adapter.base_url == "https://www.indeed.com"
        assert adapter.login_required is True
        
        # Check selectors
        assert isinstance(adapter.selectors, SelectorConfig)
        assert "login_button" in adapter.selectors.selectors
        assert "indeed_apply_button" in adapter.selectors.selectors
    
    @patch('automation.adapters.base_adapter.browser_manager')
    def test_get_page(self, mock_browser_manager, indeed_adapter):
        """Test get_page method."""
        # Reset page to None to test get_page
        indeed_adapter._page = None
        
        # Setup mock
        mock_browser_manager.get_page.return_value = MagicMock()
        
        # Call method
        page = indeed_adapter.get_page()
        
        # Verify
        assert page is not None
        mock_browser_manager.get_page.assert_called_once_with("indeed_context")
    
    @patch('automation.playwright_engine.interaction_handler.interaction_handler')
    def test_login(self, mock_interaction, indeed_adapter, mock_page):
        """Test login method."""
        # Setup
        indeed_adapter._page = mock_page
        indeed_adapter._logged_in = False
        
        # Mock successful navigation
        indeed_adapter.navigate = MagicMock(return_value=True)
        
        # Mock successful element interactions
        mock_interaction.wait_for_element.return_value = True
        mock_interaction.human_type.return_value = True
        mock_interaction.human_click.return_value = True
        mock_interaction.wait_for_navigation = MagicMock()
        
        # Mock successful login verification
        mock_page.query_selector.side_effect = lambda selector: MagicMock() if selector == "a[href='/my/myjobs']" else None
        
        # Call method
        result = indeed_adapter.login({"email": "test@example.com", "password": "password123"})
        
        # Verify
        assert result is True
        assert indeed_adapter._logged_in is True
        indeed_adapter.navigate.assert_called_once_with("https://www.indeed.com/account/login")
        mock_interaction.human_type.assert_any_call(mock_page, indeed_adapter.selectors.get("email_field"), "test@example.com")
        mock_interaction.human_type.assert_any_call(mock_page, indeed_adapter.selectors.get("password_field"), "password123")
        mock_interaction.human_click.assert_any_call(mock_page, "button[type='submit']")
    
    @patch('automation.playwright_engine.interaction_handler.interaction_handler')
    def test_login_failure(self, mock_interaction, indeed_adapter, mock_page):
        """Test login failure handling."""
        # Setup
        indeed_adapter._page = mock_page
        indeed_adapter._logged_in = False
        
        # Mock successful navigation
        indeed_adapter.navigate = MagicMock(return_value=True)
        
        # Mock successful element interactions
        mock_interaction.wait_for_element.return_value = True
        mock_interaction.human_type.return_value = True
        mock_interaction.human_click.return_value = True
        mock_interaction.wait_for_navigation = MagicMock()
        
        # Mock login error
        error_element = MagicMock()
        error_element.inner_text.return_value = "Incorrect password"
        mock_page.query_selector.side_effect = lambda selector: error_element if selector == indeed_adapter.selectors.get("login_error") else None
        
        # Call method
        result = indeed_adapter.login({"email": "test@example.com", "password": "wrong_password"})
        
        # Verify
        assert result is False
        assert indeed_adapter._logged_in is False
    
    @patch('automation.playwright_engine.interaction_handler.interaction_handler')
    def test_search_jobs(self, mock_interaction, indeed_adapter, mock_page):
        """Test job search functionality."""
        # Setup
        indeed_adapter._page = mock_page
        
        # Mock successful navigation
        indeed_adapter.navigate = MagicMock(return_value=True)
        
        # Mock successful element interactions
        mock_interaction.human_type.return_value = True
        mock_interaction.human_click.return_value = True
        mock_interaction.wait_for_navigation = MagicMock()
        
        # Mock job extraction
        indeed_adapter._extract_job_listings = MagicMock(return_value=[
            {"id": "123", "title": "Software Engineer", "company": "Tech Co"},
            {"id": "456", "title": "Data Scientist", "company": "Data Inc"}
        ])
        
        # Call method
        results = indeed_adapter.search_jobs({"keywords": "python developer", "location": "New York"})
        
        # Verify
        assert len(results) == 2
        assert results[0]["title"] == "Software Engineer"
        assert results[1]["company"] == "Data Inc"
        indeed_adapter.navigate.assert_called_once_with("https://www.indeed.com/")
        mock_interaction.human_type.assert_any_call(mock_page, indeed_adapter.selectors.get("search_jobs_input"), "python developer")
        mock_interaction.human_type.assert_any_call(mock_page, indeed_adapter.selectors.get("search_location_input"), "New York")
        mock_interaction.human_click.assert_called_once_with(mock_page, indeed_adapter.selectors.get("search_submit"))
    
    @patch('automation.playwright_engine.interaction_handler.interaction_handler')
    def test_extract_job_details(self, mock_interaction, indeed_adapter, mock_page):
        """Test job details extraction."""
        # Setup
        indeed_adapter._page = mock_page
        
        # Mock successful navigation
        indeed_adapter.navigate = MagicMock(return_value=True)
        
        # Mock successful element waiting
        mock_interaction.wait_for_element.return_value = True
        
        # Mock job detail elements
        def mock_query_selector(selector):
            elements = {
                indeed_adapter.selectors.get("job_details_title"): MagicMock(inner_text=lambda: "Senior Python Developer"),
                indeed_adapter.selectors.get("job_details_company"): MagicMock(inner_text=lambda: "Tech Company"),
                indeed_adapter.selectors.get("job_details_location"): MagicMock(inner_text=lambda: "New York, NY"),
                indeed_adapter.selectors.get("job_details_description"): MagicMock(inner_text=lambda: "Job description text"),
                indeed_adapter.selectors.get("job_details_posted_date"): MagicMock(inner_text=lambda: "Posted 2 days ago"),
                indeed_adapter.selectors.get("job_details_salary"): MagicMock(inner_text=lambda: "$100,000 - $120,000 a year"),
                indeed_adapter.selectors.get("indeed_apply_button"): MagicMock()
            }
            return elements.get(selector)
        
        mock_page.query_selector.side_effect = mock_query_selector
        
        # Call method
        job_url = "https://www.indeed.com/viewjob?jk=123456"
        details = indeed_adapter.extract_job_details(job_url)
        
        # Verify
        assert details["title"] == "Senior Python Developer"
        assert details["company"] == "Tech Company"
        assert details["location"] == "New York, NY"
        assert details["description"] == "Job description text"
        assert details["posted_date"] == "2 days ago"
        assert details["salary"] == "$100,000 - $120,000 a year"
        assert details["source_url"] == job_url
        assert details["source_website"] == "Indeed"
        assert details["indeed_apply_available"] is True
    
    @patch('automation.form_filler.form_filler')
    @patch('automation.playwright_engine.interaction_handler.interaction_handler')
    def test_apply_to_job_indeed_apply(self, mock_interaction, mock_form_filler, indeed_adapter, mock_page):
        """Test job application functionality with Indeed Apply."""
        # Setup
        indeed_adapter._page = mock_page
        indeed_adapter._logged_in = True
        
        # Mock successful navigation
        indeed_adapter.navigate = MagicMock(return_value=True)
        
        # Mock Indeed Apply button
        mock_page.query_selector.side_effect = lambda selector: MagicMock() if selector == indeed_adapter.selectors.get("indeed_apply_button") else None
        
        # Mock successful click
        mock_interaction.human_click.return_value = True
        
        # Mock application process
        indeed_adapter._apply_with_indeed_apply = MagicMock(return_value={
            "success": True,
            "message": "Application submitted successfully",
            "steps_completed": 3,
            "total_steps": 3,
            "fields_filled": 10,
            "application_type": "indeed_apply"
        })
        
        # Call method
        job_url = "https://www.indeed.com/viewjob?jk=123456"
        application_data = {
            "user_profile": {"name": "John Doe"},
            "job_context": MagicMock()
        }
        result = indeed_adapter.apply_to_job(job_url, application_data)
        
        # Verify
        assert result["success"] is True
        assert result["message"] == "Application submitted successfully"
        assert result["steps_completed"] == 3
        assert result["application_type"] == "indeed_apply"
        indeed_adapter.navigate.assert_called_once_with(job_url)
        indeed_adapter._apply_with_indeed_apply.assert_called_once_with(mock_page, application_data)
    
    @patch('automation.form_filler.form_filler')
    @patch('automation.playwright_engine.interaction_handler.interaction_handler')
    def test_apply_to_job_external_apply(self, mock_interaction, mock_form_filler, indeed_adapter, mock_page):
        """Test job application functionality with External Apply."""
        # Setup
        indeed_adapter._page = mock_page
        indeed_adapter._logged_in = True
        
        # Mock successful navigation
        indeed_adapter.navigate = MagicMock(return_value=True)
        
        # Mock External Apply button (no Indeed Apply button)
        def mock_query_selector(selector):
            if selector == indeed_adapter.selectors.get("external_apply_button"):
                return MagicMock()
            elif selector == indeed_adapter.selectors.get("indeed_apply_button"):
                return None
            return None
        
        mock_page.query_selector.side_effect = mock_query_selector
        
        # Mock successful click
        mock_interaction.human_click.return_value = True
        
        # Mock application process
        indeed_adapter._apply_with_external_link = MagicMock(return_value={
            "success": True,
            "message": "External application link opened successfully",
            "external_url": "https://example.com/careers/apply",
            "application_type": "external_apply"
        })
        
        # Call method
        job_url = "https://www.indeed.com/viewjob?jk=123456"
        application_data = {
            "user_profile": {"name": "John Doe"},
            "job_context": MagicMock()
        }
        result = indeed_adapter.apply_to_job(job_url, application_data)
        
        # Verify
        assert result["success"] is True
        assert result["message"] == "External application link opened successfully"
        assert result["external_url"] == "https://example.com/careers/apply"
        assert result["application_type"] == "external_apply"
        indeed_adapter.navigate.assert_called_once_with(job_url)
        indeed_adapter._apply_with_external_link.assert_called_once_with(mock_page, application_data)
    
    def test_extract_job_listings(self, indeed_adapter, mock_page, mock_element):
        """Test job listings extraction from search results."""
        # Setup
        # Mock job cards
        job_card1 = MagicMock()
        job_link1 = MagicMock()
        job_link1.get_attribute.return_value = "/viewjob?jk=123abc"
        job_card1.query_selector.side_effect = lambda selector: {
            "a.jcs-JobTitle": job_link1,
            indeed_adapter.selectors.get("job_title"): MagicMock(inner_text=lambda: "Python Developer"),
            indeed_adapter.selectors.get("job_company"): MagicMock(inner_text=lambda: "Tech Co"),
            indeed_adapter.selectors.get("job_location"): MagicMock(inner_text=lambda: "New York, NY"),
            indeed_adapter.selectors.get("job_description_snippet"): MagicMock(inner_text=lambda: "Great job opportunity"),
            indeed_adapter.selectors.get("job_posted_date"): MagicMock(inner_text=lambda: "1 day ago"),
            indeed_adapter.selectors.get("job_salary"): MagicMock(inner_text=lambda: "$100K-$120K")
        }.get(selector)
        
        job_card2 = MagicMock()
        job_link2 = MagicMock()
        job_link2.get_attribute.return_value = "/viewjob?jk=456def"
        job_card2.query_selector.side_effect = lambda selector: {
            "a.jcs-JobTitle": job_link2,
            indeed_adapter.selectors.get("job_title"): MagicMock(inner_text=lambda: "Data Scientist"),
            indeed_adapter.selectors.get("job_company"): MagicMock(inner_text=lambda: "Data Inc"),
            indeed_adapter.selectors.get("job_location"): MagicMock(inner_text=lambda: "Remote"),
            indeed_adapter.selectors.get("job_description_snippet"): MagicMock(inner_text=lambda: "Data science position"),
            indeed_adapter.selectors.get("job_posted_date"): MagicMock(inner_text=lambda: "2 days ago"),
            indeed_adapter.selectors.get("job_salary"): None
        }.get(selector)
        
        mock_page.query_selector_all.return_value = [job_card1, job_card2]
        
        # Call method
        results = indeed_adapter._extract_job_listings(mock_page)
        
        # Verify
        assert len(results) == 2
        assert results[0]["id"] == "123abc"
        assert results[0]["title"] == "Python Developer"
        assert results[0]["company"] == "Tech Co"
        assert results[0]["salary"] == "$100K-$120K"
        assert results[1]["id"] == "456def"
        assert results[1]["title"] == "Data Scientist"
        assert results[1]["source_website"] == "Indeed"


if __name__ == "__main__":
    pytest.main(["-xvs", "test_indeed_adapter.py"])