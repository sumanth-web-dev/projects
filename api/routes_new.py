"""
API routes for the Job Application Agent.
"""
import datetime
from flask import jsonify, request, current_app, session, g
from api import api_bp
from models.database import db
from services.auth_service import auth_service
from services.security_audit_service import security_audit_service
from api.auth import login_required, api_key_required, auth_required, role_required
from api.csrf import csrf_token_required, get_csrf_token
from api.security_middleware import (
    check_content_type, validate_json_schema, sanitize_inputs,
    prevent_parameter_pollution
)
from utils.input_sanitizer import validate_email, sanitize_dict


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
@check_content_type('application/json')
@sanitize_inputs()
@validate_json_schema({
    'email': {'type': 'string', 'required': True, 'pattern': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'},
    'password': {'type': 'string', 'required': True, 'minLength': 8},
    'personal_data': {'type': 'object', 'required': False}
})
def register():
    """Register a new user account."""
    data = request.get_json()
    
    email = data.get('email')
    password = data.get('password')
    personal_data = sanitize_dict(data.get('personal_data', {}))
    
    # Validate email format
    if not validate_email(email):
        return jsonify({
            'status': 'error',
            'message': 'Invalid email format'
        }), 400
    
    # Create user
    success, user_id, message = auth_service.create_user(email, password, personal_data)
    
    # Log security event
    security_audit_service.log_security_event(
        event_type='user_registration',
        description=f"User registration attempt: {email}",
        severity='info',
        details={'success': success}
    )
    
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
@check_content_type('application/json')
@sanitize_inputs()
@validate_json_schema({
    'email': {'type': 'string', 'required': True},
    'password': {'type': 'string', 'required': True}
})
def login():
    """Authenticate a user and create a session."""
    data = request.get_json()
    
    email = data.get('email')
    password = data.get('password')
    
    # Get client IP and user agent for logging
    client_ip = request.remote_addr
    user_agent = request.user_agent.string if request.user_agent else 'unknown'
    
    # Authenticate user
    success, user_data, message = auth_service.authenticate_user(email, password)
    
    # Log authentication attempt
    security_audit_service.log_auth_event(
        event_type='login',
        success=success,
        username=email,
        details={
            'ip_address': client_ip,
            'user_agent': user_agent
        }
    )
    
    if success and user_data:
        # Create session
        auth_service.create_session(user_data['id'])
        
        # Get CSRF token for client
        csrf_token = session.get('csrf_token')
        
        return jsonify({
            'status': 'success',
            'message': 'Login successful',
            'user': user_data,
            'csrf_token': csrf_token
        })
    else:
        return jsonify({
            'status': 'error',
            'message': message
        }), 401
        
        


@api_bp.route('/auth/csrf-token', methods=['GET'])
@login_required
def get_csrf_token_endpoint():
    """Get CSRF token for the current session."""
    try:
        csrf_token = get_csrf_token()
        return jsonify({
            'status': 'success',
            'csrf_token': csrf_token
        })
    except RuntimeError as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 400


@api_bp.route('/auth/logout', methods=['POST'])
@login_required
@csrf_token_required
def logout():
    """End the current user session."""
    # Log security event
    security_audit_service.log_auth_event(
        event_type='logout',
        success=True,
        username=g.user_id,
        details={
            'ip_address': request.remote_addr,
            'user_agent': request.user_agent.string if request.user_agent else 'unknown'
        }
    )
    
    auth_service.end_session()
    
    return jsonify({
        'status': 'success',
        'message': 'Logout successful'
    })
    

@api_bp.route('/auth/api-key', methods=['POST', 'DELETE'])
@login_required
@csrf_token_required
@check_content_type('application/json')
@sanitize_inputs()
def api_key_management():
    """Generate or revoke API keys."""
    user_id = g.user_id
    
    if request.method == 'POST':
        # Generate new API key
        data = request.get_json() or {}
        description = data.get('description', 'API Key')
        permissions = data.get('permissions', [])
        expires_days = data.get('expires_days')
        
        # Set expiration date if provided
        expires_at = None
        if expires_days is not None:
            expires_at = datetime.datetime.utcnow() + datetime.timedelta(days=expires_days)
        
        success, api_key, message = auth_service.generate_api_key(
            user_id, description, permissions, expires_at
        )
        
        # Log security event
        security_audit_service.log_security_event(
            event_type='api_key_generated',
            description=f"API key generated for user {user_id}",
            severity='info',
            details={
                'success': success,
                'description': description,
                'expires_days': expires_days
            }
        )
        
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
        
        # Log security event
        security_audit_service.log_security_event(
            event_type='api_key_revoked',
            description=f"API key revoked for user {user_id}",
            severity='info',
            details={'success': success}
        )
        
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
            
            
@api_bp.route('/get_user_role', methods=['GET'])
def get_user_role():
    """Get the current user's role."""
    user_id = auth_service.get_current_user_id()
    
    if not user_id:
        return jsonify({
            'success': False,
            'message': 'User not authenticated'
        }), 401
    
    # Get user details to determine role
    from models.user import User
    user = User.query.get(user_id)
    
    if not user:
        return jsonify({
            'success': False,
            'message': 'User not found'
        }), 404
    
    # Get user roles
    personal_data = user.personal_data or {}
    roles = personal_data.get('roles', [])
    
    return jsonify({
        'success': True,
        'roles': roles,
        'user_id': user_id
    })

@api_bp.route('/config', methods=['GET', 'PUT'])
@auth_required
@csrf_token_required
@prevent_parameter_pollution()
def config():
    """System configuration endpoints."""
    user_id = g.user_id
    
    if request.method == 'GET':
        # Log security event for configuration access
        security_audit_service.log_security_event(
            event_type='config_access',
            description=f"Configuration accessed by user {user_id}",
            severity='info'
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Get config - not implemented yet',
            'user_id': user_id
        })
    elif request.method == 'PUT':
        # Require content type check for PUT
        if not request.is_json:
            return jsonify({
                'status': 'error',
                'message': 'Content-Type must be application/json'
            }), 415
        
        # Log security event for configuration change
        security_audit_service.log_config_change(
            config_type='system',
            change_description=f"System configuration updated by user {user_id}",
            details={'user_id': user_id}
        )
        
        return jsonify({
            'status': 'success',
            'message': 'Update config - not implemented yet',
            'user_id': user_id
        })