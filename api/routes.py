"""
API routes for the Job Application Agent.
"""
from flask import jsonify, request, current_app, session, g
from api import api_bp
from models.database import db
from services.auth_service import auth_service
from api.auth import login_required, api_key_required, auth_required


@api_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        'status': 'healthy',
        'message': 'Job Application Agent API is running'
    })


@api_bp.route('/health/db', methods=['GET'])
def database_health_check():
    """Database health check endpoint."""
    try:
        # Test database connection using SQLAlchemy 2.0 syntax
        from sqlalchemy import text
        result = db.session.execute(text("SELECT 1 as test")).fetchone()
        if result and result[0] == 1:
            return jsonify({
                'status': 'healthy',
                'message': 'Database connection successful',
                'database_uri': current_app.config['SQLALCHEMY_DATABASE_URI']
            })
        else:
            return jsonify({
                'status': 'unhealthy',
                'message': 'Database connection failed - unexpected result'
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'message': f'Database connection failed: {str(e)}'
        }), 500


@api_bp.route('/auth/register', methods=['POST'])
def register():
    """Register a new user account."""
    data = request.get_json()
    
    if not data:
        return jsonify({
            'status': 'error',
            'message': 'No data provided'
        }), 400
    
    email = data.get('email')
    password = data.get('password')
    personal_data = data.get('personal_data', {})
    
    if not email or not password:
        return jsonify({
            'status': 'error',
            'message': 'Email and password are required'
        }), 400
    
    # Create user
    success, user_id, message = auth_service.create_user(email, password, personal_data)
    
    if success:
        return jsonify({
            'status': 'success',
            'message': message,
            'user_id': user_id
        }), 201
    else:
        return jsonify({
            'status': 'error',
            'message': message
        }), 400


@api_bp.route('/auth/login', methods=['POST'])
def login():
    """Authenticate a user and create a session."""
    data = request.get_json()
    
    if not data:
        return jsonify({
            'status': 'error',
            'message': 'No data provided'
        }), 400
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({
            'status': 'error',
            'message': 'Email and password are required'
        }), 400
    
    # Authenticate user
    success, user_data, message = auth_service.authenticate_user(email, password)
    
    if success and user_data:
        # Create session
        auth_service.create_session(user_data['id'])
        
        return jsonify({
            'status': 'success',
            'message': 'Login successful',
            'user': user_data
        })
    else:
        return jsonify({
            'status': 'error',
            'message': message
        }), 401


@api_bp.route('/auth/logout', methods=['POST'])
@login_required
def logout():
    """End the current user session."""
    auth_service.end_session()
    
    return jsonify({
        'status': 'success',
        'message': 'Logout successful'
    })


@api_bp.route('/auth/api-key', methods=['POST', 'DELETE'])
@login_required
def api_key_management():
    """Generate or revoke API keys."""
    user_id = g.user_id
    
    if request.method == 'POST':
        # Generate new API key
        data = request.get_json() or {}
        description = data.get('description', 'API Key')
        
        success, api_key, message = auth_service.generate_api_key(user_id, description)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message,
                'api_key': api_key
            }), 201
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 400
    
    elif request.method == 'DELETE':
        # Revoke API key
        data = request.get_json()
        
        if not data or 'api_key' not in data:
            return jsonify({
                'status': 'error',
                'message': 'API key is required'
            }), 400
        
        api_key = data.get('api_key')
        success, message = auth_service.revoke_api_key(user_id, api_key)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message
            })
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 400


@api_bp.route('/profile', methods=['GET', 'POST', 'PUT', 'DELETE'])
@auth_required
def profile():
    """Profile management endpoints."""
    user_id = g.user_id
    
    if request.method == 'GET':
        return jsonify({
            'status': 'success',
            'message': 'Get profile - not implemented yet',
            'user_id': user_id
        })
    elif request.method == 'POST':
        return jsonify({
            'status': 'success',
            'message': 'Create profile - not implemented yet',
            'user_id': user_id
        })
    elif request.method == 'PUT':
        return jsonify({
            'status': 'success',
            'message': 'Update profile - not implemented yet',
            'user_id': user_id
        })
    elif request.method == 'DELETE':
        return jsonify({
            'status': 'success',
            'message': 'Delete profile - not implemented yet',
            'user_id': user_id
        })


@api_bp.route('/jobs', methods=['GET'])
@auth_required
def jobs():
    """Job search and management endpoints."""
    return jsonify({
        'status': 'success',
        'message': 'Job endpoints - not implemented yet',
        'user_id': g.user_id
    })


@api_bp.route('/applications', methods=['GET', 'POST'])
@auth_required
def applications():
    """Application tracking endpoints."""
    user_id = g.user_id
    
    if request.method == 'GET':
        return jsonify({
            'status': 'success',
            'message': 'Get applications - not implemented yet',
            'user_id': user_id
        })
    elif request.method == 'POST':
        return jsonify({
            'status': 'success',
            'message': 'Create application - not implemented yet',
            'user_id': user_id
        })


@api_bp.route('/automation', methods=['GET', 'POST'])
@api_key_required
def automation():
    """Automation control endpoints."""
    user_id = g.user_id
    
    if request.method == 'GET':
        return jsonify({
            'status': 'success',
            'message': 'Get automation status - not implemented yet',
            'user_id': user_id
        })
    elif request.method == 'POST':
        return jsonify({
            'status': 'success',
            'message': 'Control automation - not implemented yet',
            'user_id': user_id
        })


@api_bp.route('/config', methods=['GET', 'PUT'])
@auth_required
def config():
    """System configuration endpoints."""
    user_id = g.user_id
    
    if request.method == 'GET':
        return jsonify({
            'status': 'success',
            'message': 'Get config - not implemented yet',
            'user_id': user_id
        })
    elif request.method == 'PUT':
        return jsonify({
            'status': 'success',
            'message': 'Update config - not implemented yet',
            'user_id': user_id
        })