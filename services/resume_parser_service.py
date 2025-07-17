"""
Resume parser service for extracting information from resumes.

This module provides functionality for parsing resumes in various formats (PDF, DOCX, etc.)
and extracting structured information such as contact details, education, experience, and skills.
"""
import os
import re
import logging
import uuid
from typing import Dict, List, Optional, Any
from datetime import datetime
from werkzeug.utils import secure_filename
from flask import current_app

# Set up logging
logger = logging.getLogger(__name__)


class ResumeParserService:
    """Service for parsing and extracting information from resumes."""
    
    def __init__(self, app=None):
        """Initialize the resume parser service.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self.upload_folder = None
        self.allowed_extensions = {'pdf', 'docx', 'doc', 'txt'}
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the resume parser service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
        self.upload_folder = app.config.get('UPLOAD_FOLDER', os.path.join(app.instance_path, 'uploads', 'resumes'))
        self.allowed_extensions = app.config.get('ALLOWED_RESUME_EXTENSIONS', {'pdf', 'docx', 'doc', 'txt'})
        
        # Create upload folder if it doesn't exist
        os.makedirs(self.upload_folder, exist_ok=True)
    
    def allowed_file(self, filename: str) -> bool:
        """Check if a file has an allowed extension.
        
        Args:
            filename: Name of the file
            
        Returns:
            bool: True if the file extension is allowed, False otherwise
        """
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in self.allowed_extensions
    
    def save_resume(self, file, user_id: str) -> Optional[str]:
        """Save a resume file to the upload folder.
        
        Args:
            file: File object from request.files
            user_id: ID of the user
            
        Returns:
            Optional[str]: Path to the saved file, or None if saving failed
        """
        try:
            if file and self.allowed_file(file.filename):
                # Create user folder if it doesn't exist
                user_folder = os.path.join(self.upload_folder, user_id)
                os.makedirs(user_folder, exist_ok=True)
                
                # Generate a unique filename
                filename = secure_filename(file.filename)
                file_ext = filename.rsplit('.', 1)[1].lower()
                unique_filename = f"{uuid.uuid4().hex}.{file_ext}"
                
                # Save the file
                file_path = os.path.join(user_folder, unique_filename)
                file.save(file_path)
                
                logger.info(f"Resume saved for user {user_id}: {file_path}")
                return file_path
            else:
                logger.warning(f"Invalid file type for resume upload: {file.filename if file else 'No file'}")
                return None
        except Exception as e:
            logger.error(f"Error saving resume: {str(e)}")
            return None
    
    def parse_resume(self, file_path: str) -> Dict[str, Any]:
        """Parse a resume file and extract structured information.
        
        Args:
            file_path: Path to the resume file
            
        Returns:
            Dict[str, Any]: Extracted information from the resume
        """
        try:
            # Check if file exists
            if not os.path.isfile(file_path):
                logger.error(f"Resume file not found: {file_path}")
                return {}
            
            # Get file extension
            file_ext = file_path.rsplit('.', 1)[1].lower()
            
            # Parse based on file type
            if file_ext == 'pdf':
                return self._parse_pdf(file_path)
            elif file_ext in ['docx', 'doc']:
                return self._parse_docx(file_path)
            elif file_ext == 'txt':
                return self._parse_txt(file_path)
            else:
                logger.warning(f"Unsupported file type for parsing: {file_ext}")
                return {}
        except Exception as e:
            logger.error(f"Error parsing resume: {str(e)}")
            return {}
    
    def _parse_pdf(self, file_path: str) -> Dict[str, Any]:
        """Parse a PDF resume.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            Dict[str, Any]: Extracted information from the resume
        """
        # In a real implementation, this would use a library like PyPDF2 or pdfminer
        # For this example, we'll return placeholder data
        logger.info(f"Parsing PDF resume: {file_path}")
        
        return {
            'parsed': True,
            'format': 'pdf',
            'contact_info': {
                'name': 'John Doe',
                'email': 'john.doe@example.com',
                'phone': '123-456-7890',
                'location': 'New York, NY'
            },
            'education': [
                {
                    'institution': 'Example University',
                    'degree': 'Bachelor of Science',
                    'field': 'Computer Science',
                    'start_date': '2018-09-01',
                    'end_date': '2022-05-31'
                }
            ],
            'experience': [
                {
                    'company': 'Example Corp',
                    'title': 'Software Engineer',
                    'start_date': '2022-06-01',
                    'end_date': None,
                    'description': 'Developed web applications using Python and JavaScript'
                }
            ],
            'skills': ['Python', 'JavaScript', 'React', 'SQL', 'Git']
        }
    
    def _parse_docx(self, file_path: str) -> Dict[str, Any]:
        """Parse a DOCX resume.
        
        Args:
            file_path: Path to the DOCX file
            
        Returns:
            Dict[str, Any]: Extracted information from the resume
        """
        # In a real implementation, this would use a library like python-docx
        # For this example, we'll return placeholder data
        logger.info(f"Parsing DOCX resume: {file_path}")
        
        return {
            'parsed': True,
            'format': 'docx',
            'contact_info': {
                'name': 'Jane Smith',
                'email': 'jane.smith@example.com',
                'phone': '987-654-3210',
                'location': 'San Francisco, CA'
            },
            'education': [
                {
                    'institution': 'Sample University',
                    'degree': 'Master of Science',
                    'field': 'Data Science',
                    'start_date': '2020-09-01',
                    'end_date': '2022-05-31'
                }
            ],
            'experience': [
                {
                    'company': 'Data Corp',
                    'title': 'Data Scientist',
                    'start_date': '2022-06-01',
                    'end_date': None,
                    'description': 'Analyzed large datasets and built machine learning models'
                }
            ],
            'skills': ['Python', 'R', 'Machine Learning', 'SQL', 'Tableau']
        }
    
    def _parse_txt(self, file_path: str) -> Dict[str, Any]:
        """Parse a plain text resume.
        
        Args:
            file_path: Path to the text file
            
        Returns:
            Dict[str, Any]: Extracted information from the resume
        """
        # In a real implementation, this would use regex or NLP techniques
        # For this example, we'll return placeholder data
        logger.info(f"Parsing text resume: {file_path}")
        
        return {
            'parsed': True,
            'format': 'txt',
            'contact_info': {
                'name': 'Alex Johnson',
                'email': 'alex.johnson@example.com',
                'phone': '555-123-4567',
                'location': 'Chicago, IL'
            },
            'education': [
                {
                    'institution': 'Tech University',
                    'degree': 'Bachelor of Arts',
                    'field': 'Marketing',
                    'start_date': '2017-09-01',
                    'end_date': '2021-05-31'
                }
            ],
            'experience': [
                {
                    'company': 'Marketing Agency',
                    'title': 'Marketing Specialist',
                    'start_date': '2021-06-01',
                    'end_date': None,
                    'description': 'Managed social media campaigns and content creation'
                }
            ],
            'skills': ['Social Media Marketing', 'Content Creation', 'SEO', 'Analytics', 'Copywriting']
        }
    
    def extract_skills(self, text: str) -> List[str]:
        """Extract skills from resume text.
        
        Args:
            text: Text content from resume
            
        Returns:
            List[str]: List of extracted skills
        """
        # In a real implementation, this would use NLP techniques or a skills database
        # For this example, we'll use a simple approach with common tech skills
        common_skills = [
            'Python', 'JavaScript', 'Java', 'C++', 'C#', 'Ruby', 'PHP', 'Swift',
            'React', 'Angular', 'Vue', 'Node.js', 'Django', 'Flask', 'Spring',
            'SQL', 'MongoDB', 'PostgreSQL', 'MySQL', 'Oracle', 'Redis',
            'AWS', 'Azure', 'GCP', 'Docker', 'Kubernetes', 'Jenkins',
            'Machine Learning', 'Data Science', 'AI', 'Deep Learning', 'NLP',
            'Git', 'Agile', 'Scrum', 'DevOps', 'CI/CD'
        ]
        
        found_skills = []
        for skill in common_skills:
            if re.search(r'\b' + re.escape(skill) + r'\b', text, re.IGNORECASE):
                found_skills.append(skill)
        
        return found_skills
    
    def suggest_jobs(self, resume_data: Dict[str, Any], limit: int = 5) -> List[Dict[str, Any]]:
        """Suggest jobs based on parsed resume data.
        
        Args:
            resume_data: Parsed resume data
            limit: Maximum number of job suggestions
            
        Returns:
            List[Dict[str, Any]]: List of suggested jobs
        """
        # In a real implementation, this would query the database for matching jobs
        # For this example, we'll return placeholder data
        skills = resume_data.get('skills', [])
        
        # Placeholder job suggestions
        suggestions = [
            {
                'id': '1',
                'title': 'Software Engineer',
                'company': 'Tech Solutions Inc.',
                'location': 'New York, NY',
                'match_score': 0.85,
                'match_skills': ['Python', 'JavaScript', 'React']
            },
            {
                'id': '2',
                'title': 'Data Scientist',
                'company': 'Data Analytics Corp',
                'location': 'San Francisco, CA',
                'match_score': 0.75,
                'match_skills': ['Python', 'Machine Learning', 'SQL']
            },
            {
                'id': '3',
                'title': 'Full Stack Developer',
                'company': 'Web Solutions LLC',
                'location': 'Remote',
                'match_score': 0.70,
                'match_skills': ['JavaScript', 'React', 'Node.js']
            }
        ]
        
        return suggestions[:limit]


# Create a singleton instance
resume_parser_service = ResumeParserService()