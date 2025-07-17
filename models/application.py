"""
Application model for the Job Application Agent.
"""
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, Enum
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
from models.database import db
import enum


class ApplicationStatus(enum.Enum):
    """Enumeration for application status values."""
    PENDING = "pending"
    SUBMITTED = "submitted"
    IN_REVIEW = "in_review"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    REJECTED = "rejected"
    ACCEPTED = "accepted"
    WITHDRAWN = "withdrawn"
    FAILED = "failed"


class Application(db.Model):
    """Application model for tracking job applications."""
    
    __tablename__ = 'applications'
    
    # Primary key
    id = Column(String(36), primary_key=True)
    
    # Foreign keys
    job_id = Column(String(36), ForeignKey('jobs.id'), nullable=False, index=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False, index=True)
    
    # Application status
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.PENDING, nullable=False, index=True)
    
    # Application dates
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Application materials used (JSON string)
    materials_used_json = Column(Text, nullable=True)
    
    # Custom responses to application questions (JSON string)
    custom_responses_json = Column(Text, nullable=True)
    
    # Confirmation details from successful submission (JSON string)
    confirmation_details_json = Column(Text, nullable=True)
    
    # Error information for failed applications
    error_log = Column(Text, nullable=True)
    error_count = Column(String(10), default="0", nullable=False)
    
    # Application metadata
    application_method = Column(String(50), nullable=True)  # 'automated', 'manual', 'hybrid'
    retry_count = Column(String(10), default="0", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # External tracking
    external_application_id = Column(String(255), nullable=True)
    
    # Relationships
    job = relationship("Job", back_populates="applications")
    user = relationship("User", back_populates="applications")
    
    def __init__(self, id: str, job_id: str, user_id: str, **kwargs):
        """Initialize Application instance."""
        self.id = id
        self.job_id = job_id
        self.user_id = user_id
        
        # Set default values if not provided in kwargs
        if 'status' not in kwargs:
            self.status = ApplicationStatus.PENDING
        if 'is_active' not in kwargs:
            self.is_active = True
        if 'retry_count' not in kwargs:
            self.retry_count = "0"
        if 'error_count' not in kwargs:
            self.error_count = "0"
        
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @validates('job_id')
    def validate_job_id(self, key, job_id):
        """Validate job ID."""
        if not job_id or not job_id.strip():
            raise ValueError("Job ID is required")
        
        if len(job_id) > 36:
            raise ValueError("Job ID must be 36 characters or less")
        
        return job_id.strip()
    
    @validates('user_id')
    def validate_user_id(self, key, user_id):
        """Validate user ID."""
        if not user_id or not user_id.strip():
            raise ValueError("User ID is required")
        
        if len(user_id) > 36:
            raise ValueError("User ID must be 36 characters or less")
        
        return user_id.strip()
    
    @validates('status')
    def validate_status(self, key, status):
        """Validate application status."""
        if isinstance(status, str):
            try:
                status = ApplicationStatus(status)
            except ValueError:
                valid_statuses = [s.value for s in ApplicationStatus]
                raise ValueError(f"Status must be one of: {', '.join(valid_statuses)}")
        
        if not isinstance(status, ApplicationStatus):
            raise ValueError("Status must be an ApplicationStatus enum value")
        
        return status
    
    @validates('application_method')
    def validate_application_method(self, key, method):
        """Validate application method."""
        if method:
            valid_methods = ['automated', 'manual', 'hybrid']
            if method.lower() not in valid_methods:
                raise ValueError(f"Application method must be one of: {', '.join(valid_methods)}")
            return method.lower()
        return method
    
    @hybrid_property
    def materials_used(self) -> Dict[str, Any]:
        """Get application materials as dictionary."""
        if not self.materials_used_json:
            return {}
        try:
            return json.loads(self.materials_used_json)
        except json.JSONDecodeError:
            return {}
    
    @materials_used.setter
    def materials_used(self, materials: Dict[str, Any]):
        """Set application materials from dictionary."""
        if materials and isinstance(materials, dict):
            self.materials_used_json = json.dumps(materials)
        else:
            self.materials_used_json = None
    
    @hybrid_property
    def custom_responses(self) -> Dict[str, str]:
        """Get custom responses as dictionary."""
        if not self.custom_responses_json:
            return {}
        try:
            return json.loads(self.custom_responses_json)
        except json.JSONDecodeError:
            return {}
    
    @custom_responses.setter
    def custom_responses(self, responses: Dict[str, str]):
        """Set custom responses from dictionary."""
        if responses and isinstance(responses, dict):
            self.custom_responses_json = json.dumps(responses)
        else:
            self.custom_responses_json = None
    
    @hybrid_property
    def confirmation_details(self) -> Dict[str, Any]:
        """Get confirmation details as dictionary."""
        if not self.confirmation_details_json:
            return {}
        try:
            return json.loads(self.confirmation_details_json)
        except json.JSONDecodeError:
            return {}
    
    @confirmation_details.setter
    def confirmation_details(self, details: Dict[str, Any]):
        """Set confirmation details from dictionary."""
        if details and isinstance(details, dict):
            self.confirmation_details_json = json.dumps(details)
        else:
            self.confirmation_details_json = None
    
    def validate_materials_used(self, materials: Dict[str, Any]) -> bool:
        """Validate application materials structure."""
        if not isinstance(materials, dict):
            raise ValueError("Materials used must be a dictionary")
        
        # Expected structure for materials
        expected_fields = ['resume_version', 'cover_letter_version']
        
        for field in expected_fields:
            if field in materials and not isinstance(materials[field], str):
                raise ValueError(f"Field '{field}' must be a string")
        
        return True
    
    def validate_custom_responses(self, responses: Dict[str, str]) -> bool:
        """Validate custom responses structure."""
        if not isinstance(responses, dict):
            raise ValueError("Custom responses must be a dictionary")
        
        for question, answer in responses.items():
            if not isinstance(question, str) or not isinstance(answer, str):
                raise ValueError("All questions and answers must be strings")
            
            if len(question.strip()) == 0:
                raise ValueError("Question cannot be empty")
            
            if len(answer.strip()) == 0:
                raise ValueError("Answer cannot be empty")
        
        return True
    
    def update_status(self, new_status: ApplicationStatus, error_message: Optional[str] = None):
        """Update application status with validation and logging."""
        old_status = self.status
        
        # Validate status transition
        valid_transitions = {
            ApplicationStatus.PENDING: [ApplicationStatus.SUBMITTED, ApplicationStatus.FAILED, ApplicationStatus.WITHDRAWN],
            ApplicationStatus.SUBMITTED: [ApplicationStatus.IN_REVIEW, ApplicationStatus.REJECTED, ApplicationStatus.ACCEPTED, ApplicationStatus.FAILED],
            ApplicationStatus.IN_REVIEW: [ApplicationStatus.INTERVIEW_SCHEDULED, ApplicationStatus.REJECTED, ApplicationStatus.ACCEPTED],
            ApplicationStatus.INTERVIEW_SCHEDULED: [ApplicationStatus.REJECTED, ApplicationStatus.ACCEPTED],
            ApplicationStatus.REJECTED: [],  # Terminal state
            ApplicationStatus.ACCEPTED: [],  # Terminal state
            ApplicationStatus.WITHDRAWN: [],  # Terminal state
            ApplicationStatus.FAILED: [ApplicationStatus.PENDING]  # Can retry
        }
        
        if new_status not in valid_transitions.get(old_status, []):
            raise ValueError(f"Invalid status transition from {old_status.value} to {new_status.value}")
        
        self.status = new_status
        self.updated_at = datetime.utcnow()
        
        # Set submitted_at when status changes to SUBMITTED
        if new_status == ApplicationStatus.SUBMITTED and not self.submitted_at:
            self.submitted_at = datetime.utcnow()
        
        # Handle error logging
        if new_status == ApplicationStatus.FAILED and error_message:
            self.error_log = error_message
            self.error_count = str(int(self.error_count) + 1)
    
    def add_custom_response(self, question: str, answer: str):
        """Add a custom response to the application."""
        if not question or not question.strip():
            raise ValueError("Question cannot be empty")
        
        if not answer or not answer.strip():
            raise ValueError("Answer cannot be empty")
        
        responses = self.custom_responses
        responses[question.strip()] = answer.strip()
        self.custom_responses = responses
    
    def set_materials(self, resume_version: Optional[str] = None, cover_letter_version: Optional[str] = None, **kwargs):
        """Set application materials with validation."""
        materials = self.materials_used
        
        if resume_version:
            materials['resume_version'] = resume_version
        
        if cover_letter_version:
            materials['cover_letter_version'] = cover_letter_version
        
        # Add any additional materials
        for key, value in kwargs.items():
            if value:
                materials[key] = value
        
        self.validate_materials_used(materials)
        self.materials_used = materials
    
    def set_confirmation(self, confirmation_id: Optional[str] = None, confirmation_url: Optional[str] = None, **kwargs):
        """Set confirmation details after successful submission."""
        details = {}
        
        if confirmation_id:
            details['confirmation_id'] = confirmation_id
        
        if confirmation_url:
            details['confirmation_url'] = confirmation_url
        
        # Add any additional confirmation details
        for key, value in kwargs.items():
            if value:
                details[key] = value
        
        if details:
            details['confirmed_at'] = datetime.utcnow().isoformat()
            self.confirmation_details = details
    
    def increment_retry_count(self):
        """Increment the retry count for failed applications."""
        self.retry_count = str(int(self.retry_count) + 1)
    
    def can_retry(self, max_retries: int = 3) -> bool:
        """Check if application can be retried."""
        return (self.status == ApplicationStatus.FAILED and 
                int(self.retry_count) < max_retries)
    
    def is_terminal_status(self) -> bool:
        """Check if application is in a terminal status."""
        terminal_statuses = [
            ApplicationStatus.REJECTED,
            ApplicationStatus.ACCEPTED,
            ApplicationStatus.WITHDRAWN
        ]
        return self.status in terminal_statuses
    
    def days_since_submission(self) -> Optional[int]:
        """Get number of days since application was submitted."""
        if self.submitted_at:
            delta = datetime.utcnow() - self.submitted_at
            return delta.days
        return None
    
    def to_dict(self, include_details: bool = True) -> Dict[str, Any]:
        """Convert application to dictionary representation."""
        result = {
            'id': self.id,
            'job_id': self.job_id,
            'user_id': self.user_id,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'application_method': self.application_method,
            'retry_count': int(self.retry_count),
            'error_count': int(self.error_count),
            'is_active': self.is_active,
            'external_application_id': self.external_application_id,
            'is_terminal': self.is_terminal_status(),
            'can_retry': self.can_retry(),
            'days_since_submission': self.days_since_submission()
        }
        
        if include_details:
            result.update({
                'materials_used': self.materials_used,
                'custom_responses': self.custom_responses,
                'confirmation_details': self.confirmation_details,
                'error_log': self.error_log
            })
        
        return result
    
    def __repr__(self):
        """String representation of Application."""
        return f"<Application(id='{self.id}', job_id='{self.job_id}', status='{self.status.value}')>"