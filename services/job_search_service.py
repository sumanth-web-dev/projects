"""
Job search service for advanced job searching and filtering.

This module provides functionality for searching and filtering jobs based on
various criteria such as keywords, location, salary range, experience level, etc.
"""
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy import or_, and_, func, text
from models.database import db
from models.job import Job, JobCategory, JobSkill
from models.skill import Skill

# Set up logging
logger = logging.getLogger(__name__)


class JobSearchService:
    """Service for advanced job searching and filtering."""
    
    def __init__(self, app=None):
        """Initialize the job search service.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self.default_limit = 20
        self.max_limit = 100
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the job search service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self.default_limit = app.config.get('DEFAULT_SEARCH_LIMIT', 20)
        self.max_limit = app.config.get('MAX_SEARCH_LIMIT', 100)
    
    def search_jobs(self, query_params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for jobs based on query parameters.
        
        Args:
            query_params: Dictionary of search parameters
            
        Returns:
            Dict[str, Any]: Search results and metadata
        """
        try:
            # Extract search parameters
            keywords = query_params.get('keywords', '')
            location = query_params.get('location', '')
            category_id = query_params.get('category_id')
            min_salary = query_params.get('min_salary')
            max_salary = query_params.get('max_salary')
            experience_level = query_params.get('experience_level')
            job_type = query_params.get('job_type')
            remote_option = query_params.get('remote_option')
            skills = query_params.get('skills', [])
            company = query_params.get('company', '')
            
            # Pagination parameters
            page = int(query_params.get('page', 1))
            limit = min(int(query_params.get('limit', self.default_limit)), self.max_limit)
            offset = (page - 1) * limit
            
            # Sorting parameters
            sort_by = query_params.get('sort_by', 'created_at')
            sort_order = query_params.get('sort_order', 'desc')
            
            # Build base query
            query = Job.query.filter(Job.is_active == True)
            
            # Apply filters
            if keywords:
                keyword_filter = or_(
                    Job.title.ilike(f'%{keywords}%'),
                    Job.description.ilike(f'%{keywords}%'),
                    Job.requirements.ilike(f'%{keywords}%'),
                    Job.responsibilities.ilike(f'%{keywords}%')
                )
                query = query.filter(keyword_filter)
            
            if location:
                query = query.filter(Job.location.ilike(f'%{location}%'))
            
            if category_id:
                query = query.filter(Job.category_id == category_id)
            
            if min_salary is not None:
                query = query.filter(Job.salary_min >= min_salary)
            
            if max_salary is not None:
                query = query.filter(Job.salary_max <= max_salary)
            
            if experience_level is not None:
                query = query.filter(Job.experience_required <= experience_level)
            
            if job_type:
                query = query.filter(Job.job_type == job_type)
            
            if remote_option is not None:
                query = query.filter(Job.remote_option == remote_option)
            
            if company:
                query = query.filter(Job.company.ilike(f'%{company}%'))
            
            # Filter by skills
            if skills:
                # Join with JobSkill and filter by skill names
                query = query.join(JobSkill).join(Skill).filter(
                    Skill.name.in_(skills)
                ).group_by(Job.id).having(
                    func.count(JobSkill.id) == len(skills)
                )
            
            # Count total results before pagination
            total_count = query.count()
            
            # Apply sorting
            if sort_by == 'salary':
                if sort_order == 'asc':
                    query = query.order_by(Job.salary_min.asc())
                else:
                    query = query.order_by(Job.salary_max.desc())
            elif sort_by == 'experience':
                if sort_order == 'asc':
                    query = query.order_by(Job.experience_required.asc())
                else:
                    query = query.order_by(Job.experience_required.desc())
            elif sort_by == 'created_at':
                if sort_order == 'asc':
                    query = query.order_by(Job.created_at.asc())
                else:
                    query = query.order_by(Job.created_at.desc())
            else:
                # Default sort by relevance (for keyword searches) or created_at
                query = query.order_by(Job.created_at.desc())
            
            # Apply pagination
            query = query.offset(offset).limit(limit)
            
            # Execute query
            jobs = query.all()
            
            # Calculate total pages
            total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
            
            # Prepare results
            results = {
                'jobs': [job.to_dict() for job in jobs],
                'metadata': {
                    'total_count': total_count,
                    'page': page,
                    'limit': limit,
                    'total_pages': total_pages,
                    'has_next': page < total_pages,
                    'has_prev': page > 1
                }
            }
            
            return results
            
        except Exception as e:
            logger.error(f"Error searching jobs: {str(e)}")
            return {
                'jobs': [],
                'metadata': {
                    'total_count': 0,
                    'page': 1,
                    'limit': self.default_limit,
                    'total_pages': 0,
                    'has_next': False,
                    'has_prev': False,
                    'error': str(e)
                }
            }
    
    def get_trending_searches(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get trending job searches.
        
        Args:
            limit: Maximum number of trending searches to return
            
        Returns:
            List[Dict[str, Any]]: List of trending searches with counts
        """
        try:
            # This would typically query analytics data for trending searches
            # For this example, we'll return placeholder data
            return [
                {'term': 'software engineer', 'count': 1250},
                {'term': 'data scientist', 'count': 980},
                {'term': 'product manager', 'count': 750},
                {'term': 'remote', 'count': 620},
                {'term': 'entry level', 'count': 580},
                {'term': 'full stack developer', 'count': 520},
                {'term': 'machine learning', 'count': 480},
                {'term': 'internship', 'count': 450},
                {'term': 'part time', 'count': 420},
                {'term': 'frontend developer', 'count': 400}
            ][:limit]
        except Exception as e:
            logger.error(f"Error getting trending searches: {str(e)}")
            return []
    
    def get_job_categories(self) -> List[Dict[str, Any]]:
        """Get all job categories.
        
        Returns:
            List[Dict[str, Any]]: List of job categories
        """
        try:
            categories = JobCategory.query.all()
            return [category.to_dict() for category in categories]
        except Exception as e:
            logger.error(f"Error getting job categories: {str(e)}")
            return []
    
    def get_job_types(self) -> List[str]:
        """Get all job types.
        
        Returns:
            List[str]: List of job types
        """
        try:
            # Query distinct job types
            result = db.session.query(Job.job_type).distinct().all()
            return [r[0] for r in result if r[0]]
        except Exception as e:
            logger.error(f"Error getting job types: {str(e)}")
            return []
    
    def get_popular_skills(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get popular skills from job listings.
        
        Args:
            limit: Maximum number of skills to return
            
        Returns:
            List[Dict[str, Any]]: List of popular skills with counts
        """
        try:
            # Query skills and their frequency in job listings
            result = db.session.query(
                Skill.id,
                Skill.name,
                func.count(JobSkill.id).label('count')
            ).join(JobSkill).group_by(Skill.id).order_by(text('count DESC')).limit(limit).all()
            
            return [{'id': r[0], 'name': r[1], 'count': r[2]} for r in result]
        except Exception as e:
            logger.error(f"Error getting popular skills: {str(e)}")
            return []


# Create a singleton instance
job_search_service = JobSearchService()