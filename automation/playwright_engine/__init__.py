"""
Playwright engine package for browser automation.
"""
from .browser_manager import browser_manager, BrowserManager
from .interaction_handler import interaction_handler, InteractionHandler
from .screenshot_manager import screenshot_manager, ScreenshotManager
from .error_handler import error_handler, ErrorHandler

__all__ = [
    'browser_manager',
    'BrowserManager',
    'interaction_handler',
    'InteractionHandler',
    'screenshot_manager',
    'ScreenshotManager',
    'error_handler',
    'ErrorHandler'
]