"""User services for handling user-related functionality."""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

from flask import current_app
from sqlalchemy.exc import SQLAlchemyError

from models.user import User
from models.application import Application
from models.job import Job
from extensions import db

logger = logging.getLogger(__name__)

class UserService:
    """Service for user-related operations."""
    
    def get_user_by_id(self, user_id: str) -> Optional[User]:
        """Get a user by ID.
        
        Args:
            user_id: The user ID
            
        Returns:
            User object if found, None otherwise
        """
        try:
            return User.query.get(user_id)
        except SQLAlchemyError as e:
            logger.error(f"Error retrieving user {user_id}: {str(e)}")
            return None
    
    def get_user_type(self, user_id: str) -> str:
        """Get the user type (student, employer, admin).
        
        Args:
            user_id: The user ID
            
        Returns:
            String representing user type
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return "unknown"
                
            personal_data = user.personal_data or {}
            roles = personal_data.get('roles', [])
            
            if 'admin' in roles:
                return "admin"
            elif 'employer' in roles:
                return "employer"
            else:
                return "student"  # Default role
        except Exception as e:
            logger.error(f"Error determining user type for {user_id}: {str(e)}")
            return "unknown"
    
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get statistics for a user's dashboard.
        
        Args:
            user_id: The user ID
            
        Returns:
            Dictionary of user statistics
        """
        try:
            # Initialize stats dictionary
            stats = {
                'applications_count': 0,
                'applications_this_week': 0,
                'interviews_count': 0,
                'upcoming_interviews': 0,
                'offers_count': 0,
                'pending_offers': 0,
                'profile_completion': 0,
                'new_jobs_today': 0,
                'total_recommended': 0,
                'upcoming_drives': 0
            }
            
            # Get applications count
            applications = Application.query.filter_by(user_id=user_id).all()
            stats['applications_count'] = len(applications)
            
            # Calculate applications this week
            one_week_ago = datetime.utcnow() - timedelta(days=7)
            stats['applications_this_week'] = Application.query.filter(
                Application.user_id == user_id,
                Application.created_at >= one_week_ago
            ).count()
            
            # Count interviews
            interview_count = 0
            upcoming_interviews = 0
            for application in applications:
                if hasattr(application, 'interviews'):
                    interview_count += len(application.interviews)
                    for interview in application.interviews:
                        if interview.scheduled_time > datetime.utcnow():
                            upcoming_interviews += 1
            
            stats['interviews_count'] = interview_count
            stats['upcoming_interviews'] = upcoming_interviews
            
            # Count offers
            offers_count = 0
            pending_offers = 0
            for application in applications:
                if application.status == 'offer_received':
                    offers_count += 1
                    if not application.meta_data_dict.get('offer_response'):
                        pending_offers += 1
            
            stats['offers_count'] = offers_count
            stats['pending_offers'] = pending_offers
            
            # Calculate profile completion
            stats['profile_completion'] = self.calculate_profile_completion(user_id)
            
            # Count new jobs today
            today = datetime.utcnow().date()
            stats['new_jobs_today'] = Job.query.filter(
                Job.created_at >= today
            ).count()
            
            # Count recommended jobs (placeholder)
            stats['total_recommended'] = 10
            
            # Count upcoming campus drives (placeholder)
            stats['upcoming_drives'] = 5
            
            return stats
        except Exception as e:
            logger.error(f"Error getting user stats for {user_id}: {str(e)}")
            return {}
    
    def calculate_profile_completion(self, user_id: str) -> int:
        """Calculate the profile completion percentage.
        
        Args:
            user_id: User ID
            
        Returns:
            Integer percentage of profile completion
        """
        try:
            user = self.get_user_by_id(user_id)
            if not user:
                return 0
                
            personal_data = user.personal_data or {}
            total_fields = 0
            completed_fields = 0
            
            # Basic information
            basic_fields = ['first_name', 'last_name', 'email', 'phone', 'address', 'city', 'state', 'zip_code']
            total_fields += len(basic_fields)
            for field in basic_fields:
                if personal_data.get(field):
                    completed_fields += 1
            
            # Education
            education = personal_data.get('education', [])
            if education:
                total_fields += 1
                completed_fields += 1
                
                # Check education details
                for edu in education:
                    edu_fields = ['institution', 'degree', 'field_of_study', 'start_date', 'end_date', 'gpa']
                    total_fields += len(edu_fields)
                    for field in edu_fields:
                        if edu.get(field):
                            completed_fields += 1
            
            # Skills
            skills = personal_data.get('skills', [])
            total_fields += 1
            if skills:
                completed_fields += 1
            
            # Experience
            experience = personal_data.get('experience', [])
            if experience:
                total_fields += 1
                completed_fields += 1
                
                # Check experience details
                for exp in experience:
                    exp_fields = ['company', 'position', 'start_date', 'end_date', 'description']
                    total_fields += len(exp_fields)
                    for field in exp_fields:
                        if exp.get(field):
                            completed_fields += 1
            
            # Projects
            projects = personal_data.get('projects', [])
            if projects:
                total_fields += 1
                completed_fields += 1
            
            # Resume
            if personal_data.get('resume_path'):
                total_fields += 1
                completed_fields += 1
            
            # Calculate percentage
            if total_fields == 0:
                return 0
                
            completion_percentage = (completed_fields / total_fields) * 100
            return min(round(completion_percentage), 100)  # Cap at 100%
        except Exception as e:
            logger.error(f"Error calculating profile completion: {str(e)}")
            return 0
    
    def get_user_notifications(self, user_id: str, limit: int = 5) -> List[Dict]:
        """Get recent notifications for a user.
        
        Args:
            user_id: The user ID
            limit: Maximum number of notifications to return
            
        Returns:
            List of notification dictionaries
        """
        try:
            # This would typically come from a notification service or database
            # For now, return placeholder data
            return [
                {
                    'id': '1',
                    'type': 'application_update',
                    'message': 'Your application for Software Engineer at Tech Corp has been reviewed',
                    'timestamp': datetime.utcnow().isoformat(),
                    'is_read': False
                },
                {
                    'id': '2',
                    'type': 'interview_scheduled',
                    'message': 'Interview scheduled with Innovation Labs for tomorrow at 2:00 PM',
                    'timestamp': datetime.utcnow().isoformat(),
                    'is_read': False
                },
                {
                    'id': '3',
                    'type': 'offer_received',
                    'message': 'You have received a job offer from Global Tech Solutions',
                    'timestamp': datetime.utcnow().isoformat(),
                    'is_read': True
                },
                {
                    'id': '4',
                    'type': 'campus_drive',
                    'message': 'New campus drive announced: Tech Career Fair 2025',
                    'timestamp': datetime.utcnow().isoformat(),
                    'is_read': True
                },
                {
                    'id': '5',
                    'type': 'profile_reminder',
                    'message': 'Complete your profile to improve job match recommendations',
                    'timestamp': datetime.utcnow().isoformat(),
                    'is_read': False
                }
            ][:limit]
        except Exception as e:
            logger.error(f"Error getting notifications for {user_id}: {str(e)}")
            return []

# Create a singleton instance
user_service = UserService()