/**
 * Main JavaScript for Job Application Agent
 */
document.addEventListener('DOMContentLoaded', function() {
    // Initialize tooltips
    if (typeof $().tooltip === 'function') {
        $('[data-toggle="tooltip"]').tooltip();
    }
    
    // Initialize popovers
    if (typeof $().popover === 'function') {
        $('[data-toggle="popover"]').popover();
    }
    
    // Smooth scrolling for anchor links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function(e) {
            e.preventDefault();
            
            const targetId = this.getAttribute('href');
            if (targetId === '#') return;
            
            const targetElement = document.querySelector(targetId);
            if (targetElement) {
                window.scrollTo({
                    top: targetElement.offsetTop - 70, // Adjust for header height
                    behavior: 'smooth'
                });
            }
        });
    });
    
    // Check if user is logged in and redirect if needed
    function checkLoginStatus() {
        fetch('/api/get_user_role')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // User is logged in, redirect based on role
                    const roles = data.roles || [];

                    if (roles.includes('admin')) {
                        window.location.href = '/admin/dashboard';
                    } else if (roles.includes('hr')) {
                        window.location.href = '/hr/dashboard';
                    } else if (roles.includes('student')) {
                        window.location.href = '/student/dashboard';
                    } else {
                        window.location.href = '/user/dashboard';
                    }
                }
                // If not logged in, stay on the landing page
            })
            .catch(error => {
                console.error('Error checking login status:', error);
                // Stay on landing page if there's an error
            });
    }
    
    // Only check login status on the landing page
    if (window.location.pathname === '/') {
        checkLoginStatus();
    }
});