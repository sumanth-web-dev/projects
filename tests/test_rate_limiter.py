"""
Tests for the rate limiter module.

This module contains tests for the rate limiter functionality to ensure
it correctly limits request rates and applies cooldown periods.
"""
import time
import unittest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta

from automation.playwright_engine.rate_limiter import RateLimiter


class TestRateLimiter(unittest.TestCase):
    """Test cases for the RateLimiter class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.rate_limiter = RateLimiter()
        # Reset state
        self.rate_limiter._domain_delays = {}
        self.rate_limiter._last_request_times = {}
        self.rate_limiter._request_counts = {}
        self.rate_limiter._cooldown_periods = {}
    
    def test_set_domain_delay(self):
        """Test setting a domain-specific delay."""
        self.rate_limiter.set_domain_delay("example.com", 5000)
        self.assertEqual(self.rate_limiter.get_domain_delay("example.com"), 5000)
    
    def test_default_delay(self):
        """Test that default delay is used when no domain-specific delay is set."""
        self.assertEqual(self.rate_limiter.get_domain_delay("unknown.com"), 
                         self.rate_limiter._default_delay_ms)
    
    def test_wait_applies_delay(self):
        """Test that wait applies the appropriate delay."""
        # Set a specific delay for testing
        test_delay = 500  # ms
        self.rate_limiter.set_domain_delay("test.com", test_delay)
        
        # Record start time
        start_time = time.time()
        
        # First request should not wait
        self.rate_limiter.wait("test.com")
        
        # Second request should wait approximately test_delay
        self.rate_limiter.wait("test.com")
        
        # Calculate elapsed time
        elapsed = (time.time() - start_time) * 1000  # Convert to ms
        
        # Allow for some margin of error in timing
        self.assertGreaterEqual(elapsed, test_delay * 0.8)  # At least 80% of expected delay
    
    def test_cooldown_period(self):
        """Test that cooldown periods are respected."""
        # Set a cooldown of 2 seconds
        cooldown_seconds = 2
        self.rate_limiter.set_cooldown("test.com", cooldown_seconds)
        
        # Record start time
        start_time = time.time()
        
        # Wait should respect the cooldown
        self.rate_limiter.wait("test.com")
        
        # Calculate elapsed time
        elapsed = time.time() - start_time
        
        # Should have waited at least the cooldown period
        self.assertGreaterEqual(elapsed, cooldown_seconds * 0.8)  # At least 80% of expected delay
    
    @patch('time.sleep')
    def test_rate_limiting_logic(self, mock_sleep):
        """Test the rate limiting logic with mocked sleep."""
        # Set up test data
        domain = "test.com"
        delay_ms = 1000
        self.rate_limiter.set_domain_delay(domain, delay_ms)
        
        # First request - no delay
        self.rate_limiter.wait(domain)
        mock_sleep.assert_not_called()
        
        # Set last request time manually to simulate elapsed time
        self.rate_limiter._last_request_times[domain] = time.time() * 1000 - 500  # 500ms ago
        
        # Second request - should wait approximately 500ms
        self.rate_limiter.wait(domain)
        # Allow for jitter in the calculation
        call_arg = mock_sleep.call_args[0][0]
        self.assertTrue(400 <= call_arg * 1000 <= 600)  # Between 400-600ms with jitter
    
    def test_request_counting(self):
        """Test that requests are counted correctly."""
        domain = "test.com"
        
        # Make several requests
        for _ in range(5):
            self.rate_limiter.wait(domain)
        
        # Check request count in the last minute
        count = self.rate_limiter._get_requests_in_timeframe(domain, 60)
        self.assertEqual(count, 5)
    
    def test_domain_limits(self):
        """Test that domain-specific limits are applied."""
        # Create a rate limiter with specific test limits
        limiter = RateLimiter()
        limiter._domain_limits = {
            "test.com": {
                "requests_per_minute": 3,
                "requests_per_hour": 10,
                "max_consecutive_requests": 2
            }
        }
        
        # Make requests up to the limit
        domain = "test.com"
        for _ in range(2):
            limiter.wait(domain)
        
        # No cooldown should be set yet
        self.assertNotIn(domain, limiter._cooldown_periods)
        
        # Make one more request to exceed the consecutive limit
        limiter.wait(domain)
        
        # Now a cooldown should be set
        self.assertIn(domain, limiter._cooldown_periods)


if __name__ == '__main__':
    unittest.main()