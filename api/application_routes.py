"""
Application management API routes.

This module provides API endpoints for tracking, managing, and controlling job applications.
"""
import uuid
from flask import jsonify, request, g
from api import api_bp
from services.application_service import application_service
from api.auth import auth_required, api_key_required, csrf_token_required
from models.application import ApplicationStatus


@api_bp.route('/applications', methods=['GET'])
@auth_required
def get_applications():
    """Get applications for the current user with filtering and pagination."""
    user_id = g.user_id
    
    # Extract query parameters
    status = request.args.get('status')
    active_only = request.args.get('active_only', 'true').lower() == 'true'
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    
    # Convert status string to enum if provided
    status_enum = None
    if status:
        try:
            status_enum = ApplicationStatus(status)
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': f"Invalid status: {status}"
            }), 400
    
    # Get applications
    applications = application_service.get_applications_by_user(
        user_id, 
        status=status_enum,
        active_only=active_only,
        limit=limit,
        offset=offset
    )
    
    # Convert to dictionaries
    application_dicts = [app.to_dict(include_details=False) for app in applications]
    
    return jsonify({
        'status': 'success',
        'count': len(application_dicts),
        'applications': application_dicts
    })


@api_bp.route('/applications/<application_id>', methods=['GET'])
@auth_required
def get_application_details(application_id):
    """Get detailed information about a specific application."""
    user_id = g.user_id
    
    # Get application
    application = application_service.get_application_by_id(application_id)
    
    if not application:
        return jsonify({
            'status': 'error',
            'message': 'Application not found'
        }), 404
    
    # Check if application belongs to user
    if application.user_id != user_id:
        return jsonify({
            'status': 'error',
            'message': 'Application not found'
        }), 404
    
    return jsonify({
        'status': 'success',
        'application': application.to_dict(include_details=True)
    })


@api_bp.route('/applications', methods=['POST'])
@auth_required
@csrf_token_required
def create_application():
    """Create a new job application."""
    user_id = g.user_id
    data = request.get_json()
    
    if not data:
        return jsonify({
            'status': 'error',
            'message': 'No data provided'
        }), 400
    
    # Validate required fields
    if 'job_id' not in data:
        return jsonify({
            'status': 'error',
            'message': 'Missing required field: job_id'
        }), 400
    
    # Extract application data
    job_id = data.get('job_id')
    materials = data.get('materials', {})
    application_method = data.get('application_method', 'manual')
    
    # Create application
    result = application_service.create_application(
        user_id, 
        job_id, 
        materials=materials,
        application_method=application_method
    )
    
    if not result.success:
        return jsonify({
            'status': 'error',
            'message': result.message,
            'application_id': result.application_id
        }), 400 if not result.application_id else 409
    
    return jsonify({
        'status': 'success',
        'message': result.message,
        'application_id': result.application_id
    }), 201


@api_bp.route('/applications/<application_id>', methods=['PUT'])
@auth_required
@csrf_token_required
def update_application(application_id):
    """Update an existing application."""
    user_id = g.user_id
    data = request.get_json()
    
    if not data:
        return jsonify({
            'status': 'error',
            'message': 'No data provided'
        }), 400
    
    # Get application
    application = application_service.get_application_by_id(application_id)
    
    if not application:
        return jsonify({
            'status': 'error',
            'message': 'Application not found'
        }), 404
    
    # Check if application belongs to user
    if application.user_id != user_id:
        return jsonify({
            'status': 'error',
            'message': 'Application not found'
        }), 404
    
    # Update application status if provided
    if 'status' in data:
        try:
            new_status = ApplicationStatus(data['status'])
            result = application_service.update_application_status(
                application_id, 
                new_status,
                error_message=data.get('error_message')
            )
            
            if not result.success:
                return jsonify({
                    'status': 'error',
                    'message': result.message
                }), 400
        except ValueError:
            return jsonify({
                'status': 'error',
                'message': f"Invalid status: {data['status']}"
            }), 400
    
    # Update application materials if provided
    if 'materials' in data:
        materials = data['materials']
        result = application_service.set_application_materials(
            application_id,
            resume_version=materials.get('resume_version'),
            cover_letter_version=materials.get('cover_letter_version'),
            **{k: v for k, v in materials.items() if k not in ['resume_version', 'cover_letter_version']}
        )
        
        if not result.success:
            return jsonify({
                'status': 'error',
                'message': result.message
            }), 400
    
    # Add custom responses if provided
    if 'custom_responses' in data:
        for question, answer in data['custom_responses'].items():
            result = application_service.add_custom_response(
                application_id,
                question,
                answer
            )
            
            if not result.success:
                return jsonify({
                    'status': 'error',
                    'message': result.message
                }), 400
    
    # Set confirmation details if provided
    if 'confirmation_details' in data:
        confirmation = data['confirmation_details']
        result = application_service.set_confirmation_details(
            application_id,
            confirmation_id=confirmation.get('confirmation_id'),
            confirmation_url=confirmation.get('confirmation_url'),
            **{k: v for k, v in confirmation.items() if k not in ['confirmation_id', 'confirmation_url']}
        )
        
        if not result.success:
            return jsonify({
                'status': 'error',
                'message': result.message
            }), 400
    
    # Get updated application
    application = application_service.get_application_by_id(application_id)
    
    return jsonify({
        'status': 'success',
        'message': 'Application updated successfully',
        'application': application.to_dict()
    })


@api_bp.route('/applications/<application_id>', methods=['DELETE'])
@auth_required
@csrf_token_required
def delete_application(application_id):
    """Mark an application as inactive (soft delete)."""
    user_id = g.user_id
    
    # Get application
    application = application_service.get_application_by_id(application_id)
    
    if not application:
        return jsonify({
            'status': 'error',
            'message': 'Application not found'
        }), 404
    
    # Check if application belongs to user
    if application.user_id != user_id:
        return jsonify({
            'status': 'error',
            'message': 'Application not found'
        }), 404
    
    # Mark application as inactive
    result = application_service.mark_application_inactive(application_id)
    
    if not result.success:
        return jsonify({
            'status': 'error',
            'message': result.message
        }), 400
    
    return jsonify({
        'status': 'success',
        'message': 'Application marked as inactive'
    })


@api_bp.route('/applications/<application_id>/retry', methods=['POST'])
@auth_required
@csrf_token_required
def retry_application(application_id):
    """Retry a failed application."""
    user_id = g.user_id
    
    # Get application
    application = application_service.get_application_by_id(application_id)
    
    if not application:
        return jsonify({
            'status': 'error',
            'message': 'Application not found'
        }), 404
    
    # Check if application belongs to user
    if application.user_id != user_id:
        return jsonify({
            'status': 'error',
            'message': 'Application not found'
        }), 404
    
    # Retry application
    result = application_service.retry_failed_application(application_id)
    
    if not result.success:
        return jsonify({
            'status': 'error',
            'message': result.message
        }), 400
    
    return jsonify({
        'status': 'success',
        'message': result.message,
        'application_id': result.application_id
    })


@api_bp.route('/applications/stats', methods=['GET'])
@auth_required
def get_application_stats():
    """Get statistics about applications for the current user."""
    user_id = g.user_id
    
    # Get application statistics
    stats = application_service.get_application_statistics(user_id)
    
    return jsonify({
        'status': 'success',
        'stats': stats
    })


@api_bp.route('/applications/followup', methods=['GET'])
@auth_required
def get_applications_needing_followup():
    """Get applications that may need follow-up."""
    user_id = g.user_id
    
    # Get days threshold from query parameters
    days_threshold = int(request.args.get('days_threshold', 14))
    
    # Get applications needing follow-up
    applications = application_service.get_applications_needing_followup(days_threshold)
    
    # Filter to only include user's applications
    user_applications = [app for app in applications if app.user_id == user_id]
    
    # Convert to dictionaries
    application_dicts = [app.to_dict(include_details=False) for app in user_applications]
    
    return jsonify({
        'status': 'success',
        'count': len(application_dicts),
        'applications': application_dicts
    })


# Automation control endpoints
@api_bp.route('/automation/status', methods=['GET'])
@api_key_required
def get_automation_status():
    """Get the status of automation processes."""
    user_id = g.user_id
    
    # For now, return a simple status
    # In a real implementation, this would track active automation sessions
    return jsonify({
        'status': 'success',
        'automation_status': {
            'active': False,
            'pending_applications': 0,
            'last_run': None
        }
    })


@api_bp.route('/automation/start', methods=['POST'])
@api_key_required
def start_automation():
    """Start an automation process for job applications."""
    user_id = g.user_id
    data = request.get_json() or {}
    
    # Extract automation parameters
    job_ids = data.get('job_ids', [])
    application_ids = data.get('application_ids', [])
    search_id = data.get('search_id')
    
    # Validate that at least one source of jobs is provided
    if not job_ids and not application_ids and not search_id:
        return jsonify({
            'status': 'error',
            'message': 'No jobs or applications specified for automation'
        }), 400
    
    # In a real implementation, this would start an automation process
    # For now, return a placeholder response
    return jsonify({
        'status': 'success',
        'message': 'Automation process started',
        'automation_id': 'auto_' + str(uuid.uuid4()),
        'job_count': len(job_ids),
        'application_count': len(application_ids)
    })


@api_bp.route('/automation/stop', methods=['POST'])
@api_key_required
def stop_automation():
    """Stop an active automation process."""
    user_id = g.user_id
    data = request.get_json() or {}
    
    # Extract automation ID
    automation_id = data.get('automation_id')
    
    if not automation_id:
        return jsonify({
            'status': 'error',
            'message': 'No automation ID provided'
        }), 400
    
    # In a real implementation, this would stop an automation process
    # For now, return a placeholder response
    return jsonify({
        'status': 'success',
        'message': 'Automation process stopped',
        'automation_id': automation_id
    })


@api_bp.route('/automation/logs', methods=['GET'])
@api_key_required
def get_automation_logs():
    """Get logs for automation processes."""
    user_id = g.user_id
    
    # Extract query parameters
    automation_id = request.args.get('automation_id')
    limit = int(request.args.get('limit', 100))
    offset = int(request.args.get('offset', 0))
    
    # In a real implementation, this would retrieve logs from a database
    # For now, return a placeholder response
    return jsonify({
        'status': 'success',
        'logs': [],
        'count': 0
    })


# Real-time status update endpoint
@api_bp.route('/applications/<application_id>/status', methods=['GET'])
@auth_required
def get_application_status(application_id):
    """Get the current status of an application (for real-time updates)."""
    user_id = g.user_id
    
    # Get application
    application = application_service.get_application_by_id(application_id)
    
    if not application:
        return jsonify({
            'status': 'error',
            'message': 'Application not found'
        }), 404
    
    # Check if application belongs to user
    if application.user_id != user_id:
        return jsonify({
            'status': 'error',
            'message': 'Application not found'
        }), 404
    
    return jsonify({
        'status': 'success',
        'application_status': {
            'id': application.id,
            'status': application.status.value,
            'updated_at': application.updated_at.isoformat() if application.updated_at else None,
            'submitted_at': application.submitted_at.isoformat() if application.submitted_at else None,
            'error_count': int(application.error_count),
            'retry_count': int(application.retry_count),
            'can_retry': application.can_retry(),
            'is_terminal': application.is_terminal_status()
        }
    })