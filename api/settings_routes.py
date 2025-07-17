"""
Settings API routes for the Job Application Agent.
"""
from flask import jsonify, request, g
from api import api_bp
from services.settings_service import settings_service
from api.auth import login_required
from api.csrf import csrf_token_required


@api_bp.route('/settings', methods=['GET'])
@login_required
def get_settings():
    """Get all user settings."""
    user_id = g.user_id
    
    try:
        settings = settings_service.get_user_settings(user_id)
        credentials = settings_service.get_credentials(user_id)
        system_status = settings_service.get_system_status()
        
        return jsonify({
            'success': True,
            'settings': settings,
            'credentials': credentials,
            'system_status': system_status
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to get settings: {str(e)}'
        }), 500


@api_bp.route('/settings/general', methods=['POST'])
@login_required
@csrf_token_required
def update_general_settings():
    """Update general settings."""
    user_id = g.user_id
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'No data provided'
        }), 400
    
    try:
        # Extract and validate general settings
        general_settings = {}
        
        if 'default_search_radius' in data:
            radius = int(data['default_search_radius'])
            if 5 <= radius <= 100:
                general_settings['default_search_radius'] = radius
            else:
                return jsonify({
                    'success': False,
                    'message': 'Search radius must be between 5 and 100 miles'
                }), 400
        
        if 'job_refresh_interval' in data:
            interval = int(data['job_refresh_interval'])
            if 1 <= interval <= 24:
                general_settings['job_refresh_interval'] = interval
            else:
                return jsonify({
                    'success': False,
                    'message': 'Job refresh interval must be between 1 and 24 hours'
                }), 400
        
        if 'job_sources' in data:
            sources = data['job_sources']
            if isinstance(sources, list):
                valid_sources = ['linkedin', 'indeed', 'glassdoor']
                if all(source in valid_sources for source in sources):
                    general_settings['job_sources'] = sources
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Invalid job sources provided'
                    }), 400
        
        if 'theme' in data:
            theme = data['theme']
            if theme in ['light', 'dark', 'system']:
                general_settings['theme'] = theme
            else:
                return jsonify({
                    'success': False,
                    'message': 'Invalid theme selection'
                }), 400
        
        success, message = settings_service.update_user_settings(user_id, 'general', general_settings)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'General settings updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to update general settings: {str(e)}'
        }), 500


@api_bp.route('/settings/automation', methods=['POST'])
@login_required
@csrf_token_required
def update_automation_settings():
    """Update automation settings."""
    user_id = g.user_id
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'No data provided'
        }), 400
    
    try:
        automation_settings = {}
        
        if 'auto_apply_enabled' in data:
            automation_settings['auto_apply_enabled'] = bool(data['auto_apply_enabled'])
        
        if 'daily_application_limit' in data:
            limit = int(data['daily_application_limit'])
            if 1 <= limit <= 50:
                automation_settings['daily_application_limit'] = limit
            else:
                return jsonify({
                    'success': False,
                    'message': 'Daily application limit must be between 1 and 50'
                }), 400
        
        if 'schedule_days' in data:
            days = data['schedule_days']
            if isinstance(days, list):
                valid_days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
                if all(day in valid_days for day in days):
                    automation_settings['schedule_days'] = days
                else:
                    return jsonify({
                        'success': False,
                        'message': 'Invalid schedule days provided'
                    }), 400
        
        # Handle schedule times
        schedule_times = {}
        for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']:
            time_key = f'schedule_time_{day}'
            if time_key in data:
                schedule_times[day] = data[time_key]
        
        if schedule_times:
            automation_settings['schedule_times'] = schedule_times
        
        if 'browser_type' in data:
            browser = data['browser_type']
            if browser in ['chromium', 'firefox', 'webkit']:
                automation_settings['browser_type'] = browser
            else:
                return jsonify({
                    'success': False,
                    'message': 'Invalid browser type'
                }), 400
        
        if 'headless_mode' in data:
            automation_settings['headless_mode'] = bool(data['headless_mode'])
        
        success, message = settings_service.update_user_settings(user_id, 'automation', automation_settings)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Automation settings updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to update automation settings: {str(e)}'
        }), 500


@api_bp.route('/settings/security', methods=['POST'])
@login_required
@csrf_token_required
def update_security_settings():
    """Update security settings."""
    user_id = g.user_id
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'No data provided'
        }), 400
    
    try:
        security_settings = {}
        
        if 'enable_2fa' in data:
            security_settings['enable_2fa'] = bool(data['enable_2fa'])
        
        if 'session_timeout' in data:
            timeout = int(data['session_timeout'])
            if 5 <= timeout <= 120:
                security_settings['session_timeout'] = timeout
            else:
                return jsonify({
                    'success': False,
                    'message': 'Session timeout must be between 5 and 120 minutes'
                }), 400
        
        if 'enable_api_access' in data:
            security_settings['enable_api_access'] = bool(data['enable_api_access'])
        
        success, message = settings_service.update_user_settings(user_id, 'security', security_settings)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Security settings updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to update security settings: {str(e)}'
        }), 500


@api_bp.route('/settings/credentials', methods=['POST'])
@login_required
@csrf_token_required
def update_credentials():
    """Update credentials for a service."""
    user_id = g.user_id
    data = request.get_json()
    
    if not data:
        return jsonify({
            'success': False,
            'message': 'No data provided'
        }), 400
    
    service = data.get('service')
    username = data.get('username')
    password = data.get('password')
    
    if not service or not username or not password:
        return jsonify({
            'success': False,
            'message': 'Service, username, and password are required'
        }), 400
    
    if service not in ['linkedin', 'indeed', 'glassdoor']:
        return jsonify({
            'success': False,
            'message': 'Invalid service'
        }), 400
    
    try:
        success, message = settings_service.update_credentials(user_id, service, username, password)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to update credentials: {str(e)}'
        }), 500


@api_bp.route('/settings/credentials/<service>', methods=['DELETE'])
@login_required
@csrf_token_required
def delete_credentials(service):
    """Delete credentials for a service."""
    user_id = g.user_id
    
    if service not in ['linkedin', 'indeed', 'glassdoor']:
        return jsonify({
            'success': False,
            'message': 'Invalid service'
        }), 400
    
    try:
        success, message = settings_service.delete_credentials(user_id, service)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to delete credentials: {str(e)}'
        }), 500


@api_bp.route('/settings/credential-info/<service>', methods=['GET'])
@login_required
def get_credential_info(service):
    """Get credential info (username only) for a service."""
    user_id = g.user_id
    
    if service not in ['linkedin', 'indeed', 'glassdoor']:
        return jsonify({
            'success': False,
            'message': 'Invalid service'
        }), 400
    
    try:
        success, info = settings_service.get_credential_info(user_id, service)
        
        if success:
            return jsonify({
                'success': True,
                'username': info.get('username', ''),
                'updated_at': info.get('updated_at', '')
            })
        else:
            return jsonify({
                'success': False,
                'message': 'Credentials not found'
            }), 404
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to get credential info: {str(e)}'
        }), 500


@api_bp.route('/settings/regenerate-api-key', methods=['POST'])
@login_required
@csrf_token_required
def regenerate_api_key():
    """Regenerate API key for the user."""
    user_id = g.user_id
    
    try:
        success, api_key, message = settings_service.generate_api_key(user_id)
        
        if success:
            return jsonify({
                'success': True,
                'api_key': api_key,
                'message': message
            })
        else:
            return jsonify({
                'success': False,
                'message': message
            }), 500
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to regenerate API key: {str(e)}'
        }), 500


@api_bp.route('/automation/start', methods=['POST'])
@login_required
@csrf_token_required
def start_automation():
    """Start the automation process."""
    user_id = g.user_id
    
    try:
        # This would integrate with the actual automation service
        # For now, return a placeholder response
        return jsonify({
            'success': True,
            'message': 'Automation started successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to start automation: {str(e)}'
        }), 500


@api_bp.route('/automation/stop', methods=['POST'])
@login_required
@csrf_token_required
def stop_automation():
    """Stop the automation process."""
    user_id = g.user_id
    
    try:
        # This would integrate with the actual automation service
        # For now, return a placeholder response
        return jsonify({
            'success': True,
            'message': 'Automation stopped successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to stop automation: {str(e)}'
        }), 500


@api_bp.route('/system/diagnostics', methods=['POST'])
@login_required
@csrf_token_required
def run_diagnostics():
    """Run system diagnostics."""
    user_id = g.user_id
    
    try:
        results = settings_service.run_diagnostics()
        
        return jsonify({
            'success': True,
            'results': results,
            'message': 'Diagnostics completed successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to run diagnostics: {str(e)}'
        }), 500


@api_bp.route('/settings/setup-2fa', methods=['POST'])
@login_required
@csrf_token_required
def setup_2fa():
    """Set up two-factor authentication."""
    user_id = g.user_id
    
    try:
        # This would integrate with a 2FA library like pyotp
        # For now, return a placeholder response
        return jsonify({
            'success': True,
            'qr_code': 'data:image/png;base64,placeholder_qr_code',
            'secret_key': 'PLACEHOLDER_SECRET_KEY',
            'message': '2FA setup initiated'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to setup 2FA: {str(e)}'
        }), 500


@api_bp.route('/settings/verify-2fa', methods=['POST'])
@login_required
@csrf_token_required
def verify_2fa():
    """Verify 2FA setup with a code."""
    user_id = g.user_id
    data = request.get_json()
    
    if not data or 'code' not in data:
        return jsonify({
            'success': False,
            'message': 'Verification code is required'
        }), 400
    
    code = data['code']
    
    try:
        # This would verify the 2FA code
        # For now, return a placeholder response
        if len(code) == 6 and code.isdigit():
            # Enable 2FA in user settings
            success, message = settings_service.update_user_settings(user_id, 'security', {
                'enable_2fa': True
            })
            
            if success:
                return jsonify({
                    'success': True,
                    'message': '2FA enabled successfully'
                })
            else:
                return jsonify({
                    'success': False,
                    'message': message
                }), 500
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid verification code'
            }), 400
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Failed to verify 2FA: {str(e)}'
        }), 500