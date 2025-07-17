"""
Screenshot manager for capturing and managing browser screenshots.

This module provides functionality for capturing, storing, and managing screenshots
during browser automation for debugging and reporting purposes.
"""
import os
import time
import logging
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from playwright.sync_api import Page, ElementHandle

# Set up logging
logger = logging.getLogger(__name__)


class ScreenshotManager:
    """Manager for browser screenshots."""
    
    def __init__(self, app=None):
        """Initialize ScreenshotManager instance.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self._screenshot_dir = "screenshots"
        self._enable_screenshots = True
        self._screenshot_on_error = True
        self._max_screenshots = 100
        self._screenshot_count = 0
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the screenshot manager with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self._screenshot_dir = app.config.get('SCREENSHOT_DIR', 'screenshots')
        self._enable_screenshots = app.config.get('ENABLE_SCREENSHOTS', True)
        self._screenshot_on_error = app.config.get('SCREENSHOT_ON_ERROR', True)
        self._max_screenshots = app.config.get('MAX_SCREENSHOTS', 100)
        
        # Ensure screenshot directory exists
        os.makedirs(self._screenshot_dir, exist_ok=True)
    
    def take_screenshot(self, page: Page, name: Optional[str] = None, 
                       full_page: bool = True) -> Optional[str]:
        """Take a screenshot of the current page.
        
        Args:
            page: Playwright page
            name: Optional name for the screenshot
            full_page: Whether to capture the full page
            
        Returns:
            Optional[str]: Path to the screenshot file or None if failed
        """
        if not self._enable_screenshots:
            return None
        
        if self._screenshot_count >= self._max_screenshots:
            logger.warning("Maximum screenshot limit reached")
            return None
        
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if name:
                filename = f"{timestamp}_{name}.png"
            else:
                filename = f"{timestamp}_screenshot.png"
            
            filepath = os.path.join(self._screenshot_dir, filename)
            
            # Take screenshot
            page.screenshot(path=filepath, full_page=full_page)
            
            self._screenshot_count += 1
            logger.info(f"Screenshot saved: {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error taking screenshot: {str(e)}")
            return None
    
    def take_element_screenshot(self, element: ElementHandle, 
                              name: Optional[str] = None) -> Optional[str]:
        """Take a screenshot of a specific element.
        
        Args:
            element: Playwright element handle
            name: Optional name for the screenshot
            
        Returns:
            Optional[str]: Path to the screenshot file or None if failed
        """
        if not self._enable_screenshots:
            return None
        
        if self._screenshot_count >= self._max_screenshots:
            logger.warning("Maximum screenshot limit reached")
            return None
        
        try:
            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            if name:
                filename = f"{timestamp}_{name}_element.png"
            else:
                filename = f"{timestamp}_element.png"
            
            filepath = os.path.join(self._screenshot_dir, filename)
            
            # Take element screenshot
            element.screenshot(path=filepath)
            
            self._screenshot_count += 1
            logger.info(f"Element screenshot saved: {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error taking element screenshot: {str(e)}")
            return None
    
    def capture_on_error(self, page: Page, error: Exception) -> Optional[str]:
        """Capture a screenshot when an error occurs.
        
        Args:
            page: Playwright page
            error: Exception that occurred
            
        Returns:
            Optional[str]: Path to the screenshot file or None if failed
        """
        if not self._enable_screenshots or not self._screenshot_on_error:
            return None
        
        try:
            # Generate error-specific filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            error_type = type(error).__name__
            filename = f"{timestamp}_error_{error_type}.png"
            
            filepath = os.path.join(self._screenshot_dir, filename)
            
            # Take screenshot
            page.screenshot(path=filepath, full_page=True)
            
            self._screenshot_count += 1
            logger.info(f"Error screenshot saved: {filepath}")
            
            return filepath
            
        except Exception as e:
            logger.error(f"Error taking error screenshot: {str(e)}")
            return None
    
    def clear_screenshots(self, days_old: Optional[int] = None) -> int:
        """Clear old screenshots.
        
        Args:
            days_old: Delete screenshots older than this many days
            
        Returns:
            int: Number of screenshots deleted
        """
        if not os.path.exists(self._screenshot_dir):
            return 0
        
        deleted_count = 0
        current_time = time.time()
        
        try:
            for filename in os.listdir(self._screenshot_dir):
                filepath = os.path.join(self._screenshot_dir, filename)
                
                # Skip if not a file
                if not os.path.isfile(filepath):
                    continue
                
                # Skip if not a PNG file
                if not filename.lower().endswith('.png'):
                    continue
                
                # Check file age if days_old is specified
                if days_old is not None:
                    file_time = os.path.getmtime(filepath)
                    age_in_days = (current_time - file_time) / (60 * 60 * 24)
                    
                    if age_in_days < days_old:
                        continue
                
                # Delete the file
                os.remove(filepath)
                deleted_count += 1
            
            logger.info(f"Deleted {deleted_count} screenshots")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error clearing screenshots: {str(e)}")
            return deleted_count
    
    def get_screenshot_count(self) -> int:
        """Get the number of screenshots taken in this session.
        
        Returns:
            int: Screenshot count
        """
        return self._screenshot_count
    
    def reset_screenshot_count(self) -> None:
        """Reset the screenshot counter."""
        self._screenshot_count = 0


# Create a singleton instance
screenshot_manager = ScreenshotManager()