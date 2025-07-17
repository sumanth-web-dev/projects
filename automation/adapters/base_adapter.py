"""
Base adapter for website automation.

This module provides a base class for website-specific adapters, defining
the common interface and functionality for interacting with job websites.
"""
import os
import json
import logging
import time
import random
from typing import Dict, List, Optional, Tuple, Any, Union
from urllib.parse import urlparse
from playwright.sync_api import Page, Browser, BrowserContext

from automation.playwright_engine.browser_manager import browser_manager
from automation.playwright_engine.interaction_handler import interaction_handler
from automation.playwright_engine.screenshot_manager import screenshot_manager
from automation.playwright_engine.error_handler import error_handler, AutomationError
from automation.playwright_engine.rate_limiter import rate_limiter
from automation.playwright_engine.anti_detection import anti_detection

# Set up logging
logger = logging.getLogger(__name__)


class SelectorConfig:
    """Configuration for website selectors."""
    
    def __init__(self, selectors: Dict[str, str]):
        """Initialize SelectorConfig instance.
        
        Args:
            selectors: Dictionary of selector names to CSS selectors
        """
        self.selectors = selectors
    
    def get(self, name: str, default: Optional[str] = None) -> Optional[str]:
        """Get a selector by name.
        
        Args:
            name: Selector name
            default: Default value if selector not found
            
        Returns:
            Optional[str]: Selector or default value
        """
        return self.selectors.get(name, default)
    
    def update(self, selectors: Dict[str, str]) -> None:
        """Update selectors.
        
        Args:
            selectors: Dictionary of selector names to CSS selectors
        """
        self.selectors.update(selectors)
    
    @classmethod
    def from_file(cls, filepath: str) -> 'SelectorConfig':
        """Create a SelectorConfig from a JSON file.
        
        Args:
            filepath: Path to JSON file
            
        Returns:
            SelectorConfig: Created config
            
        Raises:
            FileNotFoundError: If file not found
            ValueError: If file is not valid JSON
        """
        with open(filepath, 'r') as f:
            selectors = json.load(f)
        
        if not isinstance(selectors, dict):
            raise ValueError("Selectors file must contain a JSON object")
        
        return cls(selectors)
    
    def to_file(self, filepath: str) -> None:
        """Save selectors to a JSON file.
        
        Args:
            filepath: Path to JSON file
        """
        with open(filepath, 'w') as f:
            json.dump(self.selectors, f, indent=2)


class AdapterConfig:
    """Configuration for website adapter."""
    
    def __init__(self, name: str, base_url: str, selectors: SelectorConfig,
                login_required: bool = True, rate_limit_delay: int = 2000,
                max_retries: int = 3, timeout: int = 30000):
        """Initialize AdapterConfig instance.
        
        Args:
            name: Website name
            base_url: Base URL for the website
            selectors: Selector configuration
            login_required: Whether login is required
            rate_limit_delay: Delay between requests in ms
            max_retries: Maximum number of retries
            timeout: Default timeout in ms
        """
        self.name = name
        self.base_url = base_url
        self.selectors = selectors
        self.login_required = login_required
        self.rate_limit_delay = rate_limit_delay
        self.max_retries = max_retries
        self.timeout = timeout


class WebsiteAdapter:
    """Base class for website-specific adapters."""
    
    def __init__(self, config: AdapterConfig, app=None):
        """Initialize WebsiteAdapter instance.
        
        Args:
            config: Adapter configuration
            app: Flask application instance for configuration
        """
        self.app = app
        self.config = config
        self.name = config.name
        self.base_url = config.base_url
        self.selectors = config.selectors
        self.login_required = config.login_required
        self.rate_limit_delay = config.rate_limit_delay
        self.max_retries = config.max_retries
        self.timeout = config.timeout
        
        self._context_name = f"{self.name}_context"
        self._context = None
        self._page = None
        self._logged_in = False
        self._last_request_time = 0
        
        # Extract domain for rate limiting
        parsed_url = urlparse(self.base_url)
        self._domain = parsed_url.netloc or self.name
        
        # Set domain-specific rate limit delay
        rate_limiter.set_domain_delay(self._domain, self.rate_limit_delay)
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the adapter with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        
        # Override config from app if available
        if hasattr(app.config, f"{self.name.upper()}_BASE_URL"):
            self.base_url = app.config[f"{self.name.upper()}_BASE_URL"]
        
        if hasattr(app.config, f"{self.name.upper()}_RATE_LIMIT_DELAY"):
            self.rate_limit_delay = app.config[f"{self.name.upper()}_RATE_LIMIT_DELAY"]
        
        if hasattr(app.config, f"{self.name.upper()}_MAX_RETRIES"):
            self.max_retries = app.config[f"{self.name.upper()}_MAX_RETRIES"]
        
        if hasattr(app.config, f"{self.name.upper()}_TIMEOUT"):
            self.timeout = app.config[f"{self.name.upper()}_TIMEOUT"]
    
    def get_browser_context(self) -> BrowserContext:
        """Get or create a browser context for this adapter.
        
        Returns:
            BrowserContext: Playwright browser context
        """
        if self._context is None:
            self._context = browser_manager.get_context(self._context_name)
        
        return self._context
    
    def get_page(self) -> Page:
        """Get or create a page for this adapter.
        
        Returns:
            Page: Playwright page
        """
        if self._page is None:
            context = self.get_browser_context()
            self._page = browser_manager.get_page(self._context_name)
        
        return self._page
    
    def navigate(self, url: str, wait_for_load: bool = True) -> bool:
        """Navigate to a URL.
        
        Args:
            url: URL to navigate to
            wait_for_load: Whether to wait for page to load
            
        Returns:
            bool: True if navigation successful, False otherwise
        """
        try:
            # Apply rate limiting
            self._apply_rate_limiting()
            
            # Get page
            page = self.get_page()
            
            # Navigate to URL
            logger.info(f"Navigating to {url}")
            page.goto(url, timeout=self.timeout)
            
            # Wait for page to load
            if wait_for_load:
                interaction_handler.wait_for_navigation(page, self.timeout)
            
            # Check for rate limiting
            if error_handler.detect_rate_limiting(page):
                # If rate limiting is detected, set a cooldown period
                rate_limiter.set_cooldown(self._domain, 60)  # 1 minute cooldown
                raise AutomationError("Rate limiting detected", "rate_limit", True)
            
            # Apply anti-detection measures after page load
            self._apply_anti_detection_measures(page)
            
            # Take screenshot for debugging
            screenshot_manager.take_screenshot(page, f"{self.name}_navigate")
            
            return True
            
        except Exception as e:
            error = error_handler.handle_error(e, {"url": url})
            logger.error(f"Navigation error: {str(error)}")
            screenshot_manager.capture_on_error(self.get_page(), error)
            return False
    
    def login(self, credentials: Dict[str, str]) -> bool:
        """Login to the website.
        
        Args:
            credentials: Dictionary with login credentials
            
        Returns:
            bool: True if login successful, False otherwise
        """
        # This is a base implementation that should be overridden by subclasses
        if not self.login_required:
            logger.info(f"Login not required for {self.name}")
            self._logged_in = True
            return True
        
        logger.warning(f"Login method not implemented for {self.name}")
        return False
    
    def is_logged_in(self) -> bool:
        """Check if currently logged in.
        
        Returns:
            bool: True if logged in, False otherwise
        """
        return self._logged_in
    
    def search_jobs(self, criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Search for jobs based on criteria.
        
        Args:
            criteria: Dictionary of search criteria
            
        Returns:
            List[Dict[str, Any]]: List of job listings
        """
        # This is a base implementation that should be overridden by subclasses
        logger.warning(f"Search jobs method not implemented for {self.name}")
        return []
    
    def apply_to_job(self, job_url: str, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply to a job.
        
        Args:
            job_url: URL of the job listing
            application_data: Dictionary of application data
            
        Returns:
            Dict[str, Any]: Application result
        """
        # This is a base implementation that should be overridden by subclasses
        logger.warning(f"Apply to job method not implemented for {self.name}")
        return {"success": False, "message": "Not implemented"}
    
    def extract_job_details(self, job_url: str) -> Dict[str, Any]:
        """Extract detailed information about a job.
        
        Args:
            job_url: URL of the job listing
            
        Returns:
            Dict[str, Any]: Job details
        """
        # This is a base implementation that should be overridden by subclasses
        logger.warning(f"Extract job details method not implemented for {self.name}")
        return {}
    
    def close(self) -> None:
        """Close the adapter and clean up resources."""
        if self._context:
            browser_manager.close_context(self._context_name)
            self._context = None
            self._page = None
            self._logged_in = False
    
    def _apply_rate_limiting(self) -> None:
        """Apply rate limiting between requests using the rate limiter."""
        # Use the rate limiter to control request frequency
        rate_limiter.wait(self._domain)
        self._last_request_time = time.time() * 1000
        
    def _apply_anti_detection_measures(self, page: Page) -> None:
        """Apply anti-detection measures to the page.
        
        Args:
            page: Playwright page
        """
        try:
            # Simulate human behavior
            anti_detection.simulate_human_behavior(page)
            
            # Add random delays between actions
            self._add_random_delay()
            
            logger.debug(f"Applied anti-detection measures for {self.name}")
        except Exception as e:
            logger.error(f"Error applying anti-detection measures: {str(e)}")
    
    def _add_random_delay(self, min_ms: int = 500, max_ms: int = 2000) -> None:
        """Add a random delay to simulate human behavior.
        
        Args:
            min_ms: Minimum delay in milliseconds
            max_ms: Maximum delay in milliseconds
        """
        delay = random.randint(min_ms, max_ms)
        time.sleep(delay / 1000)