/**
 * Role Handler JavaScript
 * This script ensures the correct body class is applied based on the user role
 */
document.addEventListener('DOMContentLoaded', function() {
    // Check for student content wrapper
    if (document.querySelector('.student-content-wrapper')) {
        document.body.classList.add('student-role');
    }
    
    // Check for employer content wrapper
    if (document.querySelector('.employer-content-wrapper')) {
        document.body.classList.add('employer-role');
    }
    
    // Check for admin content wrapper
    if (document.querySelector('.admin-content-wrapper')) {
        document.body.classList.add('admin-role');
    }
});