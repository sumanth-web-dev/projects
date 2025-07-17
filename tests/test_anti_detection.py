"""
Tests for the anti-detection module.

This module contains tests for the anti-detection functionality to ensure
it correctly applies evasion techniques and simulates human behavior.
"""
import unittest
from unittest.mock import patch, MagicMock, call

from automation.playwright_engine.anti_detection import AntiDetection


class TestAntiDetection(unittest.TestCase):
    """Test cases for the AntiDetection class."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.anti_detection = AntiDetection()
    
    def test_rotate_user_agent(self):
        """Test that rotate_user_agent returns a valid user agent string."""
        user_agent = self.anti_detection.rotate_user_agent()
        self.assertIsInstance(user_agent, str)
        self.assertGreater(len(user_agent), 10)  # Basic validation
    
    def test_user_agent_rotation(self):
        """Test that user agents are rotated."""
        # Set a small list of test user agents
        self.anti_detection._user_agents = [
            "User Agent 1",
            "User Agent 2",
            "User Agent 3"
        ]
        
        # Get multiple user agents and ensure we get different ones
        agents = set()
        for _ in range(10):
            agents.add(self.anti_detection.rotate_user_agent())
        
        # Should have at least 2 different user agents
        self.assertGreaterEqual(len(agents), 2)
    
    @patch('automation.playwright_engine.anti_detection.logger')
    def test_apply_evasion_techniques(self, mock_logger):
        """Test applying evasion techniques to a browser context."""
        # Create a mock context
        mock_context = MagicMock()
        
        # Call the method
        self.anti_detection.apply_evasion_techniques(mock_context)
        
        # Verify that add_init_script was called
        mock_context.add_init_script.assert_called_once()
        
        # Verify that the logger was called
        mock_logger.info.assert_called_once()
    
    @patch('automation.playwright_engine.anti_detection.logger')
    def test_disabled_evasion(self, mock_logger):
        """Test that evasion techniques are not applied when disabled."""
        # Disable evasion
        self.anti_detection._enable_evasion = False
        
        # Create a mock context
        mock_context = MagicMock()
        
        # Call the method
        self.anti_detection.apply_evasion_techniques(mock_context)
        
        # Verify that add_init_script was not called
        mock_context.add_init_script.assert_not_called()
    
    @patch('automation.playwright_engine.anti_detection.time.sleep')
    def test_simulate_human_behavior(self, mock_sleep):
        """Test simulating human behavior on a page."""
        # Create a mock page
        mock_page = MagicMock()
        mock_page.viewport_size = {"width": 1920, "height": 1080}
        mock_page.evaluate.return_value = 1000  # Mock page height
        
        # Call the method
        self.anti_detection.simulate_human_behavior(mock_page)
        
        # Verify that mouse movements and scrolling were performed
        self.assertGreater(mock_page.mouse.move.call_count, 0)
        self.assertGreater(mock_sleep.call_count, 0)
    
    @patch('automation.playwright_engine.anti_detection.logger')
    def test_add_browser_fingerprint_noise(self, mock_logger):
        """Test adding browser fingerprint noise."""
        # Create a mock context
        mock_context = MagicMock()
        
        # Call the method
        self.anti_detection.add_browser_fingerprint_noise(mock_context)
        
        # Verify that add_init_script was called
        mock_context.add_init_script.assert_called_once()
        
        # Verify that the logger was called
        mock_logger.info.assert_called_once()


if __name__ == '__main__':
    unittest.main()