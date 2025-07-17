/**
 * Main JavaScript file for Job Application Agent
 */

// Wait for DOM to be fully loaded
document.addEventListener('DOMContentLoaded', function() {
  // Initialize any global components
  initializeAlerts();
});

/**
 * Initialize alert dismissal functionality
 */
function initializeAlerts() {
  const alerts = document.querySelectorAll('.alert');
  
  alerts.forEach(alert => {
    // Add close button to alerts
    const closeBtn = document.createElement('button');
    closeBtn.innerHTML = '&times;';
    closeBtn.className = 'alert-close';
    closeBtn.setAttribute('aria-label', 'Close');
    
    closeBtn.addEventListener('click', () => {
      alert.style.opacity = '0';
      setTimeout(() => {
        alert.remove();
      }, 300);
    });
    
    alert.appendChild(closeBtn);
    
    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      if (alert && alert.parentNode) {
        alert.style.opacity = '0';
        setTimeout(() => {
          if (alert && alert.parentNode) {
            alert.remove();
          }
        }, 300);
      }
    }, 5000);
  });
}

/**
 * Helper function to make API requests
 * @param {string} url - The API endpoint URL
 * @param {string} method - HTTP method (GET, POST, PUT, DELETE)
 * @param {Object} data - Request payload (for POST/PUT)
 * @returns {Promise} - Promise resolving to response data
 */
async function apiRequest(url, method = 'GET', data = null) {
  const options = {
    method,
    headers: {
      'Content-Type': 'application/json',
      'X-Requested-With': 'XMLHttpRequest'
    },
    credentials: 'same-origin'
  };
  
  if (data && method !== 'GET') {
    options.body = JSON.stringify(data);
  }
  
  try {
    const response = await fetch(url, options);
    
    // Handle non-2xx responses
    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.message || 'An error occurred');
    }
    
    // Check if response is JSON
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
      return await response.json();
    }
    
    return await response.text();
  } catch (error) {
    console.error('API Request Error:', error);
    throw error;
  }
}

/**
 * Display a notification message
 * @param {string} message - The message to display
 * @param {string} type - Message type (success, error, warning, info)
 */
function showNotification(message, type = 'info') {
  const container = document.querySelector('main.container');
  if (!container) return;
  
  const alert = document.createElement('div');
  alert.className = `alert alert-${type}`;
  alert.textContent = message;
  
  // Add close button
  const closeBtn = document.createElement('button');
  closeBtn.innerHTML = '&times;';
  closeBtn.className = 'alert-close';
  closeBtn.setAttribute('aria-label', 'Close');
  
  closeBtn.addEventListener('click', () => {
    alert.style.opacity = '0';
    setTimeout(() => {
      alert.remove();
    }, 300);
  });
  
  alert.appendChild(closeBtn);
  
  // Insert at the top of the container
  container.insertBefore(alert, container.firstChild);
  
  // Auto-dismiss after 5 seconds
  setTimeout(() => {
    if (alert && alert.parentNode) {
      alert.style.opacity = '0';
      setTimeout(() => {
        if (alert && alert.parentNode) {
          alert.remove();
        }
      }, 300);
    }
  }, 5000);
}