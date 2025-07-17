# Rate Limiting and Anti-Detection Features

This document describes the rate limiting and anti-detection features implemented in the job application agent to avoid detection by job websites and ensure reliable automation.

## Overview

Job websites employ various techniques to detect and block automated access. Our implementation includes:

1. **Rate Limiting**: Controls the frequency of requests to avoid triggering rate limits
2. **Anti-Detection Measures**: Simulates human behavior to avoid bot detection
3. **Browser Fingerprinting Protection**: Modifies browser fingerprints to appear as a normal user
4. **Error Handling**: Detects and responds to rate limiting and blocking

## Rate Limiter

The `RateLimiter` class (`automation/playwright_engine/rate_limiter.py`) provides:

- Domain-specific rate limiting with configurable delays
- Automatic cooldown periods when rate limiting is detected
- Request counting to enforce limits (requests per minute/hour)
- Jitter in delays to avoid predictable patterns

### Key Features

- **Domain-specific Delays**: Different websites have different sensitivity to automation
- **Cooldown Periods**: Automatically backs off when rate limiting is detected
- **Request Tracking**: Monitors request frequency to stay under limits
- **Jitter**: Adds randomness to delays to appear more human-like

### Usage

```python
# Wait before making a request to a domain
rate_limiter.wait("example.com")

# Set a custom delay for a domain
rate_limiter.set_domain_delay("example.com", 3000)  # 3 seconds

# Set a cooldown period when rate limiting is detected
rate_limiter.set_cooldown("example.com", 60)  # 1 minute cooldown
```

## Anti-Detection

The `AntiDetection` class (`automation/playwright_engine/anti_detection.py`) provides:

- Human-like mouse movements and scrolling
- Browser fingerprint modification
- User agent rotation
- Evasion of common bot detection techniques

### Key Features

- **Human Behavior Simulation**: Random mouse movements, scrolling, and delays
- **Browser Fingerprint Protection**: Modifies JavaScript APIs used for fingerprinting
- **User Agent Rotation**: Uses realistic and up-to-date user agents
- **Evasion Techniques**: Bypasses common bot detection methods

### Usage

```python
# Apply evasion techniques to a browser context
anti_detection.apply_evasion_techniques(context)

# Simulate human behavior on a page
anti_detection.simulate_human_behavior(page)

# Get a random user agent
user_agent = anti_detection.rotate_user_agent()

# Add noise to browser fingerprinting
anti_detection.add_browser_fingerprint_noise(context)
```

## Integration in Website Adapters

The base `WebsiteAdapter` class integrates these features:

- Automatically applies rate limiting before requests
- Applies anti-detection measures after page loads
- Adds random delays between actions
- Detects and responds to rate limiting

### Example

```python
def navigate(self, url: str, wait_for_load: bool = True) -> bool:
    try:
        # Apply rate limiting
        self._apply_rate_limiting()
        
        # Navigate to URL
        page = self.get_page()
        page.goto(url, timeout=self.timeout)
        
        # Wait for page to load
        if wait_for_load:
            interaction_handler.wait_for_navigation(page, self.timeout)
        
        # Check for rate limiting
        if error_handler.detect_rate_limiting(page):
            rate_limiter.set_cooldown(self._domain, 60)
            raise AutomationError("Rate limiting detected", "rate_limit", True)
        
        # Apply anti-detection measures
        self._apply_anti_detection_measures(page)
        
        return True
        
    except Exception as e:
        # Handle errors
        return False
```

## Configuration

The rate limiting and anti-detection features can be configured through the Flask application configuration:

```python
# Rate limiting configuration
app.config['RATE_LIMIT_DEFAULT_DELAY_MS'] = 2000
app.config['RATE_LIMIT_JITTER_FACTOR'] = 0.25
app.config['RATE_LIMIT_DOMAIN_DELAYS'] = {
    'linkedin.com': 3000,
    'indeed.com': 3500
}

# Anti-detection configuration
app.config['ENABLE_ANTI_DETECTION'] = True
app.config['USER_AGENTS_FILE'] = 'path/to/user_agents.json'
```

## Best Practices

1. **Start Slow**: Begin with conservative rate limits and gradually increase if needed
2. **Monitor Blocks**: Track when the automation is detected and adjust accordingly
3. **Vary Behavior**: Don't use the same patterns for every session
4. **Respect Website Terms**: Ensure automation complies with website terms of service
5. **Handle Failures Gracefully**: Implement proper error handling and recovery

## Testing

Unit tests are provided to verify the functionality of the rate limiting and anti-detection features:

- `tests/test_rate_limiter.py`: Tests for the rate limiter
- `tests/test_anti_detection.py`: Tests for the anti-detection module
- `tests/test_adapter_anti_detection.py`: Tests for the integration in website adapters