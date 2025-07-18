"""
Recommendation service for providing personalized job recommendations.
"""
import datetime
from typing import Dict, List, Optional, Tuple
from sqlalchemy import desc, func, and_, or_


class RecommendationService:
    """Service for generating personalized job recommendations."""
    
    def init_app(self, app):
        """Initialize the recommendation service with the Flask app."""
        # No initialization needed for now
        pass
    
    def get_recommendations(self, user_id: str, limit: int = 10) -> List[Dict]:
        """Get personalized job recommendations for a user."""
        try:
            from models.user import User
            
            user = User.query.get(user_id)
            if not user:
                return []
            
            personal_data = user.personal_data or {}
            user_skills = personal_data.get('skills', [])
            user_location = personal_data.get('preferred_location', '')
            user_experience = personal_data.get('experience', [])
            
            # Calculate years of experience
            years_experience = self.calculate_years_experience(user_experience)
            
            # Get jobs that match user criteria
            jobs = self.get_matching_jobs(user_skills, user_location, years_experience)
            
            # Calculate match scores
            recommendations = []
            for job in jobs:
                match_score = self.calculate_match_score(user, job)
                matching_skills = self.get_matching_skills(user_skills, job)
                
                recommendations.append({
                    'job': job,
                    'match_score': match_score,
                    'matching_skills': matching_skills
                })
            
            # Sort by match score (highest first)
            recommendations.sort(key=lambda x: x['match_score'], reverse=True)
            
            return recommendations[:limit]
        
        except Exception as e:
            return []
    
    def get_matching_jobs(self, user_skills: List[str], location: str, years_experience: int) -> List:
        """Get jobs that match user criteria."""
        try:
            from models.job import Job, JobSkill
            from models.application import Application
            from models.database import db
            
            query = Job.query.filter(Job.is_active == True)
            
            # Filter by location if specified
            if location:
                query = query.filter(
                    or_(
                        Job.location.ilike(f'%{location}%'),
                        Job.remote_option == True
                    )
                )
            
            # Filter by experience level (within reasonable range)
            if years_experience > 0:
                query = query.filter(
                    or_(
                        Job.experience_required <= years_experience + 2,
                        Job.experience_required.is_(None)
                    )
                )
            
            # Get jobs with matching skills
            if user_skills:
                skill_subquery = db.session.query(JobSkill.job_id).filter(
                    JobSkill.skill_name.in_([skill.lower() for skill in user_skills])
                ).subquery()
                
                query = query.filter(Job.id.in_(skill_subquery))
            
            # Exclude jobs user has already applied to
            applied_jobs = db.session.query(Application.job_id).filter_by(user_id=user_skills[0] if user_skills else '')
            query = query.filter(~Job.id.in_(applied_jobs))
            
            jobs = query.order_by(desc(Job.created_at)).limit(50).all()
            return jobs
        
        except Exception as e:
            return []
    
    def calculate_match_score(self, user, job) -> float:
        """Calculate match score between user and job."""
        try:
            personal_data = user.personal_data or {}
            user_skills = [skill.lower() for skill in personal_data.get('skills', [])]
            user_experience = personal_data.get('experience', [])
            user_location = personal_data.get('preferred_location', '').lower()
            
            score = 0.0
            max_score = 100.0
            
            # Skills matching (40% of total score)
            skills_score = self.calculate_skills_match(user_skills, job)
            score += skills_score * 0.4
            
            # Experience matching (25% of total score)
            experience_score = self.calculate_experience_match(user_experience, job)
            score += experience_score * 0.25
            
            # Location matching (20% of total score)
            location_score = self.calculate_location_match(user_location, job)
            score += location_score * 0.2
            
            # Job freshness (10% of total score)
            freshness_score = self.calculate_freshness_score(job)
            score += freshness_score * 0.1
            
            # Company preference (5% of total score)
            company_score = self.calculate_company_preference(user, job)
            score += company_score * 0.05
            
            return min(score / max_score, 1.0)
        
        except Exception as e:
            return 0.0
    
    def calculate_skills_match(self, user_skills: List[str], job) -> float:
        """Calculate skills match score."""
        try:
            if not user_skills:
                return 0.0
            
            job_skills = [skill.skill_name.lower() for skill in job.skills]
            
            if not job_skills:
                return 50.0  # Neutral score if job has no specified skills
            
            # Calculate intersection
            matching_skills = set(user_skills) & set(job_skills)
            
            if not matching_skills:
                return 0.0
            
            # Calculate score based on percentage of job skills matched
            match_percentage = len(matching_skills) / len(job_skills)
            
            # Bonus for having more skills than required
            if len(matching_skills) >= len(job_skills):
                match_percentage = min(match_percentage * 1.2, 1.0)
            
            return match_percentage * 100.0
        
        except Exception as e:
            return 0.0
    
    def calculate_experience_match(self, user_experience: List[Dict], job) -> float:
        """Calculate experience match score."""
        try:
            years_experience = self.calculate_years_experience(user_experience)
            required_experience = job.experience_required or 0
            
            if required_experience == 0:
                return 100.0  # Perfect match if no experience required
            
            if years_experience >= required_experience:
                # Perfect match if user meets or exceeds requirement
                if years_experience <= required_experience + 2:
                    return 100.0
                else:
                    # Slight penalty for being overqualified
                    return max(80.0, 100.0 - (years_experience - required_experience - 2) * 5)
            else:
                # Penalty for not meeting requirement
                gap = required_experience - years_experience
                return max(0.0, 100.0 - gap * 20)
        
        except Exception as e:
            return 50.0
    
    def calculate_location_match(self, user_location: str, job) -> float:
        """Calculate location match score."""
        try:
            if not user_location or not job.location:
                return 50.0  # Neutral score if location not specified
            
            job_location = job.location.lower()
            
            # Perfect match for remote jobs
            if job.remote_option:
                return 100.0
            
            # Check for location match
            if user_location in job_location or job_location in user_location:
                return 100.0
            
            # Check for city/state match
            user_parts = user_location.split(',')
            job_parts = job_location.split(',')
            
            for user_part in user_parts:
                for job_part in job_parts:
                    if user_part.strip() in job_part.strip() or job_part.strip() in user_part.strip():
                        return 80.0
            
            return 20.0  # Low score for location mismatch
        
        except Exception as e:
            return 50.0
    
    def calculate_freshness_score(self, job) -> float:
        """Calculate job freshness score."""
        try:
            if not job.created_at:
                return 50.0
            
            days_old = (datetime.datetime.utcnow() - job.created_at).days
            
            if days_old <= 7:
                return 100.0
            elif days_old <= 30:
                return 80.0
            elif days_old <= 60:
                return 60.0
            else:
                return 40.0
        
        except Exception as e:
            return 50.0
    
    def calculate_company_preference(self, user, job) -> float:
        """Calculate company preference score."""
        try:
            # This could be based on user's application history, saved companies, etc.
            # For now, return neutral score
            return 50.0
        
        except Exception as e:
            return 50.0
    
    def calculate_years_experience(self, experience_list: List[Dict]) -> int:
        """Calculate total years of experience."""
        try:
            if not experience_list:
                return 0
            
            total_months = 0
            
            for exp in experience_list:
                start_date = exp.get('start_date')
                end_date = exp.get('end_date')
                is_current = exp.get('current', False)
                
                if not start_date:
                    continue
                
                try:
                    start = datetime.datetime.strptime(start_date, '%Y-%m')
                    
                    if is_current or not end_date:
                        end = datetime.datetime.utcnow()
                    else:
                        end = datetime.datetime.strptime(end_date, '%Y-%m')
                    
                    months = (end.year - start.year) * 12 + (end.month - start.month)
                    total_months += max(0, months)
                
                except ValueError:
                    continue
            
            return total_months // 12
        
        except Exception as e:
            return 0
    
    def get_matching_skills(self, user_skills: List[str], job) -> List[str]:
        """Get skills that match between user and job."""
        try:
            user_skills_lower = [skill.lower() for skill in user_skills]
            job_skills_lower = [skill.skill_name.lower() for skill in job.skills]
            
            matching = []
            for skill in user_skills:
                if skill.lower() in job_skills_lower:
                    matching.append(skill)
            
            return matching
        
        except Exception as e:
            return []
    
    def get_similar_jobs(self, job_id: str, limit: int = 5) -> List:
        """Get jobs similar to a given job."""
        try:
            from models.job import Job
            from models.database import db
            
            job = Job.query.get(job_id)
            if not job:
                return []
            
            # Find jobs with similar skills, company, or job type
            similar_jobs = Job.query.filter(
                and_(
                    Job.id != job_id,
                    Job.is_active == True,
                    or_(
                        Job.company == job.company,
                        Job.job_type == job.job_type,
                        Job.title.ilike(f'%{job.title.split()[0]}%')  # Similar title
                    )
                )
            ).limit(limit).all()
            
            return similar_jobs
        
        except Exception as e:
            return []
    
    def get_trending_jobs(self, limit: int = 10) -> List:
        """Get trending jobs based on application activity."""
        try:
            from models.job import Job
            from models.application import Application
            from models.database import db
            
            # Get jobs with most applications in the last 7 days
            week_ago = datetime.datetime.utcnow() - datetime.timedelta(days=7)
            
            trending_jobs = db.session.query(Job)\
                .join(Application)\
                .filter(
                    and_(
                        Job.is_active == True,
                        Application.created_at >= week_ago
                    )
                )\
                .group_by(Job.id)\
                .order_by(desc(func.count(Application.id)))\
                .limit(limit)\
                .all()
            
            return trending_jobs
        
        except Exception as e:
            return []
    
    def update_user_preferences(self, user_id: str, preferences: Dict) -> bool:
        """Update user job preferences."""
        try:
            from models.user import User
            from models.database import db
            
            user = User.query.get(user_id)
            if not user:
                return False
            
            current_preferences = user.preferences or {}
            current_preferences.update(preferences)
            
            user.preferences = current_preferences
            db.session.commit()
            
            return True
        
        except Exception as e:
            db.session.rollback()
            return False


# Create service instance
recommendation_service = RecommendationService()