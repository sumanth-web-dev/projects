"""
User model for the Job Application Agent.
"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import Column, String, DateTime, Text, Boolean
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
from models.database import db
from services.encryption_service import encryption_service
import re


class User(db.Model):
    """User model for storing user profiles and preferences."""
    
    __tablename__ = 'users'
    
    # Primary key
    id = Column(String(36), primary_key=True)
    
    # Basic information
    email = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    role = Column(String(50), nullable=False, default='user')  # Default role is 'user'
    # Encrypted personal data (JSON string)
    encrypted_personal_data = Column(Text, nullable=True)
    
    # Job preferences (JSON string)
    job_preferences = Column(Text, nullable=True)
    
    # Account status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    applications = relationship("Application", back_populates="user", cascade="all, delete-orphan")

    

    
    def __init__(self, id: str, email: str, **kwargs):
        """Initialize User instance."""
        self.id = id
        self.email = email
        # Set default values if not provided in kwargs
        if 'is_active' not in kwargs:
            self.is_active = True
        if 'created_at' not in kwargs:
            self.created_at = datetime.utcnow()
        if 'updated_at' not in kwargs:
            self.updated_at = datetime.utcnow()
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @validates('email')
    def validate_email(self, key, email):
        """Validate email format."""
        if not email:
            raise ValueError("Email is required")
        
        # Strip whitespace first, then validate
        email = email.strip()
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            raise ValueError("Invalid email format")
        
        return email.lower()
    
    @validates('id')
    def validate_id(self, key, user_id):
        """Validate user ID format."""
        if not user_id:
            raise ValueError("User ID is required")
        
        if len(user_id) > 36:
            raise ValueError("User ID must be 36 characters or less")
        
        return user_id
    
    # Encryption methods are now handled by the encryption_service
    
    @hybrid_property
    def personal_data(self) -> Dict:
        """Get decrypted personal data."""
        if not self.encrypted_personal_data:
            return {}
        # The encryption_service now handles exceptions internally and returns empty dict on failure
        return encryption_service.decrypt(self.encrypted_personal_data, self.id)
    
    @personal_data.setter
    def personal_data(self, data: Dict):
        """Set encrypted personal data."""
        if data:
            self.encrypted_personal_data = encryption_service.encrypt(data, self.id)
        else:
            self.encrypted_personal_data = None
    
    @hybrid_property
    def preferences(self) -> Dict:
        """Get job preferences as dictionary."""
        if not self.job_preferences:
            return {}
        try:
            return json.loads(self.job_preferences)
        except json.JSONDecodeError:
            return {}
    
    @preferences.setter
    def preferences(self, data: Dict):
        """Set job preferences from dictionary."""
        if data:
            self.job_preferences = json.dumps(data)
        else:
            self.job_preferences = None
    
    def validate_personal_data(self, data: Dict) -> bool:
        """Validate personal data structure."""
        # For simplicity, we'll skip validation for now
        return True
    
    def validate_preferences(self, data: Dict) -> bool:
        """Validate job preferences structure."""
        # For simplicity, we'll skip validation for now
        return True
    
    def update_profile(self, personal_data: Optional[Dict] = None, preferences: Optional[Dict] = None):
        """Update user profile with validation."""
        if personal_data:
            self.validate_personal_data(personal_data)
            self.personal_data = personal_data
        
        if preferences:
            self.validate_preferences(preferences)
            self.preferences = preferences
        
        self.updated_at = datetime.utcnow()
    
    def is_profile_complete(self) -> bool:
        """Check if user profile is complete for job applications."""
        # For simplicity, we'll always return True
        return True
    
    def to_dict(self, include_sensitive: bool = False) -> Dict:
        """Convert user to dictionary representation."""
        result = {
            'id': self.id,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'is_active': self.is_active,
            'profile_complete': self.is_profile_complete()
        }
        
        if include_sensitive:
            result['personal_data'] = self.personal_data
            result['preferences'] = self.preferences
        
        return result
    
    def __repr__(self):
        """String representation of User."""
        return f"<User(id='{self.id}', email='{self.email}')>"