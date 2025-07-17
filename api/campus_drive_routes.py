"""
Campus drive routes for managing campus recruitment events.
"""
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, session, flash, redirect, url_for, g
from services.auth_service import auth_service
from services.notification_service import notification_service
from services.campus_drive_service import campus_drive_service
from api.security_middleware import validate_json_schema, sanitize_inputs, check_content_type, require_auth, require_role
from models.user import User
from models.job import Job
from models.database import db

# Create blueprint for campus drive routes
campus_drive_bp = Blueprint('campus_drive', __name__, url_prefix='/campus-drives')

@campus_drive_bp.route('/', methods=['GET'])
def list_drives():
    """List campus recruitment drives."""
    # Get filter parameters from request
    filters = {
        'institution_id': request.args.get('institution_id'),
        'status': request.args.get('status'),
        'start_date_from': request.args.get('start_date_from'),
        'start_date_to': request.args.get('start_date_to'),
        'is_virtual': request.args.get('is_virtual', type=bool)
    }
    
    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    # Get campus drives
    result = campus_drive_service.list_campus_drives(filters, page, limit)
    
    # Get institutions for filtering
    institutions = campus_drive_service.list_institutions()
    
    # Check if user is logged in
    user_id = session.get('user_id')
    user_registrations = []
    
    if user_id:
        # Get user's registrations
        user_registrations = campus_drive_service.get_student_registrations(user_id)
    
    # Render template with results
    return render_template('campus_drives/list.html',
                          campus_drives=result['campus_drives'],
                          metadata=result['metadata'],
                          filters=filters,
                          institutions=institutions,
                          user_registrations=user_registrations)

@campus_drive_bp.route('/<drive_id>', methods=['GET'])
def view_drive(drive_id):
    """View a specific campus drive."""
    # Get campus drive details
    campus_drive = campus_drive_service.get_campus_drive(drive_id)
    
    if not campus_drive:
        flash('Campus drive not found', 'error')
        return redirect(url_for('campus_drive.list_drives'))
    
    # Check if user is logged in
    user_id = session.get('user_id')
    user = None
    is_registered = False
    is_hr_or_admin = False
    
    if user_id:
        # Get user details
        user = User.query.get(user_id)
        
        # Check if user is registered for this drive
        registrations = campus_drive_service.get_student_registrations(user_id)
        is_registered = any(reg['campus_drive']['id'] == drive_id for reg in registrations)
        
        # Check if user is HR or admin
        if user:
            personal_data = user.personal_data or {}
            roles = personal_data.get('roles', [])
            is_hr_or_admin = 'hr' in roles or 'admin' in roles
    
    # Get drive statistics if user is HR or admin
    statistics = {}
    if is_hr_or_admin:
        statistics = campus_drive_service.get_drive_statistics(drive_id)
    
    # Render template with drive details
    return render_template('campus_drives/view.html',
                          campus_drive=campus_drive,
                          user=user,
                          is_registered=is_registered,
                          is_hr_or_admin=is_hr_or_admin,
                          statistics=statistics)

@campus_drive_bp.route('/create', methods=['GET', 'POST'])
@require_auth
@require_role('hr')
def create_drive():
    """Create a new campus drive."""
    if request.method == 'POST':
        try:
            # Get form data
            data = {
                'institution_id': request.form.get('institution_id'),
                'title': request.form.get('title'),
                'description': request.form.get('description'),
                'start_date': request.form.get('start_date'),
                'end_date': request.form.get('end_date'),
                'location': request.form.get('location'),
                'is_virtual': 'is_virtual' in request.form,
                'job_ids': request.form.getlist('job_ids')
            }
            
            # Get user ID
            user_id = session.get('user_id')
            
            # Create campus drive
            success, drive_id, message = campus_drive_service.create_campus_drive(data, user_id)
            
            if success:
                flash('Campus drive created successfully', 'success')
                return redirect(url_for('campus_drive.view_drive', drive_id=drive_id))
            else:
                flash(message, 'error')
        except Exception as e:
            flash(f'Error creating campus drive: {str(e)}', 'error')
    
    # Get institutions for dropdown
    institutions = campus_drive_service.list_institutions()
    
    # Get jobs for selection
    jobs = Job.query.filter_by(is_active=True).all()
    
    # Render template with form
    return render_template('campus_drives/create.html',
                          institutions=institutions,
                          jobs=jobs)

@campus_drive_bp.route('/<drive_id>/edit', methods=['GET', 'POST'])
@require_auth
@require_role('hr')
def edit_drive(drive_id):
    """Edit an existing campus drive."""
    # Get campus drive details
    campus_drive = campus_drive_service.get_campus_drive(drive_id)
    
    if not campus_drive:
        flash('Campus drive not found', 'error')
        return redirect(url_for('campus_drive.list_drives'))
    
    if request.method == 'POST':
        try:
            # Get form data
            data = {
                'title': request.form.get('title'),
                'description': request.form.get('description'),
                'start_date': request.form.get('start_date'),
                'end_date': request.form.get('end_date'),
                'location': request.form.get('location'),
                'is_virtual': 'is_virtual' in request.form,
                'status': request.form.get('status'),
                'job_ids': request.form.getlist('job_ids')
            }
            
            # Update campus drive
            success, message = campus_drive_service.update_campus_drive(drive_id, data)
            
            if success:
                flash('Campus drive updated successfully', 'success')
                return redirect(url_for('campus_drive.view_drive', drive_id=drive_id))
            else:
                flash(message, 'error')
        except Exception as e:
            flash(f'Error updating campus drive: {str(e)}', 'error')
    
    # Get institutions for dropdown
    institutions = campus_drive_service.list_institutions()
    
    # Get jobs for selection
    jobs = Job.query.filter_by(is_active=True).all()
    
    # Get selected job IDs
    selected_job_ids = [job['id'] for job in campus_drive.get('jobs', [])]
    
    # Render template with form
    return render_template('campus_drives/edit.html',
                          campus_drive=campus_drive,
                          institutions=institutions,
                          jobs=jobs,
                          selected_job_ids=selected_job_ids)

@campus_drive_bp.route('/<drive_id>/register', methods=['POST'])
@require_auth
@require_role('student')
def register_for_drive(drive_id):
    """Register for a campus drive."""
    # Get user ID
    user_id = session.get('user_id')
    
    try:
        # Register student
        success, registration_id, message = campus_drive_service.register_student(drive_id, user_id)
        
        if success:
            flash('Registration successful', 'success')
            
            # Get campus drive details for notification
            campus_drive = campus_drive_service.get_campus_drive(drive_id)
            
            # Notify HR about new registration
            if campus_drive:
                notification_service.create_notification(
                    user_id=campus_drive['created_by'],
                    title=f"New Registration: {campus_drive['title']}",
                    message=f"A new student has registered for the campus drive: {campus_drive['title']}",
                    notification_type="new_registration",
                    related_entity_id=registration_id
                )
        else:
            flash(message, 'error')
    except Exception as e:
        flash(f'Error registering for campus drive: {str(e)}', 'error')
    
    return redirect(url_for('campus_drive.view_drive', drive_id=drive_id))

@campus_drive_bp.route('/<drive_id>/registrations', methods=['GET'])
@require_auth
@require_role('hr')
def view_registrations(drive_id):
    """View registrations for a campus drive."""
    # Get campus drive details
    campus_drive = campus_drive_service.get_campus_drive(drive_id)
    
    if not campus_drive:
        flash('Campus drive not found', 'error')
        return redirect(url_for('campus_drive.list_drives'))
    
    # Get registrations
    registrations = campus_drive_service.get_drive_registrations(drive_id)
    
    # Render template with registrations
    return render_template('campus_drives/registrations.html',
                          campus_drive=campus_drive,
                          registrations=registrations)

@campus_drive_bp.route('/registrations/<registration_id>/update-status', methods=['POST'])
@require_auth
@require_role('hr')
def update_registration_status(registration_id):
    """Update the status of a registration."""
    try:
        # Get form data
        status = request.form.get('status')
        notes = request.form.get('notes')
        
        # Update status
        success, message = campus_drive_service.update_registration_status(registration_id, status, notes)
        
        if success:
            flash('Registration status updated successfully', 'success')
        else:
            flash(message, 'error')
    except Exception as e:
        flash(f'Error updating registration status: {str(e)}', 'error')
    
    # Redirect back to registrations page
    return redirect(request.referrer or url_for('campus_drive.list_drives'))

@campus_drive_bp.route('/registrations/<registration_id>/mark-attendance', methods=['POST'])
@require_auth
@require_role('hr')
def mark_attendance(registration_id):
    """Mark attendance for a student."""
    try:
        # Get form data
        attended = 'attended' in request.form
        
        # Mark attendance
        success, message = campus_drive_service.mark_attendance(registration_id, attended)
        
        if success:
            flash('Attendance marked successfully', 'success')
        else:
            flash(message, 'error')
    except Exception as e:
        flash(f'Error marking attendance: {str(e)}', 'error')
    
    # Redirect back to registrations page
    return redirect(request.referrer or url_for('campus_drive.list_drives'))

@campus_drive_bp.route('/institutions', methods=['GET', 'POST'])
@require_auth
@require_role('hr')
def manage_institutions():
    """Manage educational institutions."""
    if request.method == 'POST':
        try:
            # Get form data
            data = {
                'name': request.form.get('name'),
                'type': request.form.get('type'),
                'location': request.form.get('location'),
                'website': request.form.get('website'),
                'description': request.form.get('description')
            }
            
            # Create institution
            success, institution_id, message = campus_drive_service.create_institution(data)
            
            if success:
                flash('Institution created successfully', 'success')
            else:
                flash(message, 'error')
        except Exception as e:
            flash(f'Error creating institution: {str(e)}', 'error')
    
    # Get institutions
    institutions = campus_drive_service.list_institutions()
    
    # Render template with institutions
    return render_template('campus_drives/institutions.html',
                          institutions=institutions)

@campus_drive_bp.route('/my-registrations', methods=['GET'])
@require_auth
@require_role('student')
def my_registrations():
    """View student's campus drive registrations."""
    # Get user ID
    user_id = session.get('user_id')
    
    # Get registrations
    registrations = campus_drive_service.get_student_registrations(user_id)
    
    # Render template with registrations
    return render_template('campus_drives/my_registrations.html',
                          registrations=registrations)

@campus_drive_bp.route('/upcoming', methods=['GET'])
def upcoming_drives():
    """View upcoming campus drives."""
    # Get upcoming drives
    upcoming = campus_drive_service.get_upcoming_drives(limit=10)
    
    # Render template with upcoming drives
    return render_template('campus_drives/upcoming.html',
                          upcoming_drives=upcoming)

# API endpoints for AJAX requests
@campus_drive_bp.route('/api/drives', methods=['GET'])
def api_list_drives():
    """API endpoint for listing campus drives."""
    # Get filter parameters from request
    filters = {
        'institution_id': request.args.get('institution_id'),
        'status': request.args.get('status'),
        'start_date_from': request.args.get('start_date_from'),
        'start_date_to': request.args.get('start_date_to'),
        'is_virtual': request.args.get('is_virtual', type=bool)
    }
    
    # Remove None values
    filters = {k: v for k, v in filters.items() if v is not None}
    
    # Get pagination parameters
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    
    # Get campus drives
    result = campus_drive_service.list_campus_drives(filters, page, limit)
    
    # Return JSON response
    return jsonify(result)

@campus_drive_bp.route('/api/institutions', methods=['GET'])
def api_list_institutions():
    """API endpoint for listing institutions."""
    institutions = campus_drive_service.list_institutions()
    return jsonify(institutions)

@campus_drive_bp.route('/api/upcoming', methods=['GET'])
def api_upcoming_drives():
    """API endpoint for upcoming drives."""
    limit = request.args.get('limit', 5, type=int)
    upcoming = campus_drive_service.get_upcoming_drives(limit=limit)
    return jsonify(upcoming)