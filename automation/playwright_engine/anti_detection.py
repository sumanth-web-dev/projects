"""
Anti-detection strategies for browser automation.

This module provides functionality for avoiding detection during browser automation
by implementing various strategies to mimic human behavior and bypass anti-bot measures.
"""
import os
import json
import random
import logging
import time
from typing import Dict, List, Optional, Tuple, Any, Union
from playwright.sync_api import Page, BrowserContext

# Set up logging
logger = logging.getLogger(__name__)


class AntiDetection:
    """Anti-detection strategies for browser automation."""
    
    def __init__(self, app=None):
        """Initialize AntiDetection instance.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self._user_agents = self._load_user_agents()
        self._enable_evasion = True
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the anti-detection module with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self._enable_evasion = app.config.get('ENABLE_ANTI_DETECTION', True)
        
        # Load user agents from config if available
        user_agents_file = app.config.get('USER_AGENTS_FILE')
        if user_agents_file and os.path.exists(user_agents_file):
            self._user_agents = self._load_user_agents(user_agents_file)
    
    def apply_evasion_techniques(self, context: BrowserContext) -> None:
        """Apply evasion techniques to a browser context.
        
        Args:
            context: Playwright browser context
        """
        if not self._enable_evasion:
            return
        
        try:
            # Add script to modify navigator properties
            context.add_init_script("""
            // Overwrite the webdriver property
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false
            });
            
            // Overwrite the plugins property
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
            
            // Add fake permissions
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (parameters) => {
                return Promise.resolve({
                    state: "prompt",
                    onchange: null
                });
            };
            
            // Add fake notification API
            if (!window.Notification) {
                window.Notification = {
                    permission: 'default',
                    requestPermission: async () => 'default'
                };
            }
            
            // Add fake canvas fingerprint
            const originalToDataURL = HTMLCanvasElement.prototype.toDataURL;
            HTMLCanvasElement.prototype.toDataURL = function(type) {
                if (type === 'image/png' && this.width === 16 && this.height === 16) {
                    // This is likely a fingerprinting attempt
                    return 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAAAXNSR0IArs4c6QAAABNJREFUOE9jZGBgYGAY3AAAA2AABwAAlgD//Vj/wAAAAABJRU5ErkJggg==';
                }
                return originalToDataURL.apply(this, arguments);
            };
            
            // Add fake audio fingerprint
            const originalGetChannelData = AudioBuffer.prototype.getChannelData;
            if (originalGetChannelData) {
                AudioBuffer.prototype.getChannelData = function() {
                    const result = originalGetChannelData.apply(this, arguments);
                    // Add slight noise to the audio data
                    if (result.length > 0) {
                        // Only modify a small percentage of samples
                        const noise = 0.0001;
                        for (let i = 0; i < result.length; i += 500) {
                            result[i] = result[i] + (Math.random() * noise);
                        }
                    }
                    return result;
                };
            }
            """)
            
            logger.info("Applied anti-detection techniques to browser context")
            
        except Exception as e:
            logger.error(f"Error applying anti-detection techniques: {str(e)}")
    
    def simulate_human_behavior(self, page: Page) -> None:
        """Simulate human behavior on a page.
        
        Args:
            page: Playwright page
        """
        if not self._enable_evasion:
            return
        
        try:
            # Random mouse movements
            self._random_mouse_movements(page)
            
            # Random scrolling
            self._random_scrolling(page)
            
            # Random viewport resizing (subtle)
            self._random_viewport_resize(page)
            
            logger.debug("Simulated human behavior on page")
            
        except Exception as e:
            logger.error(f"Error simulating human behavior: {str(e)}")
    
    def rotate_user_agent(self) -> str:
        """Get a random user agent from the list.
        
        Returns:
            str: Random user agent string
        """
        if not self._user_agents:
            # Fallback user agent
            return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        
        return random.choice(self._user_agents)
    
    def add_browser_fingerprint_noise(self, context: BrowserContext) -> None:
        """Add noise to browser fingerprinting.
        
        Args:
            context: Playwright browser context
        """
        if not self._enable_evasion:
            return
        
        try:
            # Add script to add noise to fingerprinting methods
            context.add_init_script("""
            // Add noise to Date
            const originalDate = Date;
            const dateNoiseFactor = Math.floor(Math.random() * 10) * 1000; // 0-10 seconds
            
            Date = function(...args) {
                if (args.length === 0) {
                    const date = new originalDate();
                    date.setTime(date.getTime() + dateNoiseFactor);
                    return date;
                }
                return new originalDate(...args);
            };
            
            Date.now = function() {
                return originalDate.now() + dateNoiseFactor;
            };
            
            // Add noise to performance timing
            if (window.performance && window.performance.now) {
                const originalPerformanceNow = window.performance.now;
                const performanceNoiseFactor = Math.random() * 100;
                
                window.performance.now = function() {
                    return originalPerformanceNow.call(window.performance) + performanceNoiseFactor;
                };
            }
            """)
            
            logger.info("Added browser fingerprint noise")
            
        except Exception as e:
            logger.error(f"Error adding browser fingerprint noise: {str(e)}")
    
    def _random_mouse_movements(self, page: Page, movements: int = 3) -> None:
        """Perform random mouse movements on the page.
        
        Args:
            page: Playwright page
            movements: Number of random movements
        """
        try:
            # Get viewport size
            viewport = page.viewport_size
            if not viewport:
                return
            
            width = viewport["width"]
            height = viewport["height"]
            
            # Perform random movements
            for _ in range(movements):
                # Random coordinates within viewport
                x = random.randint(100, width - 100)
                y = random.randint(100, height - 100)
                
                # Move mouse with random speed
                steps = random.randint(5, 10)
                page.mouse.move(x, y, steps=steps)
                
                # Random delay between movements
                time.sleep(random.uniform(0.1, 0.5))
                
        except Exception as e:
            logger.error(f"Error performing random mouse movements: {str(e)}")
    
    def _random_scrolling(self, page: Page, scrolls: int = 2) -> None:
        """Perform random scrolling on the page.
        
        Args:
            page: Playwright page
            scrolls: Number of random scrolls
        """
        try:
            # Get page height
            page_height = page.evaluate("document.body.scrollHeight")
            viewport_height = page.viewport_size["height"]
            
            if page_height <= viewport_height:
                return  # No need to scroll
            
            # Perform random scrolls
            for _ in range(scrolls):
                # Random scroll distance
                scroll_y = random.randint(100, 500)
                
                # Scroll with random speed
                steps = random.randint(5, 15)
                for i in range(steps):
                    step_y = scroll_y * (i + 1) / steps
                    page.evaluate(f"window.scrollTo(0, window.scrollY + {step_y/steps})")
                    time.sleep(random.uniform(0.01, 0.05))
                
                # Random delay between scrolls
                time.sleep(random.uniform(0.5, 1.5))
                
        except Exception as e:
            logger.error(f"Error performing random scrolling: {str(e)}")
    
    def _random_viewport_resize(self, page: Page) -> None:
        """Perform a subtle random viewport resize.
        
        Args:
            page: Playwright page
        """
        try:
            # Get current viewport size
            viewport = page.viewport_size
            if not viewport:
                return
            
            width = viewport["width"]
            height = viewport["height"]
            
            # Small random adjustment (±20 pixels)
            new_width = width + random.randint(-20, 20)
            new_height = height + random.randint(-20, 20)
            
            # Ensure minimum size
            new_width = max(800, new_width)
            new_height = max(600, new_height)
            
            # Set new viewport size
            page.set_viewport_size({"width": new_width, "height": new_height})
            
        except Exception as e:
            logger.error(f"Error performing random viewport resize: {str(e)}")
    
    def _load_user_agents(self, filepath: Optional[str] = None) -> List[str]:
        """Load user agent strings from file or use defaults.
        
        Args:
            filepath: Optional path to user agents file
            
        Returns:
            List[str]: List of user agent strings
        """
        # Default modern user agents
        default_agents = [
            # Chrome on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/94.0.4606.81 Safari/537.36",
            # Chrome on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
            # Firefox on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:91.0) Gecko/20100101 Firefox/91.0",
            # Firefox on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:89.0) Gecko/20100101 Firefox/89.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:90.0) Gecko/20100101 Firefox/90.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:91.0) Gecko/20100101 Firefox/91.0",
            # Edge on Windows
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36 Edg/92.0.902.55",
            # Safari on macOS
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15"
        ]
        
        try:
            # Try to load from file if provided
            if filepath and os.path.exists(filepath):
                with open(filepath, 'r') as f:
                    agents = json.load(f)
                    if isinstance(agents, list) and agents:
                        return agents
            
            # Try to load from default location
            default_path = os.path.join(os.path.dirname(__file__), 'user_agents.json')
            if os.path.exists(default_path):
                with open(default_path, 'r') as f:
                    agents = json.load(f)
                    if isinstance(agents, list) and agents:
                        return agents
        except Exception as e:
            logger.warning(f"Error loading user agents: {str(e)}")
        
        # Return default agents if loading fails
        return default_agents


# Create a singleton instance
anti_detection = AntiDetection()