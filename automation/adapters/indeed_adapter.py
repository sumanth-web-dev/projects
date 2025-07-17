"""
Indeed adapter for job search and application automation.

This module provides an Indeed-specific adapter for automating job searches
and application submissions on the Indeed platform.
"""
import os
import re
import json
import logging
import time
import random
from typing import Dict, List, Optional, Tuple, Any, Union
from urllib.parse import urlparse, parse_qs, urlencode
from playwright.sync_api import Page, ElementHandle, TimeoutError

from automation.adapters.base_adapter import WebsiteAdapter, AdapterConfig, SelectorConfig
from automation.playwright_engine.interaction_handler import interaction_handler
from automation.playwright_engine.screenshot_manager import screenshot_manager
from automation.playwright_engine.error_handler import error_handler, AutomationError
from automation.form_filler import form_filler
from services.encryption_service import encryption_service

# Set up logging
logger = logging.getLogger(__name__)


class IndeedAdapter(WebsiteAdapter):
    """Indeed-specific adapter for job search and application automation."""
    
    def __init__(self, app=None):
        """Initialize IndeedAdapter instance.
        
        Args:
            app: Flask application instance for configuration
        """
        # Define Indeed-specific selectors
        selectors = SelectorConfig({
            # Login selectors
            "login_button": "a[href*='login']",
            "email_field": "#ifl-InputFormField-3",
            "password_field": "#ifl-InputFormField-7",
            "submit_login": "button[type='submit']",
            "login_error": ".auth-error-message",
            
            # Job search selectors
            "search_jobs_input": "#text-input-what",
            "search_location_input": "#text-input-where",
            "search_submit": "button[type='submit']",
            "job_card": ".job_seen_beacon",
            "job_title": ".jobTitle",
            "job_company": ".companyName",
            "job_location": ".companyLocation",
            "job_description_snippet": ".job-snippet",
            "job_posted_date": ".date",
            "job_salary": ".salary-snippet",
            
            # Job details selectors
            "job_details_title": "h1.jobsearch-JobInfoHeader-title",
            "job_details_company": ".jobsearch-InlineCompanyRating-companyName",
            "job_details_location": ".jobsearch-JobInfoHeader-subtitle .jobsearch-JobInfoHeader-locationName",
            "job_details_description": "#jobDescriptionText",
            "job_details_posted_date": ".jobsearch-HiringInsights-entry--bullet",
            "job_details_salary": ".jobsearch-JobMetadataHeader-item .icl-u-xs-mr--xs",
            
            # Apply selectors
            "apply_button": ".jobsearch-IndeedApplyButton-newDesign",
            "external_apply_button": "button[data-testid='outsideapply-button']",
            "indeed_apply_button": "button[data-testid='indeedapply-button']",
            "next_button": "button.ia-continueButton",
            "review_button": "button.ia-ReviewPage-continueButton",
            "submit_application_button": "button.ia-SubmitPage-continueButton",
            "form_field": ".ia-Questions-item",
            "form_error": ".ia-TextInputField-errorMessage",
            "application_success": ".ia-SuccessPage-title",
            
            # Navigation selectors
            "jobs_tab": "a[href='/jobs']",
            "my_jobs_tab": "a[href='/my/myjobs']",
            "applied_jobs_tab": "a[href='/my/myjobs/applied']",
            
            # Pagination selectors
            "pagination_next": "a[data-testid='pagination-page-next']",
            "pagination_prev": "a[data-testid='pagination-page-prev']",
            "pagination_page": "a[data-testid*='pagination-page-']"
        })
        
        # Create adapter configuration
        config = AdapterConfig(
            name="indeed",
            base_url="https://www.indeed.com",
            selectors=selectors,
            login_required=True,
            rate_limit_delay=3500,  # 3.5 seconds between actions (Indeed is more sensitive to automation)
            max_retries=3,
            timeout=30000  # 30 seconds
        )
        
        # Initialize the base adapter
        super().__init__(config, app)
    
    def login(self, credentials: Dict[str, str]) -> bool:
        """Login to Indeed.
        
        Args:
            credentials: Dictionary with login credentials (email, password)
            
        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            # Check if already logged in
            if self._logged_in:
                logger.info("Already logged in to Indeed")
                return True
            
            # Navigate to Indeed login page
            if not self.navigate(f"{self.base_url}/account/login"):
                logger.error("Failed to navigate to Indeed login page")
                return False
            
            # Get page
            page = self.get_page()
            
            # Wait for login form
            email_selector = self.selectors.get("email_field")
            if not interaction_handler.wait_for_element(page, email_selector):
                logger.error("Login form not found")
                return False
            
            # Enter email
            if not interaction_handler.human_type(page, email_selector, credentials.get("email", "")):
                logger.error("Failed to enter email")
                return False
            
            # Click continue or next button to proceed to password
            continue_button = page.query_selector("button[type='submit']")
            if continue_button:
                if not interaction_handler.human_click(page, "button[type='submit']"):
                    logger.error("Failed to click continue button")
                    return False
                
                # Wait for password field to appear
                interaction_handler.wait_for_element(page, self.selectors.get("password_field"))
            
            # Enter password
            password_selector = self.selectors.get("password_field")
            if not interaction_handler.human_type(page, password_selector, credentials.get("password", "")):
                logger.error("Failed to enter password")
                return False
            
            # Click login button
            submit_selector = "button[type='submit']"
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
            
            # Verify login success by checking for elements that should be present after login
            # Indeed typically shows the user's name or "My Jobs" after login
            if page.query_selector("a[href='/my/myjobs']") or page.query_selector(".gnav-LoggedInAccountMenu"):
                logger.info("Successfully logged in to Indeed")
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
        """Search for jobs on Indeed based on criteria.
        
        Args:
            criteria: Dictionary of search criteria (keywords, location, etc.)
            
        Returns:
            List[Dict[str, Any]]: List of job listings
        """
        try:
            # Navigate to jobs page
            if not self.navigate(f"{self.base_url}/"):
                logger.error("Failed to navigate to Indeed homepage")
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
                posted_text = posted_date_element.inner_text().strip()
                # Extract date from text like "Posted 30+ days ago"
                date_match = re.search(r'Posted (.*)', posted_text)
                if date_match:
                    job_details["posted_date"] = date_match.group(1).strip()
            
            # Extract salary if available
            salary_selector = self.selectors.get("job_details_salary")
            salary_element = page.query_selector(salary_selector)
            if salary_element:
                job_details["salary"] = salary_element.inner_text().strip()
            
            # Add source URL
            job_details["source_url"] = job_url
            job_details["source_website"] = "Indeed"
            
            # Check if Indeed Apply is available
            indeed_apply_selector = self.selectors.get("indeed_apply_button")
            job_details["indeed_apply_available"] = bool(page.query_selector(indeed_apply_selector))
            
            # Check if external apply is available
            external_apply_selector = self.selectors.get("external_apply_button")
            job_details["external_apply_available"] = bool(page.query_selector(external_apply_selector))
            
            return job_details
            
        except Exception as e:
            error = error_handler.handle_error(e, {"action": "extract_job_details", "url": job_url})
            logger.error(f"Job details extraction error: {str(error)}")
            screenshot_manager.capture_on_error(self.get_page(), error)
            return {}
    
    def apply_to_job(self, job_url: str, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply to a job on Indeed.
        
        Args:
            job_url: URL of the job listing
            application_data: Dictionary of application data
            
        Returns:
            Dict[str, Any]: Application result
        """
        try:
            # Ensure logged in if required
            if self.login_required and not self._logged_in:
                logger.error("Must be logged in to apply to jobs")
                return {"success": False, "message": "Not logged in"}
            
            # Navigate to job page
            if not self.navigate(job_url):
                logger.error(f"Failed to navigate to job URL: {job_url}")
                return {"success": False, "message": "Failed to navigate to job page"}
            
            # Get page
            page = self.get_page()
            
            # Check if Indeed Apply is available
            indeed_apply_selector = self.selectors.get("indeed_apply_button")
            external_apply_selector = self.selectors.get("external_apply_button")
            
            # Determine application type
            if page.query_selector(indeed_apply_selector):
                # Indeed Apply
                logger.info("Using Indeed Apply")
                return self._apply_with_indeed_apply(page, application_data)
            elif page.query_selector(external_apply_selector):
                # External Apply
                logger.info("Using External Apply")
                return self._apply_with_external_link(page, application_data)
            else:
                # No apply button found
                logger.error("No apply button found")
                return {"success": False, "message": "No apply button found"}
            
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
                job_link = card.query_selector("a.jcs-JobTitle")
                if job_link:
                    href = job_link.get_attribute("href")
                    if href:
                        # Extract job ID from URL
                        url_parts = urlparse(href)
                        path_parts = url_parts.path.split("/")
                        if len(path_parts) > 2:
                            job_id = path_parts[-1]
                        
                        # If no job ID found in path, try query parameters
                        if not job_id and "jk=" in href:
                            query_params = parse_qs(url_parts.query)
                            job_id = query_params.get("jk", [""])[0]
                
                if not job_id:
                    # Try to get from data attribute
                    job_id = card.get_attribute("data-jk")
                
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
                description_selector = self.selectors.get("job_description_snippet")
                description_element = card.query_selector(description_selector)
                if description_element:
                    job["description_snippet"] = description_element.inner_text().strip()
                
                # Extract posted date
                posted_date_selector = self.selectors.get("job_posted_date")
                posted_date_element = card.query_selector(posted_date_selector)
                if posted_date_element:
                    job["posted_date"] = posted_date_element.inner_text().strip()
                
                # Extract salary if available
                salary_selector = self.selectors.get("job_salary")
                salary_element = card.query_selector(salary_selector)
                if salary_element:
                    job["salary"] = salary_element.inner_text().strip()
                
                # Add source information
                job["source_website"] = "Indeed"
                job["source_url"] = f"{self.base_url}/viewjob?jk={job_id}"
                
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
                date_selector = f"button[data-testid='date-posted-facet']"
                
                # Click the filter dropdown
                if not interaction_handler.human_click(page, date_selector):
                    logger.error("Failed to click date posted filter")
                    return False
                
                # Wait for dropdown to appear with variable delay
                self._add_random_delay(500, 1500)
                
                # Click the specific option
                option_selector = f"[data-testid='facet-{date_value.lower().replace(' ', '-')}']"
                if not interaction_handler.human_click(page, option_selector):
                    logger.error(f"Failed to select date option: {date_value}")
                    return False
                
                # Wait for results to update with variable delay
                self._add_random_delay(1000, 3000)
                
                # Apply rate limiting between filter operations
                self._apply_rate_limiting()
            
            # Apply job type filter
            if "job_type" in filters:
                job_type = filters["job_type"]
                type_selector = f"button[data-testid='job-type-facet']"
                
                # Click the filter dropdown
                if not interaction_handler.human_click(page, type_selector):
                    logger.error("Failed to click job type filter")
                    return False
                
                # Wait for dropdown to appear with variable delay
                self._add_random_delay(500, 1500)
                
                # Click the specific option
                option_selector = f"[data-testid='facet-{job_type.lower().replace(' ', '-')}']"
                if not interaction_handler.human_click(page, option_selector):
                    logger.error(f"Failed to select job type option: {job_type}")
                    return False
                
                # Wait for results to update with variable delay
                self._add_random_delay(1000, 3000)
                
                # Apply rate limiting between filter operations
                self._apply_rate_limiting()
            
            # Apply salary filter
            if "salary" in filters:
                salary_value = filters["salary"]
                salary_selector = f"button[data-testid='salary-facet']"
                
                # Click the filter dropdown
                if not interaction_handler.human_click(page, salary_selector):
                    logger.error("Failed to click salary filter")
                    return False
                
                # Wait for dropdown to appear with variable delay
                self._add_random_delay(500, 1500)
                
                # Click the specific option
                option_selector = f"[data-testid='facet-{salary_value.lower().replace(' ', '-').replace('$', '')}']"
                if not interaction_handler.human_click(page, option_selector):
                    logger.error(f"Failed to select salary option: {salary_value}")
                    return False
                
                # Wait for results to update
                time.sleep(random.uniform(1.0, 2.0))
            
            # Apply experience level filter
            if "experience_level" in filters:
                exp_value = filters["experience_level"]
                exp_selector = f"button[data-testid='experience-level-facet']"
                
                # Click the filter dropdown
                if not interaction_handler.human_click(page, exp_selector):
                    logger.error("Failed to click experience level filter")
                    return False
                
                # Wait for dropdown to appear with variable delay
                self._add_random_delay(500, 1500)
                
                # Click the specific option
                option_selector = f"[data-testid='facet-{exp_value.lower().replace(' ', '-')}']"
                if not interaction_handler.human_click(page, option_selector):
                    logger.error(f"Failed to select experience option: {exp_value}")
                    return False
                
                # Wait for results to update with variable delay
                self._add_random_delay(1000, 3000)
            
            return True
            
        except Exception as e:
            logger.error(f"Error applying search filters: {str(e)}")
            return False
    
    def _apply_with_indeed_apply(self, page: Page, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply to a job using Indeed Apply.
        
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
                "fields_filled": 0,
                "application_type": "indeed_apply"
            }
            
            # Get job context for AI responses
            job_context = application_data.get("job_context")
            user_profile = application_data.get("user_profile", {})
            
            # Click Indeed Apply button
            indeed_apply_selector = self.selectors.get("indeed_apply_button")
            if not interaction_handler.human_click(page, indeed_apply_selector):
                result["message"] = "Failed to click Indeed Apply button"
                return result
            
            # Wait for application modal to load
            time.sleep(random.uniform(2.0, 3.0))
            
            # Process application steps
            step_count = 0
            max_steps = 10  # Safety limit
            
            while step_count < max_steps:
                step_count += 1
                
                # Take screenshot for debugging
                screenshot_manager.take_screenshot(page, f"indeed_apply_step_{step_count}")
                
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
                
                # Click next button to proceed
                next_button_selector = self.selectors.get("next_button")
                next_button = page.query_selector(next_button_selector)
                
                if next_button:
                    if not interaction_handler.human_click(page, next_button_selector):
                        result["message"] = "Failed to click next button"
                        break
                    
                    # Wait for next page to load
                    time.sleep(random.uniform(1.0, 2.0))
                else:
                    # No next button found, might be stuck
                    result["message"] = "No next button found, application flow interrupted"
                    break
            
            # If we reached max steps without completing
            if step_count >= max_steps and not result["success"]:
                result["message"] = "Application process too long, exceeded maximum steps"
            
            # Update step counts
            result["steps_completed"] = step_count
            result["total_steps"] = step_count
            
            return result
            
        except Exception as e:
            error = error_handler.handle_error(e, {"action": "apply_with_indeed_apply"})
            logger.error(f"Indeed Apply error: {str(error)}")
            screenshot_manager.capture_on_error(page, error)
            return {
                "success": False,
                "message": f"Application error: {str(error)}",
                "application_type": "indeed_apply"
            }
    
    def _apply_with_external_link(self, page: Page, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply to a job using external link.
        
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
                "external_url": None,
                "application_type": "external_apply"
            }
            
            # Click external apply button
            external_apply_selector = self.selectors.get("external_apply_button")
            if not interaction_handler.human_click(page, external_apply_selector):
                result["message"] = "Failed to click external apply button"
                return result
            
            # Wait for navigation or new tab
            time.sleep(random.uniform(2.0, 3.0))
            
            # Check if a new tab was opened
            context = self.get_browser_context()
            pages = context.pages
            
            if len(pages) > 1:
                # New tab opened
                new_page = pages[-1]  # Assume the last page is the new one
                
                # Get the URL of the external application
                external_url = new_page.url
                result["external_url"] = external_url
                
                # Take screenshot of the external page
                screenshot_manager.take_screenshot(new_page, "external_apply_page")
                
                # Close the new tab and return to original
                new_page.close()
                
                result["success"] = True
                result["message"] = "External application link opened successfully"
            else:
                # No new tab, check if current page changed
                current_url = page.url
                
                if current_url != page.url:
                    # Page navigated to external site
                    result["external_url"] = current_url
                    result["success"] = True
                    result["message"] = "Redirected to external application page"
                else:
                    # No navigation occurred
                    result["message"] = "Failed to open external application link"
            
            return result
            
        except Exception as e:
            error = error_handler.handle_error(e, {"action": "apply_with_external_link"})
            logger.error(f"External apply error: {str(error)}")
            screenshot_manager.capture_on_error(page, error)
            return {
                "success": False,
                "message": f"External application error: {str(error)}",
                "application_type": "external_apply"
            }