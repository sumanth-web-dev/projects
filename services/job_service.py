"""
Job service for managing job listings and related operations.
"""
import datetime
import uuid
from typing import Dict, List, Optional, TYPE_CHECKING
from sqlalchemy import desc, func, and_, or_

# Type checking imports
if TYPE_CHECKING:
    from models.job import Job, JobCategory
    from models.application import Application


class JobService:
    """Service for managing job listings."""
    
    def init_app(self, app):
        """Initialize the job service with the Flask app."""
        # No initialization needed for now
        pass
    
    def create_job(self, job_data: Dict, skills: List[str], created_by: str) -> str:
        """Create a new job listing."""
        try:
            from models.job import Job, JobSkill
            from models.database import db
            
            job_id = str(uuid.uuid4())
            
            job = Job(
                id=job_id,
                title=job_data['title'],
                company=job_data['company'],
                description=job_data['description'],
                created_by=created_by,
                **{k: v for k, v in job_data.items() if k not in ['title', 'company', 'description']}
            )
            
            db.session.add(job)
            
            # Add skills
            for skill_name in skills:
                skill_id = str(uuid.uuid4())
                job_skill = JobSkill(
                    id=skill_id,
                    job_id=job_id,
                    skill_name=skill_name.strip(),
                    importance=1  # Default importance
                )
                db.session.add(job_skill)
            
            db.session.commit()
            return job_id
        
        except Exception as e:
            db.session.rollback()
            raise e
    
    def update_job(self, job_id: str, job_data: Dict, skills: List[str]) -> bool:
        """Update an existing job listing."""
        try:
            from models.job import Job, JobSkill
            from models.database import db
            
            job = Job.query.get(job_id)
            if not job:
                return False
            
            # Update job fields
            for key, value in job_data.items():
                if hasattr(job, key):
                    setattr(job, key, value)
            
            job.updated_at = datetime.datetime.utcnow()
            
            # Update skills - remove existing and add new ones
            JobSkill.query.filter_by(job_id=job_id).delete()
            
            for skill_name in skills:
                skill_id = str(uuid.uuid4())
                job_skill = JobSkill(
                    id=skill_id,
                    job_id=job_id,
                    skill_name=skill_name.strip(),
                    importance=1
                )
                db.session.add(job_skill)
            
            db.session.commit()
            return True
        
        except Exception as e:
            db.session.rollback()
            return False
    
    def get_jobs_with_filters(self, status: str = 'all', department: str = '', search: str = '') -> List:
        """Get jobs with filters."""
        try:
            from models.job import Job
            
            query = Job.query
            
            # Apply status filter
            if status == 'active':
                query = query.filter(Job.is_active == True)
            elif status == 'inactive':
                query = query.filter(Job.is_active == False)
            
            # Apply department filter
            if department:
                query = query.filter(Job.company.ilike(f'%{department}%'))  # Simplified
            
            # Apply search filter
            if search:
                query = query.filter(
                    or_(
                        Job.title.ilike(f'%{search}%'),
                        Job.company.ilike(f'%{search}%'),
                        Job.description.ilike(f'%{search}%')
                    )
                )
            
            jobs = query.order_by(desc(Job.created_at)).all()
            return jobs
        
        except Exception as e:
            return []
    
    def get_job_statistics(self) -> Dict:
        """Get job statistics."""
        try:
            from models.job import Job
            
            total_jobs = Job.query.count()
            active_jobs = Job.query.filter_by(is_active=True).count()
            inactive_jobs = Job.query.filter_by(is_active=False).count()
            
            jobs_this_month = Job.query.filter(
                Job.created_at >= datetime.datetime.utcnow().replace(day=1)
            ).count()
            
            return {
                'total_jobs': total_jobs,
                'active_jobs': active_jobs,
                'inactive_jobs': inactive_jobs,
                'jobs_this_month': jobs_this_month
            }
        
        except Exception as e:
            return {
                'total_jobs': 0,
                'active_jobs': 0,
                'inactive_jobs': 0,
                'jobs_this_month': 0
            }
    
    def get_departments(self) -> List[str]:
        """Get list of departments."""
        try:
            from models.job import Job
            from models.database import db
            
            # This would typically come from a departments table
            # For now, extract unique companies as departments
            departments = db.session.query(Job.company).distinct().all()
            return [dept[0] for dept in departments if dept[0]]
        
        except Exception as e:
            return []
    
    def get_job_types(self) -> List[str]:
        """Get list of job types."""
        try:
            from models.job import Job
            from models.database import db
            
            job_types = db.session.query(Job.job_type).distinct().all()
            return [jt[0] for jt in job_types if jt[0]]
        
        except Exception as e:
            return []
    
    def get_active_jobs(self, limit: Optional[int] = None) -> List:
        """Get active jobs."""
        try:
            from models.job import Job
            
            query = Job.query.filter_by(is_active=True).order_by(desc(Job.created_at))
            
            if limit:
                query = query.limit(limit)
            
            return query.all()
        
        except Exception as e:
            return []
    
    def get_job_with_details(self, job_id: str) -> Optional:
        """Get job with full details including skills and applications."""
        try:
            from models.job import Job
            
            job = Job.query.get(job_id)
            return job
        
        except Exception as e:
            return None
    
    def get_job_categories(self) -> List:
        """Get all job categories."""
        try:
            from models.job import JobCategory
            
            categories = JobCategory.query.all()
            return categories
        
        except Exception as e:
            return []
    
    def get_job_templates(self) -> List[Dict]:
        """Get job description templates."""
        try:
            # This would typically come from a templates table
            # For now, return some common templates
            templates = [
                {
                    'id': 'software_engineer',
                    'title': 'Software Engineer',
                    'description': 'We are looking for a skilled Software Engineer...',
                    'requirements': 'Bachelor\'s degree in Computer Science...',
                    'responsibilities': 'Design and develop software applications...'
                },
                {
                    'id': 'data_scientist',
                    'title': 'Data Scientist',
                    'description': 'We are seeking a Data Scientist...',
                    'requirements': 'Master\'s degree in Data Science...',
                    'responsibilities': 'Analyze complex datasets...'
                }
            ]
            return templates
        
        except Exception as e:
            return []
    
    def deactivate_job(self, job_id: str) -> bool:
        """Deactivate a job listing."""
        try:
            from models.job import Job
            from models.database import db
            
            job = Job.query.get(job_id)
            if not job:
                return False
            
            job.is_active = False
            job.updated_at = datetime.datetime.utcnow()
            db.session.commit()
            
            return True
        
        except Exception as e:
            db.session.rollback()
            return False
    
    def activate_job(self, job_id: str) -> bool:
        """Activate a job listing."""
        try:
            from models.job import Job
            from models.database import db
            
            job = Job.query.get(job_id)
            if not job:
                return False
            
            job.is_active = True
            job.updated_at = datetime.datetime.utcnow()
            db.session.commit()
            
            return True
        
        except Exception as e:
            db.session.rollback()
            return False
    
    def delete_job(self, job_id: str) -> bool:
        """Delete a job listing (soft delete)."""
        try:
            from models.job import Job
            from models.application import Application
            from models.database import db
            
            job = Job.query.get(job_id)
            if not job:
                return False
            
            # Check if job has applications
            has_applications = Application.query.filter_by(job_id=job_id).first() is not None
            
            if has_applications:
                # Soft delete - just deactivate
                job.is_active = False
                job.updated_at = datetime.datetime.utcnow()
            else:
                # Hard delete if no applications
                db.session.delete(job)
            
            db.session.commit()
            return True
        
        except Exception as e:
            db.session.rollback()
            return False
    
    def get_job_applications_count(self, job_id: str) -> int:
        """Get number of applications for a job."""
        try:
            from models.application import Application
            
            count = Application.query.filter_by(job_id=job_id).count()
            return count
        
        except Exception as e:
            return 0
    
    def get_popular_skills(self, limit: int = 20) -> List[Dict]:
        """Get most popular skills across all jobs."""
        try:
            from models.job import JobSkill
            from models.database import db
            
            skills = db.session.query(
                JobSkill.skill_name,
                func.count(JobSkill.skill_name).label('count')
            ).group_by(JobSkill.skill_name)\
             .order_by(desc('count'))\
             .limit(limit)\
             .all()
            
            return [{'skill': skill[0], 'count': skill[1]} for skill in skills]
        
        except Exception as e:
            return []
    
    def search_jobs(self, query: str, filters: Dict = None) -> List:
        """Search jobs with advanced filtering."""
        try:
            from models.job import Job
            
            search_query = Job.query.filter(Job.is_active == True)
            
            # Text search
            if query:
                search_query = search_query.filter(
                    or_(
                        Job.title.ilike(f'%{query}%'),
                        Job.company.ilike(f'%{query}%'),
                        Job.description.ilike(f'%{query}%'),
                        Job.requirements.ilike(f'%{query}%')
                    )
                )
            
            # Apply filters if provided
            if filters:
                if filters.get('location'):
                    search_query = search_query.filter(
                        Job.location.ilike(f'%{filters["location"]}%')
                    )
                
                if filters.get('job_type'):
                    search_query = search_query.filter(
                        Job.job_type == filters['job_type']
                    )
                
                if filters.get('experience_min'):
                    search_query = search_query.filter(
                        Job.experience_required >= int(filters['experience_min'])
                    )
                
                if filters.get('experience_max'):
                    search_query = search_query.filter(
                        Job.experience_required <= int(filters['experience_max'])
                    )
                
                if filters.get('salary_min'):
                    search_query = search_query.filter(
                        Job.salary_min >= float(filters['salary_min'])
                    )
                
                if filters.get('remote_option'):
                    search_query = search_query.filter(
                        Job.remote_option == True
                    )
            
            jobs = search_query.order_by(desc(Job.created_at)).all()
            return jobs
        
        except Exception as e:
            return []
            
            
            
# Create service instance
job_service = JobService()