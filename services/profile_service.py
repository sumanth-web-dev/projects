"""
Profile service for managing user profiles and profile completion.
"""
import datetime
from typing import Dict, List, Optional


class ProfileService:
    """Service for managing user profiles."""
    
    def init_app(self, app):
        """Initialize the profile service with the Flask app."""
        # No initialization needed for now
        pass
    
    def update_profile(self, user_id: str, profile_data: Dict) -> bool:
        """Update user profile with new data."""
        try:
            from models.user import User
            from models.database import db
            
            user = User.query.get(user_id)
            if not user:
                return False
            
            # Get existing personal data
            personal_data = user.personal_data or {}
            
            # Update with new data
            personal_data.update(profile_data)
            
            # Save updated data
            user.personal_data = personal_data
            user.updated_at = datetime.datetime.utcnow()
            db.session.commit()
            
            return True
        
        except Exception as e:
            db.session.rollback()
            return False
    
    def autosave_profile(self, user_id: str, profile_data: Dict) -> bool:
        """Auto-save profile data (lightweight update)."""
        try:
            from models.user import User
            from models.database import db
            
            user = User.query.get(user_id)
            if not user:
                return False
            
            # Get existing personal data
            personal_data = user.personal_data or {}
            
            # Update only provided fields
            for key, value in profile_data.items():
                if value is not None:
                    personal_data[key] = value
            
            # Save updated data
            user.personal_data = personal_data
            db.session.commit()
            
            return True
        
        except Exception as e:
            db.session.rollback()
            return False
    
    def calculate_profile_completion(self, user_id: str) -> int:
        """Calculate profile completion percentage."""
        try:
            from models.user import User
            
            user = User.query.get(user_id)
            if not user:
                return 0
            
            personal_data = user.personal_data or {}
            
            # Define required fields and their weights
            completion_criteria = {
                'basic_info': {
                    'weight': 25,
                    'fields': ['first_name', 'last_name', 'phone']
                },
                'education': {
                    'weight': 25,
                    'fields': ['education']
                },
                'skills': {
                    'weight': 20,
                    'fields': ['skills']
                },
                'experience': {
                    'weight': 15,
                    'fields': ['experience']
                },
                'bio': {
                    'weight': 10,
                    'fields': ['bio']
                },
                'social_links': {
                    'weight': 5,
                    'fields': ['social_links']
                }
            }
            
            total_score = 0
            
            for category, criteria in completion_criteria.items():
                category_complete = True
                
                for field in criteria['fields']:
                    if field not in personal_data or not personal_data[field]:
                        category_complete = False
                        break
                    
                    # Special handling for complex fields
                    if field == 'education' and isinstance(personal_data[field], list):
                        if len(personal_data[field]) == 0:
                            category_complete = False
                    elif field == 'skills' and isinstance(personal_data[field], list):
                        if len(personal_data[field]) == 0:
                            category_complete = False
                    elif field == 'social_links' and isinstance(personal_data[field], dict):
                        if not any(personal_data[field].values()):
                            category_complete = False
                
                if category_complete:
                    total_score += criteria['weight']
            
            return min(total_score, 100)
        
        except Exception as e:
            return 0
    
    def get_profile_completion_status(self, user_id: str) -> Dict:
        """Get detailed profile completion status."""
        try:
            from models.user import User
            
            user = User.query.get(user_id)
            if not user:
                return {}
            
            personal_data = user.personal_data or {}
            
            return {
                'basic_info': bool(personal_data.get('first_name') and personal_data.get('last_name')),
                'education': bool(personal_data.get('education') and len(personal_data.get('education', [])) > 0),
                'skills': bool(personal_data.get('skills') and len(personal_data.get('skills', [])) > 0),
                'resume': bool(personal_data.get('resume_path')),
                'projects': bool(personal_data.get('projects') and len(personal_data.get('projects', [])) > 0),
                'experience': bool(personal_data.get('experience') and len(personal_data.get('experience', [])) > 0)
            }
        
        except Exception as e:
            return {}
    
    def get_profile_suggestions(self, user_id: str) -> List[str]:
        """Get suggestions for improving profile."""
        try:
            from models.user import User
            
            user = User.query.get(user_id)
            if not user:
                return []
            
            personal_data = user.personal_data or {}
            suggestions = []
            
            if not personal_data.get('bio'):
                suggestions.append("Add a professional summary to showcase your strengths")
            
            if not personal_data.get('skills') or len(personal_data.get('skills', [])) < 5:
                suggestions.append("Add more skills to improve job matching")
            
            if not personal_data.get('projects') or len(personal_data.get('projects', [])) == 0:
                suggestions.append("Add projects to demonstrate your experience")
            
            if not personal_data.get('social_links', {}).get('linkedin'):
                suggestions.append("Add your LinkedIn profile to increase visibility")
            
            if not personal_data.get('experience') or len(personal_data.get('experience', [])) == 0:
                suggestions.append("Add work experience to strengthen your profile")
            
            return suggestions
        
        except Exception as e:
            return []
    
    def export_profile(self, user_id: str, format_type: str = 'json') -> Optional[str]:
        """Export user profile data."""
        try:
            from models.user import User
            
            user = User.query.get(user_id)
            if not user:
                return None
            
            profile_data = {
                'basic_info': {
                    'email': user.email,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'updated_at': user.updated_at.isoformat() if user.updated_at else None
                },
                'personal_data': user.personal_data or {},
                'preferences': user.preferences or {}
            }
            
            if format_type == 'json':
                import json
                return json.dumps(profile_data, indent=2)
            elif format_type == 'csv':
                # Implement CSV export if needed
                pass
            
            return None
        
        except Exception as e:
            return None
    
    def get_profile(self, user_id: str) -> tuple[bool, Dict, str]:
        """Get complete user profile."""
        try:
            from models.user import User
            
            user = User.query.get(user_id)
            if not user:
                return False, {}, "User not found"
            
            profile_data = {
                'basic_info': {
                    'email': user.email,
                    'created_at': user.created_at.isoformat() if user.created_at else None,
                    'updated_at': user.updated_at.isoformat() if user.updated_at else None,
                    'is_active': user.is_active
                },
                'personal_data': user.personal_data or {},
                'preferences': user.preferences or {},
                'profile_completion': self.calculate_profile_completion(user_id)
            }
            
            return True, profile_data, "Profile retrieved successfully"
        
        except Exception as e:
            return False, {}, f"Error retrieving profile: {str(e)}"
    
    def update_personal_info(self, user_id: str, personal_info: Dict) -> tuple[bool, str]:
        """Update personal information."""
        try:
            from models.user import User
            from models.database import db
            
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            # Get existing personal data
            personal_data = user.personal_data or {}
            
            # Update with new personal info
            personal_data.update(personal_info)
            
            # Save updated data
            user.personal_data = personal_data
            user.updated_at = datetime.datetime.utcnow()
            db.session.commit()
            
            return True, "Personal information updated successfully"
        
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating personal information: {str(e)}"
    
    def update_preferences(self, user_id: str, preferences: Dict) -> tuple[bool, str]:
        """Update user preferences."""
        try:
            from models.user import User
            from models.database import db
            
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            # Get existing preferences
            current_preferences = user.preferences or {}
            
            # Update with new preferences
            current_preferences.update(preferences)
            
            # Save updated preferences
            user.preferences = current_preferences
            user.updated_at = datetime.datetime.utcnow()
            db.session.commit()
            
            return True, "Preferences updated successfully"
        
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating preferences: {str(e)}"
    
    def get_resume_list(self, user_id: str) -> List[Dict]:
        """Get list of user's resumes."""
        try:
            from models.user import User
            
            user = User.query.get(user_id)
            if not user:
                return []
            
            personal_data = user.personal_data or {}
            resumes = personal_data.get('resumes', [])
            
            return resumes
        
        except Exception as e:
            return []
    
    def add_resume(self, user_id: str, file_path: str, name: str, description: str) -> tuple[bool, str, str]:
        """Add a resume to user profile."""
        try:
            import uuid
            import os
            import shutil
            from models.user import User
            from models.database import db
            
            user = User.query.get(user_id)
            if not user:
                return False, "", "User not found"
            
            # Generate unique ID for resume
            resume_id = str(uuid.uuid4())
            
            # Create user's resume directory
            resume_dir = os.path.join('uploads', 'resumes', user_id)
            os.makedirs(resume_dir, exist_ok=True)
            
            # Get file extension
            file_ext = os.path.splitext(file_path)[1]
            
            # Create permanent file path
            permanent_path = os.path.join(resume_dir, f"{resume_id}{file_ext}")
            
            # Move file to permanent location
            shutil.move(file_path, permanent_path)
            
            # Get existing personal data
            personal_data = user.personal_data or {}
            resumes = personal_data.get('resumes', [])
            
            # Add new resume
            resume_data = {
                'id': resume_id,
                'name': name,
                'description': description,
                'file_path': permanent_path,
                'uploaded_at': datetime.datetime.utcnow().isoformat(),
                'file_size': os.path.getsize(permanent_path)
            }
            
            resumes.append(resume_data)
            personal_data['resumes'] = resumes
            
            # Save updated data
            user.personal_data = personal_data
            user.updated_at = datetime.datetime.utcnow()
            db.session.commit()
            
            return True, resume_id, "Resume uploaded successfully"
        
        except Exception as e:
            return False, "", f"Error uploading resume: {str(e)}"
    
    def get_resume_file_path(self, user_id: str, resume_id: str) -> tuple[bool, str, str]:
        """Get resume file path."""
        try:
            from models.user import User
            
            user = User.query.get(user_id)
            if not user:
                return False, "", "User not found"
            
            personal_data = user.personal_data or {}
            resumes = personal_data.get('resumes', [])
            
            # Find resume by ID
            resume = next((r for r in resumes if r.get('id') == resume_id), None)
            
            if not resume:
                return False, "", "Resume not found"
            
            file_path = resume.get('file_path', '')
            
            if not file_path or not os.path.exists(file_path):
                return False, "", "Resume file not found"
            
            return True, file_path, "Resume file found"
        
        except Exception as e:
            return False, "", f"Error retrieving resume: {str(e)}"
    
    def update_resume(self, user_id: str, resume_id: str, name: str = None, description: str = None) -> tuple[bool, str]:
        """Update resume metadata."""
        try:
            from models.user import User
            from models.database import db
            
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            personal_data = user.personal_data or {}
            resumes = personal_data.get('resumes', [])
            
            # Find and update resume
            for resume in resumes:
                if resume.get('id') == resume_id:
                    if name is not None:
                        resume['name'] = name
                    if description is not None:
                        resume['description'] = description
                    resume['updated_at'] = datetime.datetime.utcnow().isoformat()
                    break
            else:
                return False, "Resume not found"
            
            # Save updated data
            personal_data['resumes'] = resumes
            user.personal_data = personal_data
            user.updated_at = datetime.datetime.utcnow()
            db.session.commit()
            
            return True, "Resume updated successfully"
        
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating resume: {str(e)}"
    
    def delete_resume(self, user_id: str, resume_id: str) -> tuple[bool, str]:
        """Delete a resume."""
        try:
            import os
            from models.user import User
            from models.database import db
            
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            personal_data = user.personal_data or {}
            resumes = personal_data.get('resumes', [])
            
            # Find and remove resume
            resume_to_delete = None
            for i, resume in enumerate(resumes):
                if resume.get('id') == resume_id:
                    resume_to_delete = resumes.pop(i)
                    break
            
            if not resume_to_delete:
                return False, "Resume not found"
            
            # Delete file
            file_path = resume_to_delete.get('file_path', '')
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass  # Ignore file deletion errors
            
            # Save updated data
            personal_data['resumes'] = resumes
            user.personal_data = personal_data
            user.updated_at = datetime.datetime.utcnow()
            db.session.commit()
            
            return True, "Resume deleted successfully"
        
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting resume: {str(e)}"
    
    def get_cover_letter_list(self, user_id: str) -> List[Dict]:
        """Get list of user's cover letters."""
        try:
            from models.user import User
            
            user = User.query.get(user_id)
            if not user:
                return []
            
            personal_data = user.personal_data or {}
            cover_letters = personal_data.get('cover_letters', [])
            
            return cover_letters
        
        except Exception as e:
            return []
    
    def add_cover_letter(self, user_id: str, file_path: str, name: str, description: str) -> tuple[bool, str, str]:
        """Add a cover letter to user profile."""
        try:
            import uuid
            import os
            import shutil
            from models.user import User
            from models.database import db
            
            user = User.query.get(user_id)
            if not user:
                return False, "", "User not found"
            
            # Generate unique ID for cover letter
            cover_letter_id = str(uuid.uuid4())
            
            # Create user's cover letter directory
            cover_letter_dir = os.path.join('uploads', 'cover_letters', user_id)
            os.makedirs(cover_letter_dir, exist_ok=True)
            
            # Get file extension
            file_ext = os.path.splitext(file_path)[1]
            
            # Create permanent file path
            permanent_path = os.path.join(cover_letter_dir, f"{cover_letter_id}{file_ext}")
            
            # Move file to permanent location
            shutil.move(file_path, permanent_path)
            
            # Get existing personal data
            personal_data = user.personal_data or {}
            cover_letters = personal_data.get('cover_letters', [])
            
            # Add new cover letter
            cover_letter_data = {
                'id': cover_letter_id,
                'name': name,
                'description': description,
                'file_path': permanent_path,
                'uploaded_at': datetime.datetime.utcnow().isoformat(),
                'file_size': os.path.getsize(permanent_path)
            }
            
            cover_letters.append(cover_letter_data)
            personal_data['cover_letters'] = cover_letters
            
            # Save updated data
            user.personal_data = personal_data
            user.updated_at = datetime.datetime.utcnow()
            db.session.commit()
            
            return True, cover_letter_id, "Cover letter uploaded successfully"
        
        except Exception as e:
            return False, "", f"Error uploading cover letter: {str(e)}"
    
    def get_cover_letter_file_path(self, user_id: str, cover_letter_id: str) -> tuple[bool, str, str]:
        """Get cover letter file path."""
        try:
            import os
            from models.user import User
            
            user = User.query.get(user_id)
            if not user:
                return False, "", "User not found"
            
            personal_data = user.personal_data or {}
            cover_letters = personal_data.get('cover_letters', [])
            
            # Find cover letter by ID
            cover_letter = next((cl for cl in cover_letters if cl.get('id') == cover_letter_id), None)
            
            if not cover_letter:
                return False, "", "Cover letter not found"
            
            file_path = cover_letter.get('file_path', '')
            
            if not file_path or not os.path.exists(file_path):
                return False, "", "Cover letter file not found"
            
            return True, file_path, "Cover letter file found"
        
        except Exception as e:
            return False, "", f"Error retrieving cover letter: {str(e)}"
    
    def update_cover_letter(self, user_id: str, cover_letter_id: str, name: str = None, description: str = None) -> tuple[bool, str]:
        """Update cover letter metadata."""
        try:
            from models.user import User
            from models.database import db
            
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            personal_data = user.personal_data or {}
            cover_letters = personal_data.get('cover_letters', [])
            
            # Find and update cover letter
            for cover_letter in cover_letters:
                if cover_letter.get('id') == cover_letter_id:
                    if name is not None:
                        cover_letter['name'] = name
                    if description is not None:
                        cover_letter['description'] = description
                    cover_letter['updated_at'] = datetime.datetime.utcnow().isoformat()
                    break
            else:
                return False, "Cover letter not found"
            
            # Save updated data
            personal_data['cover_letters'] = cover_letters
            user.personal_data = personal_data
            user.updated_at = datetime.datetime.utcnow()
            db.session.commit()
            
            return True, "Cover letter updated successfully"
        
        except Exception as e:
            db.session.rollback()
            return False, f"Error updating cover letter: {str(e)}"
    
    def delete_cover_letter(self, user_id: str, cover_letter_id: str) -> tuple[bool, str]:
        """Delete a cover letter."""
        try:
            import os
            from models.user import User
            from models.database import db
            
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            personal_data = user.personal_data or {}
            cover_letters = personal_data.get('cover_letters', [])
            
            # Find and remove cover letter
            cover_letter_to_delete = None
            for i, cover_letter in enumerate(cover_letters):
                if cover_letter.get('id') == cover_letter_id:
                    cover_letter_to_delete = cover_letters.pop(i)
                    break
            
            if not cover_letter_to_delete:
                return False, "Cover letter not found"
            
            # Delete file
            file_path = cover_letter_to_delete.get('file_path', '')
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass  # Ignore file deletion errors
            
            # Save updated data
            personal_data['cover_letters'] = cover_letters
            user.personal_data = personal_data
            user.updated_at = datetime.datetime.utcnow()
            db.session.commit()
            
            return True, "Cover letter deleted successfully"
        
        except Exception as e:
            db.session.rollback()
            return False, f"Error deleting cover letter: {str(e)}"


# Create service instance
profile_service = ProfileService()