"""
Interview service for managing interview scheduling and operations.
"""
import datetime
import uuid
from typing import Dict, List, Optional
from sqlalchemy import desc, func, and_, or_
from models.user import User
from models.application import Application, Interview
from models.database import db


class InterviewService:
    """Service for managing interviews."""
    
    def init_app(self, app):
        """Initialize the interview service with the Flask app."""
        # No initialization needed for now
        pass
    
    def get_upcoming_interviews(self, limit: Optional[int] = None) -> List[Interview]:
        """Get upcoming interviews."""
        try:
            query = Interview.query.filter(
                Interview.scheduled_at >= datetime.datetime.utcnow()
            ).order_by(Interview.scheduled_at)
            
            if limit:
                query = query.limit(limit)
            
            return query.all()
        
        except Exception as e:
            return []
    
    def get_interview_statistics(self) -> Dict:
        """Get interview statistics."""
        try:
            total_interviews = Interview.query.count()
            
            upcoming_interviews = Interview.query.filter(
                Interview.scheduled_at >= datetime.datetime.utcnow()
            ).count()
            
            completed_interviews = Interview.query.filter_by(is_completed=True).count()
            
            today_interviews = Interview.query.filter(
                func.date(Interview.scheduled_at) == datetime.datetime.utcnow().date()
            ).count()
            
            return {
                'total_interviews': total_interviews,
                'upcoming_interviews': upcoming_interviews,
                'completed_interviews': completed_interviews,
                'today_interviews': today_interviews
            }
        
        except Exception as e:
            return {
                'total_interviews': 0,
                'upcoming_interviews': 0,
                'completed_interviews': 0,
                'today_interviews': 0
            }
    
    def get_available_interviewers(self) -> List[Dict]:
        """Get list of available interviewers."""
        try:
            # This would typically come from a separate interviewers table
            # For now, return mock data
            interviewers = [
                {'id': '1', 'name': 'John Smith', 'title': 'Senior Developer', 'email': 'john@company.com'},
                {'id': '2', 'name': 'Jane Doe', 'title': 'Tech Lead', 'email': 'jane@company.com'},
                {'id': '3', 'name': 'Mike Johnson', 'title': 'Engineering Manager', 'email': 'mike@company.com'},
                {'id': '4', 'name': 'Sarah Wilson', 'title': 'HR Manager', 'email': 'sarah@company.com'}
            ]
            
            return interviewers
        
        except Exception as e:
            return []
    
    def schedule_interview(self, interview_data: Dict, scheduled_by: str) -> str:
        """Schedule a new interview."""
        try:
            interview_id = str(uuid.uuid4())
            
            # Parse date and time
            interview_date = interview_data['interview_date']
            interview_time = interview_data['interview_time']
            scheduled_at = datetime.datetime.strptime(
                f"{interview_date} {interview_time}", 
                "%Y-%m-%d %H:%M"
            )
            
            interview = Interview(
                id=interview_id,
                application_id=interview_data['application_id'],
                scheduled_at=scheduled_at,
                duration_minutes=interview_data.get('duration', 60),
                location=interview_data.get('location', ''),
                interview_type=interview_data['interview_type']
            )
            
            # Add metadata
            meta_data = {
                'primary_interviewer': interview_data.get('primary_interviewer'),
                'additional_interviewers': interview_data.get('additional_interviewers', []),
                'focus_areas': interview_data.get('focus_areas', []),
                'meeting_instructions': interview_data.get('meeting_instructions', ''),
                'scheduled_by': scheduled_by,
                'notifications': {
                    'send_candidate_email': interview_data.get('send_candidate_email', False),
                    'send_interviewer_email': interview_data.get('send_interviewer_email', False),
                    'calendar_invite': interview_data.get('calendar_invite', False)
                }
            }
            
            interview.meta_data = meta_data
            interview.interviewer_notes = interview_data.get('interview_notes', '')
            
            db.session.add(interview)
            
            # Update application status
            application = Application.query.get(interview_data['application_id'])
            if application:
                application.status = 'interview_scheduled'
                application.last_updated_at = datetime.datetime.utcnow()
            
            db.session.commit()
            
            # Send notifications if requested
            if interview_data.get('send_candidate_email'):
                self.send_candidate_notification(interview)
            
            if interview_data.get('send_interviewer_email'):
                self.send_interviewer_notification(interview)
            
            return interview_id
        
        except Exception as e:
            db.session.rollback()
            raise e
    
    def update_interview(self, interview_id: str, interview_data: Dict) -> bool:
        """Update an existing interview."""
        try:
            interview = Interview.query.get(interview_id)
            if not interview:
                return False
            
            # Update basic fields
            if 'scheduled_at' in interview_data:
                interview.scheduled_at = interview_data['scheduled_at']
            
            if 'duration_minutes' in interview_data:
                interview.duration_minutes = interview_data['duration_minutes']
            
            if 'location' in interview_data:
                interview.location = interview_data['location']
            
            if 'interview_type' in interview_data:
                interview.interview_type = interview_data['interview_type']
            
            if 'interviewer_notes' in interview_data:
                interview.interviewer_notes = interview_data['interviewer_notes']
            
            # Update metadata
            if 'meta_data' in interview_data:
                current_meta = interview.meta_data or {}
                current_meta.update(interview_data['meta_data'])
                interview.meta_data = current_meta
            
            interview.updated_at = datetime.datetime.utcnow()
            db.session.commit()
            
            return True
        
        except Exception as e:
            db.session.rollback()
            return False
    
    def cancel_interview(self, interview_id: str, reason: str = '') -> bool:
        """Cancel an interview."""
        try:
            interview = Interview.query.get(interview_id)
            if not interview:
                return False
            
            # Add cancellation info to metadata
            meta_data = interview.meta_data or {}
            meta_data['cancelled'] = True
            meta_data['cancellation_reason'] = reason
            meta_data['cancelled_at'] = datetime.datetime.utcnow().isoformat()
            
            interview.meta_data = meta_data
            interview.updated_at = datetime.datetime.utcnow()
            
            # Update application status back to previous state
            application = interview.application
            if application and application.status == 'interview_scheduled':
                application.status = 'shortlisted'
                application.last_updated_at = datetime.datetime.utcnow()
            
            db.session.commit()
            
            # Send cancellation notifications
            self.send_cancellation_notification(interview)
            
            return True
        
        except Exception as e:
            db.session.rollback()
            return False
    
    def complete_interview(self, interview_id: str, feedback: Dict) -> bool:
        """Mark interview as completed and add feedback."""
        try:
            interview = Interview.query.get(interview_id)
            if not interview:
                return False
            
            interview.is_completed = True
            interview.interviewer_notes = feedback.get('notes', interview.interviewer_notes)
            
            # Add feedback to metadata
            meta_data = interview.meta_data or {}
            meta_data['feedback'] = {
                'rating': feedback.get('rating'),
                'strengths': feedback.get('strengths', []),
                'weaknesses': feedback.get('weaknesses', []),
                'recommendation': feedback.get('recommendation'),
                'completed_at': datetime.datetime.utcnow().isoformat()
            }
            
            interview.meta_data = meta_data
            interview.updated_at = datetime.datetime.utcnow()
            
            # Update application status based on feedback
            application = interview.application
            if application:
                recommendation = feedback.get('recommendation', 'pending')
                if recommendation == 'hire':
                    application.status = 'offer_pending'
                elif recommendation == 'reject':
                    application.status = 'rejected'
                else:
                    application.status = 'interviewed'
                
                application.last_updated_at = datetime.datetime.utcnow()
            
            db.session.commit()
            return True
        
        except Exception as e:
            db.session.rollback()
            return False
    
    def get_interview_details(self, interview_id: str) -> Optional[Interview]:
        """Get detailed interview information."""
        try:
            interview = Interview.query.get(interview_id)
            return interview
        
        except Exception as e:
            return None
    
    def get_interviewer_schedule(self, interviewer_id: str, date: datetime.date) -> List[Interview]:
        """Get interviewer's schedule for a specific date."""
        try:
            # This would typically query based on interviewer assignments
            # For now, return empty list
            return []
        
        except Exception as e:
            return []
    
    def send_candidate_notification(self, interview: Interview) -> bool:
        """Send interview notification to candidate."""
        try:
            # This would integrate with email service
            # For now, just return True
            return True
        
        except Exception as e:
            return False
    
    def send_interviewer_notification(self, interview: Interview) -> bool:
        """Send interview notification to interviewers."""
        try:
            # This would integrate with email service
            # For now, just return True
            return True
        
        except Exception as e:
            return False
    
    def send_cancellation_notification(self, interview: Interview) -> bool:
        """Send cancellation notification."""
        try:
            # This would integrate with email service
            # For now, just return True
            return True
        
        except Exception as e:
            return False
    
    def get_interview_feedback_template(self, interview_type: str) -> Dict:
        """Get feedback template for interview type."""
        try:
            templates = {
                'technical': {
                    'categories': [
                        'Technical Knowledge',
                        'Problem Solving',
                        'Code Quality',
                        'Communication'
                    ],
                    'questions': [
                        'How well did the candidate demonstrate technical knowledge?',
                        'How effectively did they approach problem-solving?',
                        'What was the quality of their code/solutions?',
                        'How well did they communicate their thought process?'
                    ]
                },
                'behavioral': {
                    'categories': [
                        'Communication',
                        'Leadership',
                        'Teamwork',
                        'Cultural Fit'
                    ],
                    'questions': [
                        'How effectively does the candidate communicate?',
                        'What leadership qualities did they demonstrate?',
                        'How well would they work in a team environment?',
                        'How well do they align with company culture?'
                    ]
                },
                'general': {
                    'categories': [
                        'Overall Impression',
                        'Relevant Experience',
                        'Motivation',
                        'Questions Asked'
                    ],
                    'questions': [
                        'What was your overall impression?',
                        'How relevant is their experience?',
                        'How motivated do they seem?',
                        'What quality of questions did they ask?'
                    ]
                }
            }
            
            return templates.get(interview_type, templates['general'])
        
        except Exception as e:
            return {}
    
    def generate_interview_report(self, date_range: str = 'month') -> Dict:
        """Generate interview analytics report."""
        try:
            # Calculate date range
            end_date = datetime.datetime.utcnow()
            if date_range == 'week':
                start_date = end_date - datetime.timedelta(days=7)
            elif date_range == 'month':
                start_date = end_date - datetime.timedelta(days=30)
            elif date_range == 'quarter':
                start_date = end_date - datetime.timedelta(days=90)
            else:
                start_date = end_date - datetime.timedelta(days=30)
            
            # Get interview statistics
            total_interviews = Interview.query.filter(
                Interview.scheduled_at.between(start_date, end_date)
            ).count()
            
            completed_interviews = Interview.query.filter(
                and_(
                    Interview.scheduled_at.between(start_date, end_date),
                    Interview.is_completed == True
                )
            ).count()
            
            # Calculate completion rate
            completion_rate = (completed_interviews / total_interviews * 100) if total_interviews > 0 else 0
            
            # Get interview types distribution
            interview_types = db.session.query(
                Interview.interview_type,
                func.count(Interview.id).label('count')
            ).filter(
                Interview.scheduled_at.between(start_date, end_date)
            ).group_by(Interview.interview_type).all()
            
            return {
                'total_interviews': total_interviews,
                'completed_interviews': completed_interviews,
                'completion_rate': round(completion_rate, 2),
                'interview_types': [{'type': it[0], 'count': it[1]} for it in interview_types],
                'date_range': {
                    'start': start_date.isoformat(),
                    'end': end_date.isoformat()
                }
            }
        
        except Exception as e:
            return {}
            
            
            
# Create service instance
interview_service = InterviewService()