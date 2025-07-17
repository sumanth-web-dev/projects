"""
Job search service for finding and filtering job listings.

This module provides functionality for searching jobs across different platforms,
filtering results based on user preferences, and detecting duplicate job listings.
"""
import uuid
import logging
import datetime
from typing import Dict, List, Optional, Tuple, Any, Set
from sqlalchemy import or_, and_, func
from sqlalchemy.exc import SQLAlchemyError
from models.database import db
from models.job import Job
from models.user import User

# Set up logging
logger = logging.getLogger(__name__)


class JobSearchService:
    """Service for searching and filtering job listings."""
    
    def __init__(self, app=None):
        """Initialize the job search service.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the job search service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
    
    def search_jobs(self, criteria: Dict) -> Tuple[bool, List[Job], str]:
        """Search for jobs based on criteria.
        
        Args:
            criteria: Dictionary containing search parameters
                - keywords: List[str] or str - Keywords to search in title/description
                - locations: List[str] or str - Locations to search
                - job_types: List[str] or str - Job types (full-time, part-time, etc.)
                - experience_levels: List[str] or str - Experience levels
                - remote_options: List[str] or str - Remote work options
                - salary_min: float - Minimum salary
                - salary_max: float - Maximum salary
                - sources: List[str] or str - Source websites to search
                - days_old: int - Maximum age of job postings in days
                - limit: int - Maximum number of results to return
                - offset: int - Offset for pagination
                
        Returns:
            Tuple[bool, List[Job], str]: (success, job_list, message)
        """
        try:
            # Start with a base query
            query = Job.query.filter(Job.is_active == True)
            
            # Apply filters based on criteria
            query = self._apply_search_filters(query, criteria)
            
            # Apply sorting - default to newest first
            sort_by = criteria.get('sort_by', 'date')
            if sort_by == 'date':
                query = query.order_by(Job.discovered_at.desc())
            elif sort_by == 'relevance':
                # For relevance sorting, we would ideally use full-text search
                # This is a simplified version that prioritizes keyword matches in title
                if 'keywords' in criteria:
                    keywords = criteria['keywords']
                    if isinstance(keywords, str):
                        keywords = [keywords]
                    
                    # This is a simplified relevance sort - in production, use a more sophisticated approach
                    # like full-text search or a scoring algorithm
                    for keyword in keywords:
                        query = query.order_by(
                            func.case(
                                [(func.lower(Job.title).contains(keyword.lower()), 1)],
                                else_=2
                            )
                        )
            
            # Apply pagination
            limit = int(criteria.get('limit', 100))
            offset = int(criteria.get('offset', 0))
            query = query.limit(limit).offset(offset)
            
            # Execute query
            jobs = query.all()
            
            return True, jobs, f"Found {len(jobs)} jobs matching criteria"
            
        except Exception as e:
            logger.error(f"Error searching jobs: {str(e)}")
            return False, [], f"Error searching jobs: {str(e)}"
    
    def filter_jobs(self, jobs: List[Job], preferences: Dict) -> List[Job]:
        """Filter jobs based on user preferences.
        
        Args:
            jobs: List of jobs to filter
            preferences: User preferences dictionary
                
        Returns:
            List[Job]: Filtered list of jobs
        """
        if not preferences:
            return jobs
        
        filtered_jobs = []
        
        for job in jobs:
            if job.matches_criteria(preferences):
                filtered_jobs.append(job)
        
        return filtered_jobs
    
    def detect_duplicates(self, jobs: List[Job]) -> List[Job]:
        """Detect and consolidate duplicate job listings.
        
        Args:
            jobs: List of jobs to check for duplicates
                
        Returns:
            List[Job]: Deduplicated list of jobs
        """
        # Use a dictionary to track unique jobs
        unique_jobs = {}
        
        for job in jobs:
            # Create a key based on company and title (normalized)
            key = f"{job.company.lower()}:{job.title.lower()}"
            
            # If we haven't seen this job before, add it
            if key not in unique_jobs:
                unique_jobs[key] = job
            else:
                # If we have seen it, keep the one with more information
                existing_job = unique_jobs[key]
                
                # Prefer jobs with descriptions
                if not existing_job.description and job.description:
                    unique_jobs[key] = job
                # Prefer jobs with salary information
                elif not existing_job.salary_range and job.salary_range:
                    unique_jobs[key] = job
                # Prefer more recently discovered jobs
                elif job.discovered_at > existing_job.discovered_at:
                    unique_jobs[key] = job
        
        return list(unique_jobs.values())
    
    def get_job_by_id(self, job_id: str) -> Optional[Job]:
        """Get a job by ID.
        
        Args:
            job_id: The job ID to look up
            
        Returns:
            Optional[Job]: The job if found, None otherwise
        """
        try:
            return Job.query.get(job_id)
        except Exception as e:
            logger.error(f"Error retrieving job: {str(e)}")
            return None
    
    def get_job_by_url(self, source_url: str) -> Optional[Job]:
        """Get a job by source URL.
        
        Args:
            source_url: The source URL to look up
            
        Returns:
            Optional[Job]: The job if found, None otherwise
        """
        try:
            return Job.query.filter_by(source_url=source_url).first()
        except Exception as e:
            logger.error(f"Error retrieving job by URL: {str(e)}")
            return None
    
    def save_job(self, job_data: Dict) -> Tuple[bool, Optional[Job], str]:
        """Save a new job or update an existing one.
        
        Args:
            job_data: Dictionary containing job data
                
        Returns:
            Tuple[bool, Optional[Job], str]: (success, job, message)
        """
        try:
            # Check if job already exists by URL
            existing_job = None
            if 'source_url' in job_data:
                existing_job = self.get_job_by_url(job_data['source_url'])
            
            if existing_job:
                # Update existing job
                for key, value in job_data.items():
                    if hasattr(existing_job, key):
                        setattr(existing_job, key, value)
                
                db.session.commit()
                return True, existing_job, "Job updated successfully"
            else:
                # Create new job
                if 'id' not in job_data:
                    job_data['id'] = str(uuid.uuid4())
                
                # Ensure required fields are present
                required_fields = ['title', 'company', 'source_website', 'source_url']
                for field in required_fields:
                    if field not in job_data:
                        return False, None, f"Missing required field: {field}"
                
                new_job = Job(**job_data)
                db.session.add(new_job)
                db.session.commit()
                return True, new_job, "Job created successfully"
                
        except ValueError as e:
            db.session.rollback()
            logger.error(f"Validation error saving job: {str(e)}")
            return False, None, f"Validation error: {str(e)}"
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error saving job: {str(e)}")
            return False, None, f"Error saving job: {str(e)}"
    
    def mark_job_inactive(self, job_id: str) -> Tuple[bool, str]:
        """Mark a job as inactive.
        
        Args:
            job_id: The job ID
                
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            job = self.get_job_by_id(job_id)
            if not job:
                return False, "Job not found"
            
            job.is_active = False
            db.session.commit()
            return True, "Job marked as inactive"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error marking job inactive: {str(e)}")
            return False, f"Error marking job inactive: {str(e)}"
    
    def get_similar_jobs(self, job_id: str, limit: int = 5) -> List[Job]:
        """Get jobs similar to the specified job.
        
        Args:
            job_id: The job ID to find similar jobs for
            limit: Maximum number of similar jobs to return
                
        Returns:
            List[Job]: List of similar jobs
        """
        try:
            job = self.get_job_by_id(job_id)
            if not job:
                return []
            
            # Extract keywords from job title and description
            keywords = job.extract_keywords()
            
            if not keywords:
                return []
            
            # Build query to find jobs with similar keywords
            query = Job.query.filter(Job.id != job_id, Job.is_active == True)
            
            # Add title similarity conditions
            title_conditions = []
            for keyword in keywords[:5]:  # Limit to top 5 keywords for performance
                title_conditions.append(func.lower(Job.title).contains(keyword.lower()))
            
            if title_conditions:
                query = query.filter(or_(*title_conditions))
            
            # Add company filter - same company
            query = query.filter(func.lower(Job.company) == func.lower(job.company))
            
            # Limit results
            similar_jobs = query.limit(limit).all()
            
            return similar_jobs
            
        except Exception as e:
            logger.error(f"Error finding similar jobs: {str(e)}")
            return []
    
    def _apply_search_filters(self, query, criteria: Dict):
        """Apply search filters to the query based on criteria.
        
        Args:
            query: SQLAlchemy query object
            criteria: Search criteria dictionary
                
        Returns:
            SQLAlchemy query with filters applied
        """
        # Filter by keywords
        if 'keywords' in criteria:
            keywords = criteria['keywords']
            if isinstance(keywords, str):
                keywords = [keywords]
            
            keyword_conditions = []
            for keyword in keywords:
                keyword_conditions.append(func.lower(Job.title).contains(keyword.lower()))
                keyword_conditions.append(func.lower(Job.description).contains(keyword.lower()))
            
            if keyword_conditions:
                query = query.filter(or_(*keyword_conditions))
        
        # Filter by locations
        if 'locations' in criteria:
            locations = criteria['locations']
            if isinstance(locations, str):
                locations = [locations]
            
            location_conditions = []
            for location in locations:
                location_conditions.append(func.lower(Job.location).contains(location.lower()))
            
            if location_conditions:
                query = query.filter(or_(*location_conditions))
        
        # Filter by job types
        if 'job_types' in criteria:
            job_types = criteria['job_types']
            if isinstance(job_types, str):
                job_types = [job_types]
            
            query = query.filter(func.lower(Job.job_type).in_([jt.lower() for jt in job_types]))
        
        # Filter by experience levels
        if 'experience_levels' in criteria:
            exp_levels = criteria['experience_levels']
            if isinstance(exp_levels, str):
                exp_levels = [exp_levels]
            
            query = query.filter(func.lower(Job.experience_level).in_([el.lower() for el in exp_levels]))
        
        # Filter by remote options
        if 'remote_options' in criteria:
            remote_options = criteria['remote_options']
            if isinstance(remote_options, str):
                remote_options = [remote_options]
            
            query = query.filter(func.lower(Job.remote_option).in_([ro.lower() for ro in remote_options]))
        
        # Filter by salary range
        if 'salary_min' in criteria:
            query = query.filter(or_(
                Job.salary_max >= float(criteria['salary_min']),
                Job.salary_min >= float(criteria['salary_min'])
            ))
        
        if 'salary_max' in criteria:
            query = query.filter(or_(
                Job.salary_min <= float(criteria['salary_max']),
                Job.salary_max <= float(criteria['salary_max'])
            ))
        
        # Filter by source websites
        if 'sources' in criteria:
            sources = criteria['sources']
            if isinstance(sources, str):
                sources = [sources]
            
            query = query.filter(func.lower(Job.source_website).in_([s.lower() for s in sources]))
        
        # Filter by posting date
        if 'days_old' in criteria:
            days_old = int(criteria['days_old'])
            cutoff_date = datetime.datetime.utcnow() - datetime.timedelta(days=days_old)
            
            # Check both posted_date and discovered_at
            query = query.filter(or_(
                and_(Job.posted_date != None, Job.posted_date >= cutoff_date),
                Job.discovered_at >= cutoff_date
            ))
        
        return query


# Create a singleton instance
job_search_service = JobSearchService()