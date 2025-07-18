"""
Enhanced HR routes with comprehensive backend functionality.
"""
import datetime
import uuid
import os
from flask import Blueprint, request, jsonify, render_template, session, flash, redirect, url_for, send_file
from werkzeug.utils import secure_filename
from services.auth_service import auth_service
from services.job_service import JobService
from services.application_service import ApplicationService
from services.interview_service import InterviewService
from services.analytics_service import AnalyticsService
from services.notification_service import notification_service
from api.security_middleware import validate_json_schema, sanitize_inputs, check_content_type, require_auth, require_role
from models.user import User
from models.job import Job, JobCategory, JobSkill
from models.application import Application, ApplicationStatus, Interview
from models.database import db
from sqlalchemy import desc, func, and_, or_
from typing import Dict, List, Optional

# Create blueprint for enhanced HR routes
hr_bp = Blueprint('hr', __name__, url_prefix='/hr')

# Initialize services
job_service = JobService()
application_service = ApplicationService()
interview_service = InterviewService()
analytics_service = AnalyticsService()

@hr_bp.before_request
@require_auth
@require_role('hr')
def check_hr_auth():
    """Ensure user is authenticated and has HR role before accessing HR routes."""
    pass

@hr_bp.route('/dashboard', methods=['GET'])
def dashboard():
    """Enhanced HR dashboard with comprehensive analytics."""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        flash('User not found', 'error')
        return redirect(url_for('auth.logout'))
    
    try:
        # Get dashboard metrics
        metrics = get_hr_dashboard_metrics()
        
        # Get recent applications
        recent_applications = get_recent_applications(limit=10)
        
        # Get active jobs
        active_jobs = job_service.get_active_jobs(limit=5)
        
        # Get upcoming interviews
        upcoming_interviews = interview_service.get_upcoming_interviews(limit=5)
        
        # Get hiring funnel data
        hiring_funnel = analytics_service.get_hiring_funnel_data()
        
        # Get top performing jobs
        top_jobs = analytics_service.get_top_performing_jobs(limit=5)
        
        return render_template('hr/dashboard.html',
                             user=user,
                             metrics=metrics,
                             recent_applications=recent_applications,
                             active_jobs=active_jobs,
                             upcoming_interviews=upcoming_interviews,
                             hiring_funnel=hiring_funnel,
                             top_jobs=top_jobs)
    
    except Exception as e:
        flash(f'Error loading dashboard: {str(e)}', 'error')
        return render_template('hr/dashboard.html', user=user)

@hr_bp.route('/jobs', methods=['GET'])
def jobs():
    """Enhanced job management with filtering and search."""
    try:
        # Get filter parameters
        status = request.args.get('status', 'all')
        department = request.args.get('department', '')
        search = request.args.get('search', '')
        
        # Get jobs with filters
        jobs = job_service.get_jobs_with_filters(status, department, search)
        
        # Get job statistics
        job_stats = job_service.get_job_statistics()
        
        # Get departments for filter
        departments = job_service.get_departments()
        
        return render_template('hr/jobs.html',
                             jobs=jobs,
                             job_stats=job_stats,
                             departments=departments,
                             current_filters={
                                 'status': status,
                                 'department': department,
                                 'search': search
                             })
    
    except Exception as e:
        flash(f'Error loading jobs: {str(e)}', 'error')
        return render_template('hr/jobs.html', jobs=[], job_stats={}, departments=[])

@hr_bp.route('/jobs/create', methods=['GET', 'POST'])
def create_job():
    """Enhanced job creation with validation and skills matching."""
    if request.method == 'POST':
        try:
            # Extract job data
            job_data = {
                'title': request.form.get('title'),
                'company': request.form.get('company'),
                'department': request.form.get('department'),
                'location': request.form.get('location'),
                'description': request.form.get('description'),
                'requirements': request.form.get('requirements'),
                'responsibilities': request.form.get('responsibilities'),
                'job_type': request.form.get('job_type'),
                'experience_required': int(request.form.get('experience_required', 0)),
                'salary_min': float(request.form.get('salary_min', 0)) if request.form.get('salary_min') else None,
                'salary_max': float(request.form.get('salary_max', 0)) if request.form.get('salary_max') else None,
                'remote_option': bool(request.form.get('remote_option')),
                'application_deadline': datetime.datetime.strptime(request.form.get('application_deadline'), '%Y-%m-%d') if request.form.get('application_deadline') else None
            }
            
            # Extract skills
            skills = [skill.strip() for skill in request.form.get('skills', '').split(',') if skill.strip()]
            
            # Create job
            job_id = job_service.create_job(job_data, skills, session.get('user_id'))
            
            flash('Job created successfully', 'success')
            return redirect(url_for('hr.job_detail', job_id=job_id))
        
        except Exception as e:
            flash(f'Error creating job: {str(e)}', 'error')
    
    # Get job categories and templates
    categories = job_service.get_job_categories()
    templates = job_service.get_job_templates()
    
    return render_template('hr/create_job.html',
                         categories=categories,
                         templates=templates)

@hr_bp.route('/jobs/<job_id>', methods=['GET'])
def job_detail(job_id):
    """View detailed job information with analytics."""
    try:
        job = job_service.get_job_with_details(job_id)
        
        if not job:
            flash('Job not found', 'error')
            return redirect(url_for('hr.jobs'))
        
        # Get job analytics
        job_analytics = analytics_service.get_job_analytics(job_id)
        
        # Get applications for this job
        applications = application_service.get_job_applications(job_id)
        
        return render_template('hr/job_detail.html',
                             job=job,
                             job_analytics=job_analytics,
                             applications=applications)
    
    except Exception as e:
        flash(f'Error loading job details: {str(e)}', 'error')
        return redirect(url_for('hr.jobs'))

@hr_bp.route('/jobs/<job_id>/edit', methods=['GET', 'POST'])
def edit_job(job_id):
    """Edit existing job listing."""
    try:
        job = Job.query.get(job_id)
        
        if not job:
            flash('Job not found', 'error')
            return redirect(url_for('hr.jobs'))
        
        if request.method == 'POST':
            # Update job data
            job_data = {
                'title': request.form.get('title'),
                'company': request.form.get('company'),
                'department': request.form.get('department'),
                'location': request.form.get('location'),
                'description': request.form.get('description'),
                'requirements': request.form.get('requirements'),
                'responsibilities': request.form.get('responsibilities'),
                'job_type': request.form.get('job_type'),
                'experience_required': int(request.form.get('experience_required', 0)),
                'salary_min': float(request.form.get('salary_min', 0)) if request.form.get('salary_min') else None,
                'salary_max': float(request.form.get('salary_max', 0)) if request.form.get('salary_max') else None,
                'remote_option': bool(request.form.get('remote_option')),
                'application_deadline': datetime.datetime.strptime(request.form.get('application_deadline'), '%Y-%m-%d') if request.form.get('application_deadline') else None
            }
            
            # Extract skills
            skills = [skill.strip() for skill in request.form.get('skills', '').split(',') if skill.strip()]
            
            # Update job
            job_service.update_job(job_id, job_data, skills)
            
            flash('Job updated successfully', 'success')
            return redirect(url_for('hr.job_detail', job_id=job_id))
        
        # Get job categories
        categories = job_service.get_job_categories()
        
        return render_template('hr/edit_job.html',
                             job=job,
                             categories=categories)
    
    except Exception as e:
        flash(f'Error editing job: {str(e)}', 'error')
        return redirect(url_for('hr.jobs'))

@hr_bp.route('/applications', methods=['GET'])
def applications():
    """Enhanced applications management with filtering and bulk actions."""
    try:
        # Get filter parameters
        status = request.args.get('status', '')
        job_id = request.args.get('job_id', '')
        date_range = request.args.get('date_range', '')
        search = request.args.get('search', '')
        
        # Get applications with filters
        applications = application_service.get_applications_with_filters(
            status=status,
            job_id=job_id,
            date_range=date_range,
            search=search
        )
        
        # Get application statistics
        stats = application_service.get_application_statistics()
        
        # Get jobs for filter dropdown
        jobs = job_service.get_active_jobs()
        
        return render_template('hr/applications.html',
                             applications=applications,
                             stats=stats,
                             jobs=jobs,
                             current_filters={
                                 'status': status,
                                 'job_id': job_id,
                                 'date_range': date_range,
                                 'search': search
                             })
    
    except Exception as e:
        flash(f'Error loading applications: {str(e)}', 'error')
        return render_template('hr/applications.html',
                             applications=[],
                             stats={},
                             jobs=[])

@hr_bp.route('/applications/<application_id>', methods=['GET'])
def application_detail(application_id):
    """View detailed application information."""
    try:
        application = application_service.get_application_with_details(application_id)
        
        if not application:
            flash('Application not found', 'error')
            return redirect(url_for('hr.applications'))
        
        # Get application timeline
        timeline = application_service.get_application_timeline(application_id)
        
        # Get similar candidates
        similar_candidates = application_service.get_similar_candidates(application_id, limit=5)
        
        return render_template('hr/application_detail.html',
                             application=application,
                             timeline=timeline,
                             similar_candidates=similar_candidates)
    
    except Exception as e:
        flash(f'Error loading application details: {str(e)}', 'error')
        return redirect(url_for('hr.applications'))

@hr_bp.route('/applications/<application_id>/status', methods=['POST'])
def update_application_status(application_id):
    """Update application status."""
    try:
        data = request.get_json()
        new_status = data.get('status')
        note = data.get('note', '')
        
        success = application_service.update_application_status(
            application_id,
            new_status,
            session.get('user_id'),
            note
        )
        
        if success:
            return jsonify({'success': True, 'message': 'Status updated successfully'})
        else:
            return jsonify({'success': False, 'error': 'Failed to update status'})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@hr_bp.route('/applications/<application_id>/add-note', methods=['POST'])
def add_application_note(application_id):
    """Add note to application."""
    try:
        note = request.form.get('note')
        
        if not note:
            flash('Note cannot be empty', 'error')
            return redirect(url_for('hr.application_detail', application_id=application_id))
        
        success = application_service.add_application_note(
            application_id,
            note,
            session.get('user_id')
        )
        
        if success:
            flash('Note added successfully', 'success')
        else:
            flash('Failed to add note', 'error')
        
        return redirect(url_for('hr.application_detail', application_id=application_id))
    
    except Exception as e:
        flash(f'Error adding note: {str(e)}', 'error')
        return redirect(url_for('hr.application_detail', application_id=application_id))

@hr_bp.route('/applications/<application_id>/download-resume')
def download_resume(application_id):
    """Download candidate's resume."""
    try:
        application = Application.query.get(application_id)
        
        if not application or not application.resume_path:
            flash('Resume not found', 'error')
            return redirect(url_for('hr.application_detail', application_id=application_id))
        
        return send_file(application.resume_path, as_attachment=True)
    
    except Exception as e:
        flash(f'Error downloading resume: {str(e)}', 'error')
        return redirect(url_for('hr.application_detail', application_id=application_id))

@hr_bp.route('/interviews', methods=['GET'])
def interviews():
    """Interview management dashboard."""
    try:
        # Get upcoming interviews
        upcoming_interviews = interview_service.get_upcoming_interviews()
        
        # Get interview statistics
        interview_stats = interview_service.get_interview_statistics()
        
        # Get interviewers
        interviewers = interview_service.get_available_interviewers()
        
        return render_template('hr/interviews.html',
                             upcoming_interviews=upcoming_interviews,
                             interview_stats=interview_stats,
                             interviewers=interviewers)
    
    except Exception as e:
        flash(f'Error loading interviews: {str(e)}', 'error')
        return render_template('hr/interviews.html',
                             upcoming_interviews=[],
                             interview_stats={},
                             interviewers=[])

@hr_bp.route('/interviews/schedule', methods=['GET', 'POST'])
def schedule_interview():
    """Schedule new interview."""
    application_id = request.args.get('application_id')
    
    if request.method == 'POST':
        try:
            # Extract interview data
            interview_data = {
                'application_id': request.form.get('application_id'),
                'interview_type': request.form.get('interview_type'),
                'interview_date': request.form.get('interview_date'),
                'interview_time': request.form.get('interview_time'),
                'duration': int(request.form.get('duration', 60)),
                'location': request.form.get('location'),
                'meeting_instructions': request.form.get('meeting_instructions'),
                'primary_interviewer': request.form.get('primary_interviewer'),
                'additional_interviewers': request.form.getlist('additional_interviewers'),
                'focus_areas': request.form.getlist('focus_areas'),
                'interview_notes': request.form.get('interview_notes'),
                'send_candidate_email': bool(request.form.get('send_candidate_email')),
                'send_interviewer_email': bool(request.form.get('send_interviewer_email')),
                'calendar_invite': bool(request.form.get('calendar_invite'))
            }
            
            # Schedule interview
            interview_id = interview_service.schedule_interview(interview_data, session.get('user_id'))
            
            flash('Interview scheduled successfully', 'success')
            return redirect(url_for('hr.interviews'))
        
        except Exception as e:
            flash(f'Error scheduling interview: {str(e)}', 'error')
    
    # Get application details if application_id provided
    application = None
    if application_id:
        application = Application.query.get(application_id)
    
    # Get available interviewers
    interviewers = interview_service.get_available_interviewers()
    
    return render_template('hr/schedule_interview.html',
                         application=application,
                         interviewers=interviewers)

@hr_bp.route('/reports', methods=['GET'])
def reports():
    """HR reports and analytics dashboard."""
    try:
        # Get report type
        report_type = request.args.get('type', 'overview')
        
        # Get date range filters
        date_range = request.args.get('date_range', 'last_30_days')
        department = request.args.get('department', '')
        job_type = request.args.get('job_type', '')
        
        # Generate reports based on type
        if report_type == 'overview':
            report_data = analytics_service.get_overview_report(date_range, department, job_type)
        elif report_type == 'hiring':
            report_data = analytics_service.get_hiring_report(date_range, department, job_type)
        elif report_type == 'performance':
            report_data = analytics_service.get_performance_report(date_range, department, job_type)
        else:
            report_data = analytics_service.get_overview_report(date_range, department, job_type)
        
        # Get filter options
        departments = job_service.get_departments()
        job_types = job_service.get_job_types()
        
        return render_template('hr/reports.html',
                             report_type=report_type,
                             report_data=report_data,
                             departments=departments,
                             job_types=job_types,
                             current_filters={
                                 'date_range': date_range,
                                 'department': department,
                                 'job_type': job_type
                             })
    
    except Exception as e:
        flash(f'Error generating reports: {str(e)}', 'error')
        return render_template('hr/reports.html',
                             report_type='overview',
                             report_data={},
                             departments=[],
                             job_types=[])

@hr_bp.route('/reports/export', methods=['GET'])
def export_report():
    """Export report data."""
    try:
        report_type = request.args.get('type', 'overview')
        format_type = request.args.get('format', 'csv')
        
        # Generate and export report
        file_path = analytics_service.export_report(report_type, format_type)
        
        return send_file(file_path, as_attachment=True)
    
    except Exception as e:
        flash(f'Error exporting report: {str(e)}', 'error')
        return redirect(url_for('hr.reports'))

@hr_bp.route('/candidates', methods=['GET'])
def candidates():
    """Candidate management and talent pool."""
    try:
        # Get filter parameters
        skills = request.args.get('skills', '')
        experience = request.args.get('experience', '')
        location = request.args.get('location', '')
        availability = request.args.get('availability', '')
        
        # Get candidates with filters
        candidates = application_service.get_candidates_with_filters(
            skills=skills,
            experience=experience,
            location=location,
            availability=availability
        )
        
        # Get candidate statistics
        candidate_stats = application_service.get_candidate_statistics()
        
        return render_template('hr/candidates.html',
                             candidates=candidates,
                             candidate_stats=candidate_stats,
                             current_filters={
                                 'skills': skills,
                                 'experience': experience,
                                 'location': location,
                                 'availability': availability
                             })
    
    except Exception as e:
        flash(f'Error loading candidates: {str(e)}', 'error')
        return render_template('hr/candidates.html',
                             candidates=[],
                             candidate_stats={})

# Helper functions
def get_hr_dashboard_metrics() -> Dict:
    """Get HR dashboard metrics."""
    try:
        # Get current date ranges
        today = datetime.datetime.utcnow().date()
        week_ago = today - datetime.timedelta(days=7)
        month_ago = today - datetime.timedelta(days=30)
        
        # Calculate metrics
        total_jobs = Job.query.filter_by(is_active=True).count()
        total_applications = Application.query.count()
        new_applications_week = Application.query.filter(
            Application.created_at >= week_ago
        ).count()
        
        interviews_scheduled = Interview.query.filter(
            Interview.scheduled_at >= datetime.datetime.utcnow()
        ).count()
        
        hired_candidates = Application.query.filter_by(
            status=ApplicationStatus.ACCEPTED
        ).count()
        
        # Calculate average time to hire (placeholder)
        avg_time_to_hire = 21  # days
        
        return {
            'total_jobs': total_jobs,
            'total_applications': total_applications,
            'new_applications_week': new_applications_week,
            'interviews_scheduled': interviews_scheduled,
            'hired_candidates': hired_candidates,
            'avg_time_to_hire': avg_time_to_hire
        }
    
    except Exception as e:
        return {
            'total_jobs': 0,
            'total_applications': 0,
            'new_applications_week': 0,
            'interviews_scheduled': 0,
            'hired_candidates': 0,
            'avg_time_to_hire': 0
        }

def get_recent_applications(limit: int = 10) -> List:
    """Get recent applications."""
    try:
        applications = Application.query\
            .order_by(desc(Application.created_at))\
            .limit(limit)\
            .all()
        return applications
    except Exception:
        return []