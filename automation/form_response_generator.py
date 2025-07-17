"""
Form response generator for intelligent form filling.

This module provides functionality for generating AI-powered responses to form fields
based on job context and user profile information.
"""
import re
import logging
from typing import Dict, List, Optional, Tuple, Any, Set
from services.ai_service import AIService, JobContext, ResponseQuality

# Set up logging
logger = logging.getLogger(__name__)


class FormField:
    """Representation of a form field."""
    
    # Field types
    TEXT = "text"
    TEXTAREA = "textarea"
    SELECT = "select"
    RADIO = "radio"
    CHECKBOX = "checkbox"
    FILE = "file"
    
    def __init__(self, field_id: str, field_type: str, label: str, 
                 options: Optional[List[str]] = None, required: bool = False,
                 placeholder: Optional[str] = None, max_length: Optional[int] = None):
        """Initialize FormField instance.
        
        Args:
            field_id: HTML ID or name of the field
            field_type: Type of field (TEXT, TEXTAREA, SELECT, etc.)
            label: Field label text
            options: Options for SELECT, RADIO, or CHECKBOX fields
            required: Whether the field is required
            placeholder: Placeholder text if available
            max_length: Maximum length of input if specified
        """
        self.field_id = field_id
        self.field_type = field_type
        self.label = label
        self.options = options or []
        self.required = required
        self.placeholder = placeholder
        self.max_length = max_length
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert field to dictionary."""
        return {
            'field_id': self.field_id,
            'field_type': self.field_type,
            'label': self.label,
            'options': self.options,
            'required': self.required,
            'placeholder': self.placeholder,
            'max_length': self.max_length
        }


class FormResponseGenerator:
    """Generator for AI-powered form responses."""
    
    def __init__(self, ai_service: Optional[AIService] = None):
        """Initialize FormResponseGenerator instance.
        
        Args:
            ai_service: AIService instance for response generation
        """
        from services.ai_service import ai_service as default_ai_service
        self.ai_service = ai_service or default_ai_service
        self._common_field_patterns = self._load_common_field_patterns()
    
    def generate_field_response(self, field: FormField, job_context: JobContext, 
                              user_profile: Dict) -> Tuple[str, ResponseQuality]:
        """Generate a response for a form field.
        
        Args:
            field: Form field information
            job_context: Context information about the job
            user_profile: User profile information
            
        Returns:
            Tuple[str, ResponseQuality]: Generated response and quality assessment
        """
        try:
            # Determine the question/prompt based on field label
            question = self._convert_field_to_question(field)
            
            # Generate response using AI service
            response = self.ai_service.generate_response(question, job_context, user_profile)
            
            # Format response based on field type
            formatted_response = self._format_response_for_field_type(response, field)
            
            # Validate response quality
            quality = self.ai_service.validate_response_quality(formatted_response, question, job_context)
            
            # Apply length constraints if needed
            if field.max_length and len(formatted_response) > field.max_length:
                formatted_response = formatted_response[:field.max_length]
                # Add quality issue for truncation
                quality.issues.append("Response was truncated to meet length constraints")
                if quality.quality == ResponseQuality.HIGH:
                    quality.quality = ResponseQuality.MEDIUM
                    quality.confidence *= 0.9
            
            return formatted_response, quality
            
        except Exception as e:
            logger.error(f"Error generating field response: {str(e)}")
            # Return fallback response
            return self._generate_fallback_response(field, user_profile), ResponseQuality(
                ResponseQuality.LOW, 0.3, ["Error generating response"]
            )
    
    def generate_form_responses(self, fields: List[FormField], job_context: JobContext, 
                              user_profile: Dict) -> Dict[str, Tuple[str, ResponseQuality]]:
        """Generate responses for multiple form fields.
        
        Args:
            fields: List of form fields
            job_context: Context information about the job
            user_profile: User profile information
            
        Returns:
            Dict[str, Tuple[str, ResponseQuality]]: Dictionary of field_id -> (response, quality)
        """
        responses = {}
        
        for field in fields:
            response, quality = self.generate_field_response(field, job_context, user_profile)
            responses[field.field_id] = (response, quality)
        
        return responses
    
    def detect_field_type(self, field_id: str, label: str, 
                         element_type: Optional[str] = None) -> str:
        """Detect the semantic type of a form field.
        
        Args:
            field_id: HTML ID or name of the field
            label: Field label text
            element_type: HTML element type if available
            
        Returns:
            str: Detected field type
        """
        field_id_lower = field_id.lower()
        label_lower = label.lower()
        
        # Check for common field patterns
        for field_type, patterns in self._common_field_patterns.items():
            for pattern in patterns:
                if re.search(pattern, field_id_lower) or re.search(pattern, label_lower):
                    return field_type
        
        # Default to text for unknown fields
        return FormField.TEXT
    
    def map_user_data_to_field(self, field: FormField, user_profile: Dict) -> Optional[str]:
        """Map user profile data to a form field.
        
        Args:
            field: Form field information
            user_profile: User profile information
            
        Returns:
            Optional[str]: Mapped user data or None if no mapping found
        """
        field_id_lower = field.field_id.lower()
        label_lower = field.label.lower()
        
        # Get personal data
        personal_data = user_profile.get('personal_data', {})
        
        # Name fields
        if any(term in field_id_lower or term in label_lower for term in ['first_name', 'firstname', 'fname']):
            return personal_data.get('first_name', '')
        
        if any(term in field_id_lower or term in label_lower for term in ['last_name', 'lastname', 'lname']):
            return personal_data.get('last_name', '')
        
        if any(term in field_id_lower or term in label_lower for term in ['full_name', 'fullname', 'name']):
            first = personal_data.get('first_name', '')
            last = personal_data.get('last_name', '')
            if first and last:
                return f"{first} {last}"
            return first or last
        
        # Contact information
        if any(term in field_id_lower or term in label_lower for term in ['email', 'e-mail']):
            return user_profile.get('email', '')
        
        if any(term in field_id_lower or term in label_lower for term in ['phone', 'telephone', 'mobile']):
            return personal_data.get('phone', '')
        
        # Address fields
        if any(term in field_id_lower or term in label_lower for term in ['address', 'street']):
            return personal_data.get('address', '')
        
        if any(term in field_id_lower or term in label_lower for term in ['city', 'town']):
            return personal_data.get('city', '')
        
        if any(term in field_id_lower or term in label_lower for term in ['state', 'province']):
            return personal_data.get('state', '')
        
        if any(term in field_id_lower or term in label_lower for term in ['zip', 'postal', 'postcode']):
            return personal_data.get('zip_code', '')
        
        if any(term in field_id_lower or term in label_lower for term in ['country']):
            return personal_data.get('country', '')
        
        # Education
        if any(term in field_id_lower or term in label_lower for term in ['education', 'degree']):
            education = personal_data.get('education', [])
            if education and isinstance(education, list) and len(education) > 0:
                edu = education[0]
                return f"{edu.get('degree', '')} in {edu.get('field', '')} from {edu.get('institution', '')}"
            return ''
        
        # Experience
        if any(term in field_id_lower or term in label_lower for term in ['experience', 'work history']):
            experience = personal_data.get('experience', [])
            if experience and isinstance(experience, list) and len(experience) > 0:
                exp = experience[0]
                return f"{exp.get('position', '')} at {exp.get('company', '')}: {exp.get('description', '')}"
            return ''
        
        # Skills
        if any(term in field_id_lower or term in label_lower for term in ['skills', 'abilities']):
            skills = personal_data.get('skills', [])
            if skills and isinstance(skills, list):
                return ', '.join(skills[:5])  # Return top 5 skills
            return ''
        
        # No direct mapping found
        return None
    
    def _convert_field_to_question(self, field: FormField) -> str:
        """Convert a form field to a question for AI response generation.
        
        Args:
            field: Form field information
            
        Returns:
            str: Question for AI service
        """
        label = field.label.strip()
        
        # Remove trailing colon if present
        if label.endswith(':'):
            label = label[:-1]
        
        # Check if label is already a question
        if label.endswith('?'):
            return label
        
        # Convert common field types to questions
        if any(term in label.lower() for term in ['name', 'email', 'phone', 'address']):
            return f"What is your {label}?"
        
        if any(term in label.lower() for term in ['experience', 'background']):
            return f"Describe your {label}."
        
        if any(term in label.lower() for term in ['skills', 'abilities']):
            return f"What {label} do you have?"
        
        if any(term in label.lower() for term in ['education', 'degree']):
            return f"What is your {label}?"
        
        if any(term in label.lower() for term in ['why', 'reason']):
            return f"{label}?"
        
        # Generic conversion for other fields
        return f"Please provide information about: {label}"
    
    def _format_response_for_field_type(self, response: str, field: FormField) -> str:
        """Format a response based on field type.
        
        Args:
            response: Generated response
            field: Form field information
            
        Returns:
            str: Formatted response
        """
        # Handle different field types
        if field.field_type == FormField.TEXT:
            # For text fields, extract first sentence or truncate
            sentences = re.split(r'[.!?]\s+', response)
            if sentences:
                return sentences[0].strip()
            return response[:50].strip()
        
        elif field.field_type == FormField.TEXTAREA:
            # For textareas, use full response but ensure reasonable length
            if len(response) > 500:
                return response[:500].strip()
            return response.strip()
        
        elif field.field_type == FormField.SELECT:
            # For select fields, try to match response to an option
            if field.options:
                # Find option that best matches the response
                best_match = None
                best_score = 0
                
                for option in field.options:
                    # Calculate simple match score
                    option_lower = option.lower()
                    response_lower = response.lower()
                    
                    if option_lower in response_lower:
                        score = len(option_lower) / len(response_lower)
                        if score > best_score:
                            best_score = score
                            best_match = option
                
                if best_match:
                    return best_match
                
                # If no good match, return first option for required fields
                if field.required and field.options:
                    return field.options[0]
            
            return ""
        
        elif field.field_type == FormField.RADIO:
            # Similar to select, try to match to an option
            if field.options:
                for option in field.options:
                    if option.lower() in response.lower():
                        return option
                
                # If no match and required, return first option
                if field.required and field.options:
                    return field.options[0]
            
            return ""
        
        elif field.field_type == FormField.CHECKBOX:
            # For checkboxes, can select multiple options
            selected = []
            
            if field.options:
                for option in field.options:
                    if option.lower() in response.lower():
                        selected.append(option)
                
                # If required and nothing selected, select first option
                if field.required and not selected and field.options:
                    selected.append(field.options[0])
            
            return selected
        
        # Default case
        return response.strip()
    
    def _generate_fallback_response(self, field: FormField, user_profile: Dict) -> str:
        """Generate a fallback response when AI generation fails.
        
        Args:
            field: Form field information
            user_profile: User profile information
            
        Returns:
            str: Fallback response
        """
        # Try to map from user profile first
        user_data = self.map_user_data_to_field(field, user_profile)
        if user_data:
            return user_data
        
        # Generic fallbacks based on field type
        if field.field_type == FormField.TEXT:
            return "Information available upon request"
        
        elif field.field_type == FormField.TEXTAREA:
            return "I would be happy to discuss this further in an interview."
        
        elif field.field_type in [FormField.SELECT, FormField.RADIO]:
            if field.options and field.required:
                return field.options[0]
            return ""
        
        elif field.field_type == FormField.CHECKBOX:
            if field.options and field.required:
                return [field.options[0]]
            return []
        
        return ""
    
    def _load_common_field_patterns(self) -> Dict[str, List[str]]:
        """Load patterns for common form field types.
        
        Returns:
            Dict[str, List[str]]: Dictionary of field type -> regex patterns
        """
        return {
            "name": [
                r'name',
                r'full[-_]?name',
                r'first[-_]?name',
                r'last[-_]?name'
            ],
            "email": [
                r'email',
                r'e[-_]?mail'
            ],
            "phone": [
                r'phone',
                r'telephone',
                r'mobile',
                r'cell'
            ],
            "address": [
                r'address',
                r'street',
                r'city',
                r'state',
                r'zip',
                r'postal',
                r'country'
            ],
            "education": [
                r'education',
                r'degree',
                r'university',
                r'college',
                r'school'
            ],
            "experience": [
                r'experience',
                r'work[-_]?history',
                r'employment',
                r'job[-_]?history'
            ],
            "skills": [
                r'skills',
                r'abilities',
                r'qualifications',
                r'competencies'
            ],
            "salary": [
                r'salary',
                r'compensation',
                r'pay',
                r'wage'
            ],
            "availability": [
                r'availability',
                r'start[-_]?date',
                r'when[-_]?available'
            ],
            "references": [
                r'references',
                r'referees',
                r'recommendations'
            ]
        }


# Create a singleton instance
form_response_generator = FormResponseGenerator()