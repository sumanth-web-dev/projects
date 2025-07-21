"""
Student routes for student users in the Job Application Agent.
"""
import datetime

def calculate_profile_completion(user):
    """Calculate the profile completion percentage for a user."""
    if not user or not user.personal_data:
        return 0
    
    personal_data = user.personal_data
    total_fields = 10  # Total number of important profile fields
    completed_fields = 0
    
    # Check basic information
    if personal_data.get('first_name'):
        completed_fields += 1
    if personal_data.get('last_name'):
        completed_fields += 1
    if personal_data.get('phone'):
        completed_fields += 1
    if personal_data.get('bio'):
        completed_fields += 1
    if personal_data.get('location'):
        completed_fields += 1
    
    # Check education
    if personal_data.get('education'):
        completed_fields += 1
    
    # Check skills
    if personal_data.get('skills') and len(personal_data.get('skills', [])) > 0:
        completed_fields += 1
    
    # Check experience
    if personal_data.get('experience') and len(personal_data.get('experience', [])) > 0:
        completed_fields += 1
    
    # Check projects
    if personal_data.get('projects') and len(personal_data.get('projects', [])) > 0:
        completed_fields += 1
    
    # Check social links
    if personal_data.get('social_links') and any(personal_data.get('social_links', {}).values()):
        completed_fields += 1
    
    # Calculate percentage
    return int((completed_fields / total_fields) * 100)
from flask import Blueprint, request, jsonify, render_template, session, flash, redirect, url_for
from services.auth_service import auth_service
from api.security_middleware import validate_json_schema, sanitize_inputs, check_content_type, require_auth, require_role
from models.user import User
from models.database import db

# Create blueprint for student routes
student_bp = Blueprint('student', __name__, url_prefix='/student')

@student_bp.before_request
@require_auth
@require_role('student')
def check_student_auth():
    """Ensure user is authenticated and has student role before accessing student routes."""
    pass

@student_bp.route('/dashboard', methods=['GET'])
def dashboard():
    """Student dashboard."""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
    
    # Create stats dictionary with placeholder data
    stats = {
        'applications_count': 0,
        'applications_this_week': 0,
        'interviews_count': 0,
        'upcoming_interviews': 0,
        'offers_count': 0,
        'pending_offers': 0,
        'profile_completion': 50,  # Default value
        'new_jobs_today': 5  # Default value
    }
    
    # This would typically fetch relevant data for the student dashboard
    # For now, we'll use placeholder data
    
    # Create empty lists for recommended jobs, recent applications, and upcoming drives
    recommended_jobs = []
    recent_applications = []
    upcoming_drives = []
    
    return render_template('student/dashboard.html', 
                          user=user, 
                          stats=stats,
                          recommended_jobs=recommended_jobs,
                          recent_applications=recent_applications,
                          upcoming_drives=upcoming_drives)

@student_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    """Student profile management."""
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
            college = request.form.get('college')
            degree = request.form.get('degree')
            graduation_year = request.form.get('graduation_year')
            skills = request.form.get('skills', '').split(',')
            
            # Get current personal data
            personal_data = user.personal_data or {}
            
            # Update personal data
            personal_data['first_name'] = first_name
            personal_data['last_name'] = last_name
            personal_data['phone'] = phone
            personal_data['education'] = {
                'college': college,
                'degree': degree,
                'graduation_year': graduation_year
            }
            personal_data['skills'] = [skill.strip() for skill in skills if skill.strip()]
            
            # Save updated personal data
            user.personal_data = personal_data
            user.updated_at = datetime.datetime.utcnow()
            db.session.commit()
            
            flash('Profile updated successfully', 'success')
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'error')
    
    # Get user data for display
    personal_data = user.personal_data or {}
    
    # Ensure social_links exists in personal_data
    if 'social_links' not in personal_data:
        personal_data['social_links'] = {}
    
    # Calculate profile completion percentage
    profile_completion = calculate_profile_completion(user)
    
    # Create a default profile_completion value if the function returns None
    if profile_completion is None:
        profile_completion = 0
    
    # Ensure personal_data has the expected structure with all required nested dictionaries
    if 'social_links' not in personal_data:
        personal_data['social_links'] = {}
    if 'education' not in personal_data:
        personal_data['education'] = []
    if 'experience' not in personal_data:
        personal_data['experience'] = []
    if 'projects' not in personal_data:
        personal_data['projects'] = []
    if 'skills' not in personal_data:
        personal_data['skills'] = []
    if 'languages' not in personal_data:
        personal_data['languages'] = []
    
    return render_template('student/profile.html', 
                          user=user,
                          personal_data=personal_data,
                          profile_completion=profile_completion)

@student_bp.route('/profile/autosave', methods=['POST'])
@require_auth
@require_role('student')
def profile_autosave():
    """Autosave profile data."""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({'success': False, 'message': 'User not found'}), 404
    
    try:
        # Get form data
        form_data = request.form
        
        # Get current personal data
        personal_data = user.personal_data or {}
        
        # Update basic information
        if form_data.get('first_name'):
            personal_data['first_name'] = form_data.get('first_name')
        if form_data.get('last_name'):
            personal_data['last_name'] = form_data.get('last_name')
        if form_data.get('phone'):
            personal_data['phone'] = form_data.get('phone')
        if form_data.get('bio'):
            personal_data['bio'] = form_data.get('bio')
        if form_data.get('location'):
            personal_data['location'] = form_data.get('location')
        if form_data.get('preferred_location'):
            personal_data['preferred_location'] = form_data.get('preferred_location')
        
        # Update skills
        if form_data.get('skills'):
            skills = form_data.get('skills', '').split(',')
            personal_data['skills'] = [skill.strip() for skill in skills if skill.strip()]
        
        # Update languages
        if form_data.get('languages'):
            languages = form_data.get('languages', '').split(',')
            personal_data['languages'] = [lang.strip() for lang in languages if lang.strip()]
        
        # Save updated personal data
        user.personal_data = personal_data
        user.updated_at = datetime.datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Profile autosaved successfully'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@student_bp.route('/resume', methods=['GET', 'POST'])
def resume():
    """Student resume management."""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
    
    if request.method == 'POST':
        # Handle resume upload or update
        try:
            # Check if resume file was uploaded
            if 'resume_file' in request.files:
                resume_file = request.files['resume_file']
                if resume_file.filename:
                    # Save resume file
                    # This would typically save the file to a storage system
                    # and store the reference in the user's data
                    
                    # Get current personal data
                    personal_data = user.personal_data or {}
                    
                    # Update resume information
                    personal_data['resume'] = {
                        'filename': resume_file.filename,
                        'uploaded_at': datetime.datetime.utcnow().isoformat()
                    }
                    
                    # Save updated personal data
                    user.personal_data = personal_data
                    user.updated_at = datetime.datetime.utcnow()
                    db.session.commit()
                    
                    flash('Resume uploaded successfully', 'success')
            else:
                flash('No resume file selected', 'error')
        except Exception as e:
            flash(f'Error uploading resume: {str(e)}', 'error')
    
    # Get user data for display
    personal_data = user.personal_data or {}
    resume_data = personal_data.get('resume', {})
    
    return render_template('student/resume.html', 
                          user=user,
                          resume_data=resume_data)

@student_bp.route('/applications', methods=['GET'])
def applications():
    """Student job applications."""
    user_id = session.get('user_id')
    
    # This would typically fetch the student's job applications from the database
    # For now, we'll return a template with placeholder data
    
    return render_template('student/applications.html')

@student_bp.route('/internships', methods=['GET'])
def internships():
    """Browse available internships."""
    # This would typically fetch available internships from the database
    # For now, we'll return a template with placeholder data
    
    return render_template('student/internships.html')

@student_bp.route('/placements', methods=['GET'])
def placements():
    """Browse available campus placements."""
    # This would typically fetch available campus placements from the database
    # For now, we'll return a template with placeholder data
    
    return render_template('student/placements.html')

@student_bp.route('/recommendations', methods=['GET'])
def recommendations():
    """View personalized job recommendations."""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
    
    # This would typically generate personalized recommendations based on the student's profile
    # For now, we'll return a template with placeholder data
    
    return render_template('student/recommendations.html')

@student_bp.route('/skills-assessment', methods=['GET', 'POST'])
def skills_assessment():
    """Take skills assessment tests."""
    user_id = session.get('user_id')
    
    if request.method == 'POST':
        # Handle skills assessment submission
        # This would typically process the assessment results and update the user's profile
        flash('Skills assessment completed successfully', 'success')
        return redirect(url_for('student.dashboard'))
    
    # This would typically fetch available skills assessments
    # For now, we'll return a template with placeholder data
    
    return render_template('student/skills_assessment.html')

@student_bp.route('/courses', methods=['GET'])
def courses():
    """Browse available courses and certifications."""
    # This would typically fetch available courses and certifications
    # For now, we'll return a template with placeholder data
    
    return render_template('student/courses.html')

@student_bp.route('/events', methods=['GET'])
def events():
    """View upcoming career events and workshops."""
    # This would typically fetch upcoming events from the database
    # For now, we'll return a template with placeholder data
    
    return render_template('student/events.html')

@student_bp.route('/interviews', methods=['GET'])
def interviews():
    """View and manage scheduled interviews."""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
    
    # This would typically fetch the student's interviews from the database
    # For now, we'll return a template with placeholder data
    
    return render_template('student/interviews.html')

@student_bp.route('/offers', methods=['GET'])
def offers():
    """View and manage job offers."""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
    
    # This would typically fetch the student's job offers from the database
    # For now, we'll return a template with placeholder data
    
    return render_template('student/offers.html')

@student_bp.route('/settings', methods=['GET', 'POST'])
def settings():
    """Student account settings."""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
    
    if request.method == 'POST':
        # Handle settings update
        try:
            # Process form data
            # Update user settings
            flash('Settings updated successfully', 'success')
        except Exception as e:
            flash(f'Error updating settings: {str(e)}', 'error')
    
    return render_template('student/settings.html', user=user)