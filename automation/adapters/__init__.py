"""
Website adapters package for handling different job websites.
"""
from .base_adapter import WebsiteAdapter, AdapterConfig, SelectorConfig

__all__ = [
    'WebsiteAdapter',
    'AdapterConfig',
    'SelectorConfig'
]