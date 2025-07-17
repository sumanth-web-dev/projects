"""
Campus Drive model for the Job Application Agent.
"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, Float, ForeignKey, Table
from sqlalchemy.orm import relationship
from models.database import db


# Association table for many-to-many relationship between campus drives and jobs
campus_drive_jobs = Table(
    'campus_drive_jobs',
    db.Model.metadata,
    Column('campus_drive_id', String(36), ForeignKey('campus_drives.id'), primary_key=True),
    Column('job_id', String(36), ForeignKey('jobs.id'), primary_key=True)
)


class CampusDrive(db.Model):
    """Model for campus recruitment drives."""
    
    __tablename__ = 'campus_drives'
    
    id = Column(String(36), primary_key=True)
    institution_id = Column(String(36), ForeignKey('institutions.id'), nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    location = Column(String(255), nullable=True)
    is_virtual = Column(Boolean, default=False, nullable=False)
    status = Column(String(50), default='scheduled', nullable=False)  # scheduled, ongoing, completed, cancelled
    created_by = Column(String(36), ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    institution = relationship("Institution")
    creator = relationship("User")
    jobs = relationship("Job", secondary=campus_drive_jobs, backref="campus_drives")
    registrations = relationship("DriveRegistration", back_populates="campus_drive", cascade="all, delete-orphan")
    
    # JSON fields
    _meta_data = Column('meta_data', Text, nullable=True)
    
    def __init__(self, id: str, institution_id: str, title: str, start_date: datetime, created_by: str, **kwargs):
        """Initialize CampusDrive instance."""
        self.id = id
        self.institution_id = institution_id
        self.title = title
        self.start_date = start_date
        self.created_by = created_by
        
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
    
    def to_dict(self, include_jobs: bool = False, include_registrations: bool = False) -> Dict:
        """Convert campus drive to dictionary representation."""
        result = {
            'id': self.id,
            'institution_id': self.institution_id,
            'title': self.title,
            'description': self.description,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'location': self.location,
            'is_virtual': self.is_virtual,
            'status': self.status,
            'created_by': self.created_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'meta_data': self.meta_data
        }
        
        if include_jobs:
            result['jobs'] = [{'id': job.id, 'title': job.title} for job in self.jobs]
        
        if include_registrations:
            result['registrations'] = [reg.to_dict() for reg in self.registrations]
        
        return result


class Institution(db.Model):
    """Model for educational institutions."""
    
    __tablename__ = 'institutions'
    
    id = Column(String(36), primary_key=True)
    name = Column(String(255), nullable=False)
    type = Column(String(100), nullable=True)  # University, College, School, etc.
    location = Column(String(255), nullable=True)
    website = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __init__(self, id: str, name: str, **kwargs):
        """Initialize Institution instance."""
        self.id = id
        self.name = name
        
        # Set optional fields from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self) -> Dict:
        """Convert institution to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'type': self.type,
            'location': self.location,
            'website': self.website,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class DriveRegistration(db.Model):
    """Model for student registrations for campus drives."""
    
    __tablename__ = 'drive_registrations'
    
    id = Column(String(36), primary_key=True)
    campus_drive_id = Column(String(36), ForeignKey('campus_drives.id'), nullable=False)
    student_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    registration_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), default='registered', nullable=False)  # registered, shortlisted, rejected, etc.
    attendance = Column(Boolean, nullable=True)
    notes = Column(Text, nullable=True)
    
    # Relationships
    campus_drive = relationship("CampusDrive", back_populates="registrations")
    student = relationship("User")
    
    def __init__(self, id: str, campus_drive_id: str, student_id: str, **kwargs):
        """Initialize DriveRegistration instance."""
        self.id = id
        self.campus_drive_id = campus_drive_id
        self.student_id = student_id
        
        # Set optional fields from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self, include_student: bool = False) -> Dict:
        """Convert registration to dictionary representation."""
        result = {
            'id': self.id,
            'campus_drive_id': self.campus_drive_id,
            'student_id': self.student_id,
            'registration_date': self.registration_date.isoformat() if self.registration_date else None,
            'status': self.status,
            'attendance': self.attendance,
            'notes': self.notes
        }
        
        if include_student and self.student:
            result['student'] = {
                'id': self.student.id,
                'email': self.student.email
            }
        
        return result