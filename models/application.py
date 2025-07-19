"""
Application model for the Job Application Agent.
"""
import json
import enum
from datetime import datetime
from typing import Dict, Optional, List
from sqlalchemy import Column, String, DateTime, Text, Boolean, ForeignKey, Enum, Integer
from sqlalchemy.orm import relationship
from models.database import db


class ApplicationStatus(enum.Enum):
    """Enum for application status values."""
    DRAFT = 'draft'
    SUBMITTED = 'submitted'
    REVIEWED = 'reviewed'
    INTERVIEW = 'interview'
    REJECTED = 'rejected'
    ACCEPTED = 'accepted'


class InterviewStatus(enum.Enum):
    """Enum for interview status values."""
    SCHEDULED = 'scheduled'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'
    RESCHEDULED = 'rescheduled'


class Application(db.Model):
    """Model for job applications."""
    
    __tablename__ = 'applications'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    job_id = Column(String(36), ForeignKey('jobs.id'), nullable=False)
    status = Column(Enum(ApplicationStatus), nullable=False, default=ApplicationStatus.DRAFT)
    cover_letter = Column(Text, nullable=True)
    resume_path = Column(String(255), nullable=True)
    submitted_at = Column(DateTime, nullable=True)
    last_updated_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    meta_data = Column(Text, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="applications")
    job = relationship("Job", back_populates="applications")
    interviews = relationship("Interview", back_populates="application", cascade="all, delete-orphan")
    
    def __init__(self, id: str, user_id: str, job_id: str, **kwargs):
        """Initialize Application instance."""
        self.id = id
        self.user_id = user_id
        self.job_id = job_id
        
        # Set default values
        self.status = kwargs.get('status', ApplicationStatus.DRAFT)
        self.created_at = kwargs.get('created_at', datetime.utcnow())
        self.last_updated_at = kwargs.get('last_updated_at', datetime.utcnow())
        
        # Set optional fields from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @property
    def meta_data_dict(self) -> Dict:
        """Get meta data as dictionary."""
        if not self.meta_data:
            return {}
        try:
            return json.loads(self.meta_data)
        except json.JSONDecodeError:
            return {}
    
    @meta_data_dict.setter
    def meta_data_dict(self, data: Dict):
        """Set meta data from dictionary."""
        if data:
            self.meta_data = json.dumps(data)
        else:
            self.meta_data = None
    
    def update_status(self, new_status: ApplicationStatus, feedback: Optional[str] = None):
        """Update application status and optionally add feedback."""
        self.status = new_status
        if new_status == ApplicationStatus.SUBMITTED and not self.submitted_at:
            self.submitted_at = datetime.utcnow()
        self.last_updated_at = datetime.utcnow()
    
    def to_dict(self, include_related: bool = False) -> Dict:
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
            'meta_data': self.meta_data_dict
        }
        
        if include_related:
            result['user'] = self.user.to_dict() if self.user else None
            result['job'] = self.job.to_dict() if self.job else None
            result['interviews'] = [interview.to_dict() for interview in self.interviews] if self.interviews else []
        
        return result
    
    def __repr__(self):
        """String representation of Application."""
        return f"<Application(id='{self.id}', user_id='{self.user_id}', job_id='{self.job_id}', status='{self.status.value}')>"


class Interview(db.Model):
    """Model for job interviews."""
    
    __tablename__ = 'interviews'
    
    id = Column(String(36), primary_key=True)
    application_id = Column(String(36), ForeignKey('applications.id'), nullable=False)
    scheduled_time = Column(DateTime, nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=60)
    location = Column(String(255), nullable=True)  # Can be physical location or virtual meeting link
    interview_type = Column(String(50), nullable=False, default='phone')  # phone, video, in-person
    interviewer_name = Column(String(255), nullable=True)
    interviewer_title = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    status = Column(Enum(InterviewStatus), nullable=False, default=InterviewStatus.SCHEDULED)
    feedback = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    application = relationship("Application", back_populates="interviews")
    
    def __init__(self, id: str, application_id: str, scheduled_time: datetime, **kwargs):
        """Initialize Interview instance."""
        self.id = id
        self.application_id = application_id
        self.scheduled_time = scheduled_time
        
        # Set default values
        self.duration_minutes = kwargs.get('duration_minutes', 60)
        self.interview_type = kwargs.get('interview_type', 'phone')
        self.status = kwargs.get('status', InterviewStatus.SCHEDULED)
        
        # Set optional fields from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def update_status(self, new_status: InterviewStatus, feedback: Optional[str] = None):
        """Update interview status and optionally add feedback."""
        self.status = new_status
        if feedback:
            self.feedback = feedback
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> Dict:
        """Convert interview to dictionary representation."""
        return {
            'id': self.id,
            'application_id': self.application_id,
            'scheduled_time': self.scheduled_time.isoformat() if self.scheduled_time else None,
            'duration_minutes': self.duration_minutes,
            'location': self.location,
            'interview_type': self.interview_type,
            'interviewer_name': self.interviewer_name,
            'interviewer_title': self.interviewer_title,
            'notes': self.notes,
            'status': self.status.value,
            'feedback': self.feedback,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        """String representation of Interview."""
        return f"<Interview(id='{self.id}', application_id='{self.application_id}', status='{self.status.value}')>"