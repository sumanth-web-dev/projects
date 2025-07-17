"""
Analytics service for tracking and analyzing system usage and metrics.

This module provides functionality for collecting, analyzing, and reporting on
various metrics related to user activity, job applications, and system performance.
"""
import logging
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from sqlalchemy import text, func
from models.database import db
from models.user import User
from models.job import Job
from models.application import Application, ApplicationStatus

# Set up logging
logger = logging.getLogger(__name__)


class AnalyticsService:
    """Service for tracking and analyzing system metrics."""
    
    def __init__(self, app=None):
        """Initialize the analytics service.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self._analytics_log_path = None
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the analytics service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        
        # Set up analytics logging
        import os
        log_dir = os.path.join(app.instance_path, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        self._analytics_log_path = os.path.join(log_dir, 'analytics.log')
    
    def log_event(self, event_type: str, user_id: Optional[str] = None, 
                 details: Optional[Dict[str, Any]] = None) -> bool:
        """Log an analytics event.
        
        Args:
            event_type: Type of event (e.g., 'page_view', 'job_application', 'search')
            user_id: ID of the user (if authenticated)
            details: Additional details about the event
            
        Returns:
            bool: True if successful, False otherwise
        """
        if not self._analytics_log_path:
            return False
        
        try:
            # Create log entry
            log_entry = {
                'timestamp': datetime.utcnow().isoformat(),
                'event_type': event_type,
                'user_id': user_id,
                'details': details or {}
            }
            
            # Write to log file
            with open(self._analytics_log_path, 'a') as f:
                f.write(json.dumps(log_entry) + '\n')
            
            return True
        except Exception as e:
            logger.error(f"Error logging analytics event: {str(e)}")
            return False
    
    def get_user_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get user-related metrics.
        
        Args:
            days: Number of days to include in the metrics
            
        Returns:
            Dict[str, Any]: User metrics
        """
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get total users
            total_users = User.query.count()
            
            # Get active users
            active_users = User.query.filter_by(is_active=True).count()
            
            # Get new users in date range
            new_users = User.query.filter(
                User.created_at >= start_date,
                User.created_at <= end_date
            ).count()
            
            # Get user roles distribution
            role_distribution = self._get_role_distribution()
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'new_users': new_users,
                'role_distribution': role_distribution,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'days': days
                }
            }
        except Exception as e:
            logger.error(f"Error getting user metrics: {str(e)}")
            return {}
    
    def _get_role_distribution(self) -> Dict[str, int]:
        """Get distribution of user roles.
        
        Returns:
            Dict[str, int]: Count of users by role
        """
        try:
            # This is a simplified approach; in a real system, you would query the database
            # For this example, we'll use a placeholder implementation
            return {
                'admin': User.query.filter(User.personal_data.contains('"roles": ["admin"]')).count(),
                'hr': User.query.filter(User.personal_data.contains('"roles": ["hr"]')).count(),
                'student': User.query.filter(User.personal_data.contains('"roles": ["student"]')).count(),
                'user': User.query.filter(User.personal_data.contains('"roles": ["user"]')).count()
            }
        except Exception as e:
            logger.error(f"Error getting role distribution: {str(e)}")
            return {}
    
    def get_job_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get job-related metrics.
        
        Args:
            days: Number of days to include in the metrics
            
        Returns:
            Dict[str, Any]: Job metrics
        """
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get total jobs
            total_jobs = Job.query.count()
            
            # Get active jobs
            active_jobs = Job.query.filter_by(is_active=True).count()
            
            # Get new jobs in date range
            new_jobs = Job.query.filter(
                Job.created_at >= start_date,
                Job.created_at <= end_date
            ).count()
            
            # Get jobs by category
            jobs_by_category = self._get_jobs_by_category()
            
            return {
                'total_jobs': total_jobs,
                'active_jobs': active_jobs,
                'new_jobs': new_jobs,
                'jobs_by_category': jobs_by_category,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'days': days
                }
            }
        except Exception as e:
            logger.error(f"Error getting job metrics: {str(e)}")
            return {}
    
    def _get_jobs_by_category(self) -> Dict[str, int]:
        """Get distribution of jobs by category.
        
        Returns:
            Dict[str, int]: Count of jobs by category
        """
        try:
            # Query jobs by category
            result = db.session.query(
                Job.category_id,
                func.count(Job.id)
            ).group_by(Job.category_id).all()
            
            # Convert to dictionary
            jobs_by_category = {}
            for category_id, count in result:
                if category_id:
                    from models.job import JobCategory
                    category = JobCategory.query.get(category_id)
                    if category:
                        jobs_by_category[category.name] = count
                else:
                    jobs_by_category['Uncategorized'] = count
            
            return jobs_by_category
        except Exception as e:
            logger.error(f"Error getting jobs by category: {str(e)}")
            return {}
    
    def get_application_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get application-related metrics.
        
        Args:
            days: Number of days to include in the metrics
            
        Returns:
            Dict[str, Any]: Application metrics
        """
        try:
            # Calculate date range
            end_date = datetime.utcnow()
            start_date = end_date - timedelta(days=days)
            
            # Get total applications
            total_applications = Application.query.count()
            
            # Get new applications in date range
            new_applications = Application.query.filter(
                Application.created_at >= start_date,
                Application.created_at <= end_date
            ).count()
            
            # Get applications by status
            applications_by_status = self._get_applications_by_status()
            
            # Calculate conversion rates
            conversion_rates = self._calculate_conversion_rates()
            
            return {
                'total_applications': total_applications,
                'new_applications': new_applications,
                'applications_by_status': applications_by_status,
                'conversion_rates': conversion_rates,
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'days': days
                }
            }
        except Exception as e:
            logger.error(f"Error getting application metrics: {str(e)}")
            return {}
    
    def _get_applications_by_status(self) -> Dict[str, int]:
        """Get distribution of applications by status.
        
        Returns:
            Dict[str, int]: Count of applications by status
        """
        try:
            # Query applications by status
            result = db.session.query(
                Application.status,
                func.count(Application.id)
            ).group_by(Application.status).all()
            
            # Convert to dictionary
            applications_by_status = {}
            for status, count in result:
                applications_by_status[status.value] = count
            
            return applications_by_status
        except Exception as e:
            logger.error(f"Error getting applications by status: {str(e)}")
            return {}
    
    def _calculate_conversion_rates(self) -> Dict[str, float]:
        """Calculate application conversion rates.
        
        Returns:
            Dict[str, float]: Conversion rates
        """
        try:
            # Get counts by status
            submitted = Application.query.filter_by(status=ApplicationStatus.SUBMITTED).count()
            shortlisted = Application.query.filter_by(status=ApplicationStatus.SHORTLISTED).count()
            interviewed = Application.query.filter_by(status=ApplicationStatus.INTERVIEWED).count()
            offered = Application.query.filter_by(status=ApplicationStatus.OFFER_RECEIVED).count()
            accepted = Application.query.filter_by(status=ApplicationStatus.ACCEPTED).count()
            
            # Calculate rates
            shortlist_rate = (shortlisted / submitted) if submitted > 0 else 0
            interview_rate = (interviewed / shortlisted) if shortlisted > 0 else 0
            offer_rate = (offered / interviewed) if interviewed > 0 else 0
            acceptance_rate = (accepted / offered) if offered > 0 else 0
            overall_success_rate = (accepted / submitted) if submitted > 0 else 0
            
            return {
                'shortlist_rate': shortlist_rate,
                'interview_rate': interview_rate,
                'offer_rate': offer_rate,
                'acceptance_rate': acceptance_rate,
                'overall_success_rate': overall_success_rate
            }
        except Exception as e:
            logger.error(f"Error calculating conversion rates: {str(e)}")
            return {}
    
    def get_system_metrics(self, days: int = 30) -> Dict[str, Any]:
        """Get system performance metrics.
        
        Args:
            days: Number of days to include in the metrics
            
        Returns:
            Dict[str, Any]: System metrics
        """
        try:
            # This would typically collect metrics from logs or monitoring systems
            # For this example, we'll return placeholder data
            return {
                'average_response_time': 120,  # ms
                'error_rate': 0.02,  # 2%
                'uptime': 0.998,  # 99.8%
                'peak_concurrent_users': 250,
                'date_range': {
                    'start': (datetime.utcnow() - timedelta(days=days)).isoformat(),
                    'end': datetime.utcnow().isoformat(),
                    'days': days
                }
            }
        except Exception as e:
            logger.error(f"Error getting system metrics: {str(e)}")
            return {}
    
    def get_search_analytics(self, days: int = 30) -> Dict[str, Any]:
        """Get search-related analytics.
        
        Args:
            days: Number of days to include in the analytics
            
        Returns:
            Dict[str, Any]: Search analytics
        """
        try:
            # This would typically analyze search logs
            # For this example, we'll return placeholder data
            return {
                'top_search_terms': [
                    {'term': 'software engineer', 'count': 1250},
                    {'term': 'data scientist', 'count': 980},
                    {'term': 'product manager', 'count': 750},
                    {'term': 'remote', 'count': 620},
                    {'term': 'entry level', 'count': 580}
                ],
                'average_searches_per_user': 4.2,
                'search_to_application_rate': 0.15,  # 15% of searches lead to applications
                'date_range': {
                    'start': (datetime.utcnow() - timedelta(days=days)).isoformat(),
                    'end': datetime.utcnow().isoformat(),
                    'days': days
                }
            }
        except Exception as e:
            logger.error(f"Error getting search analytics: {str(e)}")
            return {}
    
    def get_dashboard_summary(self) -> Dict[str, Any]:
        """Get summary metrics for the admin dashboard.
        
        Returns:
            Dict[str, Any]: Dashboard summary metrics
        """
        try:
            # Get key metrics
            total_users = User.query.count()
            active_users = User.query.filter_by(is_active=True).count()
            total_jobs = Job.query.count()
            active_jobs = Job.query.filter_by(is_active=True).count()
            total_applications = Application.query.count()
            
            # Calculate recent activity (last 7 days)
            seven_days_ago = datetime.utcnow() - timedelta(days=7)
            new_users = User.query.filter(User.created_at >= seven_days_ago).count()
            new_jobs = Job.query.filter(Job.created_at >= seven_days_ago).count()
            new_applications = Application.query.filter(Application.created_at >= seven_days_ago).count()
            
            # Calculate user growth rate
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            users_30_days_ago = User.query.filter(User.created_at < thirty_days_ago).count()
            user_growth_rate = ((total_users - users_30_days_ago) / users_30_days_ago) if users_30_days_ago > 0 else 0
            
            return {
                'total_users': total_users,
                'active_users': active_users,
                'total_jobs': total_jobs,
                'active_jobs': active_jobs,
                'total_applications': total_applications,
                'recent_activity': {
                    'new_users': new_users,
                    'new_jobs': new_jobs,
                    'new_applications': new_applications
                },
                'growth_rates': {
                    'user_growth_rate': user_growth_rate
                }
            }
        except Exception as e:
            logger.error(f"Error getting dashboard summary: {str(e)}")
            return {}


# Create a singleton instance
analytics_service = AnalyticsService()