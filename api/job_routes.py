"""
Job routes for job listings and applications in the Job Application Agent.
"""
import uuid
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, session, flash, redirect, url_for, g
from services.auth_service import auth_service
from services.notification_service import notification_service
from services.job_search_service import job_search_service
from services.recommendation_service import recommendation_service
from services.resume_parser_service import resume_parser_service
from api.security_middleware import validate_json_schema, sanitize_inputs, check_content_type, require_auth
from models.user import User
from models.job import Job, JobCategory, JobSkill
from models.application import Application, ApplicationStatus
from models.database import db

# Create blueprint for job routes
job_bp = Blueprint('job', __name__, url_prefix='/jobs')

@job_bp.route('/', methods=['GET'])
def list_jobs():
    """List job listings with search and filtering."""
    # Get search parameters from request
    query_params = {
        'keywords': request.args.get('keywords', ''),
        'location': request.args.get('location', ''),
        'category_id': request.args.get('category_id'),
        'min_salary': request.args.get('min_salary', type=float),
        'max_salary': request.args.get('max_salary', type=float),
        'experience_level': request.args.get('experience_level', type=int),
        'job_type': request.args.get('job_type'),
        'remote_option': request.args.get('remote_option', type=bool),
        'skills': request.args.getlist('skills'),
        'company': request.args.get('company', ''),
        'page': request.args.get('page', 1, type=int),
        'limit': request.args.get('limit', 20, type=int),
        'sort_by': request.args.get('sort_by', 'created_at'),
        'sort_order': request.args.get('sort_order', 'desc')
    }
    
    # Search jobs
    search_results = job_search_service.search_jobs(query_params)
    
    # Get categories for filtering
    categories = job_search_service.get_job_categories()
    
    # Get job types for filtering
    job_types = job_search_service.get_job_types()
    
    # Get popular skills for filtering
    popular_skills = job_search_service.get_popular_skills()
    
    # Check if user is logged in for personalized recommendations
    user_id = session.get('user_id')
    recommended_jobs = []
    
    if user_id:
        # Get personalized job recommendations
        recommendations = recommendation_service.get_job_recommendations(user_id, limit=5)
        recommended_jobs = [rec['job'] for rec in recommendations]
    
    # Render template with results
    return render_template('jobs/list.html',
                          jobs=search_results['jobs'],
                          metadata=search_results['metadata'],
                          query_params=query_params,
                          categories=categories,
                          job_types=job_types,
                          popular_skills=popular_skills,
                          recommended_jobs=recommended_jobs)

@job_bp.route('/<job_id>', methods=['GET'])
def view_job(job_id):
    """View a specific job listing."""
    # Get job details
    job = Job.query.get(job_id)
    
    if not job:
        flash('Job not found', 'error')
        return redirect(url_for('job.list_jobs'))
    
    # Check if user is logged in
    user_id = session.get('user_id')
    user = None
    has_applied = False
    similar_jobs = []
    
    if user_id:
        # Get user details
        user = User.query.get(user_id)
        
        # Check if user has already applied
        application = Application.query.filter_by(
            user_id=user_id,
            job_id=job_id
        ).first()
        
        has_applied = application is not None
        
        # Get similar jobs
        similar_jobs_data = recommendation_service.get_similar_jobs(job_id)
        similar_jobs = [item['job'] for item in similar_jobs_data]
    
    # Render template with job details
    return render_template('jobs/view.html',
                          job=job,
                          user=user,
                          has_applied=has_applied,
                          similar_jobs=similar_jobs)

@job_bp.route('/<job_id>/apply', methods=['GET', 'POST'])
@require_auth
def apply_job(job_id):
    """Apply for a job."""
    # Get job details
    job = Job.query.get(job_id)
    
    if not job:
        flash('Job not found', 'error')
        return redirect(url_for('job.list_jobs'))
    
    # Get user details
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
    
    # Check if user has already applied
    existing_application = Application.query.filter_by(
        user_id=user_id,
        job_id=job_id
    ).first()
    
    if existing_application:
        flash('You have already applied for this job', 'info')
        return redirect(url_for('job.view_job', job_id=job_id))
    
    if request.method == 'POST':
        try:
            # Get form data
            cover_letter = request.form.get('cover_letter', '')
            
            # Check if resume was uploaded
            resume_path = None
            if 'resume' in request.files:
                resume_file = request.files['resume']
                if resume_file.filename:
                    # Save resume
                    resume_path = resume_parser_service.save_resume(resume_file, user_id)
                    
                    if not resume_path:
                        flash('Error uploading resume. Please try again.', 'error')
                        return render_template('jobs/apply.html', job=job, user=user)
            
            # Create application
            application_id = str(uuid.uuid4())
            application = Application(
                id=application_id,
                user_id=user_id,
                job_id=job_id,
                cover_letter=cover_letter,
                resume_path=resume_path,
                status=ApplicationStatus.SUBMITTED,
                submitted_at=datetime.utcnow()
            )
            
            # Save to database
            db.session.add(application)
            db.session.commit()
            
            # Notify HR about new application
            notification_service.create_notification(
                user_id=job.created_by,
                title=f"New Application: {job.title}",
                message=f"A new application has been submitted for {job.title} by {user.email}.",
                notification_type="new_application",
                related_entity_id=application_id
            )
            
            flash('Application submitted successfully', 'success')
            return redirect(url_for('job.my_applications'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error submitting application: {str(e)}', 'error')
    
    # GET request - show application form
    return render_template('jobs/apply.html', job=job, user=user)

@job_bp.route('/my-applications', methods=['GET'])
@require_auth
def my_applications():
    """View user's job applications."""
    # Get user details
    user_id = session.get('user_id')
    
    # Get user's applications
    applications = Application.query.filter_by(user_id=user_id).order_by(
        Application.submitted_at.desc()
    ).all()
    
    # Render template with applications
    return render_template('jobs/my_applications.html', applications=applications)

@job_bp.route('/applications/<application_id>', methods=['GET'])
@require_auth
def view_application(application_id):
    """View a specific application."""
    # Get user details
    user_id = session.get('user_id')
    
    # Get application details
    application = Application.query.get(application_id)
    
    if not application or application.user_id != user_id:
        flash('Application not found', 'error')
        return redirect(url_for('job.my_applications'))
    
    # Get job details
    job = application.job
    
    # Render template with application details
    return render_template('jobs/view_application.html',
                          application=application,
                          job=job)

@job_bp.route('/applications/<application_id>/withdraw', methods=['POST'])
@require_auth
def withdraw_application(application_id):
    """Withdraw a job application."""
    # Get user details
    user_id = session.get('user_id')
    
    # Get application details
    application = Application.query.get(application_id)
    
    if not application or application.user_id != user_id:
        flash('Application not found', 'error')
        return redirect(url_for('job.my_applications'))
    
    try:
        # Update application status
        application.status = ApplicationStatus.WITHDRAWN
        application.last_updated_at = datetime.utcnow()
        db.session.commit()
        
        # Notify HR about withdrawn application
        notification_service.create_notification(
            user_id=application.job.created_by,
            title=f"Application Withdrawn: {application.job.title}",
            message=f"An application for {application.job.title} has been withdrawn.",
            notification_type="application_withdrawn",
            related_entity_id=application_id
        )
        
        flash('Application withdrawn successfully', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error withdrawing application: {str(e)}', 'error')
    
    return redirect(url_for('job.my_applications'))

@job_bp.route('/recommended', methods=['GET'])
@require_auth
def recommended_jobs():
    """View personalized job recommendations."""
    # Get user details
    user_id = session.get('user_id')
    
    # Get job recommendations
    recommendations = recommendation_service.get_job_recommendations(user_id)
    
    # Render template with recommendations
    return render_template('jobs/recommended.html', recommendations=recommendations)

@job_bp.route('/trending', methods=['GET'])
def trending_jobs():
    """View trending job searches and listings."""
    # Get trending searches
    trending_searches = job_search_service.get_trending_searches()
    
    # Get popular job categories
    categories = job_search_service.get_job_categories()
    
    # Get popular skills
    popular_skills = job_search_service.get_popular_skills()
    
    # Render template with trending data
    return render_template('jobs/trending.html',
                          trending_searches=trending_searches,
                          categories=categories,
                          popular_skills=popular_skills)

# API endpoints for AJAX requests
@job_bp.route('/api/search', methods=['GET'])
def api_search_jobs():
    """API endpoint for job search."""
    # Get search parameters from request
    query_params = {
        'keywords': request.args.get('keywords', ''),
        'location': request.args.get('location', ''),
        'category_id': request.args.get('category_id'),
        'min_salary': request.args.get('min_salary', type=float),
        'max_salary': request.args.get('max_salary', type=float),
        'experience_level': request.args.get('experience_level', type=int),
        'job_type': request.args.get('job_type'),
        'remote_option': request.args.get('remote_option', type=bool),
        'skills': request.args.getlist('skills'),
        'company': request.args.get('company', ''),
        'page': request.args.get('page', 1, type=int),
        'limit': request.args.get('limit', 20, type=int),
        'sort_by': request.args.get('sort_by', 'created_at'),
        'sort_order': request.args.get('sort_order', 'desc')
    }
    
    # Search jobs
    search_results = job_search_service.search_jobs(query_params)
    
    # Return JSON response
    return jsonify(search_results)

@job_bp.route('/api/categories', methods=['GET'])
def api_get_categories():
    """API endpoint for job categories."""
    categories = job_search_service.get_job_categories()
    return jsonify(categories)

@job_bp.route('/api/job-types', methods=['GET'])
def api_get_job_types():
    """API endpoint for job types."""
    job_types = job_search_service.get_job_types()
    return jsonify(job_types)

@job_bp.route('/api/popular-skills', methods=['GET'])
def api_get_popular_skills():
    """API endpoint for popular skills."""
    limit = request.args.get('limit', 20, type=int)
    popular_skills = job_search_service.get_popular_skills(limit=limit)
    return jsonify(popular_skills)