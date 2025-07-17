"""
LinkedIn adapter for job search and application automation.

This module provides a LinkedIn-specific adapter for automating job searches
and application submissions on the LinkedIn platform.
"""
import os
import re
import json
import logging
import time
import random
from typing import Dict, List, Optional, Tuple, Any, Union
from urllib.parse import urlparse, parse_qs
from playwright.sync_api import Page, ElementHandle, TimeoutError

from automation.adapters.base_adapter import WebsiteAdapter, AdapterConfig, SelectorConfig
from automation.playwright_engine.interaction_handler import interaction_handler
from automation.playwright_engine.screenshot_manager import screenshot_manager
from automation.playwright_engine.error_handler import error_handler, AutomationError
from automation.form_filler import form_filler
from services.encryption_service import encryption_service

# Set up logging
logger = logging.getLogger(__name__)


class LinkedInAdapter(WebsiteAdapter):
    """LinkedIn-specific adapter for job search and application automation."""
    
    def __init__(self, app=None):
        """Initialize LinkedInAdapter instance.
        
        Args:
            app: Flask application instance for configuration
        """
        # Define LinkedIn-specific selectors
        selectors = SelectorConfig({
            # Login selectors
            "login_button": "a.nav__button-secondary",
            "username_field": "#username",
            "password_field": "#password",
            "submit_login": "button[type='submit']",
            "login_error": ".alert-content",
            "remember_prompt": ".remember-me-prompt__text",
            
            # Job search selectors
            "search_jobs_input": ".jobs-search-box__text-input",
            "search_location_input": ".jobs-search-box__location-input",
            "search_submit": "button.jobs-search-box__submit-button",
            "job_card": ".job-card-container",
            "job_title": ".job-card-list__title",
            "job_company": ".job-card-container__company-name",
            "job_location": ".job-card-container__metadata-item",
            "job_description": ".job-card-list__description",
            "job_posted_date": ".job-card-container__listed-time",
            
            # Job details selectors
            "job_details_title": ".jobs-unified-top-card__job-title",
            "job_details_company": ".jobs-unified-top-card__company-name",
            "job_details_location": ".jobs-unified-top-card__bullet",
            "job_details_description": ".jobs-description-content",
            "job_details_posted_date": ".jobs-unified-top-card__posted-date",
            "job_details_applicants": ".jobs-unified-top-card__applicant-count",
            
            # Easy Apply selectors
            "easy_apply_button": ".jobs-apply-button",
            "next_button": "button[aria-label='Continue to next step']",
            "review_button": "button[aria-label='Review your application']",
            "submit_application_button": "button[aria-label='Submit application']",
            "form_field": ".fb-dash-form-element",
            "form_error": ".artdeco-inline-feedback--error",
            "application_success": ".artdeco-modal__header h2",
            
            # Navigation selectors
            "jobs_tab": "a[href='/jobs/']",
            "my_jobs_tab": "a[href='/my-items/saved-jobs/']",
            "applied_jobs_tab": "a[href='/my-items/jobs-applied/']",
            
            # Pagination selectors
            "pagination_next": "button.artdeco-pagination__button--next",
            "pagination_prev": "button.artdeco-pagination__button--previous",
            "pagination_page": ".artdeco-pagination__indicator--number button"
        })
        
        # Create adapter configuration
        config = AdapterConfig(
            name="linkedin",
            base_url="https://www.linkedin.com",
            selectors=selectors,
            login_required=True,
            rate_limit_delay=3000,  # 3 seconds between actions
            max_retries=3,
            timeout=30000  # 30 seconds
        )
        
        # Initialize the base adapter
        super().__init__(config, app)
    
    def login(self, credentials: Dict[str, str]) -> bool:
        """Login to LinkedIn.
        
        Args:
            credentials: Dictionary with login credentials (username, password)
            
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            # Check if already logged in
            if self._logged_in:
                logger.info("Already logged in to LinkedIn")
                return True
            
            # Navigate to LinkedIn login page
            if not self.navigate(f"{self.base_url}/login"):
                logger.error("Failed to navigate to LinkedIn login page")
                return False
            
            # Get page
            page = self.get_page()
            
            # Wait for login form
            username_selector = self.selectors.get("username_field")
            if not interaction_handler.wait_for_element(page, username_selector):
                logger.error("Login form not found")
                return False
            
            # Enter username
            if not interaction_handler.human_type(page, username_selector, credentials.get("username", "")):
                logger.error("Failed to enter username")
                return False
            
            # Enter password
            password_selector = self.selectors.get("password_field")
            if not interaction_handler.human_type(page, password_selector, credentials.get("password", "")):
                logger.error("Failed to enter password")
                return False
            
            # Click login button
            submit_selector = self.selectors.get("submit_login")
            if not interaction_handler.human_click(page, submit_selector):
                logger.error("Failed to click login button")
                return False
            
            # Wait for navigation
            interaction_handler.wait_for_navigation(page)
            
            # Check for login errors
            error_selector = self.selectors.get("login_error")
            if page.query_selector(error_selector):
                error_text = page.query_selector(error_selector).inner_text()
                logger.error(f"Login error: {error_text}")
                return False
            
            # Check for remember device prompt and handle it
            remember_selector = self.selectors.get("remember_prompt")
            if page.query_selector(remember_selector):
                logger.info("Handling remember device prompt")
                # Click "Not now" or similar button (adjust selector as needed)
                page.click("button.secondary-action")
                interaction_handler.wait_for_navigation(page)
            
            # Verify login success by checking for elements that should be present after login
            if page.query_selector("div.feed-identity-module"):
                logger.info("Successfully logged in to LinkedIn")
                self._logged_in = True
                return True
            else:
                logger.error("Login verification failed")
                return False
                
        except Exception as e:
            error = error_handler.handle_error(e, {"action": "login"})
            logger.error(f"Login error: {str(error)}")
            screenshot_manager.capture_on_error(self.get_page(), error)
            return False
    
    def search_jobs(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for jobs on LinkedIn based on criteria.
        
        Args:
            criteria: Dictionary of search criteria (keywords, location, etc.)
            
        Returns:
            List[Dict[str, Any]]: List of job listings
        """
        try:
            # Ensure logged in
            if not self._logged_in:
                logger.error("Must be logged in to search jobs")
                return []
            
            # Navigate to jobs page
            if not self.navigate(f"{self.base_url}/jobs/"):
                logger.error("Failed to navigate to jobs page")
                return []
            
            # Get page
            page = self.get_page()
            
            # Enter search keywords
            keywords = criteria.get("keywords", "")
            search_input_selector = self.selectors.get("search_jobs_input")
            if not interaction_handler.human_type(page, search_input_selector, keywords):
                logger.error("Failed to enter search keywords")
                return []
            
            # Enter location
            location = criteria.get("location", "")
            location_input_selector = self.selectors.get("search_location_input")
            if location and not interaction_handler.human_type(page, location_input_selector, location):
                logger.error("Failed to enter location")
                return []
            
            # Click search button
            search_button_selector = self.selectors.get("search_submit")
            if not interaction_handler.human_click(page, search_button_selector):
                logger.error("Failed to click search button")
                return []
            
            # Wait for search results
            interaction_handler.wait_for_navigation(page)
            
            # Apply additional filters if provided
            if criteria.get("filters"):
                self._apply_search_filters(page, criteria.get("filters", {}))
            
            # Extract job listings
            job_listings = []
            max_pages = criteria.get("max_pages", 1)
            max_jobs = criteria.get("max_jobs", 25)
            
            for page_num in range(max_pages):
                # Extract jobs from current page
                page_listings = self._extract_job_listings(page)
                job_listings.extend(page_listings)
                
                # Check if we have enough jobs
                if len(job_listings) >= max_jobs:
                    job_listings = job_listings[:max_jobs]
                    break
                
                # Go to next page if available
                if page_num < max_pages - 1:
                    next_button_selector = self.selectors.get("pagination_next")
                    if page.query_selector(next_button_selector):
                        if not interaction_handler.human_click(page, next_button_selector):
                            logger.error("Failed to click next page button")
                            break
                        interaction_handler.wait_for_navigation(page)
                    else:
                        # No more pages
                        break
            
            logger.info(f"Found {len(job_listings)} job listings")
            return job_listings
            
        except Exception as e:
            error = error_handler.handle_error(e, {"action": "search_jobs"})
            logger.error(f"Job search error: {str(error)}")
            screenshot_manager.capture_on_error(self.get_page(), error)
            return []
    
    def extract_job_details(self, job_url: str) -> Dict[str, Any]:
        """Extract detailed information about a job.
        
        Args:
            job_url: URL of the job listing
            
        Returns:
            Dict[str, Any]: Job details
        """
        try:
            # Ensure logged in
            if not self._logged_in:
                logger.error("Must be logged in to extract job details")
                return {}
            
            # Navigate to job page
            if not self.navigate(job_url):
                logger.error(f"Failed to navigate to job URL: {job_url}")
                return {}
            
            # Get page
            page = self.get_page()
            
            # Wait for job details to load
            title_selector = self.selectors.get("job_details_title")
            if not interaction_handler.wait_for_element(page, title_selector):
                logger.error("Job details not found")
                return {}
            
            # Extract job details
            job_details = {}
            
            # Extract title
            title_element = page.query_selector(title_selector)
            if title_element:
                job_details["title"] = title_element.inner_text().strip()
            
            # Extract company
            company_selector = self.selectors.get("job_details_company")
            company_element = page.query_selector(company_selector)
            if company_element:
                job_details["company"] = company_element.inner_text().strip()
            
            # Extract location
            location_selector = self.selectors.get("job_details_location")
            location_element = page.query_selector(location_selector)
            if location_element:
                job_details["location"] = location_element.inner_text().strip()
            
            # Extract description
            description_selector = self.selectors.get("job_details_description")
            description_element = page.query_selector(description_selector)
            if description_element:
                job_details["description"] = description_element.inner_text().strip()
            
            # Extract posted date
            posted_date_selector = self.selectors.get("job_details_posted_date")
            posted_date_element = page.query_selector(posted_date_selector)
            if posted_date_element:
                job_details["posted_date"] = posted_date_element.inner_text().strip()
            
            # Extract applicant count
            applicants_selector = self.selectors.get("job_details_applicants")
            applicants_element = page.query_selector(applicants_selector)
            if applicants_element:
                applicants_text = applicants_element.inner_text().strip()
                # Extract number from text like "25 applicants"
                applicants_match = re.search(r'(\d+)', applicants_text)
                if applicants_match:
                    job_details["applicants"] = int(applicants_match.group(1))
            
            # Add source URL
            job_details["source_url"] = job_url
            job_details["source_website"] = "LinkedIn"
            
            # Check if Easy Apply is available
            easy_apply_selector = self.selectors.get("easy_apply_button")
            job_details["easy_apply_available"] = bool(page.query_selector(easy_apply_selector))
            
            return job_details
            
        except Exception as e:
            error = error_handler.handle_error(e, {"action": "extract_job_details", "url": job_url})
            logger.error(f"Job details extraction error: {str(error)}")
            screenshot_manager.capture_on_error(self.get_page(), error)
            return {}
    
    def apply_to_job(self, job_url: str, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply to a job on LinkedIn.
        
        Args:
            job_url: URL of the job listing
            application_data: Dictionary of application data
            
        Returns:
            Dict[str, Any]: Application result
        """
        try:
            # Ensure logged in
            if not self._logged_in:
                logger.error("Must be logged in to apply to jobs")
                return {"success": False, "message": "Not logged in"}
            
            # Navigate to job page
            if not self.navigate(job_url):
                logger.error(f"Failed to navigate to job URL: {job_url}")
                return {"success": False, "message": "Failed to navigate to job page"}
            
            # Get page
            page = self.get_page()
            
            # Check if Easy Apply is available
            easy_apply_selector = self.selectors.get("easy_apply_button")
            if not page.query_selector(easy_apply_selector):
                logger.error("Easy Apply not available for this job")
                return {"success": False, "message": "Easy Apply not available"}
            
            # Click Easy Apply button
            if not interaction_handler.human_click(page, easy_apply_selector):
                logger.error("Failed to click Easy Apply button")
                return {"success": False, "message": "Failed to start application"}
            
            # Wait for application form to load
            time.sleep(random.uniform(1.0, 2.0))
            
            # Process application steps
            result = self._process_application_steps(page, application_data)
            
            return result
            
        except Exception as e:
            error = error_handler.handle_error(e, {"action": "apply_to_job", "url": job_url})
            logger.error(f"Job application error: {str(error)}")
            screenshot_manager.capture_on_error(self.get_page(), error)
            return {"success": False, "message": f"Application error: {str(error)}"}
    
    def _extract_job_listings(self, page: Page) -> List[Dict[str, Any]]:
        """Extract job listings from search results page.
        
        Args:
            page: Playwright page
            
        Returns:
            List[Dict[str, Any]]: List of job listings
        """
        job_listings = []
        
        try:
            # Get all job cards
            job_card_selector = self.selectors.get("job_card")
            job_cards = page.query_selector_all(job_card_selector)
            
            for card in job_cards:
                job = {}
                
                # Extract job ID from data attribute or URL
                job_id = None
                job_link = card.query_selector("a.job-card-list__title")
                if job_link:
                    href = job_link.get_attribute("href")
                    if href:
                        # Extract job ID from URL
                        url_parts = urlparse(href)
                        path_parts = url_parts.path.split("/")
                        if len(path_parts) > 2:
                            job_id = path_parts[-1]
                
                if not job_id:
                    # Try to get from data attribute
                    job_id = card.get_attribute("data-job-id")
                
                if not job_id:
                    # Skip if no job ID found
                    continue
                
                job["id"] = job_id
                
                # Extract job title
                title_selector = self.selectors.get("job_title")
                title_element = card.query_selector(title_selector)
                if title_element:
                    job["title"] = title_element.inner_text().strip()
                
                # Extract company name
                company_selector = self.selectors.get("job_company")
                company_element = card.query_selector(company_selector)
                if company_element:
                    job["company"] = company_element.inner_text().strip()
                
                # Extract location
                location_selector = self.selectors.get("job_location")
                location_element = card.query_selector(location_selector)
                if location_element:
                    job["location"] = location_element.inner_text().strip()
                
                # Extract description snippet
                description_selector = self.selectors.get("job_description")
                description_element = card.query_selector(description_selector)
                if description_element:
                    job["description_snippet"] = description_element.inner_text().strip()
                
                # Extract posted date
                posted_date_selector = self.selectors.get("job_posted_date")
                posted_date_element = card.query_selector(posted_date_selector)
                if posted_date_element:
                    job["posted_date"] = posted_date_element.inner_text().strip()
                
                # Add source information
                job["source_website"] = "LinkedIn"
                job["source_url"] = f"{self.base_url}/jobs/view/{job_id}/"
                
                # Add to list
                job_listings.append(job)
            
            return job_listings
            
        except Exception as e:
            logger.error(f"Error extracting job listings: {str(e)}")
            return job_listings
    
    def _apply_search_filters(self, page: Page, filters: Dict[str, Any]) -> bool:
        """Apply additional search filters.
        
        Args:
            page: Playwright page
            filters: Dictionary of filters to apply
            
        Returns:
            bool: True if filters applied successfully, False otherwise
        """
        try:
            # Apply anti-detection measures before interacting with filters
            self._apply_anti_detection_measures(page)
            
            # Apply date posted filter
            if "date_posted" in filters:
                date_value = filters["date_posted"]
                date_selector = f"button[aria-label='Date posted filter. {date_value} filter is selected.']"
                
                # Click the filter dropdown
                if not interaction_handler.human_click(page, date_selector):
                    # Try alternative selector
                    date_selector = "button[aria-label='Date posted filter.']"
                    if not interaction_handler.human_click(page, date_selector):
                        logger.error("Failed to click date posted filter")
                        return False
                
                # Wait for dropdown to appear with variable delay
                self._add_random_delay(500, 1500)
                
                # Click the specific option
                option_selector = f"label[for*='{date_value.lower().replace(' ', '-')}']"
                if not interaction_handler.human_click(page, option_selector):
                    logger.error(f"Failed to select date option: {date_value}")
                    return False
                
                # Wait for results to update with variable delay
                self._add_random_delay(1000, 3000)
                
                # Apply rate limiting between filter operations
                self._apply_rate_limiting()
            
            # Apply experience level filter
            if "experience_level" in filters:
                exp_value = filters["experience_level"]
                exp_selector = f"button[aria-label='Experience level filter.']"
                
                # Click the filter dropdown
                if not interaction_handler.human_click(page, exp_selector):
                    logger.error("Failed to click experience level filter")
                    return False
                
                # Wait for dropdown to appear with variable delay
                self._add_random_delay(500, 1500)
                
                # Click the specific option
                option_selector = f"label[for*='{exp_value.lower().replace(' ', '-')}']"
                if not interaction_handler.human_click(page, option_selector):
                    logger.error(f"Failed to select experience option: {exp_value}")
                    return False
                
                # Wait for results to update with variable delay
                self._add_random_delay(1000, 3000)
                
                # Apply rate limiting between filter operations
                self._apply_rate_limiting()
            
            # Apply job type filter
            if "job_type" in filters:
                job_type = filters["job_type"]
                type_selector = f"button[aria-label='Job type filter.']"
                
                # Click the filter dropdown
                if not interaction_handler.human_click(page, type_selector):
                    logger.error("Failed to click job type filter")
                    return False
                
                # Wait for dropdown to appear with variable delay
                self._add_random_delay(500, 1500)
                
                # Click the specific option
                option_selector = f"label[for*='{job_type.lower().replace(' ', '-')}']"
                if not interaction_handler.human_click(page, option_selector):
                    logger.error(f"Failed to select job type option: {job_type}")
                    return False
                
                # Wait for results to update with variable delay
                self._add_random_delay(1000, 3000)
            
            # Apply final anti-detection measures after all filters
            self._apply_anti_detection_measures(page)
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying search filters: {str(e)}")
            return False
    
    def _process_application_steps(self, page: Page, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process LinkedIn Easy Apply application steps.
        
        Args:
            page: Playwright page
            application_data: Dictionary of application data
            
        Returns:
            Dict[str, Any]: Application result
        """
        try:
            # Initialize result
            result = {
                "success": False,
                "message": "",
                "steps_completed": 0,
                "total_steps": 0,
                "fields_filled": 0
            }
            
            # Get job context for AI responses
            job_context = application_data.get("job_context")
            user_profile = application_data.get("user_profile", {})
            
            # Process application steps
            step_count = 0
            max_steps = 10  # Safety limit
            
            while step_count < max_steps:
                step_count += 1
                
                # Take screenshot for debugging
                screenshot_manager.take_screenshot(page, f"linkedin_apply_step_{step_count}")
                
                # Check if we're on the final submission page
                submit_button_selector = self.selectors.get("submit_application_button")
                if page.query_selector(submit_button_selector):
                    logger.info("On final submission page")
                    
                    # Click submit button
                    if interaction_handler.human_click(page, submit_button_selector):
                        # Wait for confirmation
                        time.sleep(random.uniform(2.0, 3.0))
                        
                        # Check for success message
                        success_selector = self.selectors.get("application_success")
                        success_element = page.query_selector(success_selector)
                        
                        if success_element and "application submitted" in success_element.inner_text().lower():
                            result["success"] = True
                            result["message"] = "Application submitted successfully"
                        else:
                            result["message"] = "Submission completed but confirmation not found"
                    else:
                        result["message"] = "Failed to click submit button"
                    
                    # Set final results
                    result["steps_completed"] = step_count
                    result["total_steps"] = step_count
                    break
                
                # Check if we're on the review page
                review_button_selector = self.selectors.get("review_button")
                if page.query_selector(review_button_selector):
                    logger.info("On review page")
                    
                    # Click review button
                    if not interaction_handler.human_click(page, review_button_selector):
                        result["message"] = "Failed to click review button"
                        break
                    
                    # Wait for next page
                    time.sleep(random.uniform(1.0, 2.0))
                    continue
                
                # Detect form fields on current page
                form_fields = form_filler.detect_form_fields(page)
                
                if form_fields:
                    logger.info(f"Found {len(form_fields)} form fields on step {step_count}")
                    
                    # Fill form fields
                    if form_filler.fill_form(page, form_fields, user_profile, job_context):
                        result["fields_filled"] += len(form_fields)
                    else:
                        logger.warning("Some fields could not be filled")
                
                # Check for form errors
                error_selector = self.selectors.get("form_error")
                error_elements = page.query_selector_all(error_selector)
                
                if error_elements:
                    error_messages = [elem.inner_text().strip() for elem in error_elements]
                    logger.warning(f"Form errors: {', '.join(error_messages)}")
                    
                    # Try to fix errors (basic implementation)
                    # This could be expanded with more sophisticated error handling
                
                # Click next button
                next_button_selector = self.selectors.get("next_button")
                if not page.query_selector(next_button_selector):
                    result["message"] = "No next button found, application flow may be incomplete"
                    break
                
                if not interaction_handler.human_click(page, next_button_selector):
                    result["message"] = "Failed to click next button"
                    break
                
                # Wait for next page
                time.sleep(random.uniform(1.0, 2.0))
            
            # If we reached max steps without completing
            if step_count >= max_steps and not result["success"]:
                result["message"] = "Application has too many steps, stopped for safety"
            
            # Set final counts if not already set
            if not result["total_steps"]:
                result["total_steps"] = step_count
                result["steps_completed"] = step_count
            
            return result
            
        except Exception as e:
            logger.error(f"Error processing application steps: {str(e)}")
            return {
                "success": False,
                "message": f"Application error: {str(e)}",
                "steps_completed": 0,
                "total_steps": 0,
                "fields_filled": 0
            }


# Create a singleton instance
linkedin_adapter = LinkedInAdapter()