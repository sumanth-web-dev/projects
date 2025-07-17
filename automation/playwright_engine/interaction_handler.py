"""
Interaction handler for human-like browser interactions.

This module provides functionality for simulating human-like interactions with web pages,
including realistic typing, mouse movements, and timing delays.
"""
import time
import random
import logging
from typing import Dict, List, Optional, Tuple, Any, Union
from playwright.sync_api import Page, ElementHandle

# Set up logging
logger = logging.getLogger(__name__)


class InteractionHandler:
    """Handler for human-like browser interactions."""
    
    def __init__(self, app=None):
        """Initialize InteractionHandler instance.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self._min_delay = 50  # Minimum delay in ms
        self._max_delay = 150  # Maximum delay in ms
        self._typing_speed_min = 50  # Minimum typing speed in ms
        self._typing_speed_max = 150  # Maximum typing speed in ms
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the interaction handler with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self._min_delay = app.config.get('INTERACTION_MIN_DELAY_MS', 50)
        self._max_delay = app.config.get('INTERACTION_MAX_DELAY_MS', 150)
        self._typing_speed_min = app.config.get('TYPING_SPEED_MIN_MS', 50)
        self._typing_speed_max = app.config.get('TYPING_SPEED_MAX_MS', 150)
    
    def human_click(self, page: Page, selector: str, 
                   force: bool = False, delay: Optional[int] = None) -> bool:
        """Perform a human-like click on an element.
        
        Args:
            page: Playwright page
            selector: Element selector
            force: Whether to force the click
            delay: Optional delay before clicking (ms)
            
        Returns:
            bool: True if click was successful, False otherwise
        """
        try:
            # Wait for element to be visible
            element = page.wait_for_selector(selector, state="visible")
            if not element:
                logger.warning(f"Element not found: {selector}")
                return False
            
            # Get element bounding box
            box = element.bounding_box()
            if not box:
                logger.warning(f"Could not get bounding box for element: {selector}")
                return False
            
            # Calculate click position (slightly randomized within element)
            x = box["x"] + box["width"] * random.uniform(0.3, 0.7)
            y = box["y"] + box["height"] * random.uniform(0.3, 0.7)
            
            # Move mouse to element with human-like motion
            self._human_mouse_move(page, x, y)
            
            # Optional delay before clicking
            if delay is None:
                delay = random.randint(self._min_delay, self._max_delay)
            time.sleep(delay / 1000)
            
            # Click the element
            page.mouse.click(x, y, force=force)
            
            # Small delay after clicking
            time.sleep(random.randint(50, 200) / 1000)
            
            return True
            
        except Exception as e:
            logger.error(f"Error clicking element {selector}: {str(e)}")
            return False
    
    def human_type(self, page: Page, selector: str, text: str, 
                  delay_before: Optional[int] = None, clear: bool = True) -> bool:
        """Type text into an input field with human-like timing.
        
        Args:
            page: Playwright page
            selector: Element selector
            text: Text to type
            delay_before: Optional delay before typing (ms)
            clear: Whether to clear the field before typing
            
        Returns:
            bool: True if typing was successful, False otherwise
        """
        try:
            # Wait for element to be visible
            element = page.wait_for_selector(selector, state="visible")
            if not element:
                logger.warning(f"Element not found: {selector}")
                return False
            
            # Click the element first
            self.human_click(page, selector)
            
            # Optional delay before typing
            if delay_before is None:
                delay_before = random.randint(self._min_delay, self._max_delay)
            time.sleep(delay_before / 1000)
            
            # Clear the field if requested
            if clear:
                element.fill("")
                time.sleep(random.randint(50, 150) / 1000)
            
            # Type the text with human-like timing
            for char in text:
                # Type the character
                page.keyboard.type(char)
                
                # Random delay between keystrokes
                typing_delay = random.randint(self._typing_speed_min, self._typing_speed_max)
                time.sleep(typing_delay / 1000)
                
                # Occasionally add a longer pause
                if random.random() < 0.05:
                    time.sleep(random.randint(200, 500) / 1000)
            
            # Small delay after typing
            time.sleep(random.randint(100, 300) / 1000)
            
            return True
            
        except Exception as e:
            logger.error(f"Error typing into element {selector}: {str(e)}")
            return False
    
    def human_scroll(self, page: Page, direction: str = "down", 
                    distance: Optional[int] = None, speed: str = "normal") -> bool:
        """Perform a human-like scroll action.
        
        Args:
            page: Playwright page
            direction: Scroll direction ("up", "down", "left", "right")
            distance: Scroll distance in pixels (random if None)
            speed: Scroll speed ("slow", "normal", "fast")
            
        Returns:
            bool: True if scroll was successful, False otherwise
        """
        try:
            # Set scroll parameters based on speed
            if speed == "slow":
                steps = random.randint(15, 25)
                step_delay = random.randint(30, 50)
            elif speed == "fast":
                steps = random.randint(5, 10)
                step_delay = random.randint(10, 20)
            else:  # normal
                steps = random.randint(8, 15)
                step_delay = random.randint(15, 30)
            
            # Set scroll distance
            if distance is None:
                if direction in ["down", "up"]:
                    distance = random.randint(300, 800)
                else:
                    distance = random.randint(100, 300)
            
            # Adjust direction
            if direction == "up":
                distance = -distance
            elif direction == "left":
                distance = -distance
                horizontal = True
            elif direction == "right":
                horizontal = True
            else:  # down
                horizontal = False
            
            # Calculate step size
            step_size = distance / steps
            
            # Perform scroll in steps
            for _ in range(steps):
                if horizontal:
                    page.mouse.wheel(step_size, 0)
                else:
                    page.mouse.wheel(0, step_size)
                
                time.sleep(step_delay / 1000)
            
            # Small delay after scrolling
            time.sleep(random.randint(200, 500) / 1000)
            
            return True
            
        except Exception as e:
            logger.error(f"Error scrolling: {str(e)}")
            return False
    
    def human_select_option(self, page: Page, selector: str, 
                           value: Optional[str] = None, 
                           label: Optional[str] = None,
                           index: Optional[int] = None) -> bool:
        """Select an option from a dropdown with human-like interaction.
        
        Args:
            page: Playwright page
            selector: Select element selector
            value: Option value to select
            label: Option label to select
            index: Option index to select
            
        Returns:
            bool: True if selection was successful, False otherwise
        """
        try:
            # Wait for element to be visible
            element = page.wait_for_selector(selector, state="visible")
            if not element:
                logger.warning(f"Element not found: {selector}")
                return False
            
            # Click the select element
            self.human_click(page, selector)
            
            # Small delay after clicking
            time.sleep(random.randint(300, 600) / 1000)
            
            # Select the option
            if value is not None:
                page.select_option(selector, value=value)
            elif label is not None:
                page.select_option(selector, label=label)
            elif index is not None:
                page.select_option(selector, index=index)
            else:
                # Select a random option if none specified
                options = page.eval_on_selector_all(f"{selector} > option", "options => options.map(o => o.value)")
                if options:
                    page.select_option(selector, value=random.choice(options))
            
            # Small delay after selection
            time.sleep(random.randint(200, 500) / 1000)
            
            return True
            
        except Exception as e:
            logger.error(f"Error selecting option from {selector}: {str(e)}")
            return False
    
    def human_check_checkbox(self, page: Page, selector: str, 
                           check: bool = True) -> bool:
        """Check or uncheck a checkbox with human-like interaction.
        
        Args:
            page: Playwright page
            selector: Checkbox element selector
            check: Whether to check or uncheck
            
        Returns:
            bool: True if action was successful, False otherwise
        """
        try:
            # Wait for element to be visible
            element = page.wait_for_selector(selector, state="visible")
            if not element:
                logger.warning(f"Element not found: {selector}")
                return False
            
            # Get current checked state
            current_state = element.is_checked()
            
            # Only click if state needs to change
            if current_state != check:
                self.human_click(page, selector)
                
                # Verify the change
                element = page.wait_for_selector(selector, state="visible")
                new_state = element.is_checked()
                
                if new_state != check:
                    logger.warning(f"Failed to {'check' if check else 'uncheck'} checkbox {selector}")
                    return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error {'checking' if check else 'unchecking'} checkbox {selector}: {str(e)}")
            return False
    
    def wait_for_navigation(self, page: Page, timeout: int = 30000) -> bool:
        """Wait for page navigation to complete.
        
        Args:
            page: Playwright page
            timeout: Timeout in milliseconds
            
        Returns:
            bool: True if navigation completed, False on timeout
        """
        try:
            page.wait_for_load_state("networkidle", timeout=timeout)
            return True
        except Exception as e:
            logger.warning(f"Navigation timeout: {str(e)}")
            return False
    
    def random_delay(self, min_ms: Optional[int] = None, max_ms: Optional[int] = None) -> None:
        """Introduce a random delay to simulate human behavior.
        
        Args:
            min_ms: Minimum delay in milliseconds
            max_ms: Maximum delay in milliseconds
        """
        min_delay = min_ms if min_ms is not None else self._min_delay
        max_delay = max_ms if max_ms is not None else self._max_delay
        
        delay = random.randint(min_delay, max_delay)
        time.sleep(delay / 1000)
    
    def _human_mouse_move(self, page: Page, x: float, y: float, 
                         steps: int = 10) -> None:
        """Move mouse in a human-like path to coordinates.
        
        Args:
            page: Playwright page
            x: Target X coordinate
            y: Target Y coordinate
            steps: Number of steps for the movement
        """
        # Get current mouse position
        current_pos = page.evaluate("""() => {
            return {x: window.mouseX || 0, y: window.mouseY || 0};
        }""")
        
        current_x = current_pos.get("x", 0)
        current_y = current_pos.get("y", 0)
        
        # Calculate distance
        distance_x = x - current_x
        distance_y = y - current_y
        
        # Generate a slightly curved path with Bezier curve simulation
        for i in range(steps):
            progress = (i + 1) / steps
            
            # Add some randomness to the path
            bezier_x = current_x + distance_x * self._bezier_easing(progress)
            bezier_y = current_y + distance_y * self._bezier_easing(progress)
            
            # Add slight random deviation
            deviation = 5 * (1 - progress)  # Deviation decreases as we get closer to target
            bezier_x += random.uniform(-deviation, deviation)
            bezier_y += random.uniform(-deviation, deviation)
            
            # Move to the next point
            page.mouse.move(bezier_x, bezier_y)
            
            # Random delay between movements
            time.sleep(random.randint(5, 15) / 1000)
    
    def _bezier_easing(self, t: float) -> float:
        """Simple cubic bezier easing function for smooth mouse movement.
        
        Args:
            t: Progress from 0 to 1
            
        Returns:
            float: Eased value
        """
        # Cubic bezier with control points (0, 0), (0.25, 0.1), (0.25, 1.0), (1, 1)
        return 3 * (1 - t) * (1 - t) * t * 0.25 + 3 * (1 - t) * t * t * 0.25 + t * t * t


# Create a singleton instance
interaction_handler = InteractionHandler()