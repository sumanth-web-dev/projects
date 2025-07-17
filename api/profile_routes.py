"""
Profile management API routes for the Job Application Agent.
"""
import os
from flask import jsonify, request, current_app, session, g, send_file
from werkzeug.utils import secure_filename
from api import api_bp
from api.auth import auth_required
from api.csrf import csrf_token_required
from services.profile_service import profile_service


@api_bp.route('/profile', methods=['GET', 'POST', 'PUT', 'DELETE'])
@auth_required
@csrf_token_required
def profile():
    """Profile management endpoints.
    
    GET: Retrieve user profile information
    POST: Create or replace profile information
    PUT: Update profile information
    DELETE: Delete profile information
    """
    user_id = g.user_id
    
    if request.method == 'GET':
        success, profile_data, message = profile_service.get_profile(user_id)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message,
                'profile': profile_data
            })
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 404
    
    elif request.method == 'POST':
        # Create or replace profile
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        # Handle personal information
        personal_info = data.get('personal_info')
        if personal_info:
            success, message = profile_service.update_personal_info(user_id, personal_info)
            if not success:
                return jsonify({
                    'status': 'error',
                    'message': f'Error updating personal information: {message}'
                }), 400
        
        # Handle preferences
        preferences = data.get('preferences')
        if preferences:
            success, message = profile_service.update_preferences(user_id, preferences)
            if not success:
                return jsonify({
                    'status': 'error',
                    'message': f'Error updating preferences: {message}'
                }), 400
        
        # Return updated profile
        success, profile_data, message = profile_service.get_profile(user_id)
        
        return jsonify({
            'status': 'success',
            'message': 'Profile updated successfully',
            'profile': profile_data
        }), 200
    
    elif request.method == 'PUT':
        # Update specific profile fields
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        # Handle personal information
        personal_info = data.get('personal_info')
        if personal_info:
            success, message = profile_service.update_personal_info(user_id, personal_info)
            if not success:
                return jsonify({
                    'status': 'error',
                    'message': f'Error updating personal information: {message}'
                }), 400
        
        # Handle preferences
        preferences = data.get('preferences')
        if preferences:
            success, message = profile_service.update_preferences(user_id, preferences)
            if not success:
                return jsonify({
                    'status': 'error',
                    'message': f'Error updating preferences: {message}'
                }), 400
        
        # Return updated profile
        success, profile_data, message = profile_service.get_profile(user_id)
        
        return jsonify({
            'status': 'success',
            'message': 'Profile updated successfully',
            'profile': profile_data
        })
    
    elif request.method == 'DELETE':
        # This endpoint doesn't fully delete the user account,
        # but rather clears profile information
        
        # Clear personal info (keep minimal data)
        success, message = profile_service.update_personal_info(user_id, {})
        if not success:
            return jsonify({
                'status': 'error',
                'message': f'Error clearing personal information: {message}'
            }), 400
        
        # Clear preferences
        success, message = profile_service.update_preferences(user_id, {})
        if not success:
            return jsonify({
                'status': 'error',
                'message': f'Error clearing preferences: {message}'
            }), 400
        
        return jsonify({
            'status': 'success',
            'message': 'Profile information cleared successfully'
        })


@api_bp.route('/profile/resumes', methods=['GET', 'POST'])
@auth_required
@csrf_token_required
def resumes():
    """Resume management endpoints.
    
    GET: List all resumes
    POST: Upload a new resume
    """
    user_id = g.user_id
    
    if request.method == 'GET':
        # Get list of resumes
        resumes = profile_service.get_resume_list(user_id)
        
        return jsonify({
            'status': 'success',
            'message': 'Resumes retrieved successfully',
            'resumes': resumes
        })
    
    elif request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file part in the request'
            }), 400
        
        file = request.files['file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No selected file'
            }), 400
        
        # Get metadata
        name = request.form.get('name', 'Resume')
        description = request.form.get('description', '')
        
        # Check allowed file types
        allowed_extensions = {'pdf', 'doc', 'docx', 'txt', 'rtf'}
        if not '.' in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({
                'status': 'error',
                'message': 'File type not allowed. Allowed types: pdf, doc, docx, txt, rtf'
            }), 400
        
        # Save file to temporary location
        filename = secure_filename(file.filename)
        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp', filename)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        file.save(temp_path)
        
        # Add resume to profile
        success, resume_id, message = profile_service.add_resume(user_id, temp_path, name, description)
        
        # Clean up temporary file
        try:
            os.remove(temp_path)
        except:
            pass  # Ignore cleanup errors
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message,
                'resume_id': resume_id
            }), 201
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 400


@api_bp.route('/profile/resumes/<resume_id>', methods=['GET', 'PUT', 'DELETE'])
@auth_required
@csrf_token_required
def resume_detail(resume_id):
    """Resume detail endpoints.
    
    GET: Download a specific resume
    PUT: Update resume metadata
    DELETE: Delete a resume
    """
    user_id = g.user_id
    
    if request.method == 'GET':
        # Get resume file
        success, file_path, message = profile_service.get_resume_file_path(user_id, resume_id)
        
        if success and file_path:
            # Get resume metadata to determine filename
            resumes = profile_service.get_resume_list(user_id)
            resume_data = next((r for r in resumes if r.get('id') == resume_id), None)
            
            if resume_data:
                # Get original filename or use a default
                filename = resume_data.get('name', 'resume')
                # Add file extension from the stored file
                ext = os.path.splitext(file_path)[1]
                download_name = f"{filename}{ext}"
                
                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=download_name
                )
            else:
                return send_file(file_path, as_attachment=True)
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 404
    
    elif request.method == 'PUT':
        # Update resume metadata
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        name = data.get('name')
        description = data.get('description')
        
        if not name and description is None:
            return jsonify({
                'status': 'error',
                'message': 'No update data provided'
            }), 400
        
        success, message = profile_service.update_resume(user_id, resume_id, name, description)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message
            })
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 404
    
    elif request.method == 'DELETE':
        # Delete resume
        success, message = profile_service.delete_resume(user_id, resume_id)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message
            })
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 404


@api_bp.route('/profile/cover-letters', methods=['GET', 'POST'])
@auth_required
@csrf_token_required
def cover_letters():
    """Cover letter management endpoints.
    
    GET: List all cover letters
    POST: Upload a new cover letter
    """
    user_id = g.user_id
    
    if request.method == 'GET':
        # Get list of cover letters
        cover_letters = profile_service.get_cover_letter_list(user_id)
        
        return jsonify({
            'status': 'success',
            'message': 'Cover letters retrieved successfully',
            'cover_letters': cover_letters
        })
    
    elif request.method == 'POST':
        # Check if the post request has the file part
        if 'file' not in request.files:
            return jsonify({
                'status': 'error',
                'message': 'No file part in the request'
            }), 400
        
        file = request.files['file']
        
        # If user does not select file, browser also
        # submit an empty part without filename
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': 'No selected file'
            }), 400
        
        # Get metadata
        name = request.form.get('name', 'Cover Letter')
        description = request.form.get('description', '')
        
        # Check allowed file types
        allowed_extensions = {'pdf', 'doc', 'docx', 'txt', 'rtf'}
        if not '.' in file.filename or file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({
                'status': 'error',
                'message': 'File type not allowed. Allowed types: pdf, doc, docx, txt, rtf'
            }), 400
        
        # Save file to temporary location
        filename = secure_filename(file.filename)
        temp_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'temp', filename)
        os.makedirs(os.path.dirname(temp_path), exist_ok=True)
        file.save(temp_path)
        
        # Add cover letter to profile
        success, cover_letter_id, message = profile_service.add_cover_letter(user_id, temp_path, name, description)
        
        # Clean up temporary file
        try:
            os.remove(temp_path)
        except:
            pass  # Ignore cleanup errors
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message,
                'cover_letter_id': cover_letter_id
            }), 201
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 400


@api_bp.route('/profile/cover-letters/<cover_letter_id>', methods=['GET', 'PUT', 'DELETE'])
@auth_required
@csrf_token_required
def cover_letter_detail(cover_letter_id):
    """Cover letter detail endpoints.
    
    GET: Download a specific cover letter
    PUT: Update cover letter metadata
    DELETE: Delete a cover letter
    """
    user_id = g.user_id
    
    if request.method == 'GET':
        # Get cover letter file
        success, file_path, message = profile_service.get_cover_letter_file_path(user_id, cover_letter_id)
        
        if success and file_path:
            # Get cover letter metadata to determine filename
            cover_letters = profile_service.get_cover_letter_list(user_id)
            cover_letter_data = next((cl for cl in cover_letters if cl.get('id') == cover_letter_id), None)
            
            if cover_letter_data:
                # Get original filename or use a default
                filename = cover_letter_data.get('name', 'cover_letter')
                # Add file extension from the stored file
                ext = os.path.splitext(file_path)[1]
                download_name = f"{filename}{ext}"
                
                return send_file(
                    file_path,
                    as_attachment=True,
                    download_name=download_name
                )
            else:
                return send_file(file_path, as_attachment=True)
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 404
    
    elif request.method == 'PUT':
        # Update cover letter metadata
        data = request.get_json()
        if not data:
            return jsonify({
                'status': 'error',
                'message': 'No data provided'
            }), 400
        
        name = data.get('name')
        description = data.get('description')
        
        if not name and description is None:
            return jsonify({
                'status': 'error',
                'message': 'No update data provided'
            }), 400
        
        success, message = profile_service.update_cover_letter(user_id, cover_letter_id, name, description)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message
            })
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 404
    
    elif request.method == 'DELETE':
        # Delete cover letter
        success, message = profile_service.delete_cover_letter(user_id, cover_letter_id)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message
            })
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 404