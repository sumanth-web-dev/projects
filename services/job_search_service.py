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
        # Dictionary to store active search tasks
        self.active_searches = {}
        
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
                - job_titles: List[str] - Preferred job titles
                - locations: List[str] - Preferred locations
                - remote_only: bool - Whether to only include remote jobs
                - salary_min: float - Minimum acceptable salary
                - salary_max: float - Maximum acceptable salary
                - job_types: List[str] - Preferred job types (full-time, part-time, etc.)
                - experience_levels: List[str] - Preferred experience levels
                - excluded_companies: List[str] - Companies to exclude
                - excluded_keywords: List[str] - Keywords to exclude from job title/description
                
        Returns:
            List[Job]: Filtered list of jobs
        """
        if not preferences:
            return jobs
        
        filtered_jobs = []
        
        for job in jobs:
            # Skip inactive jobs
            if not job.is_active:
                continue
                
            # Skip expired jobs if preference is set
            if preferences.get('exclude_expired', True) and job.is_expired():
                continue
                
            # Check for excluded companies
            if 'excluded_companies' in preferences and job.company:
                company_lower = job.company.lower()
                if any(company.lower() in company_lower for company in preferences['excluded_companies']):
                    continue
            
            # Check for excluded keywords
            if 'excluded_keywords' in preferences and (job.title or job.description):
                title_lower = job.title.lower() if job.title else ""
                desc_lower = job.description.lower() if job.description else ""
                combined_text = f"{title_lower} {desc_lower}"
                
                if any(keyword.lower() in combined_text for keyword in preferences['excluded_keywords']):
                    continue
            
            # Use the job's built-in criteria matching for other filters
            if job.matches_criteria(preferences):
                filtered_jobs.append(job)
        
        return filtered_jobs
    
    def detect_duplicates(self, jobs: List[Job]) -> List[Job]:
        """Detect and consolidate duplicate job listings.
        
        This algorithm identifies duplicate job listings based on multiple criteria:
        1. Exact URL matches (highest confidence)
        2. Company + title matches (high confidence)
        3. Company + location + similar title (medium confidence)
        
        When duplicates are found, the algorithm keeps the job with the most complete information.
        
        Args:
            jobs: List of jobs to check for duplicates
                
        Returns:
            List[Job]: Deduplicated list of jobs
        """
        if not jobs:
            return []
            
        # First pass: Group by URL (highest confidence match)
        url_groups = {}
        for job in jobs:
            if job.source_url:
                url_key = job.source_url.lower()
                if url_key not in url_groups:
                    url_groups[url_key] = []
                url_groups[url_key].append(job)
        
        # Second pass: Group by company + title (high confidence match)
        company_title_groups = {}
        for job in jobs:
            if job.company and job.title:
                # Normalize company and title
                company = job.company.lower().strip()
                title = job.title.lower().strip()
                key = f"{company}:{title}"
                
                if key not in company_title_groups:
                    company_title_groups[key] = []
                company_title_groups[key].append(job)
        
        # Third pass: Group by company + location + similar title (medium confidence)
        company_location_groups = {}
        for job in jobs:
            if job.company and job.location:
                # Normalize company and location
                company = job.company.lower().strip()
                location = job.location.lower().strip()
                key = f"{company}:{location}"
                
                if key not in company_location_groups:
                    company_location_groups[key] = []
                company_location_groups[key].append(job)
        
        # Consolidate duplicates, prioritizing jobs with more information
        unique_jobs = {}
        processed_ids = set()
        
        # Process URL groups first (highest confidence)
        for url_group in url_groups.values():
            if len(url_group) > 1:
                best_job = self._select_best_job(url_group)
                unique_jobs[best_job.id] = best_job
                processed_ids.update(job.id for job in url_group)
            else:
                job = url_group[0]
                unique_jobs[job.id] = job
                processed_ids.add(job.id)
        
        # Process company+title groups next
        for group in company_title_groups.values():
            # Filter out already processed jobs
            unprocessed = [job for job in group if job.id not in processed_ids]
            if len(unprocessed) > 1:
                best_job = self._select_best_job(unprocessed)
                unique_jobs[best_job.id] = best_job
                processed_ids.update(job.id for job in unprocessed)
            elif len(unprocessed) == 1:
                job = unprocessed[0]
                unique_jobs[job.id] = job
                processed_ids.add(job.id)
        
        # Process company+location groups last (lowest confidence)
        for group in company_location_groups.values():
            # Filter out already processed jobs
            unprocessed = [job for job in group if job.id not in processed_ids]
            if len(unprocessed) > 1:
                # For this lower confidence match, only consider them duplicates if titles are similar
                title_groups = self._group_by_similar_titles(unprocessed)
                for title_group in title_groups:
                    if len(title_group) > 1:
                        best_job = self._select_best_job(title_group)
                        unique_jobs[best_job.id] = best_job
                        processed_ids.update(job.id for job in title_group)
                    elif len(title_group) == 1:
                        job = title_group[0]
                        unique_jobs[job.id] = job
                        processed_ids.add(job.id)
            elif len(unprocessed) == 1:
                job = unprocessed[0]
                unique_jobs[job.id] = job
                processed_ids.add(job.id)
        
        # Add any remaining jobs that weren't processed
        for job in jobs:
            if job.id not in processed_ids:
                unique_jobs[job.id] = job
        
        return list(unique_jobs.values())
    
    def _select_best_job(self, jobs: List[Job]) -> Job:
        """Select the best job from a list of potential duplicates.
        
        Args:
            jobs: List of potential duplicate jobs
                
        Returns:
            Job: The job with the most complete information
        """
        if not jobs:
            raise ValueError("Cannot select best job from empty list")
        
        if len(jobs) == 1:
            return jobs[0]
        
        # Start with the most recently discovered job
        best_job = max(jobs, key=lambda j: j.discovered_at)
        
        # Score each job based on completeness of information
        job_scores = {}
        for job in jobs:
            score = 0
            
            # Prefer jobs with descriptions
            if job.description:
                score += 10
                # Longer descriptions are likely more informative
                score += min(10, len(job.description) // 100)
            
            # Prefer jobs with salary information
            if job.salary_range:
                score += 8
            
            # Prefer jobs with requirements
            if job.requirements:
                score += len(job.requirements) * 2
            
            # Prefer jobs with posted_date over just discovered_at
            if job.posted_date:
                score += 5
            
            # Prefer jobs with more complete metadata
            if job.job_type:
                score += 2
            if job.experience_level:
                score += 2
            if job.remote_option:
                score += 2
            
            job_scores[job.id] = score
        
        # Find the job with the highest score
        highest_score = max(job_scores.values())
        best_jobs = [job for job in jobs if job_scores[job.id] == highest_score]
        
        # If multiple jobs have the same score, prefer the most recently discovered one
        if len(best_jobs) > 1:
            return max(best_jobs, key=lambda j: j.discovered_at)
        
        return best_jobs[0]
    
    def _group_by_similar_titles(self, jobs: List[Job]) -> List[List[Job]]:
        """Group jobs by similar titles.
        
        Args:
            jobs: List of jobs to group
                
        Returns:
            List[List[Job]]: List of job groups with similar titles
        """
        if not jobs:
            return []
        
        # Simple implementation using word overlap
        groups = []
        processed = set()
        
        for i, job1 in enumerate(jobs):
            if job1.id in processed:
                continue
                
            group = [job1]
            processed.add(job1.id)
            
            # Get words from the title
            title1_words = set(job1.title.lower().split())
            
            for j, job2 in enumerate(jobs[i+1:], i+1):
                if job2.id in processed:
                    continue
                    
                # Get words from the title
                title2_words = set(job2.title.lower().split())
                
                # Calculate word overlap
                common_words = title1_words.intersection(title2_words)
                
                # If there's significant overlap, consider them similar
                if len(common_words) >= 2 and (len(common_words) / max(len(title1_words), len(title2_words))) > 0.5:
                    group.append(job2)
                    processed.add(job2.id)
            
            groups.append(group)
        
        return groups
    
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
    
    def trigger_search(self, user_id: str, criteria: Dict, preferences: Dict = None) -> Tuple[bool, str, str]:
        """Trigger a job search across configured platforms.
        
        This method initiates an asynchronous job search process across multiple job websites
        based on the provided criteria and user preferences.
        
        Args:
            user_id: The ID of the user initiating the search
            criteria: Dictionary containing search parameters
            preferences: User preferences for filtering results
                
        Returns:
            Tuple[bool, str, str]: (success, search_id, message)
        """
        try:
            # Generate a unique search ID
            search_id = str(uuid.uuid4())
            
            # Store search information
            self.active_searches[search_id] = {
                'user_id': user_id,
                'criteria': criteria,
                'preferences': preferences or {},
                'status': 'pending',
                'created_at': datetime.datetime.utcnow(),
                'results': [],
                'error': None
            }
            
            # In a real implementation, this would trigger background tasks
            # to search across different job platforms using adapters
            
            # For now, we'll simulate by searching the database
            success, jobs, message = self.search_jobs(criteria)
            
            if success:
                # Apply user preferences if provided
                if preferences:
                    jobs = self.filter_jobs(jobs, preferences)
                
                # Update search status
                self.active_searches[search_id]['status'] = 'completed'
                self.active_searches[search_id]['results'] = [job.id for job in jobs]
                self.active_searches[search_id]['completed_at'] = datetime.datetime.utcnow()
                
                return True, search_id, f"Search completed with {len(jobs)} results"
            else:
                # Update search status with error
                self.active_searches[search_id]['status'] = 'failed'
                self.active_searches[search_id]['error'] = message
                self.active_searches[search_id]['completed_at'] = datetime.datetime.utcnow()
                
                return False, search_id, f"Search failed: {message}"
                
        except Exception as e:
            logger.error(f"Error triggering job search: {str(e)}")
            return False, "", f"Error triggering job search: {str(e)}"
    
    def get_search_status(self, search_id: str) -> Tuple[bool, Dict, str]:
        """Get the status of a job search.
        
        Args:
            search_id: The ID of the search to check
                
        Returns:
            Tuple[bool, Dict, str]: (success, status_data, message)
        """
        if search_id not in self.active_searches:
            return False, {}, "Search not found"
        
        search_data = self.active_searches[search_id]
        
        # Create a copy of the search data for the response
        status_data = {
            'search_id': search_id,
            'user_id': search_data['user_id'],
            'status': search_data['status'],
            'created_at': search_data['created_at'].isoformat(),
            'completed_at': search_data['completed_at'].isoformat() if 'completed_at' in search_data else None,
            'result_count': len(search_data['results']),
            'criteria': search_data['criteria']
        }
        
        if search_data['status'] == 'failed' and search_data['error']:
            status_data['error'] = search_data['error']
        
        return True, status_data, f"Search status: {search_data['status']}"
    
    def get_search_results(self, search_id: str, limit: int = 100, offset: int = 0) -> Tuple[bool, List[Job], str]:
        """Get the results of a completed job search.
        
        Args:
            search_id: The ID of the search
            limit: Maximum number of results to return
            offset: Offset for pagination
                
        Returns:
            Tuple[bool, List[Job], str]: (success, jobs, message)
        """
        if search_id not in self.active_searches:
            return False, [], "Search not found"
        
        search_data = self.active_searches[search_id]
        
        if search_data['status'] != 'completed':
            return False, [], f"Search is not completed (status: {search_data['status']})"
        
        # Get job IDs for this page
        job_ids = search_data['results'][offset:offset+limit]
        
        # Fetch jobs from database
        jobs = []
        for job_id in job_ids:
            job = self.get_job_by_id(job_id)
            if job:
                jobs.append(job)
        
        return True, jobs, f"Retrieved {len(jobs)} jobs"
    
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