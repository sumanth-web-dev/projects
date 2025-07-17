// Settings Page JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Tab Navigation
    const tabButtons = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    
    tabButtons.forEach(button => {
        button.addEventListener('click', () => {
            const tabId = button.getAttribute('data-tab');
            
            // Update active tab button
            tabButtons.forEach(btn => btn.classList.remove('active'));
            button.classList.add('active');
            
            // Show selected tab content
            tabPanes.forEach(pane => {
                pane.classList.remove('active');
                if (pane.id === tabId) {
                    pane.classList.add('active');
                }
            });
            
            // Save active tab to session storage
            sessionStorage.setItem('activeSettingsTab', tabId);
        });
    });
    
    // Restore active tab from session storage
    const activeTab = sessionStorage.getItem('activeSettingsTab');
    if (activeTab) {
        const activeButton = document.querySelector(`.tab-btn[data-tab="${activeTab}"]`);
        if (activeButton) {
            activeButton.click();
        }
    }
    
    // Form submission handlers
    setupFormHandlers();
    
    // API Access Toggle
    const apiAccessToggle = document.getElementById('enable_api_access');
    const apiKeySection = document.getElementById('api_key_section');
    
    if (apiAccessToggle && apiKeySection) {
        apiAccessToggle.addEventListener('change', function() {
            apiKeySection.style.display = this.checked ? 'block' : 'none';
        });
    }
    
    // Copy API Key
    const copyApiKeyButton = document.getElementById('copy_api_key');
    const apiKeyInput = document.getElementById('api_key');
    
    if (copyApiKeyButton && apiKeyInput) {
        copyApiKeyButton.addEventListener('click', function() {
            apiKeyInput.select();
            document.execCommand('copy');
            
            // Show copied notification
            const originalText = this.textContent;
            this.textContent = 'Copied!';
            setTimeout(() => {
                this.textContent = originalText;
            }, 2000);
        });
    }
    
    // Regenerate API Key
    const regenerateApiKeyButton = document.getElementById('regenerate_api_key');
    
    if (regenerateApiKeyButton) {
        regenerateApiKeyButton.addEventListener('click', function() {
            if (confirm('Are you sure you want to regenerate your API key? This will invalidate the current key.')) {
                fetch('/api/settings/regenerate-api-key', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCsrfToken()
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        apiKeyInput.value = data.api_key;
                        showNotification('API key regenerated successfully', 'success');
                    } else {
                        showNotification('Failed to regenerate API key', 'error');
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    showNotification('An error occurred', 'error');
                });
            }
        });
    }
    
    // Credential Management
    const credentialButtons = document.querySelectorAll('[data-action]');
    const credentialModal = document.getElementById('credential-modal');
    const credentialForm = document.getElementById('credential-form');
    const credentialService = document.getElementById('credential-service');
    const credentialModalTitle = document.getElementById('credential-modal-title');
    const closeModalButton = document.querySelector('.close');
    const cancelCredentialButton = document.getElementById('cancel-credential');
    
    // Open credential modal
    credentialButtons.forEach(button => {
        button.addEventListener('click', function() {
            const action = this.getAttribute('data-action');
            const service = this.getAttribute('data-service');
            
            credentialService.value = service;
            
            if (action === 'edit') {
                credentialModalTitle.textContent = `${service.charAt(0).toUpperCase() + service.slice(1)} Credentials`;
                
                // If updating existing credentials, fetch current username
                if (this.textContent.trim() === 'Update') {
                    fetch(`/api/settings/credential-info/${service}`, {
                        headers: {
                            'X-CSRFToken': getCsrfToken()
                        }
                    })
                    .then(response => response.json())
                    .then(data => {
                        if (data.success) {
                            document.getElementById('credential-username').value = data.username;
                            document.getElementById('credential-password').value = '';
                        }
                    });
                }
                
                credentialModal.style.display = 'block';
            } else if (action === 'delete') {
                if (confirm(`Are you sure you want to remove your ${service} credentials?`)) {
                    deleteCredentials(service);
                }
            }
        });
    });
    
    // Close modal
    if (closeModalButton) {
        closeModalButton.addEventListener('click', () => {
            credentialModal.style.display = 'none';
        });
    }
    
    if (cancelCredentialButton) {
        cancelCredentialButton.addEventListener('click', () => {
            credentialModal.style.display = 'none';
        });
    }
    
    // Close modal when clicking outside
    window.addEventListener('click', (event) => {
        if (event.target === credentialModal) {
            credentialModal.style.display = 'none';
        }
    });
    
    // Submit credential form
    if (credentialForm) {
        credentialForm.addEventListener('submit', function(e) {
            e.preventDefault();
            
            const service = credentialService.value;
            const username = document.getElementById('credential-username').value;
            const password = document.getElementById('credential-password').value;
            
            fetch('/api/settings/update-credentials', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({
                    service: service,
                    username: username,
                    password: password
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    credentialModal.style.display = 'none';
                    showNotification(`${service.charAt(0).toUpperCase() + service.slice(1)} credentials updated successfully`, 'success');
                    
                    // Refresh the page to update credential status
                    setTimeout(() => {
                        window.location.reload();
                    }, 1500);
                } else {
                    showNotification(data.message || 'Failed to update credentials', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('An error occurred', 'error');
            });
        });
    }
    
    // Delete credentials function
    function deleteCredentials(service) {
        fetch(`/api/settings/delete-credentials/${service}`, {
            method: 'DELETE',
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(`${service.charAt(0).toUpperCase() + service.slice(1)} credentials removed successfully`, 'success');
                
                // Refresh the page to update credential status
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showNotification(data.message || 'Failed to remove credentials', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred', 'error');
        });
    }
    
    // Automation control buttons
    const startAutomationButton = document.getElementById('start_automation');
    const stopAutomationButton = document.getElementById('stop_automation');
    const runDiagnosticsButton = document.getElementById('run_diagnostics');
    
    if (startAutomationButton) {
        startAutomationButton.addEventListener('click', function() {
            toggleAutomation('start');
        });
    }
    
    if (stopAutomationButton) {
        stopAutomationButton.addEventListener('click', function() {
            toggleAutomation('stop');
        });
    }
    
    if (runDiagnosticsButton) {
        runDiagnosticsButton.addEventListener('click', function() {
            runDiagnostics();
        });
    }
    
    // Toggle automation function
    function toggleAutomation(action) {
        fetch(`/api/automation/${action}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification(`Automation ${action}ed successfully`, 'success');
                
                // Refresh the page to update automation status
                setTimeout(() => {
                    window.location.reload();
                }, 1500);
            } else {
                showNotification(data.message || `Failed to ${action} automation`, 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred', 'error');
        });
    }
    
    // Run diagnostics function
    function runDiagnostics() {
        showNotification('Running system diagnostics...', 'info');
        
        fetch('/api/system/diagnostics', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showNotification('Diagnostics completed successfully', 'success');
                
                // Show diagnostics results
                const resultsModal = document.createElement('div');
                resultsModal.className = 'modal';
                resultsModal.style.display = 'block';
                
                resultsModal.innerHTML = `
                    <div class="modal-content">
                        <span class="close">&times;</span>
                        <h3>Diagnostics Results</h3>
                        <div class="diagnostics-results">
                            <pre>${JSON.stringify(data.results, null, 2)}</pre>
                        </div>
                        <div class="form-actions">
                            <button type="button" class="btn primary">Close</button>
                        </div>
                    </div>
                `;
                
                document.body.appendChild(resultsModal);
                
                // Close modal functionality
                const closeBtn = resultsModal.querySelector('.close');
                const closeButton = resultsModal.querySelector('.btn.primary');
                
                closeBtn.addEventListener('click', () => {
                    document.body.removeChild(resultsModal);
                });
                
                closeButton.addEventListener('click', () => {
                    document.body.removeChild(resultsModal);
                });
                
                window.addEventListener('click', (event) => {
                    if (event.target === resultsModal) {
                        document.body.removeChild(resultsModal);
                    }
                });
            } else {
                showNotification(data.message || 'Failed to run diagnostics', 'error');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showNotification('An error occurred', 'error');
        });
    }
    
    // Setup 2FA button
    const setup2faButton = document.getElementById('setup_2fa');
    
    if (setup2faButton) {
        setup2faButton.addEventListener('click', function() {
            fetch('/api/settings/setup-2fa', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Show QR code modal
                    const qrModal = document.createElement('div');
                    qrModal.className = 'modal';
                    qrModal.style.display = 'block';
                    
                    qrModal.innerHTML = `
                        <div class="modal-content">
                            <span class="close">&times;</span>
                            <h3>Set Up Two-Factor Authentication</h3>
                            <div class="qr-container">
                                <p>Scan this QR code with your authenticator app:</p>
                                <img src="${data.qr_code}" alt="2FA QR Code">
                                <p>Or enter this code manually: <strong>${data.secret_key}</strong></p>
                            </div>
                            <form id="verify-2fa-form">
                                <div class="form-group">
                                    <label for="verification-code">Enter verification code:</label>
                                    <input type="text" id="verification-code" name="code" required>
                                </div>
                                <div class="form-actions">
                                    <button type="button" class="btn secondary" id="cancel-2fa">Cancel</button>
                                    <button type="submit" class="btn primary">Verify & Enable</button>
                                </div>
                            </form>
                        </div>
                    `;
                    
                    document.body.appendChild(qrModal);
                    
                    // Close modal functionality
                    const closeBtn = qrModal.querySelector('.close');
                    const cancelBtn = qrModal.querySelector('#cancel-2fa');
                    const verifyForm = qrModal.querySelector('#verify-2fa-form');
                    
                    closeBtn.addEventListener('click', () => {
                        document.body.removeChild(qrModal);
                    });
                    
                    cancelBtn.addEventListener('click', () => {
                        document.body.removeChild(qrModal);
                    });
                    
                    window.addEventListener('click', (event) => {
                        if (event.target === qrModal) {
                            document.body.removeChild(qrModal);
                        }
                    });
                    
                    // Verify 2FA code
                    verifyForm.addEventListener('submit', function(e) {
                        e.preventDefault();
                        
                        const code = document.getElementById('verification-code').value;
                        
                        fetch('/api/settings/verify-2fa', {
                            method: 'POST',
                            headers: {
                                'Content-Type': 'application/json',
                                'X-CSRFToken': getCsrfToken()
                            },
                            body: JSON.stringify({
                                code: code
                            })
                        })
                        .then(response => response.json())
                        .then(data => {
                            if (data.success) {
                                document.body.removeChild(qrModal);
                                showNotification('Two-factor authentication enabled successfully', 'success');
                                
                                // Refresh the page to update 2FA status
                                setTimeout(() => {
                                    window.location.reload();
                                }, 1500);
                            } else {
                                showNotification(data.message || 'Invalid verification code', 'error');
                            }
                        })
                        .catch(error => {
                            console.error('Error:', error);
                            showNotification('An error occurred', 'error');
                        });
                    });
                } else {
                    showNotification(data.message || 'Failed to set up 2FA', 'error');
                }
            })
            .catch(error => {
                console.error('Error:', error);
                showNotification('An error occurred', 'error');
            });
        });
    }
    
    // Helper function to get CSRF token
    function getCsrfToken() {
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : '';
    }
    
    // Helper function to show notifications
    function showNotification(message, type) {
        const notification = document.createElement('div');
        notification.className = `alert alert-${type}`;
        notification.textContent = message;
        
        // Insert at the top of the main content
        const mainContent = document.querySelector('main.container');
        mainContent.insertBefore(notification, mainContent.firstChild);
        
        // Auto-remove after 5 seconds
        setTimeout(() => {
            notification.style.opacity = '0';
            setTimeout(() => {
                if (notification.parentNode) {
                    notification.parentNode.removeChild(notification);
                }
            }, 300);
        }, 5000);
    }
});