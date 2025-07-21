"""
API endpoint to get the current user's role.
"""
from flask import jsonify, session, g
from api import api_bp
from services.auth_service import auth_service
from models.user import User

@api_bp.route('/get_user_role', methods=['GET'])
def get_current_user_role():
    """Get the current user's role."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'message': 'Not logged in'
        })
    
    try:
        user = User.query.get(user_id)
        if not user:
            return jsonify({
                'success': False,
                'message': 'User not found'
            })
        
        personal_data = user.personal_data or {}
        roles = personal_data.get('roles', [])
        
        return jsonify({
            'success': True,
            'user_id': user_id,
            'roles': roles
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })