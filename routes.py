"""
Main routes for the Job Application Agent web interface.
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from services.profile_service import profile_service
from services.auth_service import auth_service

# Create blueprint for main routes
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Render the dashboard page."""
    # Get the current user's ID
    user_id = auth_service.get_current_user_id()
    if not user_id:
        flash('Please log in to access your dashboard.', 'error')
        return redirect(url_for('auth.login'))
    
    return render_template('dashboard.html')

@main_bp.route('/profile')
def profile():
    """Render the profile management page."""
    # Get the current user's profile
    user_id = auth_service.get_current_user_id()
    if not user_id:
        flash('Please log in to access your profile.', 'error')
        return redirect(url_for('auth.login'))
    
    profile_data = profile_service.get_profile(user_id)
    return render_template('profile.html', profile=profile_data)

@main_bp.route('/jobs')
def jobs():
    """Render the jobs management page."""
    return render_template('jobs.html')

@main_bp.route('/applications')
def applications():
    """Render the applications management page."""
    return render_template('applications.html')

@main_bp.route('/settings')
def settings():
    """Render the settings page."""
    # Get the current user's ID
    user_id = auth_service.get_current_user_id()
    if not user_id:
        flash('Please log in to access settings.', 'error')
        return redirect(url_for('auth.login'))
    
    # Get user settings and system status
    from services.settings_service import settings_service
    
    user_settings = settings_service.get_user_settings(user_id)
    credentials = settings_service.get_credentials(user_id)
    system_status = settings_service.get_system_status()
    
    # Flatten settings for template access
    settings_data = {
        'default_search_radius': user_settings['general']['default_search_radius'],
        'job_refresh_interval': user_settings['general']['job_refresh_interval'],
        'job_sources': user_settings['general']['job_sources'],
        'theme': user_settings['general']['theme'],
        'auto_apply_enabled': user_settings['automation']['auto_apply_enabled'],
        'daily_application_limit': user_settings['automation']['daily_application_limit'],
        'schedule_days': user_settings['automation']['schedule_days'],
        'schedule_times': user_settings['automation']['schedule_times'],
        'browser_type': user_settings['automation']['browser_type'],
        'headless_mode': user_settings['automation']['headless_mode'],
        'enable_2fa': user_settings['security']['enable_2fa'],
        'session_timeout': user_settings['security']['session_timeout'],
        'enable_api_access': user_settings['security']['enable_api_access'],
        'api_key': user_settings['security']['api_key'] or '',
        'credentials': credentials
    }
    
    return render_template('settings.html', 
                         settings=settings_data, 
                         system_status=system_status)