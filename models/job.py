"""
Job model for the Job Application Agent.
"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from models.database import db


class JobCategory(db.Model):
    """Model for job categories."""
    
    __tablename__ = 'job_categories'
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    parent_id = Column(String(36), ForeignKey('job_categories.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    parent = relationship("JobCategory", remote_side=[id], backref="subcategories")
    jobs = relationship("Job", back_populates="category")
    
    def __init__(self, id: str, name: str, description: Optional[str] = None, parent_id: Optional[str] = None):
        """Initialize JobCategory instance."""
        self.id = id
        self.name = name
        self.description = description
        self.parent_id = parent_id
    
    def to_dict(self) -> Dict:
        """Convert category to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'parent_id': self.parent_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Job(db.Model):
    """Model for job listings."""
    
    __tablename__ = 'jobs'
    
    id = Column(String(36), primary_key=True)
    title = Column(String(255), nullable=False)
    company = Column(String(255), nullable=False)
    location = Column(String(255), nullable=True)
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    experience_required = Column(Integer, nullable=True)  # In years
    job_type = Column(String(50), nullable=True)  # Full-time, Part-time, Contract, etc.
    remote_option = Column(Boolean, default=False, nullable=False)
    application_deadline = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Foreign keys
    category_id = Column(String(36), ForeignKey('job_categories.id'), nullable=True)
    created_by = Column(String(36), ForeignKey('users.id'), nullable=False)
    
    # Relationships
    category = relationship("JobCategory", back_populates="jobs")
    creator = relationship("User", backref="created_jobs")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    skills = relationship("JobSkill", back_populates="job", cascade="all, delete-orphan")
    
    # JSON fields
    _meta_data = Column('meta_data', Text, nullable=True)
    
    def __init__(self, id: str, title: str, company: str, description: str, created_by: str, **kwargs):
        """Initialize Job instance."""
        self.id = id
        self.title = title
        self.company = company
        self.description = description
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
    
    def to_dict(self, include_applications: bool = False) -> Dict:
        """Convert job to dictionary representation."""
        result = {
            'id': self.id,
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'description': self.description,
            'requirements': self.requirements,
            'responsibilities': self.responsibilities,
            'salary_min': self.salary_min,
            'salary_max': self.salary_max,
            'experience_required': self.experience_required,
            'job_type': self.job_type,
            'remote_option': self.remote_option,
            'application_deadline': self.application_deadline.isoformat() if self.application_deadline else None,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'category': self.category.to_dict() if self.category else None,
            'skills': [skill.to_dict() for skill in self.skills] if self.skills else [],
            'meta_data': self.meta_data
        }
        
        if include_applications:
            result['applications'] = [app.to_dict() for app in self.applications]
        
        return result


class JobSkill(db.Model):
    """Model for skills required for a job."""
    
    __tablename__ = 'job_skills'
    
    id = Column(String(36), primary_key=True)
    job_id = Column(String(36), ForeignKey('jobs.id'), nullable=False)
    skill_name = Column(String(100), nullable=False)
    importance = Column(Integer, default=1, nullable=False)  # 1-5 scale
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    job = relationship("Job", back_populates="skills")
    
    def __init__(self, id: str, job_id: str, skill_name: str, importance: int = 1):
        """Initialize JobSkill instance."""
        self.id = id
        self.job_id = job_id
        self.skill_name = skill_name
        self.importance = importance
    
    def to_dict(self) -> Dict:
        """Convert job skill to dictionary representation."""
        return {
            'id': self.id,
            'job_id': self.job_id,
            'skill_name': self.skill_name,
            'importance': self.importance,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }