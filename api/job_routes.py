"""
Job search and management API routes.

This module provides API endpoints for searching, filtering, and managing job listings.
"""
from flask import jsonify, request, g
from api import api_bp
from services.job_search_service import job_search_service
from api.auth import auth_required
from api.csrf import csrf_token_required
from models.database import db


@api_bp.route('/jobs', methods=['GET'])
@auth_required
def get_jobs():
    """Get job listings with filtering and pagination."""
    user_id = g.user_id
    
    # Extract query parameters
    criteria = {
        'keywords': request.args.get('keywords', ''),
        'locations': request.args.get('locations', ''),
        'job_types': request.args.get('job_types', ''),
        'experience_levels': request.args.get('experience_levels', ''),
        'remote_options': request.args.get('remote_options', ''),
        'sources': request.args.get('sources', ''),
        'sort_by': request.args.get('sort_by', 'date'),  # date or relevance
        'limit': request.args.get('limit', 50),
        'offset': request.args.get('offset', 0)
    }
    
    # Add optional filters if provided
    if 'salary_min' in request.args:
        criteria['salary_min'] = request.args.get('salary_min')
    if 'salary_max' in request.args:
        criteria['salary_max'] = request.args.get('salary_max')
    if 'days_old' in request.args:
        criteria['days_old'] = request.args.get('days_old')
    
    # Convert comma-separated values to lists
    for key in ['keywords', 'locations', 'job_types', 'experience_levels', 'remote_options', 'sources']:
        if criteria[key] and isinstance(criteria[key], str) and ',' in criteria[key]:
            criteria[key] = [item.strip() for item in criteria[key].split(',')]
    
    # Search for jobs
    success, jobs, message = job_search_service.search_jobs(criteria)
    
    if not success:
        return jsonify({
            'status': 'error',
            'message': message
        }), 400
    
    # Convert jobs to dictionaries
    job_dicts = [job.to_dict(include_description=False) for job in jobs]
    
    return jsonify({
        'status': 'success',
        'message': message,
        'count': len(job_dicts),
        'jobs': job_dicts
    })


@api_bp.route('/jobs/<job_id>', methods=['GET'])
@auth_required
def get_job_details(job_id):
    """Get detailed information about a specific job."""
    user_id = g.user_id
    
    job = job_search_service.get_job_by_id(job_id)
    
    if not job:
        return jsonify({
            'status': 'error',
            'message': 'Job not found'
        }), 404
    
    # Get similar jobs
    similar_jobs = job_search_service.get_similar_jobs(job_id, limit=5)
    similar_job_dicts = [j.to_dict(include_description=False) for j in similar_jobs]
    
    return jsonify({
        'status': 'success',
        'job': job.to_dict(include_description=True),
        'similar_jobs': similar_job_dicts
    })


@api_bp.route('/jobs', methods=['POST'])
@auth_required
@csrf_token_required
def create_job():
    """Create a new job listing."""
    user_id = g.user_id
    data = request.get_json()
    
    if not data:
        return jsonify({
            'status': 'error',
            'message': 'No data provided'
        }), 400
    
    # Validate required fields
    required_fields = ['title', 'company', 'source_website', 'source_url']
    for field in required_fields:
        if field not in data:
            return jsonify({
                'status': 'error',
                'message': f'Missing required field: {field}'
            }), 400
    
    # Save job
    success, job, message = job_search_service.save_job(data)
    
    if not success:
        return jsonify({
            'status': 'error',
            'message': message
        }), 400
    
    return jsonify({
        'status': 'success',
        'message': message,
        'job': job.to_dict()
    }), 201


@api_bp.route('/jobs/<job_id>', methods=['PUT'])
@auth_required
@csrf_token_required
def update_job(job_id):
    """Update an existing job listing."""
    user_id = g.user_id
    data = request.get_json()
    
    if not data:
        return jsonify({
            'status': 'error',
            'message': 'No data provided'
        }), 400
    
    # Check if job exists
    job = job_search_service.get_job_by_id(job_id)
    if not job:
        return jsonify({
            'status': 'error',
            'message': 'Job not found'
        }), 404
    
    # Update job data
    data['id'] = job_id  # Ensure ID is preserved
    success, updated_job, message = job_search_service.save_job(data)
    
    if not success:
        return jsonify({
            'status': 'error',
            'message': message
        }), 400
    
    return jsonify({
        'status': 'success',
        'message': message,
        'job': updated_job.to_dict()
    })


@api_bp.route('/jobs/<job_id>', methods=['DELETE'])
@auth_required
@csrf_token_required
def delete_job(job_id):
    """Mark a job as inactive (soft delete)."""
    user_id = g.user_id
    
    # Check if job exists
    job = job_search_service.get_job_by_id(job_id)
    if not job:
        return jsonify({
            'status': 'error',
            'message': 'Job not found'
        }), 404
    
    # Mark job as inactive
    success, message = job_search_service.mark_job_inactive(job_id)
    
    if not success:
        return jsonify({
            'status': 'error',
            'message': message
        }), 400
    
    return jsonify({
        'status': 'success',
        'message': message
    })


@api_bp.route('/search', methods=['POST'])
@auth_required
@csrf_token_required
def trigger_job_search():
    """Trigger a job search across configured platforms."""
    user_id = g.user_id
    data = request.get_json() or {}
    
    # Extract search criteria
    criteria = {
        'keywords': data.get('keywords', []),
        'locations': data.get('locations', []),
        'job_types': data.get('job_types', []),
        'experience_levels': data.get('experience_levels', []),
        'remote_options': data.get('remote_options', []),
        'salary_min': data.get('salary_min'),
        'salary_max': data.get('salary_max'),
        'sources': data.get('sources', []),
        'days_old': data.get('days_old', 30)
    }
    
    # Get user preferences for filtering
    preferences = data.get('preferences', {})
    
    # Validate sources
    valid_sources = ['linkedin', 'indeed', 'glassdoor', 'monster', 'ziprecruiter', 'other']
    if criteria['sources']:
        invalid_sources = [s for s in criteria['sources'] if s.lower() not in valid_sources]
        if invalid_sources:
            return jsonify({
                'status': 'error',
                'message': f"Invalid sources: {', '.join(invalid_sources)}. Valid sources are: {', '.join(valid_sources)}"
            }), 400
    
    # Import job search service here to avoid circular imports
    from services.job_search_service import job_search_service
    
    # Trigger the search process
    success, search_id, message = job_search_service.trigger_search(user_id, criteria, preferences)
    
    if not success:
        return jsonify({
            'status': 'error',
            'message': message
        }), 400
    
    return jsonify({
        'status': 'success',
        'message': message,
        'search_id': search_id,
        'criteria': criteria
    })


@api_bp.route('/jobs/filter', methods=['POST'])
@auth_required
def filter_jobs():
    """Filter jobs based on user preferences."""
    user_id = g.user_id
    data = request.get_json() or {}
    
    # Extract job IDs to filter
    job_ids = data.get('job_ids', [])
    if not job_ids:
        return jsonify({
            'status': 'error',
            'message': 'No job IDs provided'
        }), 400
    
    # Extract preferences
    preferences = data.get('preferences', {})
    
    # Get jobs by IDs
    jobs = []
    for job_id in job_ids:
        job = job_search_service.get_job_by_id(job_id)
        if job:
            jobs.append(job)
    
    # Apply filtering
    filtered_jobs = job_search_service.filter_jobs(jobs, preferences)
    
    # Convert to dictionaries
    job_dicts = [job.to_dict(include_description=False) for job in filtered_jobs]
    
    return jsonify({
        'status': 'success',
        'count': len(job_dicts),
        'jobs': job_dicts
    })
@api_bp.route('/search/<search_id>', methods=['GET'])
@auth_required
def get_search_status(search_id):
    """Get the status of a job search."""
    user_id = g.user_id
    
    # Get search status
    success, status_data, message = job_search_service.get_search_status(search_id)
    
    if not success:
        return jsonify({
            'status': 'error',
            'message': message
        }), 404
    
    # Check if search belongs to user
    if status_data.get('user_id') != user_id:
        return jsonify({
            'status': 'error',
            'message': 'Search not found'
        }), 404
    
    return jsonify({
        'status': 'success',
        'search': status_data
    })


@api_bp.route('/search/<search_id>/results', methods=['GET'])
@auth_required
def get_search_results(search_id):
    """Get the results of a completed job search."""
    user_id = g.user_id
    
    # Extract pagination parameters
    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)
    
    # Get search results
    success, jobs, message = job_search_service.get_search_results(search_id, limit, offset)
    
    if not success:
        return jsonify({
            'status': 'error',
            'message': message
        }), 404
    
    # Convert jobs to dictionaries
    job_dicts = [job.to_dict(include_description=False) for job in jobs]
    
    return jsonify({
        'status': 'success',
        'count': len(job_dicts),
        'jobs': job_dicts,
        'message': message
    })


@api_bp.route('/jobs/sort', methods=['POST'])
@auth_required
def sort_jobs():
    """Sort jobs based on specified criteria."""
    user_id = g.user_id
    data = request.get_json() or {}
    
    # Extract job IDs to sort
    job_ids = data.get('job_ids', [])
    if not job_ids:
        return jsonify({
            'status': 'error',
            'message': 'No job IDs provided'
        }), 400
    
    # Extract sort parameters
    sort_by = data.get('sort_by', 'date')  # date, relevance, company, title
    sort_order = data.get('sort_order', 'desc')  # asc, desc
    
    # Get jobs by IDs
    jobs = []
    for job_id in job_ids:
        job = job_search_service.get_job_by_id(job_id)
        if job:
            jobs.append(job)
    
    # Sort jobs
    if sort_by == 'date':
        jobs.sort(key=lambda j: j.discovered_at or datetime.datetime.min, 
                  reverse=(sort_order == 'desc'))
    elif sort_by == 'company':
        jobs.sort(key=lambda j: j.company.lower() if j.company else '', 
                  reverse=(sort_order == 'desc'))
    elif sort_by == 'title':
        jobs.sort(key=lambda j: j.title.lower() if j.title else '', 
                  reverse=(sort_order == 'desc'))
    elif sort_by == 'salary':
        # Sort by maximum salary if available, otherwise minimum
        jobs.sort(key=lambda j: (j.salary_max or j.salary_min or 0), 
                  reverse=(sort_order == 'desc'))
    
    # Convert to dictionaries
    job_dicts = [job.to_dict(include_description=False) for job in jobs]
    
    return jsonify({
        'status': 'success',
        'count': len(job_dicts),
        'jobs': job_dicts
    })


@api_bp.route('/jobs/stats', methods=['GET'])
@auth_required
def get_job_stats():
    """Get statistics about job listings."""
    user_id = g.user_id
    
    try:
        # Get total job count
        total_jobs = db.session.query(db.func.count(Job.id)).filter(Job.is_active == True).scalar() or 0
        
        # Get jobs by source website
        jobs_by_source = db.session.query(
            Job.source_website, 
            db.func.count(Job.id)
        ).filter(
            Job.is_active == True
        ).group_by(
            Job.source_website
        ).all()
        
        # Get jobs by job type
        jobs_by_type = db.session.query(
            Job.job_type, 
            db.func.count(Job.id)
        ).filter(
            Job.is_active == True,
            Job.job_type != None
        ).group_by(
            Job.job_type
        ).all()
        
        # Get jobs by experience level
        jobs_by_experience = db.session.query(
            Job.experience_level, 
            db.func.count(Job.id)
        ).filter(
            Job.is_active == True,
            Job.experience_level != None
        ).group_by(
            Job.experience_level
        ).all()
        
        # Get jobs by remote option
        jobs_by_remote = db.session.query(
            Job.remote_option, 
            db.func.count(Job.id)
        ).filter(
            Job.is_active == True,
            Job.remote_option != None
        ).group_by(
            Job.remote_option
        ).all()
        
        # Format results
        stats = {
            'total_jobs': total_jobs,
            'by_source': {source: count for source, count in jobs_by_source},
            'by_job_type': {job_type: count for job_type, count in jobs_by_type},
            'by_experience': {exp: count for exp, count in jobs_by_experience},
            'by_remote_option': {remote: count for remote, count in jobs_by_remote}
        }
        
        return jsonify({
            'status': 'success',
            'stats': stats
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f"Error retrieving job statistics: {str(e)}"
        }), 500