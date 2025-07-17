"""
Rate limiter for controlling request frequency in browser automation.

This module provides functionality for controlling the frequency of requests
to websites to avoid detection and respect rate limits.
"""
import time
import random
import logging
import threading
from typing import Dict, List, Optional, Tuple, Any, Union
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger(__name__)


class RateLimiter:
    """Rate limiter for controlling request frequency."""
    
    def __init__(self, app=None):
        """Initialize RateLimiter instance.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self._default_delay_ms = 2000  # Default delay between requests in ms
        self._jitter_factor = 0.25  # Random jitter factor (±25%)
        self._domain_delays = {}  # Domain-specific delays
        self._last_request_times = {}  # Last request time per domain
        self._request_counts = {}  # Request count per domain
        self._cooldown_periods = {}  # Cooldown periods for domains
        self._lock = threading.RLock()  # Lock for thread safety
        
        # Default limits
        self._default_limits = {
            "requests_per_minute": 20,
            "requests_per_hour": 300,
            "max_consecutive_requests": 5
        }
        
        # Domain-specific limits
        self._domain_limits = {
            "linkedin.com": {
                "requests_per_minute": 10,
                "requests_per_hour": 100,
                "max_consecutive_requests": 3
            },
            "indeed.com": {
                "requests_per_minute": 8,
                "requests_per_hour": 80,
                "max_consecutive_requests": 3
            }
        }
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the rate limiter with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self._default_delay_ms = app.config.get('RATE_LIMIT_DEFAULT_DELAY_MS', 2000)
        self._jitter_factor = app.config.get('RATE_LIMIT_JITTER_FACTOR', 0.25)
        
        # Load domain-specific settings from config
        domain_delays = app.config.get('RATE_LIMIT_DOMAIN_DELAYS', {})
        for domain, delay in domain_delays.items():
            self.set_domain_delay(domain, delay)
        
        # Load domain-specific limits from config
        domain_limits = app.config.get('RATE_LIMIT_DOMAIN_LIMITS', {})
        for domain, limits in domain_limits.items():
            self._domain_limits[domain] = limits
    
    def wait(self, domain: str = "default") -> None:
        """Wait for the appropriate delay before making a request.
        
        Args:
            domain: Domain name for domain-specific rate limiting
        """
        with self._lock:
            # Get the delay for this domain
            delay_ms = self._get_domain_delay(domain)
            
            # Check if domain is in cooldown
            if domain in self._cooldown_periods:
                cooldown_end = self._cooldown_periods[domain]
                if datetime.now() < cooldown_end:
                    remaining_seconds = (cooldown_end - datetime.now()).total_seconds()
                    logger.info(f"Domain {domain} in cooldown. Waiting {remaining_seconds:.1f} seconds")
                    time.sleep(remaining_seconds)
                    # Remove from cooldown after waiting
                    del self._cooldown_periods[domain]
            
            # Get the last request time for this domain
            last_request_time = self._last_request_times.get(domain, 0)
            
            # Calculate elapsed time since last request
            current_time = time.time() * 1000  # Convert to ms
            elapsed = current_time - last_request_time
            
            # Apply rate limiting if needed
            if elapsed < delay_ms:
                # Calculate wait time with jitter
                base_wait = delay_ms - elapsed
                jitter = base_wait * self._jitter_factor * random.uniform(-1, 1)
                wait_time = max(0, base_wait + jitter)
                
                logger.debug(f"Rate limiting for {domain}: waiting {wait_time:.1f}ms")
                time.sleep(wait_time / 1000)
            
            # Update last request time
            self._last_request_times[domain] = time.time() * 1000
            
            # Update request counts
            self._update_request_count(domain)
            
            # Check if we need to enforce limits
            self._check_limits(domain)
    
    def set_domain_delay(self, domain: str, delay_ms: int) -> None:
        """Set a custom delay for a specific domain.
        
        Args:
            domain: Domain name
            delay_ms: Delay in milliseconds
        """
        with self._lock:
            self._domain_delays[domain] = delay_ms
            logger.info(f"Set rate limit delay for {domain} to {delay_ms}ms")
    
    def get_domain_delay(self, domain: str) -> int:
        """Get the current delay for a domain.
        
        Args:
            domain: Domain name
            
        Returns:
            int: Delay in milliseconds
        """
        return self._get_domain_delay(domain)
    
    def set_cooldown(self, domain: str, duration_seconds: int) -> None:
        """Set a cooldown period for a domain.
        
        Args:
            domain: Domain name
            duration_seconds: Cooldown duration in seconds
        """
        with self._lock:
            cooldown_end = datetime.now() + timedelta(seconds=duration_seconds)
            self._cooldown_periods[domain] = cooldown_end
            logger.info(f"Set cooldown for {domain} for {duration_seconds} seconds")
    
    def get_request_stats(self, domain: str = None) -> Dict[str, Any]:
        """Get request statistics for a domain or all domains.
        
        Args:
            domain: Domain name or None for all domains
            
        Returns:
            Dict[str, Any]: Request statistics
        """
        with self._lock:
            if domain:
                return {
                    "domain": domain,
                    "requests_last_minute": self._get_requests_in_timeframe(domain, 60),
                    "requests_last_hour": self._get_requests_in_timeframe(domain, 3600),
                    "in_cooldown": domain in self._cooldown_periods,
                    "delay_ms": self._get_domain_delay(domain)
                }
            else:
                stats = {}
                domains = set(list(self._last_request_times.keys()) + 
                             list(self._domain_delays.keys()) + 
                             list(self._request_counts.keys()))
                
                for d in domains:
                    stats[d] = self.get_request_stats(d)
                
                return stats
    
    def _get_domain_delay(self, domain: str) -> int:
        """Get the delay for a domain, falling back to default if not set.
        
        Args:
            domain: Domain name
            
        Returns:
            int: Delay in milliseconds
        """
        # Check for exact domain match
        if domain in self._domain_delays:
            return self._domain_delays[domain]
        
        # Check for domain suffix match (e.g., linkedin.com matches www.linkedin.com)
        for d, delay in self._domain_delays.items():
            if domain.endswith(d):
                return delay
        
        # Fall back to default
        return self._default_delay_ms
    
    def _update_request_count(self, domain: str) -> None:
        """Update request count for a domain.
        
        Args:
            domain: Domain name
        """
        current_time = time.time()
        
        if domain not in self._request_counts:
            self._request_counts[domain] = []
        
        # Add current request timestamp
        self._request_counts[domain].append(current_time)
        
        # Remove timestamps older than 1 hour
        one_hour_ago = current_time - 3600
        self._request_counts[domain] = [t for t in self._request_counts[domain] if t > one_hour_ago]
    
    def _get_requests_in_timeframe(self, domain: str, seconds: int) -> int:
        """Get the number of requests in a timeframe.
        
        Args:
            domain: Domain name
            seconds: Timeframe in seconds
            
        Returns:
            int: Number of requests
        """
        if domain not in self._request_counts:
            return 0
        
        current_time = time.time()
        timeframe_start = current_time - seconds
        
        return sum(1 for t in self._request_counts[domain] if t > timeframe_start)
    
    def _check_limits(self, domain: str) -> None:
        """Check if any limits have been exceeded and apply cooldown if needed.
        
        Args:
            domain: Domain name
        """
        # Get limits for this domain
        limits = self._get_domain_limits(domain)
        
        # Check requests per minute
        requests_per_minute = self._get_requests_in_timeframe(domain, 60)
        if requests_per_minute >= limits["requests_per_minute"]:
            logger.warning(f"Rate limit exceeded for {domain}: {requests_per_minute} requests in last minute")
            self.set_cooldown(domain, 60)  # 1 minute cooldown
        
        # Check requests per hour
        requests_per_hour = self._get_requests_in_timeframe(domain, 3600)
        if requests_per_hour >= limits["requests_per_hour"]:
            logger.warning(f"Rate limit exceeded for {domain}: {requests_per_hour} requests in last hour")
            self.set_cooldown(domain, 300)  # 5 minute cooldown
        
        # Check consecutive requests
        consecutive_threshold = limits["max_consecutive_requests"]
        recent_requests = self._get_requests_in_timeframe(domain, 10)  # Last 10 seconds
        
        if recent_requests >= consecutive_threshold:
            logger.warning(f"Too many consecutive requests for {domain}: {recent_requests} in 10 seconds")
            self.set_cooldown(domain, 30)  # 30 second cooldown
    
    def _get_domain_limits(self, domain: str) -> Dict[str, int]:
        """Get the limits for a domain, falling back to default if not set.
        
        Args:
            domain: Domain name
            
        Returns:
            Dict[str, int]: Domain limits
        """
        # Check for exact domain match
        if domain in self._domain_limits:
            return self._domain_limits[domain]
        
        # Check for domain suffix match
        for d, limits in self._domain_limits.items():
            if domain.endswith(d):
                return limits
        
        # Fall back to default
        return self._default_limits


# Create a singleton instance
rate_limiter = RateLimiter()