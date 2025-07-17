"""
Campus drive service for managing campus recruitment events.

This module provides functionality for creating, managing, and participating in
campus recruitment drives, including student registrations and event scheduling.
"""
import logging
import uuid
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from sqlalchemy import func
from models.database import db
from models.campus_drive import CampusDrive, Institution, DriveRegistration
from models.user import User
from models.job import Job

# Set up logging
logger = logging.getLogger(__name__)


class CampusDriveService:
    """Service for managing campus recruitment drives."""
    
    def __init__(self, app=None):
        """Initialize the campus drive service.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the campus drive service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
    
    def create_campus_drive(self, data: Dict[str, Any], created_by: str) -> Tuple[bool, Optional[str], str]:
        """Create a new campus recruitment drive.
        
        Args:
            data: Dictionary containing campus drive details
            created_by: ID of the user creating the drive
            
        Returns:
            Tuple[bool, Optional[str], str]: (success, drive_id, message)
        """
        try:
            # Validate required fields
            required_fields = ['institution_id', 'title', 'start_date']
            for field in required_fields:
                if field not in data or not data[field]:
                    return False, None, f"Missing required field: {field}"
            
            # Generate drive ID
            drive_id = str(uuid.uuid4())
            
            # Parse dates
            start_date = datetime.fromisoformat(data['start_date']) if isinstance(data['start_date'], str) else data['start_date']
            end_date = None
            if 'end_date' in data and data['end_date']:
                end_date = datetime.fromisoformat(data['end_date']) if isinstance(data['end_date'], str) else data['end_date']
            
            # Create campus drive
            campus_drive = CampusDrive(
                id=drive_id,
                institution_id=data['institution_id'],
                title=data['title'],
                description=data.get('description'),
                start_date=start_date,
                end_date=end_date,
                location=data.get('location'),
                is_virtual=data.get('is_virtual', False),
                status=data.get('status', 'scheduled'),
                created_by=created_by
            )
            
            # Add jobs to the drive
            if 'job_ids' in data and data['job_ids']:
                jobs = Job.query.filter(Job.id.in_(data['job_ids'])).all()
                campus_drive.jobs = jobs
            
            # Save to database
            db.session.add(campus_drive)
            db.session.commit()
            
            logger.info(f"Created campus drive {drive_id}: {data['title']}")
            return True, drive_id, "Campus drive created successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating campus drive: {str(e)}")
            return False, None, f"Error creating campus drive: {str(e)}"
    
    def update_campus_drive(self, drive_id: str, data: Dict[str, Any]) -> Tuple[bool, str]:
        """Update an existing campus drive.
        
        Args:
            drive_id: ID of the campus drive
            data: Dictionary containing updated details
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Get campus drive
            campus_drive = CampusDrive.query.get(drive_id)
            if not campus_drive:
                return False, "Campus drive not found"
            
            # Update fields
            if 'title' in data:
                campus_drive.title = data['title']
            
            if 'description' in data:
                campus_drive.description = data['description']
            
            if 'start_date' in data:
                campus_drive.start_date = datetime.fromisoformat(data['start_date']) if isinstance(data['start_date'], str) else data['start_date']
            
            if 'end_date' in data:
                campus_drive.end_date = datetime.fromisoformat(data['end_date']) if isinstance(data['end_date'], str) else data['end_date'] if data['end_date'] else None
            
            if 'location' in data:
                campus_drive.location = data['location']
            
            if 'is_virtual' in data:
                campus_drive.is_virtual = data['is_virtual']
            
            if 'status' in data:
                campus_drive.status = data['status']
            
            # Update jobs
            if 'job_ids' in data:
                jobs = Job.query.filter(Job.id.in_(data['job_ids'])).all()
                campus_drive.jobs = jobs
            
            # Update meta data
            if 'meta_data' in data:
                campus_drive.meta_data = data['meta_data']
            
            # Save changes
            db.session.commit()
            
            logger.info(f"Updated campus drive {drive_id}")
            return True, "Campus drive updated successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating campus drive: {str(e)}")
            return False, f"Error updating campus drive: {str(e)}"
    
    def get_campus_drive(self, drive_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a campus drive.
        
        Args:
            drive_id: ID of the campus drive
            
        Returns:
            Optional[Dict[str, Any]]: Campus drive details or None if not found
        """
        try:
            campus_drive = CampusDrive.query.get(drive_id)
            if not campus_drive:
                return None
            
            return campus_drive.to_dict(include_jobs=True, include_registrations=True)
            
        except Exception as e:
            logger.error(f"Error getting campus drive: {str(e)}")
            return None
    
    def list_campus_drives(self, filters: Dict[str, Any] = None, page: int = 1, limit: int = 20) -> Dict[str, Any]:
        """List campus drives with optional filtering.
        
        Args:
            filters: Dictionary of filter criteria
            page: Page number for pagination
            limit: Maximum number of results per page
            
        Returns:
            Dict[str, Any]: Dictionary containing campus drives and metadata
        """
        try:
            # Start with base query
            query = CampusDrive.query
            
            # Apply filters
            if filters:
                if 'institution_id' in filters:
                    query = query.filter(CampusDrive.institution_id == filters['institution_id'])
                
                if 'status' in filters:
                    query = query.filter(CampusDrive.status == filters['status'])
                
                if 'created_by' in filters:
                    query = query.filter(CampusDrive.created_by == filters['created_by'])
                
                if 'start_date_from' in filters:
                    start_date = datetime.fromisoformat(filters['start_date_from']) if isinstance(filters['start_date_from'], str) else filters['start_date_from']
                    query = query.filter(CampusDrive.start_date >= start_date)
                
                if 'start_date_to' in filters:
                    end_date = datetime.fromisoformat(filters['start_date_to']) if isinstance(filters['start_date_to'], str) else filters['start_date_to']
                    query = query.filter(CampusDrive.start_date <= end_date)
                
                if 'is_virtual' in filters:
                    query = query.filter(CampusDrive.is_virtual == filters['is_virtual'])
            
            # Count total results
            total_count = query.count()
            
            # Apply pagination
            offset = (page - 1) * limit
            query = query.order_by(CampusDrive.start_date.desc()).offset(offset).limit(limit)
            
            # Execute query
            campus_drives = query.all()
            
            # Calculate total pages
            total_pages = (total_count + limit - 1) // limit if limit > 0 else 1
            
            # Prepare results
            results = {
                'campus_drives': [drive.to_dict() for drive in campus_drives],
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
            logger.error(f"Error listing campus drives: {str(e)}")
            return {
                'campus_drives': [],
                'metadata': {
                    'total_count': 0,
                    'page': page,
                    'limit': limit,
                    'total_pages': 0,
                    'has_next': False,
                    'has_prev': False,
                    'error': str(e)
                }
            }
    
    def register_student(self, drive_id: str, student_id: str) -> Tuple[bool, Optional[str], str]:
        """Register a student for a campus drive.
        
        Args:
            drive_id: ID of the campus drive
            student_id: ID of the student
            
        Returns:
            Tuple[bool, Optional[str], str]: (success, registration_id, message)
        """
        try:
            # Check if campus drive exists
            campus_drive = CampusDrive.query.get(drive_id)
            if not campus_drive:
                return False, None, "Campus drive not found"
            
            # Check if student exists
            student = User.query.get(student_id)
            if not student:
                return False, None, "Student not found"
            
            # Check if student is already registered
            existing_registration = DriveRegistration.query.filter_by(
                campus_drive_id=drive_id,
                student_id=student_id
            ).first()
            
            if existing_registration:
                return False, None, "Student is already registered for this drive"
            
            # Generate registration ID
            registration_id = str(uuid.uuid4())
            
            # Create registration
            registration = DriveRegistration(
                id=registration_id,
                campus_drive_id=drive_id,
                student_id=student_id
            )
            
            # Save to database
            db.session.add(registration)
            db.session.commit()
            
            logger.info(f"Registered student {student_id} for campus drive {drive_id}")
            return True, registration_id, "Student registered successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error registering student: {str(e)}")
            return False, None, f"Error registering student: {str(e)}"
    
    def update_registration_status(self, registration_id: str, status: str, notes: str = None) -> Tuple[bool, str]:
        """Update the status of a student registration.
        
        Args:
            registration_id: ID of the registration
            status: New status (e.g., 'registered', 'shortlisted', 'rejected')
            notes: Optional notes about the status update
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Get registration
            registration = DriveRegistration.query.get(registration_id)
            if not registration:
                return False, "Registration not found"
            
            # Update status
            registration.status = status
            
            # Update notes if provided
            if notes is not None:
                registration.notes = notes
            
            # Save changes
            db.session.commit()
            
            logger.info(f"Updated registration {registration_id} status to {status}")
            return True, "Registration status updated successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating registration status: {str(e)}")
            return False, f"Error updating registration status: {str(e)}"
    
    def mark_attendance(self, registration_id: str, attended: bool) -> Tuple[bool, str]:
        """Mark attendance for a student at a campus drive.
        
        Args:
            registration_id: ID of the registration
            attended: Whether the student attended
            
        Returns:
            Tuple[bool, str]: (success, message)
        """
        try:
            # Get registration
            registration = DriveRegistration.query.get(registration_id)
            if not registration:
                return False, "Registration not found"
            
            # Update attendance
            registration.attendance = attended
            
            # Save changes
            db.session.commit()
            
            logger.info(f"Marked attendance for registration {registration_id}: {attended}")
            return True, "Attendance marked successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error marking attendance: {str(e)}")
            return False, f"Error marking attendance: {str(e)}"
    
    def get_student_registrations(self, student_id: str) -> List[Dict[str, Any]]:
        """Get all campus drive registrations for a student.
        
        Args:
            student_id: ID of the student
            
        Returns:
            List[Dict[str, Any]]: List of registrations
        """
        try:
            # Get registrations
            registrations = DriveRegistration.query.filter_by(student_id=student_id).all()
            
            # Prepare results
            results = []
            for registration in registrations:
                # Get campus drive details
                campus_drive = registration.campus_drive
                
                # Add to results
                results.append({
                    'registration': registration.to_dict(),
                    'campus_drive': campus_drive.to_dict()
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting student registrations: {str(e)}")
            return []
    
    def get_drive_registrations(self, drive_id: str) -> List[Dict[str, Any]]:
        """Get all student registrations for a campus drive.
        
        Args:
            drive_id: ID of the campus drive
            
        Returns:
            List[Dict[str, Any]]: List of registrations
        """
        try:
            # Get registrations
            registrations = DriveRegistration.query.filter_by(campus_drive_id=drive_id).all()
            
            # Prepare results
            results = []
            for registration in registrations:
                # Get student details
                student = registration.student
                
                # Add to results
                results.append({
                    'registration': registration.to_dict(),
                    'student': student.to_dict()
                })
            
            return results
            
        except Exception as e:
            logger.error(f"Error getting drive registrations: {str(e)}")
            return []
    
    def create_institution(self, data: Dict[str, Any]) -> Tuple[bool, Optional[str], str]:
        """Create a new educational institution.
        
        Args:
            data: Dictionary containing institution details
            
        Returns:
            Tuple[bool, Optional[str], str]: (success, institution_id, message)
        """
        try:
            # Validate required fields
            if 'name' not in data or not data['name']:
                return False, None, "Institution name is required"
            
            # Generate institution ID
            institution_id = str(uuid.uuid4())
            
            # Create institution
            institution = Institution(
                id=institution_id,
                name=data['name'],
                type=data.get('type'),
                location=data.get('location'),
                website=data.get('website'),
                description=data.get('description')
            )
            
            # Save to database
            db.session.add(institution)
            db.session.commit()
            
            logger.info(f"Created institution {institution_id}: {data['name']}")
            return True, institution_id, "Institution created successfully"
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating institution: {str(e)}")
            return False, None, f"Error creating institution: {str(e)}"
    
    def list_institutions(self) -> List[Dict[str, Any]]:
        """List all educational institutions.
        
        Returns:
            List[Dict[str, Any]]: List of institutions
        """
        try:
            # Get institutions
            institutions = Institution.query.order_by(Institution.name).all()
            
            # Prepare results
            return [institution.to_dict() for institution in institutions]
            
        except Exception as e:
            logger.error(f"Error listing institutions: {str(e)}")
            return []
    
    def get_upcoming_drives(self, limit: int = 5) -> List[Dict[str, Any]]:
        """Get upcoming campus drives.
        
        Args:
            limit: Maximum number of drives to return
            
        Returns:
            List[Dict[str, Any]]: List of upcoming drives
        """
        try:
            # Get current date
            now = datetime.utcnow()
            
            # Get upcoming drives
            upcoming_drives = CampusDrive.query.filter(
                CampusDrive.start_date >= now,
                CampusDrive.status == 'scheduled'
            ).order_by(CampusDrive.start_date).limit(limit).all()
            
            # Prepare results
            return [drive.to_dict() for drive in upcoming_drives]
            
        except Exception as e:
            logger.error(f"Error getting upcoming drives: {str(e)}")
            return []
    
    def get_drive_statistics(self, drive_id: str) -> Dict[str, Any]:
        """Get statistics for a campus drive.
        
        Args:
            drive_id: ID of the campus drive
            
        Returns:
            Dict[str, Any]: Statistics for the drive
        """
        try:
            # Get campus drive
            campus_drive = CampusDrive.query.get(drive_id)
            if not campus_drive:
                return {}
            
            # Get registration counts
            total_registrations = DriveRegistration.query.filter_by(campus_drive_id=drive_id).count()
            
            # Get status counts
            status_counts = db.session.query(
                DriveRegistration.status,
                func.count(DriveRegistration.id)
            ).filter_by(campus_drive_id=drive_id).group_by(DriveRegistration.status).all()
            
            # Get attendance counts
            attended_count = DriveRegistration.query.filter_by(
                campus_drive_id=drive_id,
                attendance=True
            ).count()
            
            # Prepare results
            status_dict = {status: count for status, count in status_counts}
            
            return {
                'total_registrations': total_registrations,
                'status_counts': status_dict,
                'attended_count': attended_count,
                'attendance_rate': (attended_count / total_registrations) if total_registrations > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting drive statistics: {str(e)}")
            return {}


# Create a singleton instance
campus_drive_service = CampusDriveService()