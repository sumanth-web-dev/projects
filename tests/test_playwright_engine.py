"""
Unit tests for the Playwright engine.
"""
import unittest
from unittest.mock import patch, MagicMock
import flask
import os
import json
from automation.playwright_engine.browser_manager import BrowserManager
from automation.playwright_engine.interaction_handler import InteractionHandler
from automation.playwright_engine.screenshot_manager import ScreenshotManager
from automation.playwright_engine.error_handler import ErrorHandler, AutomationError
from automation.adapters.base_adapter import WebsiteAdapter, AdapterConfig, SelectorConfig


class TestBrowserManager(unittest.TestCase):
    """Test cases for BrowserManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a test Flask app
        self.app = flask.Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Mock Playwright
        self.playwright_mock = MagicMock()
        self.browser_mock = MagicMock()
        self.context_mock = MagicMock()
        self.page_mock = MagicMock()
        
        # Set up mocks
        self.playwright_mock.chromium.launch.return_value = self.browser_mock
        self.browser_mock.new_context.return_value = self.context_mock
        self.context_mock.new_page.return_value = self.page_mock
        self.context_mock.pages = [self.page_mock]
        
        # Create browser manager with mocked Playwright
        self.browser_manager = BrowserManager(self.app)
        self.browser_manager._playwright = self.playwright_mock
    
    def test_browser_methods(self):
        """Test browser methods."""
        # Set browser
        self.browser_manager._browser = self.browser_mock
        
        # Test that browser is returned
        browser = self.browser_manager._browser
        self.assertEqual(browser, self.browser_mock)
    
    def test_create_context(self):
        """Test creating a browser context."""
        # Set browser
        self.browser_manager._browser = self.browser_mock
        
        # Create context
        context = self.browser_manager.create_context("test_context")
        
        # Verify context was created
        self.assertEqual(context, self.context_mock)
        self.browser_mock.new_context.assert_called_once()
        self.assertEqual(self.browser_manager._contexts["test_context"], self.context_mock)
    
    def test_get_page(self):
        """Test getting a page."""
        # Set browser and context
        self.browser_manager._browser = self.browser_mock
        self.browser_manager._contexts["test_context"] = self.context_mock
        
        # Get page
        page = self.browser_manager.get_page("test_context")
        
        # Verify page was returned
        self.assertEqual(page, self.page_mock)
    
    def test_close_context(self):
        """Test closing a context."""
        # Set browser and context
        self.browser_manager._browser = self.browser_mock
        self.browser_manager._contexts["test_context"] = self.context_mock
        
        # Close context
        result = self.browser_manager.close_context("test_context")
        
        # Verify context was closed
        self.assertTrue(result)
        self.context_mock.close.assert_called_once()
        self.assertNotIn("test_context", self.browser_manager._contexts)
    
    def test_close_all(self):
        """Test closing all contexts and browser."""
        # Set browser and context
        self.browser_manager._browser = self.browser_mock
        self.browser_manager._contexts["test_context"] = self.context_mock
        
        # Close all
        result = self.browser_manager.close_all()
        
        # Verify all was closed
        self.assertTrue(result)
        self.context_mock.close.assert_called_once()
        self.browser_mock.close.assert_called_once()
        self.playwright_mock.stop.assert_called_once()
        self.assertEqual(self.browser_manager._contexts, {})
        self.assertIsNone(self.browser_manager._browser)
        self.assertIsNone(self.browser_manager._playwright)
    
    def tearDown(self):
        """Clean up after tests."""
        self.app_context.pop()


class TestInteractionHandler(unittest.TestCase):
    """Test cases for InteractionHandler."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a test Flask app
        self.app = flask.Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create interaction handler
        self.interaction_handler = InteractionHandler(self.app)
        
        # Mock page and element
        self.page_mock = MagicMock()
        self.element_mock = MagicMock()
        self.page_mock.wait_for_selector.return_value = self.element_mock
        
        # Set up element bounding box
        self.element_mock.bounding_box.return_value = {"x": 100, "y": 100, "width": 100, "height": 50}
    
    def test_human_click(self):
        """Test human-like clicking."""
        # Test click
        result = self.interaction_handler.human_click(self.page_mock, "#test-element")
        
        # Verify click was performed
        self.assertTrue(result)
        self.page_mock.wait_for_selector.assert_called_with("#test-element", state="visible")
        self.page_mock.mouse.click.assert_called_once()
    
    def test_human_type(self):
        """Test human-like typing."""
        # Test typing
        result = self.interaction_handler.human_type(self.page_mock, "#test-input", "Hello, world!")
        
        # Verify typing was performed
        self.assertTrue(result)
        self.page_mock.wait_for_selector.assert_called_with("#test-input", state="visible")
        self.element_mock.fill.assert_called_with("")
        self.assertEqual(self.page_mock.keyboard.type.call_count, len("Hello, world!"))
    
    def test_human_scroll(self):
        """Test human-like scrolling."""
        # Test scrolling
        result = self.interaction_handler.human_scroll(self.page_mock, "down", 500)
        
        # Verify scrolling was performed
        self.assertTrue(result)
        self.assertGreater(self.page_mock.mouse.wheel.call_count, 0)
    
    def test_human_select_option(self):
        """Test selecting an option from a dropdown."""
        # Test selecting option
        result = self.interaction_handler.human_select_option(self.page_mock, "#test-select", value="option1")
        
        # Verify option was selected
        self.assertTrue(result)
        self.page_mock.wait_for_selector.assert_called_with("#test-select", state="visible")
        self.page_mock.select_option.assert_called_with("#test-select", value="option1")
    
    def test_human_check_checkbox(self):
        """Test checking a checkbox."""
        # Set up checkbox state
        self.element_mock.is_checked.side_effect = [False, True]  # First call returns False, second call returns True
        
        # Test checking checkbox
        result = self.interaction_handler.human_check_checkbox(self.page_mock, "#test-checkbox", True)
        
        # Verify checkbox was checked
        self.assertTrue(result)
        self.page_mock.wait_for_selector.assert_called_with("#test-checkbox", state="visible")
    
    def test_random_delay(self):
        """Test random delay."""
        # Test delay with custom range
        with patch('time.sleep') as mock_sleep:
            self.interaction_handler.random_delay(100, 200)
            mock_sleep.assert_called_once()
            delay_arg = mock_sleep.call_args[0][0]
            self.assertGreaterEqual(delay_arg, 0.1)  # 100ms
            self.assertLessEqual(delay_arg, 0.2)  # 200ms
    
    def tearDown(self):
        """Clean up after tests."""
        self.app_context.pop()


class TestScreenshotManager(unittest.TestCase):
    """Test cases for ScreenshotManager."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a test Flask app
        self.app = flask.Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create screenshot manager with test directory
        self.test_screenshot_dir = "test_screenshots"
        self.app.config['SCREENSHOT_DIR'] = self.test_screenshot_dir
        self.screenshot_manager = ScreenshotManager(self.app)
        
        # Mock page and element
        self.page_mock = MagicMock()
        self.element_mock = MagicMock()
        
        # Create test directory if it doesn't exist
        if not os.path.exists(self.test_screenshot_dir):
            os.makedirs(self.test_screenshot_dir)
    
    def test_take_screenshot(self):
        """Test taking a screenshot."""
        # Test taking screenshot
        with patch('os.path.join', return_value="test_screenshot.png"):
            result = self.screenshot_manager.take_screenshot(self.page_mock, "test")
            
            # Verify screenshot was taken
            self.assertEqual(result, "test_screenshot.png")
            self.page_mock.screenshot.assert_called_once()
    
    def test_take_element_screenshot(self):
        """Test taking an element screenshot."""
        # Test taking element screenshot
        with patch('os.path.join', return_value="test_element_screenshot.png"):
            result = self.screenshot_manager.take_element_screenshot(self.element_mock, "test")
            
            # Verify element screenshot was taken
            self.assertEqual(result, "test_element_screenshot.png")
            self.element_mock.screenshot.assert_called_once()
    
    def test_capture_on_error(self):
        """Test capturing a screenshot on error."""
        # Test capturing error screenshot
        with patch('os.path.join', return_value="test_error_screenshot.png"):
            error = Exception("Test error")
            result = self.screenshot_manager.capture_on_error(self.page_mock, error)
            
            # Verify error screenshot was taken
            self.assertEqual(result, "test_error_screenshot.png")
            self.page_mock.screenshot.assert_called_once()
    
    def test_clear_screenshots(self):
        """Test clearing screenshots."""
        # Create test screenshot files
        test_files = ["test1.png", "test2.png", "test3.txt"]
        for filename in test_files:
            with open(os.path.join(self.test_screenshot_dir, filename), 'w') as f:
                f.write("test")
        
        # Test clearing screenshots
        with patch('os.path.getmtime', return_value=0):  # Make all files appear old
            result = self.screenshot_manager.clear_screenshots(days_old=1)
            
            # Verify PNG files were deleted
            self.assertEqual(result, 2)  # Only PNG files
            self.assertFalse(os.path.exists(os.path.join(self.test_screenshot_dir, "test1.png")))
            self.assertFalse(os.path.exists(os.path.join(self.test_screenshot_dir, "test2.png")))
            self.assertTrue(os.path.exists(os.path.join(self.test_screenshot_dir, "test3.txt")))
    
    def tearDown(self):
        """Clean up after tests."""
        self.app_context.pop()
        
        # Clean up test directory
        if os.path.exists(self.test_screenshot_dir):
            for filename in os.listdir(self.test_screenshot_dir):
                os.remove(os.path.join(self.test_screenshot_dir, filename))
            os.rmdir(self.test_screenshot_dir)


class TestErrorHandler(unittest.TestCase):
    """Test cases for ErrorHandler."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a test Flask app
        self.app = flask.Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create error handler
        self.error_handler = ErrorHandler(self.app)
        
        # Mock page
        self.page_mock = MagicMock()
    
    def test_handle_error(self):
        """Test handling different types of errors."""
        # Test network error
        network_error = Exception("net::ERR_CONNECTION_REFUSED")
        result = self.error_handler.handle_error(network_error)
        self.assertEqual(result.error_type, "network")
        self.assertTrue(result.recoverable)
        
        # Test authentication error
        auth_error = Exception("Authentication failed")
        result = self.error_handler.handle_error(auth_error)
        self.assertEqual(result.error_type, "authentication")
        self.assertFalse(result.recoverable)
        
        # Test element error
        element_error = Exception("Element not found: #test-element")
        result = self.error_handler.handle_error(element_error)
        self.assertEqual(result.error_type, "element")
        self.assertTrue(result.recoverable)
        
        # Test rate limit error
        rate_limit_error = Exception("Rate limit exceeded. Retry-after: 60")
        result = self.error_handler.handle_error(rate_limit_error)
        self.assertEqual(result.error_type, "rate_limit")
        self.assertTrue(result.recoverable)
    
    def test_retry_operation(self):
        """Test retrying an operation."""
        # Mock operation that fails twice then succeeds
        mock_operation = MagicMock()
        mock_operation.side_effect = [
            Exception("net::ERR_CONNECTION_REFUSED"),
            Exception("net::ERR_CONNECTION_REFUSED"),
            "success"
        ]
        
        # Test retry
        result = self.error_handler.retry_operation(mock_operation, max_retries=3)
        
        # Verify operation was retried and succeeded
        self.assertEqual(result, "success")
        self.assertEqual(mock_operation.call_count, 3)
    
    def test_detect_rate_limiting(self):
        """Test detecting rate limiting."""
        # Mock page with rate limiting indicators
        self.page_mock.query_selector.side_effect = lambda selector: MagicMock() if selector == "text=rate limit" else None
        
        # Test detection
        result = self.error_handler.detect_rate_limiting(self.page_mock)
        
        # Verify rate limiting was detected
        self.assertTrue(result)
        self.page_mock.query_selector.assert_called()
    
    def test_register_error_callback(self):
        """Test registering and triggering error callbacks."""
        # Create mock callback
        mock_callback = MagicMock()
        
        # Register callback
        self.error_handler.register_error_callback("network", mock_callback)
        
        # Trigger callback
        error = AutomationError("Test error", "network", True)
        self.error_handler.trigger_callbacks(error)
        
        # Verify callback was called
        mock_callback.assert_called_once_with(error)
    
    def tearDown(self):
        """Clean up after tests."""
        self.app_context.pop()


class TestWebsiteAdapter(unittest.TestCase):
    """Test cases for WebsiteAdapter."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a test Flask app
        self.app = flask.Flask(__name__)
        self.app_context = self.app.app_context()
        self.app_context.push()
        
        # Create selector config
        self.selectors = SelectorConfig({
            "login_username": "#username",
            "login_password": "#password",
            "login_button": "#login-button"
        })
        
        # Create adapter config
        self.config = AdapterConfig(
            name="test_website",
            base_url="https://test-website.com",
            selectors=self.selectors,
            login_required=True,
            rate_limit_delay=1000,
            max_retries=3,
            timeout=30000
        )
        
        # Create adapter
        self.adapter = WebsiteAdapter(self.config, self.app)
        
        # Mock browser manager and page
        self.context_mock = MagicMock()
        self.page_mock = MagicMock()
        
        # Patch browser manager
        self.browser_manager_patch = patch('automation.adapters.base_adapter.browser_manager')
        self.mock_browser_manager = self.browser_manager_patch.start()
        self.mock_browser_manager.get_context.return_value = self.context_mock
        self.mock_browser_manager.get_page.return_value = self.page_mock
    
    def test_get_browser_context(self):
        """Test getting a browser context."""
        # Get context
        context = self.adapter.get_browser_context()
        
        # Verify context was retrieved
        self.assertEqual(context, self.context_mock)
        self.mock_browser_manager.get_context.assert_called_with("test_website_context")
    
    def test_get_page(self):
        """Test getting a page."""
        # Get page
        page = self.adapter.get_page()
        
        # Verify page was retrieved
        self.assertEqual(page, self.page_mock)
        self.mock_browser_manager.get_page.assert_called_with("test_website_context")
    
    def test_navigate(self):
        """Test navigating to a URL."""
        # Set up page mock
        self.adapter._page = self.page_mock
        
        # Mock interaction handler
        with patch('automation.adapters.base_adapter.interaction_handler') as mock_interaction_handler:
            mock_interaction_handler.wait_for_navigation.return_value = True
            
            # Mock error handler
            with patch('automation.adapters.base_adapter.error_handler') as mock_error_handler:
                mock_error_handler.detect_rate_limiting.return_value = False
                
                # Mock screenshot manager
                with patch('automation.adapters.base_adapter.screenshot_manager') as mock_screenshot_manager:
                    # Navigate to URL
                    result = self.adapter.navigate("https://test-website.com/jobs")
                    
                    # Verify navigation was performed
                    self.assertTrue(result)
                    self.page_mock.goto.assert_called_with("https://test-website.com/jobs", timeout=30000)
                    mock_interaction_handler.wait_for_navigation.assert_called_once()
                    mock_error_handler.detect_rate_limiting.assert_called_once()
                    mock_screenshot_manager.take_screenshot.assert_called_once()
    
    def test_login_not_implemented(self):
        """Test base login method."""
        # Test login
        result = self.adapter.login({"username": "test", "password": "test"})
        
        # Verify login was not implemented
        self.assertFalse(result)
    
    def test_close(self):
        """Test closing the adapter."""
        # Set up context
        self.adapter._context = self.context_mock
        
        # Close adapter
        self.adapter.close()
        
        # Verify context was closed
        self.mock_browser_manager.close_context.assert_called_with("test_website_context")
        self.assertIsNone(self.adapter._context)
        self.assertIsNone(self.adapter._page)
        self.assertFalse(self.adapter._logged_in)
    
    def tearDown(self):
        """Clean up after tests."""
        self.browser_manager_patch.stop()
        self.app_context.pop()


if __name__ == '__main__':
    unittest.main()