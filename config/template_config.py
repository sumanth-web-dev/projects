"""
Template configuration for the application.
This module defines the template paths for different user roles.
"""

# Template paths for different user roles
TEMPLATE_PATHS = {
    'student': {
        'base': 'common/student_base.html',
        'dashboard': 'student/dashboard.html',
        'profile': 'student/profile.html',
        'resume': 'student/resume.html',
        'applications': 'student/applications.html',
        'interviews': 'student/interviews.html',
        'offers': 'student/offers.html',
        'test': 'student/test.html',
    },
    'employer': {
        'base': 'common/employer_base.html',
        'dashboard': 'hr/dashboard.html',
        'profile': 'hr/profile.html',
        'jobs': 'hr/jobs.html',
        'applications': 'hr/applications.html',
        'candidates': 'hr/candidates.html',
        'interviews': 'hr/interviews.html',
        'offers': 'hr/offers.html',
        'analytics': 'hr/analytics.html',
    },
    'admin': {
        'base': 'common/admin_base.html',
        'dashboard': 'admin/dashboard.html',
        'users': 'admin/users.html',
        'jobs': 'admin/jobs.html',
        'companies': 'admin/companies.html',
        'applications': 'admin/applications.html',
        'campus_drives': 'admin/campus_drives.html',
        'reports': 'admin/reports.html',
        'settings': 'admin/settings.html',
        'logs': 'admin/logs.html',
        'backup': 'admin/backup.html',
    }
}

def get_template_path(role, template_name):
    """
    Get the template path for a specific role and template name.
    
    Args:
        role (str): The user role (student, employer, admin)
        template_name (str): The template name
        
    Returns:
        str: The template path
    """
    if role in TEMPLATE_PATHS and template_name in TEMPLATE_PATHS[role]:
        return TEMPLATE_PATHS[role][template_name]
    return f"{role}/{template_name}.html"  # Default fallback