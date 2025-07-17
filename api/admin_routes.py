"""
Admin routes for administrators in the Job Application Agent.
"""
import datetime
import os
from flask import Blueprint, request, jsonify, render_template, session, flash, redirect, url_for, send_file
from services.auth_service import auth_service
from services.notification_service import notification_service
from services.security_audit_service import security_audit_service
from api.security_middleware import validate_json_schema, sanitize_inputs, check_content_type, require_auth, require_role
from models.user import User
from models.database import db

# Create blueprint for admin routes
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.before_request
@require_auth
@require_role('admin')
def check_admin_auth():
    """Ensure user is authenticated and has admin role before accessing admin routes."""
    pass

@admin_bp.route('/dashboard', methods=['GET'])
def dashboard():
    """Admin dashboard."""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
    
    # This would typically fetch summary data for the admin dashboard
    # For now, we'll return a template with placeholder data
    
    return render_template('admin/dashboard.html', user=user)

@admin_bp.route('/users', methods=['GET'])
def users():
    """Manage users."""
    # Get all users from the database
    users = User.query.all()
    
    # Filter by role if specified
    role_filter = request.args.get('role')
    if role_filter:
        filtered_users = []
        for user in users:
            personal_data = user.personal_data or {}
            roles = personal_data.get('roles', [])
            if role_filter in roles:
                filtered_users.append(user)
        users = filtered_users
    
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/create', methods=['GET', 'POST'])
def create_user():
    """Create a new user."""
    if request.method == 'POST':
        # Handle user creation
        try:
            # Get form data
            email = request.form.get('email')
            password = request.form.get('password')
            confirm_password = request.form.get('confirm_password')
            roles = request.form.getlist('roles')
            is_active = 'is_active' in request.form
            
            # Validate inputs
            if not email or not password or not confirm_password:
                flash('Email and password are required', 'error')
                return render_template('admin/create_user.html')
            
            if password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('admin/create_user.html')
            
            # Create user
            personal_data = {'roles': roles}
            success, user_id, message = auth_service.create_user(email, password, personal_data)
            
            if success:
                # Set active status if needed
                if not is_active:
                    user = User.query.get(user_id)
                    user.is_active = False
                    db.session.commit()
                
                flash('User created successfully', 'success')
                return redirect(url_for('admin.users'))
            else:
                flash(message, 'error')
        except Exception as e:
            flash(f'Error creating user: {str(e)}', 'error')
    
    return render_template('admin/create_user.html')

@admin_bp.route('/users/<user_id>', methods=['GET', 'POST'])
def edit_user(user_id):
    """Edit user details."""
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.users'))
    
    if request.method == 'POST':
        # Handle user update
        try:
            # Get form data
            email = request.form.get('email')
            is_active = 'is_active' in request.form
            roles = request.form.getlist('roles')
            
            # Update user
            user.email = email
            user.is_active = is_active
            
            # Update roles
            personal_data = user.personal_data or {}
            personal_data['roles'] = roles
            user.personal_data = personal_data
            
            db.session.commit()
            
            flash('User updated successfully', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            flash(f'Error updating user: {str(e)}', 'error')
    
    # Get user data for display
    personal_data = user.personal_data or {}
    roles = personal_data.get('roles', [])
    
    return render_template('admin/edit_user.html', 
                          user=user,
                          roles=roles)

@admin_bp.route('/users/<user_id>/reset-password', methods=['GET', 'POST'])
def reset_user_password(user_id):
    """Reset a user's password."""
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.users'))
    
    if request.method == 'POST':
        # Handle password reset
        try:
            # Get form data
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            # Validate inputs
            if not new_password or not confirm_password:
                flash('New password is required', 'error')
                return render_template('admin/reset_password.html', user=user)
            
            if new_password != confirm_password:
                flash('Passwords do not match', 'error')
                return render_template('admin/reset_password.html', user=user)
            
            # Update password in personal data
            personal_data = user.personal_data or {}
            personal_data['password'] = auth_service.hash_password(new_password)
            user.personal_data = personal_data
            
            db.session.commit()
            
            # Notify user about password reset
            notification_service.notify_system_alert(
                user_id=user_id,
                alert_type='security',
                message='Your password has been reset by an administrator. Please log in with your new password.'
            )
            
            flash('Password reset successfully', 'success')
            return redirect(url_for('admin.users'))
        except Exception as e:
            flash(f'Error resetting password: {str(e)}', 'error')
    
    return render_template('admin/reset_password.html', user=user)

@admin_bp.route('/users/<user_id>/delete', methods=['POST'])
def delete_user(user_id):
    """Delete a user."""
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('admin.users'))
    
    try:
        # Log the deletion
        security_audit_service.log_security_event(
            event_type='user_deletion',
            description=f"User {user.email} (ID: {user.id}) deleted by admin {session.get('user_id')}",
            severity='warning'
        )
        
        # Delete the user
        db.session.delete(user)
        db.session.commit()
        
        flash('User deleted successfully', 'success')
    except Exception as e:
        flash(f'Error deleting user: {str(e)}', 'error')
    
    return redirect(url_for('admin.users'))

@admin_bp.route('/roles', methods=['GET', 'POST'])
def roles():
    """Manage user roles."""
    if request.method == 'POST':
        # Handle role creation
        try:
            role_name = request.form.get('role_name')
            role_description = request.form.get('role_description')
            
            # Create role (placeholder for actual implementation)
            # This would typically save the role to the database
            
            flash('Role created successfully', 'success')
            return redirect(url_for('admin.roles'))
        except Exception as e:
            flash(f'Error creating role: {str(e)}', 'error')
    
    # This would typically fetch roles from the database
    # For now, we'll use placeholder data
    roles = [
        {'name': 'admin', 'description': 'Administrator with full access'},
        {'name': 'hr', 'description': 'HR personnel with hiring capabilities'},
        {'name': 'student', 'description': 'Student user with job search capabilities'},
        {'name': 'user', 'description': 'Regular user with basic access'}
    ]
    
    return render_template('admin/roles.html', roles=roles)

@admin_bp.route('/system-settings', methods=['GET', 'POST'])
def system_settings():
    """Manage system settings."""
    if request.method == 'POST':
        # Handle settings update
        try:
            # Get form data
            site_name = request.form.get('site_name')
            site_description = request.form.get('site_description')
            contact_email = request.form.get('contact_email')
            max_file_size = request.form.get('max_file_size')
            allowed_file_types = request.form.get('allowed_file_types')
            
            # Update settings (placeholder for actual implementation)
            # This would typically update settings in the database
            
            flash('System settings updated successfully', 'success')
        except Exception as e:
            flash(f'Error updating system settings: {str(e)}', 'error')
    
    # This would typically fetch current settings from the database
    # For now, we'll use placeholder data
    settings = {
        'site_name': 'Job Application Agent',
        'site_description': 'A platform for job seekers and employers',
        'contact_email': 'contact@example.com',
        'max_file_size': '5',
        'allowed_file_types': 'pdf,doc,docx'
    }
    
    return render_template('admin/system_settings.html', settings=settings)

@admin_bp.route('/email-templates', methods=['GET', 'POST'])
def email_templates():
    """Manage email templates."""
    template_id = request.args.get('id')
    
    if request.method == 'POST' and template_id:
        # Handle template update
        try:
            subject = request.form.get('subject')
            body = request.form.get('body')
            
            # Update template (placeholder for actual implementation)
            # This would typically update the template in the database
            
            flash('Email template updated successfully', 'success')
            return redirect(url_for('admin.email_templates'))
        except Exception as e:
            flash(f'Error updating email template: {str(e)}', 'error')
    
    # This would typically fetch email templates from the database
    # For now, we'll use placeholder data
    templates = [
        {'id': 'welcome', 'name': 'Welcome Email', 'subject': 'Welcome to Job Application Agent'},
        {'id': 'password_reset', 'name': 'Password Reset', 'subject': 'Reset Your Password'},
        {'id': 'application_status', 'name': 'Application Status Update', 'subject': 'Your Application Status'}
    ]
    
    template = None
    if template_id:
        # Find the selected template
        for t in templates:
            if t['id'] == template_id:
                template = t
                break
    
    return render_template('admin/email_templates.html', templates=templates, template=template)

@admin_bp.route('/logs', methods=['GET'])
def logs():
    """View system logs."""
    log_type = request.args.get('type', 'system')
    
    # This would typically fetch logs from the log files or database
    # For now, we'll use placeholder data
    logs = [
        {'timestamp': '2025-07-18 10:30:45', 'level': 'INFO', 'message': 'User logged in successfully'},
        {'timestamp': '2025-07-18 10:35:12', 'level': 'WARNING', 'message': 'Failed login attempt'},
        {'timestamp': '2025-07-18 11:15:30', 'level': 'ERROR', 'message': 'Database connection error'}
    ]
    
    return render_template('admin/logs.html', logs=logs, log_type=log_type)

@admin_bp.route('/logs/download', methods=['GET'])
def download_logs():
    """Download system logs."""
    log_type = request.args.get('type', 'system')
    
    # This would typically generate a log file for download
    # For now, we'll return a placeholder response
    
    return jsonify({'success': False, 'message': 'Log download not implemented yet'})

@admin_bp.route('/security-audit', methods=['GET'])
def security_audit():
    """View security audit logs."""
    # This would typically fetch security audit logs from the database
    # For now, we'll use placeholder data
    audit_logs = [
        {'timestamp': '2025-07-18 09:45:22', 'event_type': 'login_success', 'user': 'admin@example.com', 'ip': '192.168.1.1'},
        {'timestamp': '2025-07-18 10:12:35', 'event_type': 'permission_denied', 'user': 'user@example.com', 'ip': '192.168.1.2'},
        {'timestamp': '2025-07-18 11:30:18', 'event_type': 'user_created', 'user': 'admin@example.com', 'ip': '192.168.1.1'}
    ]
    
    return render_template('admin/security_audit.html', audit_logs=audit_logs)

@admin_bp.route('/backup', methods=['GET', 'POST'])
def backup():
    """Manage database backups."""
    if request.method == 'POST':
        # Handle backup creation
        try:
            # Create backup (placeholder for actual implementation)
            # This would typically create a database backup
            
            flash('Backup created successfully', 'success')
            return redirect(url_for('admin.backup'))
        except Exception as e:
            flash(f'Error creating backup: {str(e)}', 'error')
    
    # This would typically fetch backup history from the database
    # For now, we'll use placeholder data
    backups = [
        {'id': '1', 'timestamp': '2025-07-17 23:00:00', 'size': '24.5 MB', 'status': 'Completed'},
        {'id': '2', 'timestamp': '2025-07-16 23:00:00', 'size': '24.3 MB', 'status': 'Completed'},
        {'id': '3', 'timestamp': '2025-07-15 23:00:00', 'size': '24.1 MB', 'status': 'Completed'}
    ]
    
    return render_template('admin/backup.html', backups=backups)

@admin_bp.route('/analytics', methods=['GET'])
def analytics():
    """View system analytics."""
    # This would typically fetch analytics data from the database
    # For now, we'll use placeholder data
    analytics_data = {
        'total_users': 1250,
        'active_users': 875,
        'total_jobs': 320,
        'total_applications': 4500,
        'conversion_rate': '3.5%',
        'user_growth': '+12%'
    }
    
    return render_template('admin/analytics.html', analytics=analytics_data)

@admin_bp.route('/notifications', methods=['GET', 'POST'])
def notifications():
    """Manage system notifications."""
    if request.method == 'POST':
        # Handle sending a notification
        try:
            notification_type = request.form.get('notification_type')
            recipient_type = request.form.get('recipient_type')
            subject = request.form.get('subject')
            message = request.form.get('message')
            
            # Send notification (placeholder for actual implementation)
            # This would typically send notifications to selected users
            
            flash('Notification sent successfully', 'success')
            return redirect(url_for('admin.notifications'))
        except Exception as e:
            flash(f'Error sending notification: {str(e)}', 'error')
    
    return render_template('admin/notifications.html')

@admin_bp.route('/job-categories', methods=['GET', 'POST'])
def job_categories():
    """Manage job categories."""
    if request.method == 'POST':
        # Handle category creation/update
        try:
            category_name = request.form.get('category_name')
            parent_category = request.form.get('parent_category')
            
            # Create/update category (placeholder for actual implementation)
            # This would typically save the category to the database
            
            flash('Category saved successfully', 'success')
            return redirect(url_for('admin.job_categories'))
        except Exception as e:
            flash(f'Error saving category: {str(e)}', 'error')
    
    # This would typically fetch categories from the database
    # For now, we'll use placeholder data
    categories = [
        {'id': '1', 'name': 'Information Technology', 'parent': None},
        {'id': '2', 'name': 'Software Development', 'parent': '1'},
        {'id': '3', 'name': 'Network Administration', 'parent': '1'},
        {'id': '4', 'name': 'Finance', 'parent': None},
        {'id': '5', 'name': 'Accounting', 'parent': '4'}
    ]
    
    return render_template('admin/job_categories.html', categories=categories)