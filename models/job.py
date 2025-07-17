"""
Job model for the Job Application Agent.
"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import Column, String, DateTime, Text, Float, Integer, Boolean, Index
from sqlalchemy.orm import relationship, validates
from sqlalchemy.ext.hybrid import hybrid_property
from models.database import db
import re


class Job(db.Model):
    """Job model for storing job listings and details."""
    
    __tablename__ = 'jobs'
    
    # Primary key
    id = Column(String(36), primary_key=True)
    
    # Basic job information
    title = Column(String(255), nullable=False, index=True)
    company = Column(String(255), nullable=False, index=True)
    location = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=True)
    
    # Job requirements and details (JSON string)
    requirements_json = Column(Text, nullable=True)
    
    # Salary information
    salary_min = Column(Float, nullable=True)
    salary_max = Column(Float, nullable=True)
    salary_currency = Column(String(3), default='USD', nullable=False)
    
    # Source information
    source_website = Column(String(100), nullable=False, index=True)
    source_url = Column(String(1000), nullable=False, unique=True)
    external_id = Column(String(255), nullable=True, index=True)
    
    # Dates
    posted_date = Column(DateTime, nullable=True)
    discovered_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=True)
    
    # Job status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    job_type = Column(String(50), nullable=True)  # full-time, part-time, contract, etc.
    experience_level = Column(String(50), nullable=True)  # entry, mid, senior, etc.
    remote_option = Column(String(20), nullable=True)  # remote, hybrid, onsite
    
    # Application tracking
    application_count = Column(Integer, default=0, nullable=False)
    
    # Relationships
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    
    # Indexes for better query performance
    __table_args__ = (
        Index('idx_job_search', 'title', 'company', 'location'),
        Index('idx_job_source', 'source_website', 'external_id'),
        Index('idx_job_dates', 'posted_date', 'discovered_at'),
    )
    
    def __init__(self, id: str, title: str, company: str, source_website: str, source_url: str, **kwargs):
        """Initialize Job instance."""
        self.id = id
        self.title = title
        self.company = company
        self.source_website = source_website
        self.source_url = source_url
        
        # Set default values if not provided in kwargs
        if 'is_active' not in kwargs:
            self.is_active = True
        if 'application_count' not in kwargs:
            self.application_count = 0
        if 'salary_currency' not in kwargs:
            self.salary_currency = 'USD'
            
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @validates('title')
    def validate_title(self, key, title):
        """Validate job title."""
        if not title or not title.strip():
            raise ValueError("Job title is required")
        
        if len(title) > 255:
            raise ValueError("Job title must be 255 characters or less")
        
        return title.strip()
    
    @validates('company')
    def validate_company(self, key, company):
        """Validate company name."""
        if not company or not company.strip():
            raise ValueError("Company name is required")
        
        if len(company) > 255:
            raise ValueError("Company name must be 255 characters or less")
        
        return company.strip()
    
    @validates('source_website')
    def validate_source_website(self, key, source_website):
        """Validate source website."""
        if not source_website or not source_website.strip():
            raise ValueError("Source website is required")
        
        valid_sources = ['linkedin', 'indeed', 'glassdoor', 'monster', 'ziprecruiter', 'other']
        if source_website.lower() not in valid_sources:
            raise ValueError(f"Source website must be one of: {', '.join(valid_sources)}")
        
        return source_website.lower()
    
    @validates('source_url')
    def validate_source_url(self, key, source_url):
        """Validate source URL."""
        if not source_url or not source_url.strip():
            raise ValueError("Source URL is required")
        
        # Basic URL validation
        url_pattern = r'^https?://.+'
        if not re.match(url_pattern, source_url):
            raise ValueError("Source URL must be a valid HTTP/HTTPS URL")
        
        if len(source_url) > 1000:
            raise ValueError("Source URL must be 1000 characters or less")
        
        return source_url.strip()
    
    @validates('salary_min', 'salary_max')
    def validate_salary(self, key, salary):
        """Validate salary values."""
        if salary is not None:
            if salary < 0:
                raise ValueError("Salary values must be positive")
            if salary > 10000000:  # 10 million cap
                raise ValueError("Salary value seems unrealistic")
        return salary
    
    @validates('salary_currency')
    def validate_currency(self, key, currency):
        """Validate currency code."""
        if currency:
            valid_currencies = ['USD', 'EUR', 'GBP', 'CAD', 'AUD']
            if currency.upper() not in valid_currencies:
                raise ValueError(f"Currency must be one of: {', '.join(valid_currencies)}")
            return currency.upper()
        return 'USD'
    
    @hybrid_property
    def requirements(self) -> List[str]:
        """Get job requirements as list."""
        if not self.requirements_json:
            return []
        try:
            data = json.loads(self.requirements_json)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []
    
    @requirements.setter
    def requirements(self, requirements: List[str]):
        """Set job requirements from list."""
        if requirements and isinstance(requirements, list):
            self.requirements_json = json.dumps(requirements)
        else:
            self.requirements_json = None
    
    @hybrid_property
    def salary_range(self) -> Optional[Dict]:
        """Get salary range as dictionary."""
        if self.salary_min is not None or self.salary_max is not None:
            return {
                'min': self.salary_min,
                'max': self.salary_max,
                'currency': self.salary_currency
            }
        return None
    
    def set_salary_range(self, min_salary: Optional[float], max_salary: Optional[float], currency: str = 'USD'):
        """Set salary range with validation."""
        if min_salary is not None and max_salary is not None:
            if min_salary > max_salary:
                raise ValueError("Minimum salary cannot be greater than maximum salary")
        
        self.salary_min = min_salary
        self.salary_max = max_salary
        self.salary_currency = currency
    
    def matches_criteria(self, criteria: Dict) -> bool:
        """Check if job matches search criteria."""
        # Title matching
        if 'keywords' in criteria:
            keywords = criteria['keywords']
            if isinstance(keywords, str):
                keywords = [keywords]
            
            title_lower = self.title.lower()
            description_lower = (self.description or '').lower()
            
            for keyword in keywords:
                if keyword.lower() not in title_lower and keyword.lower() not in description_lower:
                    return False
        
        # Location matching
        if 'locations' in criteria and self.location:
            locations = criteria['locations']
            if isinstance(locations, str):
                locations = [locations]
            
            job_location_lower = self.location.lower()
            location_match = any(loc.lower() in job_location_lower for loc in locations)
            if not location_match:
                return False
        
        # Salary matching
        if 'salary_min' in criteria and self.salary_max:
            if self.salary_max < criteria['salary_min']:
                return False
        
        if 'salary_max' in criteria and self.salary_min:
            if self.salary_min > criteria['salary_max']:
                return False
        
        # Experience level matching
        if 'experience_levels' in criteria and self.experience_level:
            if self.experience_level not in criteria['experience_levels']:
                return False
        
        # Remote option matching
        if 'remote_options' in criteria and self.remote_option:
            if self.remote_option not in criteria['remote_options']:
                return False
        
        return True
    
    def extract_keywords(self) -> List[str]:
        """Extract keywords from job title and description."""
        text = f"{self.title} {self.description or ''}"
        
        # Simple keyword extraction (can be enhanced with NLP)
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        
        # Filter out common words
        stop_words = {'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had', 'her', 'was', 'one', 'our', 'out', 'day', 'get', 'has', 'him', 'his', 'how', 'man', 'new', 'now', 'old', 'see', 'two', 'way', 'who', 'boy', 'did', 'its', 'let', 'put', 'say', 'she', 'too', 'use'}
        
        keywords = [word for word in set(words) if word not in stop_words and len(word) > 2]
        return sorted(keywords)
    
    def is_expired(self) -> bool:
        """Check if job posting has expired."""
        if self.expires_at:
            return datetime.utcnow() > self.expires_at
        return False
    
    def days_since_posted(self) -> Optional[int]:
        """Get number of days since job was posted."""
        if self.posted_date:
            delta = datetime.utcnow() - self.posted_date
            return delta.days
        return None
    
    def increment_application_count(self):
        """Increment the application count for this job."""
        self.application_count += 1
    
    def to_dict(self, include_description: bool = True) -> Dict:
        """Convert job to dictionary representation."""
        result = {
            'id': self.id,
            'title': self.title,
            'company': self.company,
            'location': self.location,
            'source_website': self.source_website,
            'source_url': self.source_url,
            'external_id': self.external_id,
            'posted_date': self.posted_date.isoformat() if self.posted_date else None,
            'discovered_at': self.discovered_at.isoformat() if self.discovered_at else None,
            'expires_at': self.expires_at.isoformat() if self.expires_at else None,
            'is_active': self.is_active,
            'job_type': self.job_type,
            'experience_level': self.experience_level,
            'remote_option': self.remote_option,
            'application_count': self.application_count,
            'salary_range': self.salary_range,
            'requirements': self.requirements,
            'is_expired': self.is_expired(),
            'days_since_posted': self.days_since_posted()
        }
        
        if include_description:
            result['description'] = self.description
        
        return result
    
    def __repr__(self):
        """String representation of Job."""
        return f"<Job(id='{self.id}', title='{self.title}', company='{self.company}')>"