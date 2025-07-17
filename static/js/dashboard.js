// Dashboard JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Elements
    const applicationsList = document.getElementById('applications-list');
    const statusFilter = document.getElementById('status-filter');
    const dateFilter = document.getElementById('date-filter');
    const activeFilter = document.getElementById('active-filter');
    const refreshButton = document.getElementById('refresh-applications');
    const prevPageButton = document.getElementById('prev-page');
    const nextPageButton = document.getElementById('next-page');
    const pageInfo = document.getElementById('page-info');
    const modal = document.getElementById('application-modal');
    const closeModalBtn = document.querySelector('.close-modal');
    const closeModalButton = document.getElementById('close-modal');
    const retryButton = document.getElementById('retry-application');
    
    // State
    let currentPage = 1;
    let totalPages = 1;
    let pageSize = 10;
    let currentApplicationId = null;
    
    // Initialize
    loadApplicationStats();
    loadApplications();
    
    // Event Listeners
    statusFilter.addEventListener('change', resetAndLoadApplications);
    dateFilter.addEventListener('change', resetAndLoadApplications);
    activeFilter.addEventListener('change', resetAndLoadApplications);
    refreshButton.addEventListener('click', refreshData);
    prevPageButton.addEventListener('click', goToPrevPage);
    nextPageButton.addEventListener('click', goToNextPage);
    closeModalBtn.addEventListener('click', closeModal);
    closeModalButton.addEventListener('click', closeModal);
    retryButton.addEventListener('click', retryApplication);
    
    // Functions
    function resetAndLoadApplications() {
        currentPage = 1;
        loadApplications();
    }
    
    function refreshData() {
        loadApplicationStats();
        loadApplications();
    }
    
    function goToPrevPage() {
        if (currentPage > 1) {
            currentPage--;
            loadApplications();
        }
    }
    
    function goToNextPage() {
        if (currentPage < totalPages) {
            currentPage++;
            loadApplications();
        }
    }
    
    function loadApplicationStats() {
        fetch('/api/applications/stats')
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    updateStatCards(data.stats);
                }
            })
            .catch(error => {
                console.error('Error loading application statistics:', error);
            });
    }
    
    function updateStatCards(stats) {
        document.getElementById('total-applications').textContent = stats.total || 0;
        document.getElementById('pending-applications').textContent = stats.by_status?.pending || 0;
        document.getElementById('submitted-applications').textContent = 
            (stats.by_status?.submitted || 0) + (stats.by_status?.in_review || 0);
        document.getElementById('interview-applications').textContent = stats.by_status?.interview_scheduled || 0;
        document.getElementById('accepted-applications').textContent = stats.by_status?.accepted || 0;
    }
    
    function loadApplications() {
        // Show loading indicator
        applicationsList.innerHTML = '<div class="loading-indicator">Loading applications...</div>';
        
        // Build query parameters
        const status = statusFilter.value;
        const activeOnly = activeFilter.value;
        const offset = (currentPage - 1) * pageSize;
        
        let url = `/api/applications?limit=${pageSize}&offset=${offset}&active_only=${activeOnly}`;
        
        if (status) {
            url += `&status=${status}`;
        }
        
        // Add date filter if selected
        const dateValue = dateFilter.value;
        if (dateValue && dateValue !== 'all') {
            const days = parseInt(dateValue);
            // This would be handled on the server side
            url += `&days=${days}`;
        }
        
        fetch(url)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    displayApplications(data.applications);
                    updatePagination(data.count);
                } else {
                    applicationsList.innerHTML = '<div class="no-applications">Failed to load applications.</div>';
                }
            })
            .catch(error => {
                console.error('Error loading applications:', error);
                applicationsList.innerHTML = '<div class="no-applications">Error loading applications.</div>';
            });
    }
    
    function displayApplications(applications) {
        if (!applications || applications.length === 0) {
            applicationsList.innerHTML = '<div class="no-applications">No applications found.</div>';
            return;
        }
        
        applicationsList.innerHTML = '';
        
        applications.forEach(app => {
            const appElement = document.createElement('div');
            appElement.className = 'application-item';
            
            // Format date
            const dateToShow = app.submitted_at ? new Date(app.submitted_at) : new Date(app.created_at);
            const formattedDate = dateToShow.toLocaleDateString();
            
            appElement.innerHTML = `
                <div class="application-cell company-cell">${app.job?.company || 'Unknown Company'}</div>
                <div class="application-cell">${app.job?.title || 'Unknown Position'}</div>
                <div class="application-cell">
                    <span class="status-badge status-${app.status}">${formatStatus(app.status)}</span>
                </div>
                <div class="application-cell">${formattedDate}</div>
                <div class="application-cell">
                    <div class="action-buttons">
                        <button class="btn btn-sm btn-edit view-details" data-id="${app.id}">Details</button>
                        ${app.can_retry ? `<button class="btn btn-sm retry-app" data-id="${app.id}">Retry</button>` : ''}
                    </div>
                </div>
            `;
            
            applicationsList.appendChild(appElement);
            
            // Add event listeners to buttons
            const viewDetailsBtn = appElement.querySelector('.view-details');
            viewDetailsBtn.addEventListener('click', () => showApplicationDetails(app.id));
            
            const retryBtn = appElement.querySelector('.retry-app');
            if (retryBtn) {
                retryBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    retryApplication(app.id);
                });
            }
        });
    }
    
    function formatStatus(status) {
        // Convert snake_case to Title Case
        return status
            .split('_')
            .map(word => word.charAt(0).toUpperCase() + word.slice(1))
            .join(' ');
    }
    
    function updatePagination(totalCount) {
        totalPages = Math.ceil(totalCount / pageSize);
        pageInfo.textContent = `Page ${currentPage} of ${totalPages}`;
        
        prevPageButton.disabled = currentPage <= 1;
        nextPageButton.disabled = currentPage >= totalPages;
    }
    
    function showApplicationDetails(applicationId) {
        currentApplicationId = applicationId;
        
        fetch(`/api/applications/${applicationId}`)
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    displayApplicationDetails(data.application);
                    openModal();
                    
                    // Show/hide retry button based on application status
                    retryButton.style.display = data.application.can_retry ? 'block' : 'none';
                }
            })
            .catch(error => {
                console.error('Error loading application details:', error);
            });
    }
    
    function displayApplicationDetails(application) {
        const detailsContainer = document.getElementById('application-details');
        const job = application.job || {};
        
        // Format dates
        const createdDate = new Date(application.created_at).toLocaleString();
        const submittedDate = application.submitted_at ? new Date(application.submitted_at).toLocaleString() : 'Not submitted';
        const updatedDate = new Date(application.updated_at).toLocaleString();
        
        let materialsHtml = '';
        if (application.materials_used && Object.keys(application.materials_used).length > 0) {
            materialsHtml = '<ul class="materials-list">';
            for (const [key, value] of Object.entries(application.materials_used)) {
                materialsHtml += `<li><strong>${formatKey(key)}:</strong> ${value}</li>`;
            }
            materialsHtml += '</ul>';
        } else {
            materialsHtml = '<p>No materials specified</p>';
        }
        
        let responsesHtml = '';
        if (application.custom_responses && Object.keys(application.custom_responses).length > 0) {
            responsesHtml = '<ul class="responses-list">';
            for (const [question, answer] of Object.entries(application.custom_responses)) {
                responsesHtml += `
                    <li>
                        <div class="question">${question}</div>
                        <div class="answer">${answer}</div>
                    </li>
                `;
            }
            responsesHtml += '</ul>';
        } else {
            responsesHtml = '<p>No custom responses</p>';
        }
        
        let errorHtml = '';
        if (application.error_log) {
            errorHtml = `
                <div class="detail-section">
                    <h4>Error Information</h4>
                    <div class="error-log">${application.error_log}</div>
                    <div class="detail-row">
                        <div class="detail-label">Error Count:</div>
                        <div class="detail-value">${application.error_count}</div>
                    </div>
                    <div class="detail-row">
                        <div class="detail-label">Retry Count:</div>
                        <div class="detail-value">${application.retry_count}</div>
                    </div>
                </div>
            `;
        }
        
        detailsContainer.innerHTML = `
            <div class="detail-section">
                <h4>Job Information</h4>
                <div class="detail-row">
                    <div class="detail-label">Position:</div>
                    <div class="detail-value">${job.title || 'Unknown'}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Company:</div>
                    <div class="detail-value">${job.company || 'Unknown'}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Location:</div>
                    <div class="detail-value">${job.location || 'Not specified'}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Job Type:</div>
                    <div class="detail-value">${job.job_type || 'Not specified'}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Source:</div>
                    <div class="detail-value">${job.source_website || 'Unknown'}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Job URL:</div>
                    <div class="detail-value">
                        <a href="${job.source_url || '#'}" target="_blank">View Original Job Posting</a>
                    </div>
                </div>
            </div>
            
            <div class="detail-section">
                <h4>Application Status</h4>
                <div class="detail-row">
                    <div class="detail-label">Status:</div>
                    <div class="detail-value">
                        <span class="status-badge status-${application.status}">${formatStatus(application.status)}</span>
                    </div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Created:</div>
                    <div class="detail-value">${createdDate}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Submitted:</div>
                    <div class="detail-value">${submittedDate}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Last Updated:</div>
                    <div class="detail-value">${updatedDate}</div>
                </div>
                <div class="detail-row">
                    <div class="detail-label">Method:</div>
                    <div class="detail-value">${application.application_method || 'Not specified'}</div>
                </div>
            </div>
            
            <div class="detail-section">
                <h4>Application Materials</h4>
                ${materialsHtml}
            </div>
            
            <div class="detail-section">
                <h4>Custom Responses</h4>
                ${responsesHtml}
            </div>
            
            ${errorHtml}
        `;
        
        // Update modal title
        document.getElementById('modal-title').textContent = `${job.title || 'Application'} at ${job.company || 'Unknown Company'}`;
    }
    
    function formatKey(key) {
        // Convert snake_case or camelCase to Title Case
        return key
            .replace(/_/g, ' ')
            .replace(/([A-Z])/g, ' $1')
            .replace(/^./, str => str.toUpperCase());
    }
    
    function openModal() {
        modal.style.display = 'block';
        document.body.style.overflow = 'hidden'; // Prevent scrolling behind modal
    }
    
    function closeModal() {
        modal.style.display = 'none';
        document.body.style.overflow = '';
    }
    
    function retryApplication(applicationId = null) {
        const appId = applicationId || currentApplicationId;
        if (!appId) return;
        
        fetch(`/api/applications/${appId}/retry`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRF-Token': getCsrfToken()
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                closeModal();
                refreshData();
                showNotification('Application retry initiated successfully', 'success');
            } else {
                showNotification(data.message || 'Failed to retry application', 'error');
            }
        })
        .catch(error => {
            console.error('Error retrying application:', error);
            showNotification('An error occurred while retrying the application', 'error');
        });
    }
    
    function getCsrfToken() {
        // This assumes you have a CSRF token in a meta tag or similar
        const metaTag = document.querySelector('meta[name="csrf-token"]');
        return metaTag ? metaTag.getAttribute('content') : '';
    }
    
    function showNotification(message, type = 'info') {
        // Check if notification container exists, create if not
        let notificationContainer = document.getElementById('notification-container');
        if (!notificationContainer) {
            notificationContainer = document.createElement('div');
            notificationContainer.id = 'notification-container';
            notificationContainer.style.position = 'fixed';
            notificationContainer.style.top = '20px';
            notificationContainer.style.right = '20px';
            notificationContainer.style.zIndex = '9999';
            document.body.appendChild(notificationContainer);
        }
        
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type}`;
        notification.style.marginBottom = '10px';
        notification.style.minWidth = '250px';
        notification.textContent = message;
        
        // Add to container
        notificationContainer.appendChild(notification);
        
        // Remove after delay
        setTimeout(() => {
            notification.style.opacity = '0';
            notification.style.transition = 'opacity 0.5s';
            setTimeout(() => {
                notificationContainer.removeChild(notification);
            }, 500);
        }, 5000);
    }
    
    // Close modal if user clicks outside of it
    window.addEventListener('click', function(event) {
        if (event.target === modal) {
            closeModal();
        }
    });
});