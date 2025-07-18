"""
Analytics service for generating HR reports and insights.
"""
import datetime
import csv
import json
from typing import Dict, List, Optional
from sqlalchemy import desc, func, and_, or_, extract
from models.user import User
from models.job import Job, JobSkill
from models.application import Application, ApplicationStatus, Interview
from models.database import db


class AnalyticsService:
    """Service for generating analytics and reports."""
    
    def init_app(self, app):
        """Initialize the analytics service with the Flask app."""
        # No initialization needed for now
        pass
    
    def get_hiring_funnel_data(self) -> Dict:
        """Get hiring funnel statistics."""
        try:
            # Get applications count by status
            applications = Application.query.count()
            screened = Application.query.filter(
                Application.status.in_([
                    ApplicationStatus.UNDER_REVIEW,
                    ApplicationStatus.SHORTLISTED,
                    ApplicationStatus.INTERVIEW_SCHEDULED,
                    ApplicationStatus.INTERVIEWED,
                    ApplicationStatus.OFFER_PENDING,
                    ApplicationStatus.OFFER_RECEIVED,
                    ApplicationStatus.ACCEPTED
                ])
            ).count()
            
            interviewed = Application.query.filter(
                Application.status.in_([
                    ApplicationStatus.INTERVIEW_SCHEDULED,
                    ApplicationStatus.INTERVIEWED,
                    ApplicationStatus.OFFER_PENDING,
                    ApplicationStatus.OFFER_RECEIVED,
                    ApplicationStatus.ACCEPTED
                ])
            ).count()
            
            offers = Application.query.filter(
                Application.status.in_([
                    ApplicationStatus.OFFER_PENDING,
                    ApplicationStatus.OFFER_RECEIVED,
                    ApplicationStatus.ACCEPTED
                ])
            ).count()
            
            hired = Application.query.filter_by(status=ApplicationStatus.ACCEPTED).count()
            
            return {
                'applications': applications,
                'screened': screened,
                'interviewed': interviewed,
                'offers': offers,
                'hired': hired
            }
        
        except Exception as e:
            return {
                'applications': 0,
                'screened': 0,
                'interviewed': 0,
                'offers': 0,
                'hired': 0
            }
    
    def get_top_performing_jobs(self, limit: int = 5) -> List[Dict]:
        """Get top performing jobs by application count."""
        try:
            top_jobs = db.session.query(
                Job.id,
                Job.title,
                Job.company,
                func.count(Application.id).label('application_count')
            ).join(Application)\
             .group_by(Job.id, Job.title, Job.company)\
             .order_by(desc('application_count'))\
             .limit(limit)\
             .all()
            
            result = []
            for job in top_jobs:
                # Calculate conversion rate (hired / applications)
                hired_count = Application.query.filter(
                    and_(
                        Application.job_id == job.id,
                        Application.status == ApplicationStatus.ACCEPTED
                    )
                ).count()
                
                conversion_rate = (hired_count / job.application_count * 100) if job.application_count > 0 else 0
                
                result.append({
                    'id': job.id,
                    'title': job.title,
                    'company': job.company,
                    'application_count': job.application_count,
                    'conversion_rate': round(conversion_rate, 2)
                })
            
            return result
        
        except Exception as e:
            return []
    
    def get_job_analytics(self, job_id: str) -> Dict:
        """Get analytics for a specific job."""
        try:
            job = Job.query.get(job_id)
            if not job:
                return {}
            
            # Get application statistics
            total_applications = Application.query.filter_by(job_id=job_id).count()
            
            status_counts = db.session.query(
                Application.status,
                func.count(Application.id).label('count')
            ).filter_by(job_id=job_id)\
             .group_by(Application.status)\
             .all()
            
            # Get application timeline (applications per day)
            timeline = db.session.query(
                func.date(Application.created_at).label('date'),
                func.count(Application.id).label('count')
            ).filter_by(job_id=job_id)\
             .group_by(func.date(Application.created_at))\
             .order_by('date')\
             .all()
            
            # Calculate average time to hire
            hired_applications = Application.query.filter(
                and_(
                    Application.job_id == job_id,
                    Application.status == ApplicationStatus.ACCEPTED
                )
            ).all()
            
            avg_time_to_hire = 0
            if hired_applications:
                total_days = 0
                for app in hired_applications:
                    if app.submitted_at and app.last_updated_at:
                        days = (app.last_updated_at - app.submitted_at).days
                        total_days += days
                
                avg_time_to_hire = total_days / len(hired_applications)
            
            return {
                'job_id': job_id,
                'total_applications': total_applications,
                'status_distribution': [{'status': sc[0].value, 'count': sc[1]} for sc in status_counts],
                'application_timeline': [{'date': str(tl[0]), 'count': tl[1]} for tl in timeline],
                'avg_time_to_hire': round(avg_time_to_hire, 1),
                'views': 0,  # Placeholder - would track job views
                'conversion_rate': 0  # Placeholder - would calculate view to application rate
            }
        
        except Exception as e:
            return {}
    
    def get_overview_report(self, date_range: str, department: str = '', job_type: str = '') -> Dict:
        """Generate overview report."""
        try:
            # Calculate date range
            end_date = datetime.datetime.utcnow()
            if date_range == 'last_7_days':
                start_date = end_date - datetime.timedelta(days=7)
            elif date_range == 'last_30_days':
                start_date = end_date - datetime.timedelta(days=30)
            elif date_range == 'last_90_days':
                start_date = end_date - datetime.timedelta(days=90)
            elif date_range == 'last_year':
                start_date = end_date - datetime.timedelta(days=365)
            else:
                start_date = end_date - datetime.timedelta(days=30)
            
            # Base query
            query = Application.query.filter(
                Application.created_at.between(start_date, end_date)
            )
            
            # Apply filters
            if department:
                query = query.join(Job).filter(Job.company.ilike(f'%{department}%'))
            
            if job_type:
                query = query.join(Job).filter(Job.job_type == job_type)
            
            # Get metrics
            total_applications = query.count()
            
            hired = query.filter(Application.status == ApplicationStatus.ACCEPTED).count()
            
            rejected = query.filter(Application.status == ApplicationStatus.REJECTED).count()
            
            in_progress = query.filter(
                Application.status.in_([
                    ApplicationStatus.SUBMITTED,
                    ApplicationStatus.UNDER_REVIEW,
                    ApplicationStatus.SHORTLISTED,
                    ApplicationStatus.INTERVIEW_SCHEDULED,
                    ApplicationStatus.INTERVIEWED
                ])
            ).count()
            
            # Calculate rates
            hire_rate = (hired / total_applications * 100) if total_applications > 0 else 0
            rejection_rate = (rejected / total_applications * 100) if total_applications > 0 else 0
            
            # Get top sources (placeholder)
            top_sources = [
                {'source': 'Company Website', 'applications': total_applications // 3},
                {'source': 'LinkedIn', 'applications': total_applications // 4},
                {'source': 'Job Boards', 'applications': total_applications // 5}
            ]
            
            return {
                'period': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat(),
                    'range': date_range
                },
                'metrics': {
                    'total_applications': total_applications,
                    'hired': hired,
                    'rejected': rejected,
                    'in_progress': in_progress,
                    'hire_rate': round(hire_rate, 2),
                    'rejection_rate': round(rejection_rate, 2)
                },
                'top_sources': top_sources
            }
        
        except Exception as e:
            return {}
    
    def get_hiring_report(self, date_range: str, department: str = '', job_type: str = '') -> Dict:
        """Generate hiring-focused report."""
        try:
            # Similar to overview but focused on hiring metrics
            end_date = datetime.datetime.utcnow()
            if date_range == 'last_30_days':
                start_date = end_date - datetime.timedelta(days=30)
            else:
                start_date = end_date - datetime.timedelta(days=30)
            
            # Get hiring by month
            hiring_by_month = db.session.query(
                extract('year', Application.last_updated_at).label('year'),
                extract('month', Application.last_updated_at).label('month'),
                func.count(Application.id).label('count')
            ).filter(
                and_(
                    Application.status == ApplicationStatus.ACCEPTED,
                    Application.last_updated_at.between(start_date, end_date)
                )
            ).group_by('year', 'month').all()
            
            # Get average time to hire by job
            time_to_hire = db.session.query(
                Job.title,
                func.avg(
                    func.julianday(Application.last_updated_at) - 
                    func.julianday(Application.submitted_at)
                ).label('avg_days')
            ).join(Application).filter(
                and_(
                    Application.status == ApplicationStatus.ACCEPTED,
                    Application.submitted_at.isnot(None),
                    Application.last_updated_at.between(start_date, end_date)
                )
            ).group_by(Job.title).all()
            
            return {
                'hiring_by_month': [
                    {
                        'year': int(hbm[0]),
                        'month': int(hbm[1]),
                        'count': hbm[2]
                    } for hbm in hiring_by_month
                ],
                'time_to_hire': [
                    {
                        'job_title': tth[0],
                        'avg_days': round(tth[1], 1) if tth[1] else 0
                    } for tth in time_to_hire
                ]
            }
        
        except Exception as e:
            return {}
    
    def get_performance_report(self, date_range: str, department: str = '', job_type: str = '') -> Dict:
        """Generate performance report."""
        try:
            # Get recruiter performance (placeholder)
            recruiter_performance = [
                {'name': 'John Doe', 'applications_reviewed': 45, 'hires': 8},
                {'name': 'Jane Smith', 'applications_reviewed': 38, 'hires': 6},
                {'name': 'Mike Johnson', 'applications_reviewed': 52, 'hires': 10}
            ]
            
            # Get job posting performance
            job_performance = db.session.query(
                Job.title,
                Job.company,
                func.count(Application.id).label('applications'),
                func.sum(
                    func.case(
                        [(Application.status == ApplicationStatus.ACCEPTED, 1)],
                        else_=0
                    )
                ).label('hires')
            ).join(Application)\
             .group_by(Job.id, Job.title, Job.company)\
             .order_by(desc('applications'))\
             .limit(10)\
             .all()
            
            return {
                'recruiter_performance': recruiter_performance,
                'job_performance': [
                    {
                        'title': jp[0],
                        'company': jp[1],
                        'applications': jp[2],
                        'hires': jp[3] or 0,
                        'conversion_rate': round((jp[3] or 0) / jp[2] * 100, 2) if jp[2] > 0 else 0
                    } for jp in job_performance
                ]
            }
        
        except Exception as e:
            return {}
    
    def export_report(self, report_type: str, format_type: str = 'csv') -> str:
        """Export report data to file."""
        try:
            # Generate report data
            if report_type == 'overview':
                data = self.get_overview_report('last_30_days')
            elif report_type == 'hiring':
                data = self.get_hiring_report('last_30_days')
            elif report_type == 'performance':
                data = self.get_performance_report('last_30_days')
            else:
                data = self.get_overview_report('last_30_days')
            
            # Generate filename
            timestamp = datetime.datetime.utcnow().strftime('%Y%m%d_%H%M%S')
            filename = f"{report_type}_report_{timestamp}.{format_type}"
            filepath = f"exports/{filename}"
            
            # Create exports directory if it doesn't exist
            import os
            os.makedirs('exports', exist_ok=True)
            
            if format_type == 'csv':
                self._export_to_csv(data, filepath)
            elif format_type == 'json':
                self._export_to_json(data, filepath)
            else:
                raise ValueError(f"Unsupported format: {format_type}")
            
            return filepath
        
        except Exception as e:
            raise e
    
    def _export_to_csv(self, data: Dict, filepath: str):
        """Export data to CSV format."""
        with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
            if 'metrics' in data:
                # Overview report format
                writer = csv.writer(csvfile)
                writer.writerow(['Metric', 'Value'])
                
                metrics = data['metrics']
                for key, value in metrics.items():
                    writer.writerow([key.replace('_', ' ').title(), value])
            
            elif 'job_performance' in data:
                # Performance report format
                writer = csv.writer(csvfile)
                writer.writerow(['Job Title', 'Company', 'Applications', 'Hires', 'Conversion Rate'])
                
                for job in data['job_performance']:
                    writer.writerow([
                        job['title'],
                        job['company'],
                        job['applications'],
                        job['hires'],
                        f"{job['conversion_rate']}%"
                    ])
    
    def _export_to_json(self, data: Dict, filepath: str):
        """Export data to JSON format."""
        with open(filepath, 'w', encoding='utf-8') as jsonfile:
            json.dump(data, jsonfile, indent=2, default=str)
    
    def get_diversity_metrics(self) -> Dict:
        """Get diversity and inclusion metrics."""
        try:
            # This would typically analyze demographic data
            # For now, return placeholder data
            return {
                'gender_distribution': {
                    'male': 60,
                    'female': 35,
                    'other': 5
                },
                'age_distribution': {
                    '18-25': 25,
                    '26-35': 45,
                    '36-45': 20,
                    '46+': 10
                },
                'education_distribution': {
                    'bachelors': 50,
                    'masters': 35,
                    'phd': 10,
                    'other': 5
                }
            }
        
        except Exception as e:
            return {}
    
    def get_salary_analytics(self) -> Dict:
        """Get salary analytics."""
        try:
            # Get salary ranges from job postings
            salary_data = db.session.query(
                Job.job_type,
                func.avg(Job.salary_min).label('avg_min'),
                func.avg(Job.salary_max).label('avg_max')
            ).filter(
                and_(
                    Job.salary_min.isnot(None),
                    Job.salary_max.isnot(None)
                )
            ).group_by(Job.job_type).all()
            
            return {
                'salary_by_type': [
                    {
                        'job_type': sd[0],
                        'avg_min': round(sd[1], 2) if sd[1] else 0,
                        'avg_max': round(sd[2], 2) if sd[2] else 0
                    } for sd in salary_data
                ]
            }
        
        except Exception as e:
            return {}
    
    def get_skills_demand_analysis(self) -> Dict:
        """Analyze skills demand across job postings."""
        try:
            # Get most in-demand skills
            skills_demand = db.session.query(
                JobSkill.skill_name,
                func.count(JobSkill.job_id).label('demand_count')
            ).join(Job).filter(Job.is_active == True)\
             .group_by(JobSkill.skill_name)\
             .order_by(desc('demand_count'))\
             .limit(20)\
             .all()
            
            return {
                'top_skills': [
                    {
                        'skill': sd[0],
                        'demand_count': sd[1]
                    } for sd in skills_demand
                ]
            }
        
        except Exception as e:
            return {}
            
# Create service instance
analytics_service = AnalyticsService()