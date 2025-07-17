"""
Application service for managing job application workflow.

This module provides functionality for managing job applications, including
submission tracking, status updates, retry logic, and application workflow management.
"""
import uuid
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import and_, or_
from models.database import db
from models.application import Application, ApplicationStatus
from models.job import Job
from models.user import User

# Set up logging
logger = logging.getLogger(__name__)


class ApplicationResult:
    """Result object for application operations."""
    
    def __init__(self, success: bool, application_id: Optional[str] = None, 
                 message: str = "", error: Optional[str] = None, 
                 confirmation_details: Optional[Dict] = None):
        self.success = success
        self.application_id = application_id
        self.message = message
        self.error = error
        self.confirmation_details = confirmation_details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            'success': self.success,
            'application_id': self.application_id,
            'message': self.message,
            'error': self.error,
            'confirmation_details': self.confirmation_details
        }
class ApplicationService:
    """Service for managing job application workflow."""
    
    def __init__(self, app=None):
        """Initialize the application service.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self.max_retries = 3  # Default max retries
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the application service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self.max_retries = app.config.get('MAX_APPLICATION_RETRIES', 3)
    
    def get_application_by_id(self, application_id: str) -> Optional[Application]:
        """Get an application by ID.
        
        Args:
            application_id: The application ID to look up
            
        Returns:
            Optional[Application]: The application if found, None otherwise
        """
        try:
            return Application.query.get(application_id)
        except Exception as e:
            logger.error(f"Error retrieving application: {str(e)}")
            return None
    
    def get_applications_by_user(self, user_id: str, 
                                 status: Optional[ApplicationStatus] = None,
                                 active_only: bool = True,
                                 limit: int = 100,
                                 offset: int = 0) -> List[Application]:
        """Get applications for a specific user.
        
        Args:
            user_id: The user ID
            status: Optional filter by application status
            active_only: Whether to only include active applications
            limit: Maximum number of applications to return
            offset: Offset for pagination
            
        Returns:
            List[Application]: List of applications
        """
        try:
            query = Application.query.filter(Application.user_id == user_id)
            
            if status:
                query = query.filter(Application.status == status)
            
            if active_only:
                query = query.filter(Application.is_active == True)
            
            # Order by most recently updated first
            query = query.order_by(Application.updated_at.desc())
            
            # Apply pagination
            query = query.limit(limit).offset(offset)
            
            return query.all()
        except Exception as e:
            logger.error(f"Error retrieving applications for user: {str(e)}")
            return []
    
    def get_applications_by_job(self, job_id: str, 
                               status: Optional[ApplicationStatus] = None,
                               active_only: bool = True) -> List[Application]:
        """Get applications for a specific job.
        
        Args:
            job_id: The job ID
            status: Optional filter by application status
            active_only: Whether to only include active applications
            
        Returns:
            List[Application]: List of applications
        """
        try:
            query = Application.query.filter(Application.job_id == job_id)
            
            if status:
                query = query.filter(Application.status == status)
            
            if active_only:
                query = query.filter(Application.is_active == True)
            
            # Order by most recently updated first
            query = query.order_by(Application.updated_at.desc())
            
            return query.all()
        except Exception as e:
            logger.error(f"Error retrieving applications for job: {str(e)}")
            return []
    
    def create_application(self, user_id: str, job_id: str, 
                          materials: Optional[Dict] = None,
                          application_method: str = "automated") -> ApplicationResult:
        """Create a new job application.
        
        Args:
            user_id: The user ID
            job_id: The job ID
            materials: Dictionary of application materials (resume_version, cover_letter_version, etc.)
            application_method: Method of application ('automated', 'manual', 'hybrid')
            
        Returns:
            ApplicationResult: Result of the operation
        """
        try:
            # Validate user and job exist
            user = User.query.get(user_id)
            if not user:
                return ApplicationResult(False, message="User not found")
            
            job = Job.query.get(job_id)
            if not job:
                return ApplicationResult(False, message="Job not found")
            
            # Check if application already exists
            existing_app = Application.query.filter(
                Application.user_id == user_id,
                Application.job_id == job_id,
                Application.is_active == True
            ).first()
            
            if existing_app:
                return ApplicationResult(
                    False, 
                    application_id=existing_app.id,
                    message="Application already exists for this job"
                )
            
            # Create new application
            application_id = str(uuid.uuid4())
            application = Application(
                id=application_id,
                user_id=user_id,
                job_id=job_id,
                application_method=application_method,
                status=ApplicationStatus.PENDING
            )
            
            # Set materials if provided
            if materials:
                try:
                    application.validate_materials_used(materials)
                    application.materials_used = materials
                except ValueError as e:
                    return ApplicationResult(False, message=f"Invalid materials: {str(e)}")
            
            db.session.add(application)
            db.session.commit()
            
            return ApplicationResult(
                True,
                application_id=application_id,
                message="Application created successfully"
            )
            
        except ValueError as e:
            db.session.rollback()
            logger.error(f"Validation error creating application: {str(e)}")
            return ApplicationResult(False, message=f"Validation error: {str(e)}")
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating application: {str(e)}")
            return ApplicationResult(False, message=f"Error creating application: {str(e)}")
    
    def update_application_status(self, application_id: str, 
                                 new_status: ApplicationStatus,
                                 error_message: Optional[str] = None) -> ApplicationResult:
        """Update the status of an application.
        
        Args:
            application_id: The application ID
            new_status: The new status to set
            error_message: Optional error message for failed applications
            
        Returns:
            ApplicationResult: Result of the operation
        """
        try:
            application = self.get_application_by_id(application_id)
            if not application:
                return ApplicationResult(False, message="Application not found")
            
            old_status = application.status
            
            try:
                application.update_status(new_status, error_message)
                db.session.commit()
                
                return ApplicationResult(
                    True,
                    application_id=application_id,
                    message=f"Status updated from {old_status.value} to {new_status.value}"
                )
            except ValueError as e:
                db.session.rollback()
                return ApplicationResult(False, message=str(e))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating application status: {str(e)}")
            return ApplicationResult(False, message=f"Error updating application status: {str(e)}")
    
    def add_custom_response(self, application_id: str, 
                           question: str, answer: str) -> ApplicationResult:
        """Add a custom response to an application.
        
        Args:
            application_id: The application ID
            question: The question text
            answer: The answer text
            
        Returns:
            ApplicationResult: Result of the operation
        """
        try:
            application = self.get_application_by_id(application_id)
            if not application:
                return ApplicationResult(False, message="Application not found")
            
            try:
                application.add_custom_response(question, answer)
                db.session.commit()
                
                return ApplicationResult(
                    True,
                    application_id=application_id,
                    message="Custom response added successfully"
                )
            except ValueError as e:
                db.session.rollback()
                return ApplicationResult(False, message=str(e))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error adding custom response: {str(e)}")
            return ApplicationResult(False, message=f"Error adding custom response: {str(e)}")
    
    def set_application_materials(self, application_id: str, 
                                resume_version: Optional[str] = None,
                                cover_letter_version: Optional[str] = None,
                                **kwargs) -> ApplicationResult:
        """Set application materials.
        
        Args:
            application_id: The application ID
            resume_version: Optional resume version ID
            cover_letter_version: Optional cover letter version ID
            **kwargs: Additional materials
            
        Returns:
            ApplicationResult: Result of the operation
        """
        try:
            application = self.get_application_by_id(application_id)
            if not application:
                return ApplicationResult(False, message="Application not found")
            
            try:
                application.set_materials(resume_version, cover_letter_version, **kwargs)
                db.session.commit()
                
                return ApplicationResult(
                    True,
                    application_id=application_id,
                    message="Application materials updated successfully"
                )
            except ValueError as e:
                db.session.rollback()
                return ApplicationResult(False, message=str(e))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error setting application materials: {str(e)}")
            return ApplicationResult(False, message=f"Error setting application materials: {str(e)}")
    
    def set_confirmation_details(self, application_id: str,
                               confirmation_id: Optional[str] = None,
                               confirmation_url: Optional[str] = None,
                               **kwargs) -> ApplicationResult:
        """Set confirmation details after successful submission.
        
        Args:
            application_id: The application ID
            confirmation_id: Optional confirmation ID from the job site
            confirmation_url: Optional confirmation URL
            **kwargs: Additional confirmation details
            
        Returns:
            ApplicationResult: Result of the operation
        """
        try:
            application = self.get_application_by_id(application_id)
            if not application:
                return ApplicationResult(False, message="Application not found")
            
            # Set confirmation details
            application.set_confirmation(confirmation_id, confirmation_url, **kwargs)
            
            # Update status to SUBMITTED if currently PENDING
            if application.status == ApplicationStatus.PENDING:
                application.update_status(ApplicationStatus.SUBMITTED)
            
            db.session.commit()
            
            return ApplicationResult(
                True,
                application_id=application_id,
                message="Confirmation details added successfully",
                confirmation_details=application.confirmation_details
            )
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error setting confirmation details: {str(e)}")
            return ApplicationResult(False, message=f"Error setting confirmation details: {str(e)}")
    
    def retry_failed_application(self, application_id: str) -> ApplicationResult:
        """Retry a failed application.
        
        Args:
            application_id: The application ID
            
        Returns:
            ApplicationResult: Result of the operation
        """
        try:
            application = self.get_application_by_id(application_id)
            if not application:
                return ApplicationResult(False, message="Application not found")
            
            # Check if application can be retried
            if not application.can_retry(self.max_retries):
                if application.status != ApplicationStatus.FAILED:
                    return ApplicationResult(
                        False,
                        application_id=application_id,
                        message=f"Application is not in FAILED status (current: {application.status.value})"
                    )
                else:
                    return ApplicationResult(
                        False,
                        application_id=application_id,
                        message=f"Maximum retry attempts ({self.max_retries}) reached"
                    )
            
            # Increment retry count
            application.increment_retry_count()
            
            # Reset to PENDING status
            application.update_status(ApplicationStatus.PENDING)
            
            db.session.commit()
            
            return ApplicationResult(
                True,
                application_id=application_id,
                message=f"Application reset to PENDING for retry (attempt {application.retry_count})"
            )
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error retrying application: {str(e)}")
            return ApplicationResult(False, message=f"Error retrying application: {str(e)}")
    
    def submit_application(self, application_id: str) -> ApplicationResult:
        """Submit an application (mark as submitted).
        
        This method updates the status to SUBMITTED and sets the submitted_at timestamp.
        For actual submission logic, use the automation engine.
        
        Args:
            application_id: The application ID
            
        Returns:
            ApplicationResult: Result of the operation
        """
        try:
            application = self.get_application_by_id(application_id)
            if not application:
                return ApplicationResult(False, message="Application not found")
            
            # Check if application is in PENDING status
            if application.status != ApplicationStatus.PENDING:
                return ApplicationResult(
                    False,
                    application_id=application_id,
                    message=f"Application is not in PENDING status (current: {application.status.value})"
                )
            
            # Update status to SUBMITTED
            application.update_status(ApplicationStatus.SUBMITTED)
            
            db.session.commit()
            
            return ApplicationResult(
                True,
                application_id=application_id,
                message="Application marked as submitted"
            )
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error submitting application: {str(e)}")
            return ApplicationResult(False, message=f"Error submitting application: {str(e)}")
    
    def mark_application_failed(self, application_id: str, error_message: str) -> ApplicationResult:
        """Mark an application as failed with an error message.
        
        Args:
            application_id: The application ID
            error_message: Error message describing the failure
            
        Returns:
            ApplicationResult: Result of the operation
        """
        try:
            application = self.get_application_by_id(application_id)
            if not application:
                return ApplicationResult(False, message="Application not found")
            
            # Update status to FAILED with error message
            application.update_status(ApplicationStatus.FAILED, error_message)
            
            db.session.commit()
            
            return ApplicationResult(
                True,
                application_id=application_id,
                message="Application marked as failed",
                error=error_message
            )
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error marking application as failed: {str(e)}")
            return ApplicationResult(False, message=f"Error marking application as failed: {str(e)}")
    
    def get_applications_needing_followup(self, days_threshold: int = 14) -> List[Application]:
        """Get applications that may need follow-up based on time since submission.
        
        Args:
            days_threshold: Number of days after which to suggest follow-up
            
        Returns:
            List[Application]: List of applications needing follow-up
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days_threshold)
            
            # Find applications that are submitted but not in terminal status
            # and were submitted before the cutoff date
            query = Application.query.filter(
                Application.status == ApplicationStatus.SUBMITTED,
                Application.submitted_at <= cutoff_date,
                Application.is_active == True
            )
            
            return query.all()
        except Exception as e:
            logger.error(f"Error retrieving applications needing follow-up: {str(e)}")
            return []
    
    def get_application_statistics(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Get application statistics.
        
        Args:
            user_id: Optional user ID to filter statistics for a specific user
            
        Returns:
            Dict[str, Any]: Dictionary of application statistics
        """
        try:
            # Base query
            query = Application.query
            
            # Filter by user if specified
            if user_id:
                query = query.filter(Application.user_id == user_id)
            
            # Total applications
            total_count = query.count()
            
            # Count by status
            status_counts = {}
            for status in ApplicationStatus:
                count = query.filter(Application.status == status).count()
                status_counts[status.value] = count
            
            # Active vs. inactive
            active_count = query.filter(Application.is_active == True).count()
            inactive_count = total_count - active_count
            
            # Applications by method
            method_counts = {}
            for method in ['automated', 'manual', 'hybrid']:
                count = query.filter(Application.application_method == method).count()
                method_counts[method] = count
            
            # Recent activity
            recent_cutoff = datetime.utcnow() - timedelta(days=7)
            recent_count = query.filter(Application.updated_at >= recent_cutoff).count()
            
            # Success rate (accepted / (accepted + rejected))
            accepted_count = status_counts.get(ApplicationStatus.ACCEPTED.value, 0)
            rejected_count = status_counts.get(ApplicationStatus.REJECTED.value, 0)
            total_completed = accepted_count + rejected_count
            success_rate = (accepted_count / total_completed) if total_completed > 0 else 0
            
            return {
                'total_applications': total_count,
                'status_counts': status_counts,
                'active_count': active_count,
                'inactive_count': inactive_count,
                'method_counts': method_counts,
                'recent_activity_count': recent_count,
                'success_rate': success_rate
            }
            
        except Exception as e:
            logger.error(f"Error retrieving application statistics: {str(e)}")
            return {
                'error': str(e),
                'total_applications': 0,
                'status_counts': {},
                'success_rate': 0
            }
    
    def delete_application(self, application_id: str) -> ApplicationResult:
        """Delete an application.
        
        Args:
            application_id: The application ID
            
        Returns:
            ApplicationResult: Result of the operation
        """
        try:
            application = self.get_application_by_id(application_id)
            if not application:
                return ApplicationResult(False, message="Application not found")
            
            db.session.delete(application)
            db.session.commit()
            
            return ApplicationResult(
                True,
                message="Application deleted successfully"
            )
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error deleting application: {str(e)}")
            return ApplicationResult(False, message=f"Error deleting application: {str(e)}")
    
    def mark_application_inactive(self, application_id: str) -> ApplicationResult:
        """Mark an application as inactive.
        
        Args:
            application_id: The application ID
            
        Returns:
            ApplicationResult: Result of the operation
        """
        try:
            application = self.get_application_by_id(application_id)
            if not application:
                return ApplicationResult(False, message="Application not found")
            
            application.is_active = False
            db.session.commit()
            
            return ApplicationResult(
                True,
                application_id=application_id,
                message="Application marked as inactive"
            )
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error marking application inactive: {str(e)}")
            return ApplicationResult(False, message=f"Error marking application inactive: {str(e)}")


# Create a singleton instance
application_service = ApplicationService()