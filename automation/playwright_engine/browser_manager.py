"""
Browser manager for handling Playwright browser instances.

This module provides functionality for creating and managing Playwright browser instances,
including browser contexts, pages, and anti-detection measures.
"""
import os
import logging
import random
import json
from typing import Dict, List, Optional, Tuple, Any, Union
from playwright.sync_api import sync_playwright, Browser, BrowserContext, Page, Playwright

# Set up logging
logger = logging.getLogger(__name__)


class BrowserManager:
    """Manager for Playwright browser instances and contexts."""
    
    # Browser types
    CHROMIUM = "chromium"
    FIREFOX = "firefox"
    WEBKIT = "webkit"
    
    # Launch modes
    HEADLESS = "headless"
    HEADED = "headed"
    
    def __init__(self, app=None):
        """Initialize BrowserManager instance.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self._playwright = None
        self._browser = None
        self._contexts = {}
        self._default_context = None
        self._default_page = None
        self._browser_type = self.CHROMIUM
        self._launch_mode = self.HEADLESS
        self._user_agent_list = self._load_user_agents()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the browser manager with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self._browser_type = app.config.get('BROWSER_TYPE', self.CHROMIUM)
        self._launch_mode = app.config.get('BROWSER_LAUNCH_MODE', self.HEADLESS)
    
    def start(self, browser_type: Optional[str] = None, headless: Optional[bool] = None) -> Browser:
        """Start the Playwright browser.
        
        Args:
            browser_type: Browser type (chromium, firefox, webkit)
            headless: Whether to run in headless mode
            
        Returns:
            Browser: Playwright browser instance
        """
        if self._browser is not None:
            logger.info("Browser already started")
            return self._browser
        
        try:
            # Use provided parameters or defaults
            browser_type = browser_type or self._browser_type
            headless_mode = headless if headless is not None else (self._launch_mode == self.HEADLESS)
            
            # Start Playwright
            self._playwright = sync_playwright().start()
            
            # Get browser instance based on type
            if browser_type == self.CHROMIUM:
                browser_instance = self._playwright.chromium
            elif browser_type == self.FIREFOX:
                browser_instance = self._playwright.firefox
            elif browser_type == self.WEBKIT:
                browser_instance = self._playwright.webkit
            else:
                raise ValueError(f"Unsupported browser type: {browser_type}")
            
            # Launch browser with anti-detection measures
            self._browser = browser_instance.launch(
                headless=headless_mode,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--disable-features=IsolateOrigins,site-per-process',
                    '--disable-site-isolation-trials'
                ]
            )
            
            logger.info(f"Started {browser_type} browser in {'headless' if headless_mode else 'headed'} mode")
            return self._browser
            
        except Exception as e:
            logger.error(f"Error starting browser: {str(e)}")
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
            raise
    
    def create_context(self, context_name: str, user_agent: Optional[str] = None, 
                      viewport: Optional[Dict[str, int]] = None,
                      geolocation: Optional[Dict[str, float]] = None,
                      locale: Optional[str] = None) -> BrowserContext:
        """Create a new browser context with specific settings.
        
        Args:
            context_name: Name for the context
            user_agent: User agent string (random if None)
            viewport: Viewport dimensions
            geolocation: Geolocation settings
            locale: Browser locale
            
        Returns:
            BrowserContext: Playwright browser context
        """
        if self._browser is None:
            self.start()
        
        if context_name in self._contexts:
            logger.info(f"Context '{context_name}' already exists")
            return self._contexts[context_name]
        
        try:
            # Set up context options with anti-detection measures
            context_options = {
                "user_agent": user_agent or self._get_random_user_agent(),
                "viewport": viewport or {"width": 1920, "height": 1080},
                "locale": locale or "en-US",
                "timezone_id": "America/New_York",
                "permissions": ["geolocation"],
                "bypass_csp": True,  # Bypass Content Security Policy
                "ignore_https_errors": True
            }
            
            if geolocation:
                context_options["geolocation"] = geolocation
            
            # Create the context
            context = self._browser.new_context(**context_options)
            
            # Apply additional anti-detection measures
            self._apply_anti_detection_measures(context)
            
            # Store the context
            self._contexts[context_name] = context
            
            # Set as default if it's the first context
            if self._default_context is None:
                self._default_context = context
            
            logger.info(f"Created browser context: {context_name}")
            return context
            
        except Exception as e:
            logger.error(f"Error creating browser context: {str(e)}")
            raise
    
    def get_context(self, context_name: Optional[str] = None) -> BrowserContext:
        """Get a browser context by name or the default context.
        
        Args:
            context_name: Name of the context to get
            
        Returns:
            BrowserContext: Playwright browser context
        """
        if self._browser is None:
            self.start()
        
        if context_name is None:
            # Return default context or create one
            if self._default_context is None:
                self._default_context = self.create_context("default")
            return self._default_context
        
        # Return named context or create it
        if context_name not in self._contexts:
            return self.create_context(context_name)
        
        return self._contexts[context_name]
    
    def new_page(self, context_name: Optional[str] = None) -> Page:
        """Create a new page in the specified context.
        
        Args:
            context_name: Name of the context to use
            
        Returns:
            Page: Playwright page
        """
        context = self.get_context(context_name)
        page = context.new_page()
        
        # Set default page if none exists
        if self._default_page is None:
            self._default_page = page
        
        return page
    
    def get_page(self, context_name: Optional[str] = None) -> Page:
        """Get the first page in a context or create a new one.
        
        Args:
            context_name: Name of the context to use
            
        Returns:
            Page: Playwright page
        """
        context = self.get_context(context_name)
        
        # Get existing pages
        pages = context.pages
        
        if pages:
            return pages[0]
        else:
            return self.new_page(context_name)
    
    def close_context(self, context_name: str) -> bool:
        """Close a browser context by name.
        
        Args:
            context_name: Name of the context to close
            
        Returns:
            bool: True if closed successfully, False otherwise
        """
        if context_name not in self._contexts:
            logger.warning(f"Context '{context_name}' not found")
            return False
        
        try:
            # Close the context
            self._contexts[context_name].close()
            
            # Remove from contexts dict
            del self._contexts[context_name]
            
            # Reset default context if it was closed
            if self._default_context == self._contexts.get(context_name):
                self._default_context = None
                self._default_page = None
            
            logger.info(f"Closed browser context: {context_name}")
            return True
            
        except Exception as e:
            logger.error(f"Error closing browser context: {str(e)}")
            return False
    
    def close_all(self) -> bool:
        """Close all browser contexts and the browser.
        
        Returns:
            bool: True if closed successfully, False otherwise
        """
        try:
            # Close all contexts
            for context_name in list(self._contexts.keys()):
                self.close_context(context_name)
            
            # Close browser
            if self._browser:
                self._browser.close()
                self._browser = None
            
            # Stop Playwright
            if self._playwright:
                self._playwright.stop()
                self._playwright = None
            
            # Reset state
            self._contexts = {}
            self._default_context = None
            self._default_page = None
            
            logger.info("Closed all browser contexts and browser")
            return True
            
        except Exception as e:
            logger.error(f"Error closing browser: {str(e)}")
            return False
    
    def _apply_anti_detection_measures(self, context: BrowserContext) -> None:
        """Apply anti-detection measures to a browser context.
        
        Args:
            context: Browser context to modify
        """
        # Add script to modify navigator properties
        context.add_init_script("""
        Object.defineProperty(navigator, 'webdriver', {
            get: () => false
        });
        
        // Overwrite the plugins property to use a custom getter
        Object.defineProperty(navigator, 'plugins', {
            get: () => {
                // Create a plugins array with some fake plugins
                const plugins = [
                    { name: 'Chrome PDF Plugin', filename: 'internal-pdf-viewer' },
                    { name: 'Chrome PDF Viewer', filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai' },
                    { name: 'Native Client', filename: 'internal-nacl-plugin' }
                ];
                
                // Add properties to make it look like a real PluginArray
                plugins.refresh = () => {};
                plugins.item = (index) => plugins[index];
                plugins.namedItem = (name) => plugins.find(p => p.name === name);
                plugins.length = plugins.length;
                
                return plugins;
            }
        });
        
        // Modify languages
        Object.defineProperty(navigator, 'languages', {
            get: () => ['en-US', 'en']
        });
        
        // Add a fake notification API
        if (!window.Notification) {
            window.Notification = {
                permission: 'default',
                requestPermission: async () => 'default'
            };
        }
        """)
    
    def _get_random_user_agent(self) -> str:
        """Get a random user agent string.
        
        Returns:
            str: Random user agent string
        """
        if not self._user_agent_list:
            # Fallback user agent if list is empty
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        
        return random.choice(self._user_agent_list)
    
    def _load_user_agents(self) -> List[str]:
        """Load user agent strings from file or use defaults.
        
        Returns:
            List[str]: List of user agent strings
        """
        # Default user agents (modern browsers)
        default_agents = [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            # Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
            # Firefox on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0",
            # Edge on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36 Edg/92.0.902.55"
        ]
        
        try:
            # Try to load from config if app is available
            if self.app:
                user_agents_file = self.app.config.get('USER_AGENTS_FILE')
                if user_agents_file and os.path.exists(user_agents_file):
                    with open(user_agents_file, 'r') as f:
                        agents = json.load(f)
                        if isinstance(agents, list) and agents:
                            return agents
            
            # Try to load from default location
            user_agents_path = os.path.join(os.path.dirname(__file__), 'user_agents.json')
            if os.path.exists(user_agents_path):
                with open(user_agents_path, 'r') as f:
                    agents = json.load(f)
                    if isinstance(agents, list) and agents:
                        return agents
        except Exception as e:
            logger.warning(f"Error loading user agents: {str(e)}")
        
        # Return default agents if loading fails
        return default_agents


# Create a singleton instance
browser_manager = BrowserManager()