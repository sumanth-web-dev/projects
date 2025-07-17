"""
Website adapters package for handling different job websites.
"""
from .base_adapter import WebsiteAdapter, AdapterConfig, SelectorConfig
from .linkedin_adapter import LinkedInAdapter, linkedin_adapter
from .indeed_adapter import IndeedAdapter

# Create singleton instance
indeed_adapter = IndeedAdapter()

__all__ = [
    'WebsiteAdapter',
    'AdapterConfig',
    'SelectorConfig',
    'LinkedInAdapter',
    'linkedin_adapter',
    'IndeedAdapter',
    'indeed_adapter'
]