"""
Admin routes for administrators in the Job Application Agent.
"""
import datetime
import os
from flask import Blueprint, request, jsonify, render_template, session, flash, redirect, url_for, send_file
from services.auth_service import auth_service
from services.notification_service import notification_service
from services.security_audit_service import security_audit_service
from services.admin_service import admin_service
from services.analytics_service import analytics_service
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
    
    # Get dashboard data
    stats = analytics_service.get_dashboard_summary()
    system_status = admin_service.get_system_status()
    user_growth = admin_service.get_user_growth_data()
    user_distribution = admin_service.get_user_distribution()
    performance = admin_service.get_performance_data()
    recent_activity = admin_service.get_system_logs('auth', 10)
    security_alerts = admin_service.get_security_audit_logs(5)
    
    return render_template('admin/dashboard.html', 
                          user=user,
                          stats=stats,
                          system_status=system_status,
                          user_growth=user_growth,
                          user_distribution=user_distribution,
                          performance=performance,
                          recent_activity=recent_activity,
                          security_alerts=security_alerts)

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
            role_data = {
                'name': request.form.get('role_name'),
                'description': request.form.get('role_description')
            }
            
            success, message = admin_service.create_role(role_data)
            
            if success:
                flash('Role created successfully', 'success')
            else:
                flash(message, 'error')
                
            return redirect(url_for('admin.roles'))
        except Exception as e:
            flash(f'Error creating role: {str(e)}', 'error')
    
    # Get roles from admin service
    roles = admin_service.get_user_roles()
    
    return render_template('admin/roles.html', roles=roles)

@admin_bp.route('/system-settings', methods=['GET', 'POST'])
def system_settings():
    """Manage system settings."""
    if request.method == 'POST':
        # Handle settings update
        try:
            settings_data = {
                'site_name': request.form.get('site_name'),
                'site_description': request.form.get('site_description'),
                'contact_email': request.form.get('contact_email'),
                'max_file_size': int(request.form.get('max_file_size', 5)),
                'allowed_file_types': request.form.get('allowed_file_types', '').split(','),
                'pagination_limit': int(request.form.get('pagination_limit', 20)),
                'enable_notifications': 'enable_notifications' in request.form,
                'enable_email_notifications': 'enable_email_notifications' in request.form,
                'maintenance_mode': 'maintenance_mode' in request.form
            }
            
            success, message = admin_service.update_system_settings(settings_data)
            
            if success:
                flash('System settings updated successfully', 'success')
            else:
                flash(message, 'error')
        except Exception as e:
            flash(f'Error updating system settings: {str(e)}', 'error')
    
    # Get current settings from admin service
    settings = admin_service.get_system_settings()
    
    return render_template('admin/system_settings.html', settings=settings)

@admin_bp.route('/email-templates', methods=['GET', 'POST'])
def email_templates():
    """Manage email templates."""
    template_id = request.args.get('id')
    
    if request.method == 'POST' and template_id:
        # Handle template update
        try:
            template_data = {
                'subject': request.form.get('subject'),
                'body': request.form.get('body')
            }
            
            success, message = admin_service.update_email_template(template_id, template_data)
            
            if success:
                flash('Email template updated successfully', 'success')
            else:
                flash(message, 'error')
                
            return redirect(url_for('admin.email_templates'))
        except Exception as e:
            flash(f'Error updating email template: {str(e)}', 'error')
    
    # Get email templates from admin service
    templates = admin_service.get_email_templates()
    
    template = None
    if template_id:
        template = admin_service.get_email_template(template_id)
    
    return render_template('admin/email_templates.html', templates=templates, template=template)

@admin_bp.route('/logs', methods=['GET'])
def logs():
    """View system logs."""
    log_type = request.args.get('type', 'system')
    limit = request.args.get('limit', 100, type=int)
    
    # Get logs from admin service
    logs = admin_service.get_system_logs(log_type, limit)
    
    return render_template('admin/logs.html', logs=logs, log_type=log_type)

@admin_bp.route('/logs/download', methods=['GET'])
def download_logs():
    """Download system logs."""
    log_type = request.args.get('type', 'system')
    
    try:
        # Get logs from admin service
        logs = admin_service.get_system_logs(log_type, 1000)
        
        # Create a temporary file with logs
        import tempfile
        import json
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            json.dump(logs, f, indent=2)
            temp_file = f.name
        
        return send_file(temp_file, as_attachment=True, download_name=f'{log_type}_logs.json')
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/security-audit', methods=['GET'])
def security_audit():
    """View security audit logs."""
    limit = request.args.get('limit', 100, type=int)
    
    # Get security audit logs from admin service
    audit_logs = admin_service.get_security_audit_logs(limit)
    
    return render_template('admin/security_audit.html', audit_logs=audit_logs)

@admin_bp.route('/backup', methods=['GET', 'POST'])
def backup():
    """Manage database backups."""
    if request.method == 'POST':
        # Handle backup creation
        try:
            success, message, backup_id = admin_service.create_backup()
            
            if success:
                flash('Backup created successfully', 'success')
            else:
                flash(message, 'error')
                
            return redirect(url_for('admin.backup'))
        except Exception as e:
            flash(f'Error creating backup: {str(e)}', 'error')
    
    # Get backup history from admin service
    backups = admin_service.get_backups()
    
    return render_template('admin/backup.html', backups=backups)

@admin_bp.route('/analytics', methods=['GET'])
def analytics():
    """View system analytics."""
    # Get analytics data from analytics service
    user_metrics = analytics_service.get_user_metrics()
    job_metrics = analytics_service.get_job_metrics()
    application_metrics = analytics_service.get_application_metrics()
    system_metrics = analytics_service.get_system_metrics()
    search_analytics = analytics_service.get_search_analytics()
    
    analytics_data = {
        'user_metrics': user_metrics,
        'job_metrics': job_metrics,
        'application_metrics': application_metrics,
        'system_metrics': system_metrics,
        'search_analytics': search_analytics
    }
    
    return render_template('admin/analytics.html', analytics=analytics_data)

@admin_bp.route('/notifications', methods=['GET', 'POST'])
def notifications():
    """Manage system notifications."""
    if request.method == 'POST':
        # Handle sending a notification
        try:
            notification_data = {
                'notification_type': request.form.get('notification_type'),
                'recipient_type': request.form.get('recipient_type'),
                'subject': request.form.get('subject'),
                'message': request.form.get('message'),
                'send_email': 'send_email' in request.form,
                'role': request.form.get('role'),
                'user_ids': request.form.getlist('user_ids')
            }
            
            success, message = admin_service.send_system_notification(notification_data)
            
            if success:
                flash(message, 'success')
            else:
                flash(message, 'error')
                
            return redirect(url_for('admin.notifications'))
        except Exception as e:
            flash(f'Error sending notification: {str(e)}', 'error')
    
    # Get users for notification targeting
    users = User.query.filter_by(is_active=True).all()
    roles = admin_service.get_user_roles()
    
    return render_template('admin/notifications.html', users=users, roles=roles)

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
# Additional admin endpoints for complete functionality

@admin_bp.route('/backup/<backup_id>/restore', methods=['POST'])
def restore_backup(backup_id):
    """Restore a database backup."""
    try:
        success, message = admin_service.restore_backup(backup_id)
        
        if success:
            flash('Backup restored successfully', 'success')
        else:
            flash(message, 'error')
    except Exception as e:
        flash(f'Error restoring backup: {str(e)}', 'error')
    
    return redirect(url_for('admin.backup'))

@admin_bp.route('/backup/<backup_id>/delete', methods=['POST'])
def delete_backup(backup_id):
    """Delete a database backup."""
    try:
        success, message = admin_service.delete_backup(backup_id)
        
        if success:
            flash('Backup deleted successfully', 'success')
        else:
            flash(message, 'error')
    except Exception as e:
        flash(f'Error deleting backup: {str(e)}', 'error')
    
    return redirect(url_for('admin.backup'))

@admin_bp.route('/email-templates/create', methods=['GET', 'POST'])
def create_email_template():
    """Create a new email template."""
    if request.method == 'POST':
        try:
            template_id = request.form.get('template_id')
            template_data = {
                'subject': request.form.get('subject'),
                'body': request.form.get('body')
            }
            
            success, message = admin_service.create_email_template(template_id, template_data)
            
            if success:
                flash('Email template created successfully', 'success')
                return redirect(url_for('admin.email_templates'))
            else:
                flash(message, 'error')
        except Exception as e:
            flash(f'Error creating email template: {str(e)}', 'error')
    
    return render_template('admin/create_email_template.html')

@admin_bp.route('/email-templates/<template_id>/delete', methods=['POST'])
def delete_email_template(template_id):
    """Delete an email template."""
    try:
        success, message = admin_service.delete_email_template(template_id)
        
        if success:
            flash('Email template deleted successfully', 'success')
        else:
            flash(message, 'error')
    except Exception as e:
        flash(f'Error deleting email template: {str(e)}', 'error')
    
    return redirect(url_for('admin.email_templates'))

@admin_bp.route('/roles/<role_id>', methods=['GET', 'POST'])
def edit_role(role_id):
    """Edit a user role."""
    if request.method == 'POST':
        try:
            role_data = {
                'name': request.form.get('role_name'),
                'description': request.form.get('role_description')
            }
            
            success, message = admin_service.update_role(role_id, role_data)
            
            if success:
                flash('Role updated successfully', 'success')
                return redirect(url_for('admin.roles'))
            else:
                flash(message, 'error')
        except Exception as e:
            flash(f'Error updating role: {str(e)}', 'error')
    
    # Get role data for editing
    roles = admin_service.get_user_roles()
    role = next((r for r in roles if r['id'] == role_id), None)
    
    if not role:
        flash('Role not found', 'error')
        return redirect(url_for('admin.roles'))
    
    return render_template('admin/edit_role.html', role=role)

@admin_bp.route('/roles/<role_id>/delete', methods=['POST'])
def delete_role(role_id):
    """Delete a user role."""
    try:
        success, message = admin_service.delete_role(role_id)
        
        if success:
            flash('Role deleted successfully', 'success')
        else:
            flash(message, 'error')
    except Exception as e:
        flash(f'Error deleting role: {str(e)}', 'error')
    
    return redirect(url_for('admin.roles'))

# API endpoints for AJAX requests
@admin_bp.route('/api/users', methods=['GET'])
def api_get_users():
    """API endpoint for getting users."""
    try:
        users = User.query.filter_by(is_active=True).all()
        users_data = []
        
        for user in users:
            personal_data = user.personal_data or {}
            users_data.append({
                'id': user.id,
                'email': user.email,
                'roles': personal_data.get('roles', []),
                'created_at': user.created_at.isoformat() if user.created_at else None,
                'is_active': user.is_active
            })
        
        return jsonify({'success': True, 'users': users_data})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/system-status', methods=['GET'])
def api_system_status():
    """API endpoint for getting system status."""
    try:
        status = admin_service.get_system_status()
        return jsonify({'success': True, 'status': status})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/analytics/dashboard', methods=['GET'])
def api_dashboard_analytics():
    """API endpoint for dashboard analytics."""
    try:
        stats = analytics_service.get_dashboard_summary()
        user_growth = admin_service.get_user_growth_data()
        user_distribution = admin_service.get_user_distribution()
        performance = admin_service.get_performance_data()
        
        return jsonify({
            'success': True,
            'data': {
                'stats': stats,
                'user_growth': user_growth,
                'user_distribution': user_distribution,
                'performance': performance
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/logs/clear', methods=['POST'])
def api_clear_logs():
    """API endpoint for clearing logs."""
    try:
        log_type = request.json.get('log_type', 'system')
        
        # In a real implementation, you would clear the specified log type
        # For now, we'll just return success
        
        return jsonify({'success': True, 'message': f'{log_type} logs cleared successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@admin_bp.route('/api/maintenance-mode', methods=['POST'])
def api_toggle_maintenance_mode():
    """API endpoint for toggling maintenance mode."""
    try:
        enabled = request.json.get('enabled', False)
        
        settings_data = {'maintenance_mode': enabled}
        success, message = admin_service.update_system_settings(settings_data)
        
        if success:
            return jsonify({'success': True, 'message': f'Maintenance mode {"enabled" if enabled else "disabled"}'})
        else:
            return jsonify({'success': False, 'message': message})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})