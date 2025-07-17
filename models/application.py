"""
Application model for the Job Application Agent.
"""
import json
import enum
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship
from models.database import db


class ApplicationStatus(enum.Enum):
    """Enum for application status."""
    DRAFT = "draft"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    SHORTLISTED = "shortlisted"
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEWED = "interviewed"
    OFFER_PENDING = "offer_pending"
    OFFER_RECEIVED = "offer_received"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class Application(db.Model):
    """Model for job applications."""
    
    __tablename__ = 'applications'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    job_id = Column(String(36), ForeignKey('jobs.id'), nullable=False)
    status = Column(Enum(ApplicationStatus), default=ApplicationStatus.DRAFT, nullable=False)
    cover_letter = Column(Text, nullable=True)
    resume_path = Column(String(255), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    last_updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    interviews = relationship("Interview", back_populates="application", cascade="all, delete-orphan")
    
    # JSON fields
    _meta_data = Column('meta_data', Text, nullable=True)
    
    def __init__(self, id: str, user_id: str, job_id: str, **kwargs):
        """Initialize Application instance."""
        self.id = id
        self.user_id = user_id
        self.job_id = job_id
        
        # Set optional fields from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @property
    def meta_data(self) -> Dict:
        """Get meta data as dictionary."""
        if not self._meta_data:
            return {}
        try:
            return json.loads(self._meta_data)
        except json.JSONDecodeError:
            return {}
    
    @meta_data.setter
    def meta_data(self, data: Dict):
        """Set meta data from dictionary."""
        if data:
            self._meta_data = json.dumps(data)
        else:
            self._meta_data = None
    
    def submit(self):
        """Submit the application."""
        if self.status == ApplicationStatus.DRAFT:
            self.status = ApplicationStatus.SUBMITTED
            self.submitted_at = datetime.utcnow()
    
    def update_status(self, status: ApplicationStatus):
        """Update application status."""
        self.status = status
        self.last_updated_at = datetime.utcnow()
    
    def to_dict(self, include_job: bool = False, include_user: bool = False) -> Dict:
        """Convert application to dictionary representation."""
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'job_id': self.job_id,
            'status': self.status.value,
            'cover_letter': self.cover_letter,
            'resume_path': self.resume_path,
            'submitted_at': self.submitted_at.isoformat() if self.submitted_at else None,
            'last_updated_at': self.last_updated_at.isoformat() if self.last_updated_at else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'meta_data': self.meta_data
        }
        
        if include_job and self.job:
            result['job'] = {
                'id': self.job.id,
                'title': self.job.title,
                'company': self.job.company
            }
        
        if include_user and self.user:
            result['user'] = {
                'id': self.user.id,
                'email': self.user.email
            }
        
        return result


class Interview(db.Model):
    """Model for job interviews."""
    
    __tablename__ = 'interviews'
    
    id = Column(String(36), primary_key=True)
    application_id = Column(String(36), ForeignKey('applications.id'), nullable=False)
    scheduled_at = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, default=60, nullable=False)
    location = Column(String(255), nullable=True)
    interview_type = Column(String(50), nullable=False)  # In-person, Phone, Video, etc.
    interviewer_notes = Column(Text, nullable=True)
    candidate_notes = Column(Text, nullable=True)
    is_completed = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    application = relationship("Application", back_populates="interviews")
    
    # JSON fields
    _meta_data = Column('meta_data', Text, nullable=True)
    
    def __init__(self, id: str, application_id: str, scheduled_at: datetime, interview_type: str, **kwargs):
        """Initialize Interview instance."""
        self.id = id
        self.application_id = application_id
        self.scheduled_at = scheduled_at
        self.interview_type = interview_type
        
        # Set optional fields from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @property
    def meta_data(self) -> Dict:
        """Get meta data as dictionary."""
        if not self._meta_data:
            return {}
        try:
            return json.loads(self._meta_data)
        except json.JSONDecodeError:
            return {}
    
    @meta_data.setter
    def meta_data(self, data: Dict):
        """Set meta data from dictionary."""
        if data:
            self._meta_data = json.dumps(data)
        else:
            self._meta_data = None
    
    def to_dict(self, include_application: bool = False) -> Dict:
        """Convert interview to dictionary representation."""
        result = {
            'id': self.id,
            'application_id': self.application_id,
            'scheduled_at': self.scheduled_at.isoformat() if self.scheduled_at else None,
            'duration_minutes': self.duration_minutes,
            'location': self.location,
            'interview_type': self.interview_type,
            'interviewer_notes': self.interviewer_notes,
            'candidate_notes': self.candidate_notes,
            'is_completed': self.is_completed,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'meta_data': self.meta_data
        }
        
        if include_application and self.application:
            result['application'] = self.application.to_dict()
        
        return result