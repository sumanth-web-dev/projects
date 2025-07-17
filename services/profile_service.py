"""
Profile management service for handling user profiles and application materials.

This module provides functionality for managing user profiles, including personal information,
job preferences, resumes, and cover letters. It handles CRUD operations, validation,
and template management.
"""
import os
import uuid
import logging
import datetime
from typing import Dict, List, Optional, Tuple, Any, Union
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.utils import secure_filename
from models.database import db
from models.user import User
from services.encryption_service import encryption_service

# Set up logging
logger = logging.getLogger(__name__)


class ProfileService:
    """Service for managing user profiles and application materials."""
    
    def __init__(self, app=None):
        """Initialize the profile service.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self._upload_folder = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the profile service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self._upload_folder = app.config.get('UPLOAD_FOLDER', 'uploads')
        
        # Ensure upload directory exists
        os.makedirs(os.path.join(self._upload_folder, 'resumes'), exist_ok=True)
        os.makedirs(os.path.join(self._upload_folder, 'cover_letters'), exist_ok=True)
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID.
        
        Args:
            user_id: The user ID to look up
            
        Returns:
            Optional[User]: The user if found, None otherwise
        """
        try:
            return User.query.get(user_id)
        except Exception as e:
            logger.error(f"Error retrieving user: {str(e)}")
            return None
    
    def get_user_by_email(self, email: str) -> Optional[User]:
        """Get a user by email.
        
        Args:
            email: The email to look up
            
        Returns:
            Optional[User]: The user if found, None otherwise
        """
        try:
            return User.query.filter_by(email=email.lower()).first()
        except Exception as e:
            logger.error(f"Error retrieving user by email: {str(e)}")
            return None
    
    def get_profile(self, user_id: str) -> Tuple[bool, Dict, str]:
        """Get a user's profile data.
        
        Args:
            user_id: The user ID
            
        Returns:
            Tuple[bool, Dict, str]: (success, profile_data, message)
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False, {}, "User not found"
            
            # Get user data including sensitive information
            profile_data = user.to_dict(include_sensitive=True)
            
            # Add additional profile information
            profile_data['resumes'] = self.get_resume_list(user_id)
            profile_data['cover_letters'] = self.get_cover_letter_list(user_id)
            
            return True, profile_data, "Profile retrieved successfully"
        except Exception as e:
            logger.error(f"Error retrieving profile: {str(e)}")
            return False, {}, f"Error retrieving profile: {str(e)}"
    
    def update_personal_info(self, user_id: str, personal_info: Dict) -> Tuple[bool, str]:
        """Update a user's personal information.
        
        Args:
            user_id: The user ID
            personal_info: Dictionary of personal information
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False, "User not found"
            
            # Get current personal data
            current_data = user.personal_data
            
            # Sanitize input data
            sanitized_data = self._sanitize_personal_info(personal_info)
            
            # Merge with existing data, preserving password and other sensitive fields
            for key, value in sanitized_data.items():
                if key != 'password' and key != 'api_keys':  # Don't overwrite these fields
                    current_data[key] = value
            
            # Validate and update
            try:
                user.validate_personal_data(current_data)
                user.personal_data = current_data
                db.session.commit()
                return True, "Personal information updated successfully"
            except ValueError as e:
                db.session.rollback()
                return False, str(e)
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating personal info: {str(e)}")
            return False, f"Error updating personal info: {str(e)}"
    
    def update_preferences(self, user_id: str, preferences: Dict) -> Tuple[bool, str]:
        """Update a user's job preferences.
        
        Args:
            user_id: The user ID
            preferences: Dictionary of job preferences
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False, "User not found"
            
            # Sanitize input data
            sanitized_prefs = self._sanitize_preferences(preferences)
            
            # Validate and update
            try:
                user.validate_preferences(sanitized_prefs)
                user.preferences = sanitized_prefs
                db.session.commit()
                return True, "Job preferences updated successfully"
            except ValueError as e:
                db.session.rollback()
                return False, str(e)
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating preferences: {str(e)}")
            return False, f"Error updating preferences: {str(e)}"
    
    def get_resume_list(self, user_id: str) -> List[Dict]:
        """Get a list of user's resumes.
        
        Args:
            user_id: The user ID
            
        Returns:
            List[Dict]: List of resume metadata
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return []
            
            personal_data = user.personal_data
            resumes = personal_data.get('resumes', [])
            
            # Ensure it's a list
            if not isinstance(resumes, list):
                return []
            
            return resumes
        except Exception as e:
            logger.error(f"Error retrieving resume list: {str(e)}")
            return []
    
    def get_cover_letter_list(self, user_id: str) -> List[Dict]:
        """Get a list of user's cover letters.
        
        Args:
            user_id: The user ID
            
        Returns:
            List[Dict]: List of cover letter metadata
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return []
            
            personal_data = user.personal_data
            cover_letters = personal_data.get('cover_letters', [])
            
            # Ensure it's a list
            if not isinstance(cover_letters, list):
                return []
            
            return cover_letters
        except Exception as e:
            logger.error(f"Error retrieving cover letter list: {str(e)}")
            return []
    
    def add_resume(self, user_id: str, file_path: str, name: str, description: str = None) -> Tuple[bool, Optional[str], str]:
        """Add a resume to the user's profile.
        
        Args:
            user_id: The user ID
            file_path: Path to the resume file
            name: Name for the resume
            description: Optional description
            
        Returns:
            Tuple[bool, Optional[str], str]: (success, resume_id, message)
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False, None, "User not found"
            
            # Generate a unique ID for this resume
            resume_id = str(uuid.uuid4())
            
            # Get file extension
            _, ext = os.path.splitext(file_path)
            
            # Create a secure filename
            filename = f"{user_id}_{resume_id}{ext}"
            
            # Destination path
            dest_path = os.path.join(self._upload_folder, 'resumes', filename)
            
            # Copy file to destination
            try:
                with open(file_path, 'rb') as src_file:
                    with open(dest_path, 'wb') as dest_file:
                        dest_file.write(src_file.read())
            except Exception as e:
                return False, None, f"Error saving resume file: {str(e)}"
            
            # Create resume metadata
            resume_data = {
                'id': resume_id,
                'name': name,
                'description': description or '',
                'filename': filename,
                'created_at': datetime.datetime.utcnow().isoformat(),
                'updated_at': datetime.datetime.utcnow().isoformat()
            }
            
            # Add to user's personal data
            personal_data = user.personal_data
            if 'resumes' not in personal_data:
                personal_data['resumes'] = []
            
            personal_data['resumes'].append(resume_data)
            user.personal_data = personal_data
            
            db.session.commit()
            return True, resume_id, "Resume added successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding resume: {str(e)}")
            return False, None, f"Error adding resume: {str(e)}"
    
    def update_resume(self, user_id: str, resume_id: str, name: str = None, description: str = None) -> Tuple[bool, str]:
        """Update resume metadata.
        
        Args:
            user_id: The user ID
            resume_id: The resume ID
            name: New name (optional)
            description: New description (optional)
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False, "User not found"
            
            # Get personal data
            personal_data = user.personal_data
            
            # Find the resume
            resumes = personal_data.get('resumes', [])
            resume_index = None
            
            for i, resume in enumerate(resumes):
                if resume.get('id') == resume_id:
                    resume_index = i
                    break
            
            if resume_index is None:
                return False, "Resume not found"
            
            # Update fields
            if name:
                resumes[resume_index]['name'] = name
            
            if description is not None:
                resumes[resume_index]['description'] = description
            
            resumes[resume_index]['updated_at'] = datetime.datetime.utcnow().isoformat()
            
            # Save changes
            personal_data['resumes'] = resumes
            user.personal_data = personal_data
            
            db.session.commit()
            return True, "Resume updated successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating resume: {str(e)}")
            return False, f"Error updating resume: {str(e)}"
    
    def delete_resume(self, user_id: str, resume_id: str) -> Tuple[bool, str]:
        """Delete a resume.
        
        Args:
            user_id: The user ID
            resume_id: The resume ID
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False, "User not found"
            
            # Get personal data
            personal_data = user.personal_data
            
            # Find the resume
            resumes = personal_data.get('resumes', [])
            resume_to_delete = None
            
            for i, resume in enumerate(resumes):
                if resume.get('id') == resume_id:
                    resume_to_delete = resume
                    resumes.pop(i)
                    break
            
            if not resume_to_delete:
                return False, "Resume not found"
            
            # Delete the file
            try:
                filename = resume_to_delete.get('filename')
                if filename:
                    file_path = os.path.join(self._upload_folder, 'resumes', filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
            except Exception as e:
                logger.warning(f"Error deleting resume file: {str(e)}")
                # Continue even if file deletion fails
            
            # Save changes
            personal_data['resumes'] = resumes
            user.personal_data = personal_data
            
            db.session.commit()
            return True, "Resume deleted successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting resume: {str(e)}")
            return False, f"Error deleting resume: {str(e)}"
    
    def add_cover_letter(self, user_id: str, file_path: str, name: str, description: str = None) -> Tuple[bool, Optional[str], str]:
        """Add a cover letter to the user's profile.
        
        Args:
            user_id: The user ID
            file_path: Path to the cover letter file
            name: Name for the cover letter
            description: Optional description
            
        Returns:
            Tuple[bool, Optional[str], str]: (success, cover_letter_id, message)
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False, None, "User not found"
            
            # Generate a unique ID for this cover letter
            cover_letter_id = str(uuid.uuid4())
            
            # Get file extension
            _, ext = os.path.splitext(file_path)
            
            # Create a secure filename
            filename = f"{user_id}_{cover_letter_id}{ext}"
            
            # Destination path
            dest_path = os.path.join(self._upload_folder, 'cover_letters', filename)
            
            # Copy file to destination
            try:
                with open(file_path, 'rb') as src_file:
                    with open(dest_path, 'wb') as dest_file:
                        dest_file.write(src_file.read())
            except Exception as e:
                return False, None, f"Error saving cover letter file: {str(e)}"
            
            # Create cover letter metadata
            cover_letter_data = {
                'id': cover_letter_id,
                'name': name,
                'description': description or '',
                'filename': filename,
                'created_at': datetime.datetime.utcnow().isoformat(),
                'updated_at': datetime.datetime.utcnow().isoformat()
            }
            
            # Add to user's personal data
            personal_data = user.personal_data
            if 'cover_letters' not in personal_data:
                personal_data['cover_letters'] = []
            
            personal_data['cover_letters'].append(cover_letter_data)
            user.personal_data = personal_data
            
            db.session.commit()
            return True, cover_letter_id, "Cover letter added successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding cover letter: {str(e)}")
            return False, None, f"Error adding cover letter: {str(e)}"
    
    def update_cover_letter(self, user_id: str, cover_letter_id: str, name: str = None, description: str = None) -> Tuple[bool, str]:
        """Update cover letter metadata.
        
        Args:
            user_id: The user ID
            cover_letter_id: The cover letter ID
            name: New name (optional)
            description: New description (optional)
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False, "User not found"
            
            # Get personal data
            personal_data = user.personal_data
            
            # Find the cover letter
            cover_letters = personal_data.get('cover_letters', [])
            cover_letter_index = None
            
            for i, cover_letter in enumerate(cover_letters):
                if cover_letter.get('id') == cover_letter_id:
                    cover_letter_index = i
                    break
            
            if cover_letter_index is None:
                return False, "Cover letter not found"
            
            # Update fields
            if name:
                cover_letters[cover_letter_index]['name'] = name
            
            if description is not None:
                cover_letters[cover_letter_index]['description'] = description
            
            cover_letters[cover_letter_index]['updated_at'] = datetime.datetime.utcnow().isoformat()
            
            # Save changes
            personal_data['cover_letters'] = cover_letters
            user.personal_data = personal_data
            
            db.session.commit()
            return True, "Cover letter updated successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating cover letter: {str(e)}")
            return False, f"Error updating cover letter: {str(e)}"
    
    def delete_cover_letter(self, user_id: str, cover_letter_id: str) -> Tuple[bool, str]:
        """Delete a cover letter.
        
        Args:
            user_id: The user ID
            cover_letter_id: The cover letter ID
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False, "User not found"
            
            # Get personal data
            personal_data = user.personal_data
            
            # Find the cover letter
            cover_letters = personal_data.get('cover_letters', [])
            cover_letter_to_delete = None
            
            for i, cover_letter in enumerate(cover_letters):
                if cover_letter.get('id') == cover_letter_id:
                    cover_letter_to_delete = cover_letter
                    cover_letters.pop(i)
                    break
            
            if not cover_letter_to_delete:
                return False, "Cover letter not found"
            
            # Delete the file
            try:
                filename = cover_letter_to_delete.get('filename')
                if filename:
                    file_path = os.path.join(self._upload_folder, 'cover_letters', filename)
                    if os.path.exists(file_path):
                        os.remove(file_path)
            except Exception as e:
                logger.warning(f"Error deleting cover letter file: {str(e)}")
                # Continue even if file deletion fails
            
            # Save changes
            personal_data['cover_letters'] = cover_letters
            user.personal_data = personal_data
            
            db.session.commit()
            return True, "Cover letter deleted successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting cover letter: {str(e)}")
            return False, f"Error deleting cover letter: {str(e)}"
    
    def get_resume_file_path(self, user_id: str, resume_id: str) -> Tuple[bool, Optional[str], str]:
        """Get the file path for a resume.
        
        Args:
            user_id: The user ID
            resume_id: The resume ID
            
        Returns:
            Tuple[bool, Optional[str], str]: (success, file_path, message)
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False, None, "User not found"
            
            # Find the resume
            resumes = user.personal_data.get('resumes', [])
            resume = None
            
            for r in resumes:
                if r.get('id') == resume_id:
                    resume = r
                    break
            
            if not resume:
                return False, None, "Resume not found"
            
            filename = resume.get('filename')
            if not filename:
                return False, None, "Resume filename not found"
            
            file_path = os.path.join(self._upload_folder, 'resumes', filename)
            
            if not os.path.exists(file_path):
                return False, None, "Resume file not found on disk"
            
            return True, file_path, "Resume file found"
            
        except Exception as e:
            logger.error(f"Error getting resume file path: {str(e)}")
            return False, None, f"Error getting resume file path: {str(e)}"
    
    def get_cover_letter_file_path(self, user_id: str, cover_letter_id: str) -> Tuple[bool, Optional[str], str]:
        """Get the file path for a cover letter.
        
        Args:
            user_id: The user ID
            cover_letter_id: The cover letter ID
            
        Returns:
            Tuple[bool, Optional[str], str]: (success, file_path, message)
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return False, None, "User not found"
            
            # Find the cover letter
            cover_letters = user.personal_data.get('cover_letters', [])
            cover_letter = None
            
            for cl in cover_letters:
                if cl.get('id') == cover_letter_id:
                    cover_letter = cl
                    break
            
            if not cover_letter:
                return False, None, "Cover letter not found"
            
            filename = cover_letter.get('filename')
            if not filename:
                return False, None, "Cover letter filename not found"
            
            file_path = os.path.join(self._upload_folder, 'cover_letters', filename)
            
            if not os.path.exists(file_path):
                return False, None, "Cover letter file not found on disk"
            
            return True, file_path, "Cover letter file found"
            
        except Exception as e:
            logger.error(f"Error getting cover letter file path: {str(e)}")
            return False, None, f"Error getting cover letter file path: {str(e)}"
    
    def _sanitize_personal_info(self, personal_info: Dict) -> Dict:
        """Sanitize personal information input.
        
        Args:
            personal_info: Raw personal information dictionary
            
        Returns:
            Dict: Sanitized personal information
        """
        sanitized = {}
        
        # Process only expected fields
        expected_fields = [
            'first_name', 'last_name', 'phone', 'address', 'city', 'state',
            'zip_code', 'country', 'linkedin_url', 'github_url', 'website',
            'summary', 'skills', 'education', 'experience'
        ]
        
        for field in expected_fields:
            if field in personal_info:
                # Basic sanitization - strip whitespace from strings
                if isinstance(personal_info[field], str):
                    sanitized[field] = personal_info[field].strip()
                else:
                    sanitized[field] = personal_info[field]
        
        return sanitized
    
    def _sanitize_preferences(self, preferences: Dict) -> Dict:
        """Sanitize job preferences input.
        
        Args:
            preferences: Raw preferences dictionary
            
        Returns:
            Dict: Sanitized preferences
        """
        sanitized = {}
        
        # Process expected fields
        if 'job_titles' in preferences:
            if isinstance(preferences['job_titles'], list):
                sanitized['job_titles'] = [title.strip() for title in preferences['job_titles'] if isinstance(title, str)]
            else:
                sanitized['job_titles'] = []
        
        if 'locations' in preferences:
            if isinstance(preferences['locations'], list):
                sanitized['locations'] = [loc.strip() for loc in preferences['locations'] if isinstance(loc, str)]
            else:
                sanitized['locations'] = []
        
        if 'remote_only' in preferences:
            sanitized['remote_only'] = bool(preferences['remote_only'])
        
        if 'salary_min' in preferences:
            try:
                sanitized['salary_min'] = float(preferences['salary_min'])
            except (ValueError, TypeError):
                pass
        
        if 'salary_max' in preferences:
            try:
                sanitized['salary_max'] = float(preferences['salary_max'])
            except (ValueError, TypeError):
                pass
        
        if 'experience_level' in preferences:
            sanitized['experience_level'] = preferences['experience_level']
        
        if 'job_types' in preferences:
            if isinstance(preferences['job_types'], list):
                sanitized['job_types'] = [jt.strip() for jt in preferences['job_types'] if isinstance(jt, str)]
            else:
                sanitized['job_types'] = []
        
        if 'industries' in preferences:
            if isinstance(preferences['industries'], list):
                sanitized['industries'] = [ind.strip() for ind in preferences['industries'] if isinstance(ind, str)]
            else:
                sanitized['industries'] = []
        
        if 'keywords' in preferences:
            if isinstance(preferences['keywords'], list):
                sanitized['keywords'] = [kw.strip() for kw in preferences['keywords'] if isinstance(kw, str)]
            else:
                sanitized['keywords'] = []
        
        if 'excluded_keywords' in preferences:
            if isinstance(preferences['excluded_keywords'], list):
                sanitized['excluded_keywords'] = [kw.strip() for kw in preferences['excluded_keywords'] if isinstance(kw, str)]
            else:
                sanitized['excluded_keywords'] = []
        
        return sanitized


# Create a singleton instance
profile_service = ProfileService()