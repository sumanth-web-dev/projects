"""
Recommendation service for job and candidate matching.

This module provides functionality for generating personalized job recommendations
for users and candidate recommendations for job postings based on skills, experience,
and other factors.
"""
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from sqlalchemy import text
from models.database import db
from models.user import User
from models.job import Job
from models.skill import UserSkill, Skill

# Set up logging
logger = logging.getLogger(__name__)


class RecommendationService:
    """Service for generating personalized recommendations."""
    
    def __init__(self, app=None):
        """Initialize the recommendation service.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self.min_match_score = 0.3  # Minimum score to consider a match
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the recommendation service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self.min_match_score = app.config.get('MIN_MATCH_SCORE', 0.3)
    
    def get_job_recommendations(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get job recommendations for a user.
        
        Args:
            user_id: ID of the user
            limit: Maximum number of recommendations to return
            
        Returns:
            List[Dict[str, Any]]: List of job recommendations with match scores
        """
        try:
            # Get user skills
            user_skills = UserSkill.query.filter_by(user_id=user_id).all()
            if not user_skills:
                logger.info(f"No skills found for user {user_id}")
                return []
            
            # Get user skill IDs and proficiency levels
            user_skill_map = {skill.skill_id: skill.proficiency_level for skill in user_skills}
            user_skill_ids = list(user_skill_map.keys())
            
            # Get active jobs
            jobs = Job.query.filter_by(is_active=True).all()
            if not jobs:
                logger.info("No active jobs found")
                return []
            
            # Calculate match scores
            recommendations = []
            for job in jobs:
                match_score, match_reasons = self._calculate_job_match(job, user_skill_ids, user_skill_map)
                
                if match_score >= self.min_match_score:
                    recommendations.append({
                        'job': job.to_dict(),
                        'match_score': match_score,
                        'match_reasons': match_reasons
                    })
            
            # Sort by match score (descending)
            recommendations.sort(key=lambda x: x['match_score'], reverse=True)
            
            # Limit results
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error generating job recommendations: {str(e)}")
            return []
    
    def _calculate_job_match(self, job: Job, user_skill_ids: List[str], 
                           user_skill_map: Dict[str, int]) -> Tuple[float, List[str]]:
        """Calculate match score between a job and user skills.
        
        Args:
            job: Job object
            user_skill_ids: List of user skill IDs
            user_skill_map: Dictionary mapping skill IDs to proficiency levels
            
        Returns:
            Tuple[float, List[str]]: Match score (0-1) and list of match reasons
        """
        # Get job skills
        job_skills = job.skills
        if not job_skills:
            return 0.0, []
        
        # Initialize variables
        total_importance = sum(skill.importance for skill in job_skills)
        if total_importance == 0:
            total_importance = len(job_skills)  # Default importance if all are 0
        
        matched_importance = 0
        match_reasons = []
        
        # Check each job skill
        for job_skill in job_skills:
            # Get skill details
            skill = Skill.query.get(job_skill.skill_id)
            if not skill:
                continue
            
            # Check if user has this skill
            if job_skill.skill_id in user_skill_ids:
                # Calculate match based on proficiency and importance
                user_proficiency = user_skill_map[job_skill.skill_id]
                skill_match = (user_proficiency / 5) * job_skill.importance
                matched_importance += skill_match
                
                # Add match reason
                match_reasons.append(f"You have {skill.name} skill required for this job")
        
        # Calculate overall match score (0-1)
        match_score = matched_importance / total_importance if total_importance > 0 else 0
        
        # Add other match factors
        # (This could include location, experience, education, etc.)
        
        return match_score, match_reasons
    
    def get_candidate_recommendations(self, job_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get candidate recommendations for a job.
        
        Args:
            job_id: ID of the job
            limit: Maximum number of recommendations to return
            
        Returns:
            List[Dict[str, Any]]: List of candidate recommendations with match scores
        """
        try:
            # Get job details
            job = Job.query.get(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return []
            
            # Get job skills
            job_skills = job.skills
            if not job_skills:
                logger.info(f"No skills defined for job {job_id}")
                return []
            
            # Get job skill IDs and importance levels
            job_skill_map = {skill.skill_id: skill.importance for skill in job_skills}
            job_skill_ids = list(job_skill_map.keys())
            
            # Get users with matching skills
            users_with_skills = db.session.query(User).join(UserSkill).filter(
                UserSkill.skill_id.in_(job_skill_ids),
                User.is_active == True
            ).distinct().all()
            
            if not users_with_skills:
                logger.info(f"No candidates found with skills matching job {job_id}")
                return []
            
            # Calculate match scores
            recommendations = []
            for user in users_with_skills:
                # Get user skills
                user_skills = UserSkill.query.filter_by(user_id=user.id).all()
                user_skill_map = {skill.skill_id: skill.proficiency_level for skill in user_skills}
                
                match_score, match_reasons = self._calculate_candidate_match(job, user, job_skill_ids, job_skill_map, user_skill_map)
                
                if match_score >= self.min_match_score:
                    recommendations.append({
                        'user': user.to_dict(),
                        'match_score': match_score,
                        'match_reasons': match_reasons
                    })
            
            # Sort by match score (descending)
            recommendations.sort(key=lambda x: x['match_score'], reverse=True)
            
            # Limit results
            return recommendations[:limit]
            
        except Exception as e:
            logger.error(f"Error generating candidate recommendations: {str(e)}")
            return []
    
    def _calculate_candidate_match(self, job: Job, user: User, job_skill_ids: List[str],
                                 job_skill_map: Dict[str, int], user_skill_map: Dict[str, int]) -> Tuple[float, List[str]]:
        """Calculate match score between a candidate and job requirements.
        
        Args:
            job: Job object
            user: User object
            job_skill_ids: List of job skill IDs
            job_skill_map: Dictionary mapping job skill IDs to importance levels
            user_skill_map: Dictionary mapping user skill IDs to proficiency levels
            
        Returns:
            Tuple[float, List[str]]: Match score (0-1) and list of match reasons
        """
        # Initialize variables
        total_importance = sum(job_skill_map.values())
        if total_importance == 0:
            total_importance = len(job_skill_ids)  # Default importance if all are 0
        
        matched_importance = 0
        match_reasons = []
        
        # Check each job skill
        for skill_id in job_skill_ids:
            # Get skill details
            skill = Skill.query.get(skill_id)
            if not skill:
                continue
            
            # Check if user has this skill
            if skill_id in user_skill_map:
                # Calculate match based on proficiency and importance
                user_proficiency = user_skill_map[skill_id]
                job_importance = job_skill_map[skill_id]
                skill_match = (user_proficiency / 5) * job_importance
                matched_importance += skill_match
                
                # Add match reason
                match_reasons.append(f"Candidate has {skill.name} skill required for this job")
        
        # Calculate overall match score (0-1)
        match_score = matched_importance / total_importance if total_importance > 0 else 0
        
        # Add other match factors
        # (This could include experience, education, etc.)
        
        return match_score, match_reasons
    
    def get_similar_jobs(self, job_id: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get similar jobs to a given job.
        
        Args:
            job_id: ID of the job
            limit: Maximum number of similar jobs to return
            
        Returns:
            List[Dict[str, Any]]: List of similar jobs with similarity scores
        """
        try:
            # Get job details
            job = Job.query.get(job_id)
            if not job:
                logger.error(f"Job {job_id} not found")
                return []
            
            # Get job skills
            job_skills = job.skills
            if not job_skills:
                logger.info(f"No skills defined for job {job_id}")
                return []
            
            # Get job skill IDs
            job_skill_ids = [skill.skill_id for skill in job_skills]
            
            # Get other active jobs with similar skills
            other_jobs = Job.query.filter(
                Job.id != job_id,
                Job.is_active == True
            ).all()
            
            if not other_jobs:
                logger.info("No other active jobs found")
                return []
            
            # Calculate similarity scores
            similar_jobs = []
            for other_job in other_jobs:
                other_job_skill_ids = [skill.skill_id for skill in other_job.skills]
                
                # Calculate Jaccard similarity (intersection over union)
                intersection = len(set(job_skill_ids) & set(other_job_skill_ids))
                union = len(set(job_skill_ids) | set(other_job_skill_ids))
                similarity = intersection / union if union > 0 else 0
                
                if similarity > 0:
                    similar_jobs.append({
                        'job': other_job.to_dict(),
                        'similarity': similarity
                    })
            
            # Sort by similarity (descending)
            similar_jobs.sort(key=lambda x: x['similarity'], reverse=True)
            
            # Limit results
            return similar_jobs[:limit]
            
        except Exception as e:
            logger.error(f"Error finding similar jobs: {str(e)}")
            return []


# Create a singleton instance
recommendation_service = RecommendationService()