"""
Education model for the Job Application Agent.
"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from models.database import db


class Education(db.Model):
    """Model for user education details."""
    
    __tablename__ = 'education'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    institution = Column(String(255), nullable=False)
    degree = Column(String(255), nullable=False)
    field_of_study = Column(String(255), nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    grade = Column(String(50), nullable=True)
    activities = Column(Text, nullable=True)
    description = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="education_history")
    
    # JSON fields
    _meta_data = Column('meta_data', Text, nullable=True)
    
    def __init__(self, id: str, user_id: str, institution: str, degree: str, start_date: datetime, **kwargs):
        """Initialize Education instance."""
        self.id = id
        self.user_id = user_id
        self.institution = institution
        self.degree = degree
        self.start_date = start_date
        
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
    
    def to_dict(self) -> Dict:
        """Convert education to dictionary representation."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'institution': self.institution,
            'degree': self.degree,
            'field_of_study': self.field_of_study,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'grade': self.grade,
            'activities': self.activities,
            'description': self.description,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'meta_data': self.meta_data
        }


class Certification(db.Model):
    """Model for user certifications."""
    
    __tablename__ = 'certifications'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    name = Column(String(255), nullable=False)
    issuing_organization = Column(String(255), nullable=False)
    issue_date = Column(DateTime, nullable=False)
    expiration_date = Column(DateTime, nullable=True)
    credential_id = Column(String(255), nullable=True)
    credential_url = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="certifications")
    
    def __init__(self, id: str, user_id: str, name: str, issuing_organization: str, issue_date: datetime, **kwargs):
        """Initialize Certification instance."""
        self.id = id
        self.user_id = user_id
        self.name = name
        self.issuing_organization = issuing_organization
        self.issue_date = issue_date
        
        # Set optional fields from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self) -> Dict:
        """Convert certification to dictionary representation."""
        return {
            'id': self.id,
            'user_id': self.user_id,
            'name': self.name,
            'issuing_organization': self.issuing_organization,
            'issue_date': self.issue_date.isoformat() if self.issue_date else None,
            'expiration_date': self.expiration_date.isoformat() if self.expiration_date else None,
            'credential_id': self.credential_id,
            'credential_url': self.credential_url,
            'description': self.description,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }