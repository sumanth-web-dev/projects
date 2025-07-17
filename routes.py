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
    return render_template('settings.html')