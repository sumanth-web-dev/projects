"""
Enhanced Student routes with comprehensive backend functionality.
"""
import datetime
import uuid
import os
from flask import Blueprint, request, jsonify, render_template, session, flash, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from services.auth_service import auth_service
from services.recommendation_service import RecommendationService
from services.skills_service import SkillsService
from services.application_service import ApplicationService
from services.profile_service import ProfileService
from api.security_middleware import validate_json_schema, sanitize_inputs, check_content_type, require_auth, require_role
from models.user import User
from models.job import Job
from models.application import Application, ApplicationStatus
from models.campus_drive import CampusDrive
from models.database import db
from sqlalchemy import desc, func
from typing import Dict, List, Optional

# Create blueprint for enhanced student routes
student_bp = Blueprint('student', __name__, url_prefix='/student')

# Initialize services
recommendation_service = RecommendationService()
skills_service = SkillsService()
application_service = ApplicationService()
profile_service = ProfileService()

@student_bp.before_request
@require_auth
@require_role('student')
def check_student_auth():
    """Ensure user is authenticated and has student role before accessing student routes."""
    pass

@student_bp.route('/dashboard', methods=['GET'])
def dashboard():
    """Enhanced student dashboard with comprehensive data."""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
    
    try:
        # Get dashboard statistics
        stats = get_dashboard_stats(user_id)
        
        # Get recommended jobs
        recommended_jobs = recommendation_service.get_recommendations(user_id, limit=3)
        
        # Get recent applications
        recent_applications = get_recent_applications(user_id, limit=5)
        
        # Get upcoming campus drives
        upcoming_drives = get_upcoming_campus_drives(limit=3)
        
        # Get upcoming events
        upcoming_events = get_upcoming_events(limit=3)
        
        # Get internships
        internships = get_available_internships(limit=3)
        
        # Get recommended courses
        recommended_courses = get_recommended_courses(user_id, limit=4)
        
        # Get placement statistics
        placement_stats = get_placement_statistics()
        
        # Get my registrations
        my_registrations = get_my_registrations(user_id, limit=4)
        
        # Get profile completion data
        profile_checks = profile_service.get_profile_completion_status(user_id)
        
        return render_template('student/dashboard.html',
                             user=user,
                             stats=stats,
                             recommended_jobs=recommended_jobs,
                             recent_applications=recent_applications,
                             upcoming_drives=upcoming_drives,
                             upcoming_events=upcoming_events,
                             internships=internships,
                             recommended_courses=recommended_courses,
                             placement_stats=placement_stats,
                             my_registrations=my_registrations,
                             profile_checks=profile_checks)
    
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('student/dashboard.html', user=user)

@student_bp.route('/dashboard/refresh', methods=['GET'])
def dashboard_refresh():
    """API endpoint to refresh dashboard data."""
    user_id = session.get('user_id')
    
    try:
        stats = get_dashboard_stats(user_id)
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@student_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    """Enhanced student profile management."""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
    
    if request.method == 'POST':
        try:
            # Handle profile update
            profile_data = {
                'first_name': request.form.get('first_name'),
                'last_name': request.form.get('last_name'),
                'phone': request.form.get('phone'),
                'date_of_birth': request.form.get('date_of_birth'),
                'bio': request.form.get('bio'),
                'location': request.form.get('location'),
                'preferred_location': request.form.get('preferred_location'),
                'skills': [skill.strip() for skill in request.form.get('skills', '').split(',') if skill.strip()],
                'languages': [lang.strip() for lang in request.form.get('languages', '').split(',') if lang.strip()],
            }
            
            # Handle education data
            education_data = []
            education_indices = set()
            for key in request.form.keys():
                if key.startswith('education[') and key.endswith('][institution]'):
                    index = key.split('[')[1].split(']')[0]
                    education_indices.add(index)
            
            for index in education_indices:
                edu = {
                    'institution': request.form.get(f'education[{index}][institution]'),
                    'degree': request.form.get(f'education[{index}][degree]'),
                    'field': request.form.get(f'education[{index}][field]'),
                    'year': request.form.get(f'education[{index}][year]'),
                    'gpa': request.form.get(f'education[{index}][gpa]')
                }
                if edu['institution'] and edu['degree']:
                    education_data.append(edu)
            
            profile_data['education'] = education_data
            
            # Handle experience data
            experience_data = []
            experience_indices = set()
            for key in request.form.keys():
                if key.startswith('experience[') and key.endswith('][title]'):
                    index = key.split('[')[1].split(']')[0]
                    experience_indices.add(index)
            
            for index in experience_indices:
                exp = {
                    'title': request.form.get(f'experience[{index}][title]'),
                    'company': request.form.get(f'experience[{index}][company]'),
                    'start_date': request.form.get(f'experience[{index}][start_date]'),
                    'end_date': request.form.get(f'experience[{index}][end_date]'),
                    'current': bool(request.form.get(f'experience[{index}][current]')),
                    'description': request.form.get(f'experience[{index}][description]')
                }
                if exp['title'] and exp['company']:
                    experience_data.append(exp)
            
            profile_data['experience'] = experience_data
            
            # Handle projects data
            projects_data = []
            project_indices = set()
            for key in request.form.keys():
                if key.startswith('projects[') and key.endswith('][name]'):
                    index = key.split('[')[1].split(']')[0]
                    project_indices.add(index)
            
            for index in project_indices:
                project = {
                    'name': request.form.get(f'projects[{index}][name]'),
                    'url': request.form.get(f'projects[{index}][url]'),
                    'description': request.form.get(f'projects[{index}][description]'),
                    'technologies': [tech.strip() for tech in request.form.get(f'projects[{index}][technologies]', '').split(',') if tech.strip()]
                }
                if project['name']:
                    projects_data.append(project)
            
            profile_data['projects'] = projects_data
            
            # Handle social links
            profile_data['social_links'] = {
                'linkedin': request.form.get('linkedin'),
                'github': request.form.get('github'),
                'portfolio': request.form.get('portfolio'),
                'twitter': request.form.get('twitter')
            }
            
            # Handle profile picture upload
            if 'profile_picture' in request.files:
                file = request.files['profile_picture']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    upload_path = os.path.join('uploads', 'profiles', user_id)
                    os.makedirs(upload_path, exist_ok=True)
                    file_path = os.path.join(upload_path, filename)
                    file.save(file_path)
                    profile_data['profile_picture'] = f'/uploads/profiles/{user_id}/{filename}'
            
            # Update user profile
            profile_service.update_profile(user_id, profile_data)
            
            flash('Profile updated successfully', 'success')
            return redirect(url_for('student.profile'))
            
        except Exception as e:
            flash(f'Error updating profile: {str(e)}', 'error')
    
    # Get profile completion status
    profile_completion = profile_service.calculate_profile_completion(user_id)
    
    return render_template('student/profile.html',
                         user=user,
                         profile_completion=profile_completion)

@student_bp.route('/profile/autosave', methods=['POST'])
def profile_autosave():
    """Auto-save profile data."""
    user_id = session.get('user_id')
    
    try:
        # Extract form data for auto-save
        profile_data = {
            'first_name': request.form.get('first_name'),
            'last_name': request.form.get('last_name'),
            'bio': request.form.get('bio')
        }
        
        # Save to temporary storage or update profile
        profile_service.autosave_profile(user_id, profile_data)
        
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@student_bp.route('/applications', methods=['GET'])
def applications():
    """Enhanced student job applications with filtering and stats."""
    user_id = session.get('user_id')
    
    try:
        # Get application statistics
        stats = application_service.get_application_stats(user_id)
        
        # Get all applications with job and status details
        applications = application_service.get_user_applications(user_id)
        
        # Get unique companies for filtering
        companies = list(set([app.job.company for app in applications if app.job]))
        
        return render_template('student/applications.html',
                             applications=applications,
                             stats=stats,
                             companies=companies)
    
    except Exception as e:
        flash(f'Error loading applications: {str(e)}', 'error')
        return render_template('student/applications.html',
                             applications=[],
                             stats={},
                             companies=[])

@student_bp.route('/applications/<application_id>/withdraw', methods=['POST'])
def withdraw_application(application_id):
    """Withdraw a job application."""
    user_id = session.get('user_id')
    
    try:
        success = application_service.withdraw_application(application_id, user_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Application withdrawn successfully'})
        else:
            return jsonify({'success': False, 'error': 'Unable to withdraw application'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@student_bp.route('/applications/<application_id>/accept-offer', methods=['POST'])
def accept_offer(application_id):
    """Accept a job offer."""
    user_id = session.get('user_id')
    
    try:
        success = application_service.accept_offer(application_id, user_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Offer accepted successfully'})
        else:
            return jsonify({'success': False, 'error': 'Unable to accept offer'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@student_bp.route('/applications/<application_id>/decline-offer', methods=['POST'])
def decline_offer(application_id):
    """Decline a job offer."""
    user_id = session.get('user_id')
    
    try:
        success = application_service.decline_offer(application_id, user_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Offer declined'})
        else:
            return jsonify({'success': False, 'error': 'Unable to decline offer'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@student_bp.route('/resume', methods=['GET', 'POST'])
def resume():
    """Enhanced resume builder and management."""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
    
    if request.method == 'POST':
        try:
            # Handle resume upload
            if 'resume_file' in request.files:
                file = request.files['resume_file']
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    upload_path = os.path.join('uploads', 'resumes', user_id)
                    os.makedirs(upload_path, exist_ok=True)
                    file_path = os.path.join(upload_path, filename)
                    file.save(file_path)
                    
                    # Update user's resume path
                    personal_data = user.personal_data or {}
                    personal_data['resume_path'] = file_path
                    user.personal_data = personal_data
                    db.session.commit()
                    
                    flash('Resume uploaded successfully', 'success')
        
        except Exception as e:
            flash(f'Error uploading resume: {str(e)}', 'error')
    
    return render_template('student/resume.html', user=user)

@student_bp.route('/resume/save', methods=['POST'])
def save_resume():
    """Save resume configuration."""
    user_id = session.get('user_id')
    
    try:
        data = request.get_json()
        template = data.get('template')
        sections = data.get('sections')
        
        # Save resume configuration
        personal_data = User.query.get(user_id).personal_data or {}
        personal_data['resume_config'] = {
            'template': template,
            'sections': sections,
            'updated_at': datetime.datetime.utcnow().isoformat()
        }
        
        user = User.query.get(user_id)
        user.personal_data = personal_data
        db.session.commit()
        
        return jsonify({'success': True})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@student_bp.route('/resume/upload', methods=['POST'])
def upload_resume():
    """Upload resume file."""
    user_id = session.get('user_id')
    
    try:
        if 'resume_file' not in request.files:
            return jsonify({'success': False, 'message': 'No file uploaded'})
        
        file = request.files['resume_file']
        if file.filename == '':
            return jsonify({'success': False, 'message': 'No file selected'})
        
        if file:
            filename = secure_filename(file.filename)
            upload_path = os.path.join('uploads', 'resumes', user_id)
            os.makedirs(upload_path, exist_ok=True)
            file_path = os.path.join(upload_path, filename)
            file.save(file_path)
            
            # Update user's resume path
            user = User.query.get(user_id)
            personal_data = user.personal_data or {}
            personal_data['resume_path'] = file_path
            user.personal_data = personal_data
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Resume uploaded successfully'})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@student_bp.route('/resume/analyze', methods=['POST'])
def analyze_resume():
    """Analyze resume and provide suggestions."""
    try:
        data = request.get_json()
        resume_content = data.get('resume_content')
        
        # Analyze resume (placeholder implementation)
        analysis = {
            'score': 75,
            'suggestions': [
                'Add more quantifiable achievements',
                'Include relevant keywords for your target roles',
                'Improve formatting consistency'
            ]
        }
        
        return jsonify({'success': True, **analysis})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@student_bp.route('/skills-assessment', methods=['GET'])
def skills_assessment():
    """Skills assessment dashboard."""
    user_id = session.get('user_id')
    
    try:
        # Get assessment statistics
        stats = skills_service.get_assessment_stats(user_id)
        
        # Get assessment history
        assessment_history = skills_service.get_assessment_history(user_id)
        
        # Get skills data for radar chart
        skills_data = skills_service.get_skills_radar_data(user_id)
        
        # Get improvement recommendations
        recommendations = skills_service.get_improvement_recommendations(user_id)
        
        return render_template('student/skills_assessment.html',
                             stats=stats,
                             assessment_history=assessment_history,
                             skills_data=skills_data,
                             recommendations=recommendations)
    
    except Exception as e:
        flash(f'Error loading skills assessment: {str(e)}', 'error')
        return render_template('student/skills_assessment.html')

@student_bp.route('/skills-assessment/start/<category>', methods=['POST'])
def start_assessment(category):
    """Start a skills assessment."""
    user_id = session.get('user_id')
    
    try:
        assessment = skills_service.start_assessment(user_id, category)
        return jsonify({'success': True, 'assessment': assessment})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@student_bp.route('/skills-assessment/submit', methods=['POST'])
def submit_assessment():
    """Submit assessment answers."""
    user_id = session.get('user_id')
    
    try:
        data = request.get_json()
        assessment_id = data.get('assessment_id')
        answers = data.get('answers')
        
        result = skills_service.submit_assessment(assessment_id, answers, user_id)
        return jsonify({'success': True, 'score': result['score']})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# Helper functions
def get_dashboard_stats(user_id: str) -> Dict:
    """Get dashboard statistics for a user."""
    try:
        applications_count = Application.query.filter_by(user_id=user_id).count()
        applications_this_week = Application.query.filter(
            Application.user_id == user_id,
            Application.created_at >= datetime.datetime.utcnow() - datetime.timedelta(days=7)
        ).count()
        
        interviews_count = db.session.query(func.count(Application.id)).filter(
            Application.user_id == user_id,
            Application.status.in_([ApplicationStatus.INTERVIEW_SCHEDULED, ApplicationStatus.INTERVIEWED])
        ).scalar()
        
        offers_count = db.session.query(func.count(Application.id)).filter(
            Application.user_id == user_id,
            Application.status.in_([ApplicationStatus.OFFER_RECEIVED, ApplicationStatus.OFFER_PENDING])
        ).scalar()
        
        # Calculate profile completion
        user = User.query.get(user_id)
        profile_completion = profile_service.calculate_profile_completion(user_id)
        
        # Get new jobs today
        new_jobs_today = Job.query.filter(
            Job.created_at >= datetime.datetime.utcnow().date(),
            Job.is_active == True
        ).count()
        
        return {
            'applications_count': applications_count,
            'applications_this_week': applications_this_week,
            'interviews_count': interviews_count,
            'upcoming_interviews': 0,  # Placeholder
            'offers_count': offers_count,
            'pending_offers': 0,  # Placeholder
            'profile_completion': profile_completion,
            'new_jobs_today': new_jobs_today,
            'total_recommended': 0,  # Placeholder
            'upcoming_drives': 0  # Placeholder
        }
    
    except Exception as e:
        return {
            'applications_count': 0,
            'applications_this_week': 0,
            'interviews_count': 0,
            'upcoming_interviews': 0,
            'offers_count': 0,
            'pending_offers': 0,
            'profile_completion': 0,
            'new_jobs_today': 0,
            'total_recommended': 0,
            'upcoming_drives': 0
        }

def get_recent_applications(user_id: str, limit: int = 5) -> List:
    """Get recent applications for a user."""
    try:
        applications = Application.query.filter_by(user_id=user_id)\
            .order_by(desc(Application.created_at))\
            .limit(limit)\
            .all()
        return applications
    except Exception:
        return []

def get_upcoming_campus_drives(limit: int = 3) -> List:
    """Get upcoming campus drives."""
    try:
        # Placeholder implementation
        return []
    except Exception:
        return []

def get_upcoming_events(limit: int = 3) -> List:
    """Get upcoming events."""
    try:
        # Placeholder implementation
        return []
    except Exception:
        return []

def get_available_internships(limit: int = 3) -> List:
    """Get available internships."""
    try:
        # Placeholder implementation
        return []
    except Exception:
        return []

def get_recommended_courses(user_id: str, limit: int = 4) -> List:
    """Get recommended courses for a user."""
    try:
        # Placeholder implementation
        return []
    except Exception:
        return []

def get_placement_statistics() -> Dict:
    """Get placement statistics."""
    try:
        # Placeholder implementation
        return {
            'total_placements': 0,
            'average_package': '$0',
            'highest_package': '$0',
            'placement_rate': 0
        }
    except Exception:
        return {}

def get_my_registrations(user_id: str, limit: int = 4) -> List:
    """Get user's registrations."""
    try:
        # Placeholder implementation
        return []
    except Exception:
        return []