"""
Tests for the anti-detection and rate limiting integration in website adapters.

This module contains tests to verify that the website adapters correctly
integrate with the rate limiter and anti-detection modules.
"""
import unittest
from unittest.mock import patch, MagicMock, call

from automation.adapters.base_adapter import WebsiteAdapter, AdapterConfig, SelectorConfig


class TestAdapterAntiDetection(unittest.TestCase):
    """Test cases for anti-detection and rate limiting in WebsiteAdapter."""
    
    def setUp(self):
        """Set up test fixtures."""
        # Create a simple adapter configuration
        selectors = SelectorConfig({})
        self.config = AdapterConfig(
            name="test",
            base_url="https://example.com",
            selectors=selectors,
            rate_limit_delay=1000
        )
    
    @patch('automation.adapters.base_adapter.rate_limiter')
    def test_adapter_sets_rate_limit_delay(self, mock_rate_limiter):
        """Test that adapter sets domain-specific rate limit delay."""
        # Create adapter
        adapter = WebsiteAdapter(self.config)
        
        # Verify that set_domain_delay was called with correct parameters
        mock_rate_limiter.set_domain_delay.assert_called_once_with("example.com", 1000)
    
    @patch('automation.adapters.base_adapter.rate_limiter')
    def test_apply_rate_limiting(self, mock_rate_limiter):
        """Test that _apply_rate_limiting calls rate_limiter.wait."""
        # Create adapter
        adapter = WebsiteAdapter(self.config)
        
        # Call _apply_rate_limiting
        adapter._apply_rate_limiting()
        
        # Verify that wait was called with correct domain
        mock_rate_limiter.wait.assert_called_once_with("example.com")
    
    @patch('automation.adapters.base_adapter.anti_detection')
    def test_apply_anti_detection_measures(self, mock_anti_detection):
        """Test that _apply_anti_detection_measures calls anti_detection.simulate_human_behavior."""
        # Create adapter
        adapter = WebsiteAdapter(self.config)
        
        # Create mock page
        mock_page = MagicMock()
        
        # Call _apply_anti_detection_measures
        adapter._apply_anti_detection_measures(mock_page)
        
        # Verify that simulate_human_behavior was called with correct page
        mock_anti_detection.simulate_human_behavior.assert_called_once_with(mock_page)
    
    @patch('automation.adapters.base_adapter.time.sleep')
    def test_add_random_delay(self, mock_sleep):
        """Test that _add_random_delay adds a delay within the specified range."""
        # Create adapter
        adapter = WebsiteAdapter(self.config)
        
        # Call _add_random_delay with specific range
        min_ms = 100
        max_ms = 200
        adapter._add_random_delay(min_ms, max_ms)
        
        # Verify that sleep was called with a value in the correct range
        sleep_arg = mock_sleep.call_args[0][0]
        self.assertTrue(min_ms/1000 <= sleep_arg <= max_ms/1000)
    
    @patch('automation.adapters.base_adapter.rate_limiter')
    @patch('automation.adapters.base_adapter.error_handler')
    def test_navigate_sets_cooldown_on_rate_limit(self, mock_error_handler, mock_rate_limiter):
        """Test that navigate sets a cooldown when rate limiting is detected."""
        # Create adapter with mocked components
        adapter = WebsiteAdapter(self.config)
        adapter.get_page = MagicMock(return_value=MagicMock())
        adapter._apply_rate_limiting = MagicMock()
        adapter._apply_anti_detection_measures = MagicMock()
        
        # Configure error_handler to detect rate limiting
        mock_error_handler.detect_rate_limiting.return_value = True
        
        # Call navigate
        result = adapter.navigate("https://example.com/test")
        
        # Verify that set_cooldown was called
        mock_rate_limiter.set_cooldown.assert_called_once_with("example.com", 60)


if __name__ == '__main__':
    unittest.main()