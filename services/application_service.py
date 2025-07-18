"""
Application service for managing job applications.
"""
import datetime
import uuid
from typing import Dict, List, Optional
from sqlalchemy import desc, func, and_, or_


class ApplicationService:
    """Service for managing job applications."""
    
    def init_app(self, app):
        """Initialize the application service with the Flask app."""
        # No initialization needed for now
        pass
    
    def get_user_applications(self, user_id: str) -> List:
        """Get all applications for a user."""
        try:
            from models.application import Application
            
            applications = Application.query.filter_by(user_id=user_id)\
                .order_by(desc(Application.created_at))\
                .all()
            return applications
        except Exception as e:
            return []
    
    def get_application_stats(self, user_id: str) -> Dict:
        """Get application statistics for a user."""
        try:
            from models.application import Application, ApplicationStatus
            
            total_applications = Application.query.filter_by(user_id=user_id).count()
            
            under_review = Application.query.filter(
                Application.user_id == user_id,
                Application.status.in_([ApplicationStatus.SUBMITTED, ApplicationStatus.UNDER_REVIEW])
            ).count()
            
            interviews_scheduled = Application.query.filter(
                Application.user_id == user_id,
                Application.status == ApplicationStatus.INTERVIEW_SCHEDULED
            ).count()
            
            offers_received = Application.query.filter(
                Application.user_id == user_id,
                Application.status.in_([ApplicationStatus.OFFER_RECEIVED, ApplicationStatus.OFFER_PENDING])
            ).count()
            
            return {
                'total_applications': total_applications,
                'under_review': under_review,
                'interviews_scheduled': interviews_scheduled,
                'offers_received': offers_received
            }
        
        except Exception as e:
            return {
                'total_applications': 0,
                'under_review': 0,
                'interviews_scheduled': 0,
                'offers_received': 0
            }
    
    def withdraw_application(self, application_id: str, user_id: str) -> bool:
        """Withdraw a job application."""
        try:
            from models.application import Application, ApplicationStatus
            from models.database import db
            
            application = Application.query.filter_by(
                id=application_id,
                user_id=user_id
            ).first()
            
            if not application:
                return False
            
            # Check if application can be withdrawn
            if application.status in [ApplicationStatus.ACCEPTED, ApplicationStatus.REJECTED]:
                return False
            
            application.status = ApplicationStatus.WITHDRAWN
            application.last_updated_at = datetime.datetime.utcnow()
            db.session.commit()
            
            return True
        
        except Exception as e:
            db.session.rollback()
            return False
    
    def accept_offer(self, application_id: str, user_id: str) -> bool:
        """Accept a job offer."""
        try:
            from models.application import Application, ApplicationStatus
            from models.database import db
            
            application = Application.query.filter_by(
                id=application_id,
                user_id=user_id
            ).first()
            
            if not application:
                return False
            
            # Check if application has an offer
            if application.status != ApplicationStatus.OFFER_RECEIVED:
                return False
            
            application.status = ApplicationStatus.ACCEPTED
            application.last_updated_at = datetime.datetime.utcnow()
            db.session.commit()
            
            return True
        
        except Exception as e:
            db.session.rollback()
            return False
    
    def decline_offer(self, application_id: str, user_id: str) -> bool:
        """Decline a job offer."""
        try:
            from models.application import Application, ApplicationStatus
            from models.database import db
            
            application = Application.query.filter_by(
                id=application_id,
                user_id=user_id
            ).first()
            
            if not application:
                return False
            
            # Check if application has an offer
            if application.status != ApplicationStatus.OFFER_RECEIVED:
                return False
            
            application.status = ApplicationStatus.REJECTED
            application.last_updated_at = datetime.datetime.utcnow()
            db.session.commit()
            
            return True
        
        except Exception as e:
            db.session.rollback()
            return False
    
    def get_applications_with_filters(self, status: str = '', job_id: str = '', 
                                    date_range: str = '', search: str = '') -> List:
        """Get applications with filters for HR."""
        try:
            from models.application import Application, ApplicationStatus
            from models.user import User
            
            query = Application.query
            
            # Apply status filter
            if status:
                query = query.filter(Application.status == ApplicationStatus(status))
            
            # Apply job filter
            if job_id:
                query = query.filter(Application.job_id == job_id)
            
            # Apply date range filter
            if date_range:
                today = datetime.datetime.utcnow().date()
                if date_range == 'today':
                    query = query.filter(Application.created_at >= today)
                elif date_range == 'week':
                    week_ago = today - datetime.timedelta(days=7)
                    query = query.filter(Application.created_at >= week_ago)
                elif date_range == 'month':
                    month_ago = today - datetime.timedelta(days=30)
                    query = query.filter(Application.created_at >= month_ago)
            
            # Apply search filter
            if search:
                query = query.join(User).filter(
                    or_(
                        User.email.ilike(f'%{search}%'),
                        func.json_extract(User.encrypted_personal_data, '$.first_name').ilike(f'%{search}%'),
                        func.json_extract(User.encrypted_personal_data, '$.last_name').ilike(f'%{search}%')
                    )
                )
            
            applications = query.order_by(desc(Application.created_at)).all()
            return applications
        
        except Exception as e:
            return []
    
    def get_application_statistics(self) -> Dict:
        """Get overall application statistics for HR."""
        try:
            from models.application import Application, ApplicationStatus
            
            total_applications = Application.query.count()
            
            new_applications = Application.query.filter(
                Application.created_at >= datetime.datetime.utcnow().date()
            ).count()
            
            under_review = Application.query.filter(
                Application.status == ApplicationStatus.UNDER_REVIEW
            ).count()
            
            shortlisted = Application.query.filter(
                Application.status == ApplicationStatus.SHORTLISTED
            ).count()
            
            return {
                'total_applications': total_applications,
                'new_applications': new_applications,
                'under_review': under_review,
                'shortlisted': shortlisted
            }
        
        except Exception as e:
            return {
                'total_applications': 0,
                'new_applications': 0,
                'under_review': 0,
                'shortlisted': 0
            }
    
    def get_application_with_details(self, application_id: str) -> Optional:
        """Get application with full details."""
        try:
            from models.application import Application
            
            application = Application.query.get(application_id)
            return application
        except Exception as e:
            return None
    
    def get_application_timeline(self, application_id: str) -> List[Dict]:
        """Get application status change timeline."""
        try:
            from models.application import Application, ApplicationStatus
            
            # This would typically come from an audit/history table
            # For now, return basic timeline
            application = Application.query.get(application_id)
            if not application:
                return []
            
            timeline = [
                {
                    'status': 'submitted',
                    'date': application.submitted_at or application.created_at,
                    'note': 'Application submitted'
                }
            ]
            
            if application.status != ApplicationStatus.SUBMITTED:
                timeline.append({
                    'status': application.status.value,
                    'date': application.last_updated_at,
                    'note': f'Status changed to {application.status.value}'
                })
            
            return timeline
        
        except Exception as e:
            return []
    
    def get_similar_candidates(self, application_id: str, limit: int = 5) -> List:
        """Get similar candidates based on skills and experience."""
        try:
            from models.application import Application
            
            application = Application.query.get(application_id)
            if not application:
                return []
            
            # Get candidates for the same job
            similar_applications = Application.query.filter(
                and_(
                    Application.job_id == application.job_id,
                    Application.id != application_id
                )
            ).limit(limit).all()
            
            return similar_applications
        
        except Exception as e:
            return []
    
    def update_application_status(self, application_id: str, new_status: str, 
                                updated_by: str, note: str = '') -> bool:
        """Update application status."""
        try:
            from models.application import Application, ApplicationStatus
            from models.database import db
            
            application = Application.query.get(application_id)
            if not application:
                return False
            
            application.status = ApplicationStatus(new_status)
            application.last_updated_at = datetime.datetime.utcnow()
            
            # Add note to meta_data if provided
            if note:
                meta_data = application.meta_data or {}
                if 'notes' not in meta_data:
                    meta_data['notes'] = []
                
                meta_data['notes'].append({
                    'note': note,
                    'added_by': updated_by,
                    'added_at': datetime.datetime.utcnow().isoformat()
                })
                
                application.meta_data = meta_data
            
            db.session.commit()
            return True
        
        except Exception as e:
            db.session.rollback()
            return False
    
    def add_application_note(self, application_id: str, note: str, added_by: str) -> bool:
        """Add note to application."""
        try:
            from models.application import Application
            from models.database import db
            
            application = Application.query.get(application_id)
            if not application:
                return False
            
            meta_data = application.meta_data or {}
            if 'notes' not in meta_data:
                meta_data['notes'] = []
            
            meta_data['notes'].append({
                'note': note,
                'added_by': added_by,
                'added_at': datetime.datetime.utcnow().isoformat()
            })
            
            application.meta_data = meta_data
            db.session.commit()
            
            return True
        
        except Exception as e:
            db.session.rollback()
            return False
    
    def get_job_applications(self, job_id: str) -> List:
        """Get all applications for a specific job."""
        try:
            from models.application import Application
            
            applications = Application.query.filter_by(job_id=job_id)\
                .order_by(desc(Application.created_at))\
                .all()
            return applications
        except Exception as e:
            return []
    
    def get_candidates_with_filters(self, skills: str = '', experience: str = '', 
                                  location: str = '', availability: str = '') -> List:
        """Get candidates with filters."""
        try:
            from models.user import User
            from models.application import Application
            from models.database import db
            
            # This would typically involve more complex filtering
            # For now, return users who have submitted applications
            query = db.session.query(User).join(Application)
            
            # Apply filters based on personal_data (would need proper JSON querying)
            candidates = query.distinct().all()
            
            return candidates
        
        except Exception as e:
            return []
    
    def get_candidate_statistics(self) -> Dict:
        """Get candidate statistics."""
        try:
            from models.user import User
            from models.application import Application, ApplicationStatus
            from models.database import db
            
            total_candidates = db.session.query(User).join(Application).distinct().count()
            
            active_candidates = db.session.query(User).join(Application).filter(
                Application.status.in_([
                    ApplicationStatus.SUBMITTED,
                    ApplicationStatus.UNDER_REVIEW,
                    ApplicationStatus.SHORTLISTED,
                    ApplicationStatus.INTERVIEW_SCHEDULED
                ])
            ).distinct().count()
            
            return {
                'total_candidates': total_candidates,
                'active_candidates': active_candidates,
                'new_candidates_week': 0,  # Placeholder
                'hired_candidates': 0  # Placeholder
            }
        
        except Exception as e:
            return {
                'total_candidates': 0,
                'active_candidates': 0,
                'new_candidates_week': 0,
                'hired_candidates': 0
            }
# Create service instance
application_service = ApplicationService()