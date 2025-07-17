"""
User routes for regular users in the Job Application Agent.
"""
import datetime
from flask import Blueprint, request, jsonify, render_template, session, flash, redirect, url_for
from services.auth_service import auth_service
from api.security_middleware import validate_json_schema, sanitize_inputs, check_content_type, require_auth
from models.user import User
from models.database import db

# Create blueprint for user routes
user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.before_request
@require_auth
def check_user_auth():
    """Ensure user is authenticated before accessing user routes."""
    pass

@user_bp.route('/dashboard', methods=['GET'])
def dashboard():
    """User dashboard."""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
    
    return render_template('user/dashboard.html', user=user)

@user_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    """User profile management."""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
    
    if request.method == 'POST':
        # Handle profile update
        try:
            # Get form data
            first_name = request.form.get('first_name')
            last_name = request.form.get('last_name')
            phone = request.form.get('phone')
            
            # Get current personal data
            personal_data = user.personal_data or {}
            
            # Update personal data
            personal_data['first_name'] = first_name
            personal_data['last_name'] = last_name
            personal_data['phone'] = phone
            
            # Save updated personal data
            user.personal_data = personal_data
            user.updated_at = datetime.datetime.utcnow()
            db.session.commit()
            
            flash('Profile updated successfully', 'success')
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'error')
    
    # Get user data for display
    personal_data = user.personal_data or {}
    
    return render_template('user/profile.html', 
                          user=user,
                          personal_data=personal_data)

@user_bp.route('/applications', methods=['GET'])
def applications():
    """User job applications."""
    user_id = session.get('user_id')
    
    # This would typically fetch the user's applications from the database
    # For now, we'll return a template with placeholder data
    
    return render_template('user/applications.html')

@user_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """User settings."""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
    
    if request.method == 'POST':
        # Handle settings update
        try:
            # Get form data for notification preferences
            email_notifications = 'email_notifications' in request.form
            
            # Get current preferences
            preferences = user.preferences or {}
            
            # Update preferences
            preferences['email_notifications'] = email_notifications
            
            # Save updated preferences
            user.preferences = preferences
            db.session.commit()
            
            flash('Settings updated successfully', 'success')
        except Exception as e:
            flash(f'Error updating settings: {str(e)}', 'error')
    
    # Get user preferences for display
    preferences = user.preferences or {}
    
    return render_template('user/settings.html', 
                          user=user,
                          preferences=preferences)

@user_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    """Change user password."""
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        # Get form data
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate inputs
        if not current_password or not new_password or not confirm_password:
            flash('All fields are required', 'error')
            return render_template('user/change_password.html')
        
        if new_password != confirm_password:
            flash('New passwords do not match', 'error')
            return render_template('user/change_password.html')
        
        # Update password
        success, message = auth_service.update_password(user_id, current_password, new_password)
        
        if success:
            flash('Password updated successfully', 'success')
            return redirect(url_for('user.settings'))
        else:
            flash(message, 'error')
    
    return render_template('user/change_password.html')