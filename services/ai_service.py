"""
AI service for generating contextual responses and analyzing job descriptions.

This module provides functionality for generating AI-powered responses to job application
questions, analyzing job descriptions for keyword matching, and selecting appropriate
templates based on job requirements.
"""
import re
import logging
import json
from typing import Dict, List, Optional, Tuple, Any, Set
from models.job import Job
from models.user import User

# Set up logging
logger = logging.getLogger(__name__)


class JobAnalysis:
    """Result of job description analysis."""
    
    def __init__(self, keywords: List[str], skills: List[str], 
                 experience_level: Optional[str] = None,
                 education_requirements: Optional[List[str]] = None,
                 job_type: Optional[str] = None):
        """Initialize JobAnalysis instance.
        
        Args:
            keywords: Extracted keywords from job description
            skills: Required skills mentioned in job description
            experience_level: Detected experience level (entry, mid, senior)
            education_requirements: Detected education requirements
            job_type: Detected job type (full-time, part-time, contract)
        """
        self.keywords = keywords
        self.skills = skills
        self.experience_level = experience_level
        self.education_requirements = education_requirements or []
        self.job_type = job_type
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert analysis to dictionary."""
        return {
            'keywords': self.keywords,
            'skills': self.skills,
            'experience_level': self.experience_level,
            'education_requirements': self.education_requirements,
            'job_type': self.job_type
        }


class JobContext:
    """Context information about a job for AI response generation."""
    
    def __init__(self, job: Job, analysis: Optional[JobAnalysis] = None):
        """Initialize JobContext instance.
        
        Args:
            job: Job model instance
            analysis: Optional pre-computed job analysis
        """
        self.job = job
        self._analysis = analysis
    
    @property
    def analysis(self) -> JobAnalysis:
        """Get job analysis, computing it if not already available."""
        if not self._analysis:
            # Lazy load analysis if not provided
            ai_service = AIService()
            self._analysis = ai_service.analyze_job_requirements(self.job.description)
        return self._analysis
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            'job': self.job.to_dict(),
            'analysis': self.analysis.to_dict() if self._analysis else None
        }


class Template:
    """Template for resume or cover letter."""
    
    def __init__(self, template_id: str, name: str, content: str, 
                 metadata: Optional[Dict[str, Any]] = None):
        """Initialize Template instance.
        
        Args:
            template_id: Unique identifier for the template
            name: Template name
            content: Template content
            metadata: Additional template metadata
        """
        self.id = template_id
        self.name = name
        self.content = content
        self.metadata = metadata or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert template to dictionary."""
        return {
            'id': self.id,
            'name': self.name,
            'metadata': self.metadata
        }


class ResponseQuality:
    """Quality assessment of an AI-generated response."""
    
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    
    def __init__(self, quality: str, confidence: float, issues: List[str] = None):
        """Initialize ResponseQuality instance.
        
        Args:
            quality: Quality level (HIGH, MEDIUM, LOW)
            confidence: Confidence score (0.0 to 1.0)
            issues: List of identified issues with the response
        """
        self.quality = quality
        self.confidence = confidence
        self.issues = issues or []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert quality assessment to dictionary."""
        return {
            'quality': self.quality,
            'confidence': self.confidence,
            'issues': self.issues
        }


class AIService:
    """Service for AI-powered job application assistance."""
    
    def __init__(self, app=None):
        """Initialize the AI service.
        
        Args:
            app: Flask application instance for configuration
        """
        self.app = app
        self._skill_keywords = self._load_skill_keywords()
        self._education_keywords = self._load_education_keywords()
        self._experience_patterns = self._load_experience_patterns()
        
        if app is not None:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize the AI service with a Flask app.
        
        Args:
            app: Flask application instance
        """
        self.app = app
    
    def generate_response(self, question: str, job_context: JobContext, 
                         user_profile: Dict) -> str:
        """Generate a contextual response to a job application question.
        
        Args:
            question: The question text
            job_context: Context information about the job
            user_profile: User profile information
            
        Returns:
            str: Generated response
        """
        try:
            # Analyze the question type
            question_type = self._analyze_question_type(question)
            
            # Extract relevant information from job and user profile
            job_info = job_context.job.to_dict()
            job_analysis = job_context.analysis
            
            # Generate response based on question type
            if question_type == "experience":
                return self._generate_experience_response(question, job_analysis, user_profile)
            elif question_type == "skills":
                return self._generate_skills_response(question, job_analysis, user_profile)
            elif question_type == "education":
                return self._generate_education_response(question, job_analysis, user_profile)
            elif question_type == "salary":
                return self._generate_salary_response(question, job_info, user_profile)
            elif question_type == "motivation":
                return self._generate_motivation_response(question, job_info, user_profile)
            elif question_type == "strength_weakness":
                return self._generate_strength_weakness_response(question, job_analysis, user_profile)
            elif question_type == "availability":
                return self._generate_availability_response(question, user_profile)
            else:
                # Generic response for other question types
                return self._generate_generic_response(question, job_context, user_profile)
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            # Fallback to a generic response
            return self._generate_fallback_response(question, user_profile)
    
    def analyze_job_requirements(self, job_description: str) -> JobAnalysis:
        """Analyze job description to extract requirements and keywords.
        
        Args:
            job_description: The job description text
            
        Returns:
            JobAnalysis: Analysis results
        """
        if not job_description:
            return JobAnalysis(keywords=[], skills=[])
        
        try:
            # Extract keywords using simple frequency analysis
            keywords = self._extract_keywords(job_description)
            
            # Extract skills mentioned in the job description
            skills = self._extract_skills(job_description)
            
            # Detect experience level
            experience_level = self._detect_experience_level(job_description)
            
            # Extract education requirements
            education_requirements = self._extract_education_requirements(job_description)
            
            # Detect job type
            job_type = self._detect_job_type(job_description)
            
            return JobAnalysis(
                keywords=keywords,
                skills=skills,
                experience_level=experience_level,
                education_requirements=education_requirements,
                job_type=job_type
            )
            
        except Exception as e:
            logger.error(f"Error analyzing job requirements: {str(e)}")
            return JobAnalysis(keywords=[], skills=[])
    
    def select_best_template(self, job: Job, templates: List[Template]) -> Template:
        """Select the most appropriate template based on job requirements.
        
        Args:
            job: Job model instance
            templates: List of available templates
            
        Returns:
            Template: Best matching template
        """
        if not templates:
            raise ValueError("No templates provided")
        
        try:
            # Analyze job requirements
            job_analysis = self.analyze_job_requirements(job.description)
            
            # Score each template based on keyword matching
            template_scores = []
            
            for template in templates:
                score = self._calculate_template_match_score(template, job_analysis)
                template_scores.append((template, score))
            
            # Sort by score (highest first)
            template_scores.sort(key=lambda x: x[1], reverse=True)
            
            # Return the highest scoring template
            return template_scores[0][0]
            
        except Exception as e:
            logger.error(f"Error selecting best template: {str(e)}")
            # Return the first template as fallback
            return templates[0]
    
    def validate_response_quality(self, response: str, question: str, 
                                job_context: JobContext) -> ResponseQuality:
        """Validate the quality of a generated response.
        
        Args:
            response: The generated response
            question: The original question
            job_context: Context information about the job
            
        Returns:
            ResponseQuality: Quality assessment
        """
        issues = []
        
        # Check response length
        if len(response) < 50:
            issues.append("Response is too short")
        elif len(response) > 500:
            issues.append("Response may be too long")
        
        # Check for keyword inclusion
        job_keywords = job_context.analysis.keywords[:5]  # Top 5 keywords
        keyword_matches = sum(1 for kw in job_keywords if kw.lower() in response.lower())
        keyword_ratio = keyword_matches / len(job_keywords) if job_keywords else 1.0
        
        if keyword_ratio < 0.3:
            issues.append("Response doesn't include enough relevant keywords")
        
        # Determine quality level based on issues
        if not issues:
            quality = ResponseQuality.HIGH
            confidence = 0.9
        elif len(issues) == 1:
            quality = ResponseQuality.MEDIUM
            confidence = 0.7
        else:
            quality = ResponseQuality.LOW
            confidence = 0.5
        
        return ResponseQuality(quality, confidence, issues)
    
    def _analyze_question_type(self, question: str) -> str:
        """Analyze the type of question being asked.
        
        Args:
            question: The question text
            
        Returns:
            str: Question type category
        """
        question_lower = question.lower()
        
        # Experience-related questions
        if any(kw in question_lower for kw in ["experience", "worked", "previous role", "background"]):
            return "experience"
        
        # Skills-related questions
        if any(kw in question_lower for kw in ["skills", "proficient", "familiar with", "expertise"]):
            return "skills"
        
        # Education-related questions
        if any(kw in question_lower for kw in ["education", "degree", "graduate", "certification"]):
            return "education"
        
        # Salary-related questions
        if any(kw in question_lower for kw in ["salary", "compensation", "pay", "expected"]):
            return "salary"
        
        # Motivation-related questions
        if any(kw in question_lower for kw in ["why", "interest", "motivation", "passionate"]):
            return "motivation"
        
        # Strengths/weaknesses questions
        if any(kw in question_lower for kw in ["strength", "weakness", "challenge", "difficult"]):
            return "strength_weakness"
        
        # Availability questions
        if any(kw in question_lower for kw in ["available", "start", "notice", "when can you"]):
            return "availability"
        
        # Default to generic
        return "generic"
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text.
        
        Args:
            text: The text to analyze
            
        Returns:
            List[str]: Extracted keywords
        """
        # Convert to lowercase and split into words
        words = re.findall(r'\b[a-zA-Z][a-zA-Z0-9_-]{2,}\b', text.lower())
        
        # Remove common stop words
        stop_words = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'any', 'can', 'had', 'has',
            'have', 'her', 'his', 'our', 'out', 'who', 'why', 'will', 'with', 'was', 'what',
            'when', 'where', 'which', 'this', 'that', 'these', 'those', 'from', 'your', 'they'
        }
        
        filtered_words = [word for word in words if word not in stop_words]
        
        # Count word frequencies
        word_counts = {}
        for word in filtered_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Sort by frequency
        sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Return top keywords (up to 20)
        return [word for word, count in sorted_words[:20]]
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills mentioned in text.
        
        Args:
            text: The text to analyze
            
        Returns:
            List[str]: Extracted skills
        """
        text_lower = text.lower()
        found_skills = set()
        
        # Look for skills in the text
        for skill in self._skill_keywords:
            if skill.lower() in text_lower:
                found_skills.add(skill)
        
        # Look for common skill patterns
        skill_patterns = [
            r'experience (?:with|in) ([a-zA-Z0-9_\-\+\#]+)',
            r'knowledge of ([a-zA-Z0-9_\-\+\#]+)',
            r'proficient (?:with|in) ([a-zA-Z0-9_\-\+\#]+)',
            r'familiar with ([a-zA-Z0-9_\-\+\#]+)',
            r'skills in ([a-zA-Z0-9_\-\+\#]+)'
        ]
        
        for pattern in skill_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                if len(match) > 2:  # Avoid short matches
                    found_skills.add(match.capitalize())
        
        return sorted(list(found_skills))
    
    def _detect_experience_level(self, text: str) -> Optional[str]:
        """Detect required experience level from text.
        
        Args:
            text: The text to analyze
            
        Returns:
            Optional[str]: Detected experience level or None
        """
        text_lower = text.lower()
        
        # Check for entry-level indicators
        entry_patterns = [
            r'\bentry[- ]level\b',
            r'\bjunior\b',
            r'\b0-2 years\b',
            r'\bless than 2 years\b',
            r'\bno experience\b',
            r'\brecent graduate\b'
        ]
        
        # Check for mid-level indicators
        mid_patterns = [
            r'\bmid[- ]level\b',
            r'\bintermediate\b',
            r'\b2-5 years\b',
            r'\b3-5 years\b'
        ]
        
        # Check for senior-level indicators
        senior_patterns = [
            r'\bsenior\b',
            r'\blead\b',
            r'\b5\+? years\b',
            r'\b7\+? years\b',
            r'\b10\+? years\b',
            r'\bextensive experience\b'
        ]
        
        # Check patterns in order of specificity
        for pattern in senior_patterns:
            if re.search(pattern, text_lower):
                return "senior"
        
        for pattern in mid_patterns:
            if re.search(pattern, text_lower):
                return "mid"
        
        for pattern in entry_patterns:
            if re.search(pattern, text_lower):
                return "entry"
        
        return None
    
    def _extract_education_requirements(self, text: str) -> List[str]:
        """Extract education requirements from text.
        
        Args:
            text: The text to analyze
            
        Returns:
            List[str]: Extracted education requirements
        """
        text_lower = text.lower()
        requirements = []
        
        # Look for degree requirements
        degree_patterns = [
            r"bachelor'?s degree",
            r"master'?s degree",
            r"phd",
            r"doctorate",
            r"associate'?s degree",
            r"high school diploma",
            r"ged"
        ]
        
        for pattern in degree_patterns:
            if re.search(pattern, text_lower):
                requirements.append(pattern.capitalize())
        
        # Look for field of study
        if requirements and re.search(r"(?:degree|education) in ([a-zA-Z, ]+)", text_lower):
            matches = re.findall(r"(?:degree|education) in ([a-zA-Z, ]+)", text_lower)
            if matches:
                field = matches[0].strip()
                if field and len(field) > 2:
                    requirements.append(f"Field: {field.capitalize()}")
        
        return requirements
    
    def _detect_job_type(self, text: str) -> Optional[str]:
        """Detect job type from text.
        
        Args:
            text: The text to analyze
            
        Returns:
            Optional[str]: Detected job type or None
        """
        text_lower = text.lower()
        
        if re.search(r"full[- ]time", text_lower):
            return "full-time"
        elif re.search(r"part[- ]time", text_lower):
            return "part-time"
        elif re.search(r"contract", text_lower):
            return "contract"
        elif re.search(r"freelance", text_lower):
            return "freelance"
        elif re.search(r"internship", text_lower):
            return "internship"
        elif re.search(r"temporary", text_lower):
            return "temporary"
        
        return None
    
    def _calculate_template_match_score(self, template: Template, job_analysis: JobAnalysis) -> float:
        """Calculate how well a template matches job requirements.
        
        Args:
            template: Template to evaluate
            job_analysis: Job requirement analysis
            
        Returns:
            float: Match score (higher is better)
        """
        score = 0.0
        
        # Check template metadata for target job types
        if 'target_job_types' in template.metadata:
            target_types = template.metadata['target_job_types']
            if job_analysis.job_type in target_types:
                score += 2.0
        
        # Check template metadata for target experience levels
        if 'target_experience_levels' in template.metadata:
            target_levels = template.metadata['target_experience_levels']
            if job_analysis.experience_level in target_levels:
                score += 1.5
        
        # Check template metadata for target skills
        if 'target_skills' in template.metadata:
            target_skills = set(s.lower() for s in template.metadata['target_skills'])
            job_skills = set(s.lower() for s in job_analysis.skills)
            
            # Calculate skill overlap
            common_skills = target_skills.intersection(job_skills)
            if common_skills:
                skill_score = len(common_skills) / max(len(target_skills), 1)
                score += skill_score * 3.0
        
        # Check template content for keyword matches
        template_text = template.content.lower()
        keyword_matches = sum(1 for kw in job_analysis.keywords if kw.lower() in template_text)
        keyword_score = keyword_matches / max(len(job_analysis.keywords), 1)
        score += keyword_score * 2.0
        
        return score
    
    def _generate_experience_response(self, question: str, job_analysis: JobAnalysis, 
                                    user_profile: Dict) -> str:
        """Generate response to experience-related questions.
        
        Args:
            question: The question text
            job_analysis: Job requirement analysis
            user_profile: User profile information
            
        Returns:
            str: Generated response
        """
        # Extract user experience from profile
        experience = user_profile.get('personal_data', {}).get('experience', [])
        
        if not experience:
            return "I have relevant experience that aligns with this position's requirements. My background includes developing skills in problem-solving, collaboration, and delivering results in fast-paced environments."
        
        # Find most relevant experience based on job skills
        relevant_exp = []
        for exp in experience:
            # Calculate relevance score based on skill overlap
            exp_description = exp.get('description', '').lower()
            skill_matches = sum(1 for skill in job_analysis.skills if skill.lower() in exp_description)
            if skill_matches > 0:
                relevant_exp.append((exp, skill_matches))
        
        # Sort by relevance
        relevant_exp.sort(key=lambda x: x[1], reverse=True)
        
        # Generate response using most relevant experiences
        if relevant_exp:
            top_exp = relevant_exp[0][0]
            company = top_exp.get('company', 'my previous company')
            position = top_exp.get('position', 'my previous role')
            
            response = f"I have relevant experience from my time as {position} at {company}. "
            response += f"In this role, I {top_exp.get('description', 'developed skills relevant to this position')}. "
            
            # Add second most relevant experience if available
            if len(relevant_exp) > 1:
                second_exp = relevant_exp[1][0]
                response += f"Additionally, as {second_exp.get('position', 'a professional')} at {second_exp.get('company', 'another organization')}, "
                response += f"I gained experience in {second_exp.get('description', 'areas relevant to this role')}."
            
            return response
        else:
            # Fallback response
            return "My professional experience includes developing skills in " + ", ".join(job_analysis.skills[:3]) + " and other areas relevant to this position. I've consistently demonstrated the ability to learn quickly and apply my knowledge effectively to achieve results."
    
    def _generate_skills_response(self, question: str, job_analysis: JobAnalysis, 
                                user_profile: Dict) -> str:
        """Generate response to skills-related questions.
        
        Args:
            question: The question text
            job_analysis: Job requirement analysis
            user_profile: User profile information
            
        Returns:
            str: Generated response
        """
        # Extract user skills from profile
        user_skills = user_profile.get('personal_data', {}).get('skills', [])
        
        # Find matching skills between user and job requirements
        matching_skills = []
        for skill in job_analysis.skills:
            if any(user_skill.lower() == skill.lower() for user_skill in user_skills):
                matching_skills.append(skill)
        
        # Generate response based on matching skills
        if matching_skills:
            response = f"I am proficient in {', '.join(matching_skills[:3])}"
            if len(matching_skills) > 3:
                response += f", and have experience with {', '.join(matching_skills[3:5])}"
            response += ". "
            
            # Add context about how skills were applied
            response += "I've applied these skills in professional settings to deliver results and solve complex problems. "
            response += "I'm also committed to continuous learning and staying updated with industry best practices."
            
            return response
        else:
            # Fallback response highlighting adaptability
            return f"I have a diverse skill set that includes technical proficiency in areas relevant to this role. While I may not have experience with every tool mentioned, I'm a quick learner who adapts rapidly to new technologies and methodologies. My core strengths include problem-solving, attention to detail, and the ability to collaborate effectively with cross-functional teams."
    
    def _generate_education_response(self, question: str, job_analysis: JobAnalysis, 
                                   user_profile: Dict) -> str:
        """Generate response to education-related questions.
        
        Args:
            question: The question text
            job_analysis: Job requirement analysis
            user_profile: User profile information
            
        Returns:
            str: Generated response
        """
        # Extract user education from profile
        education = user_profile.get('personal_data', {}).get('education', [])
        
        if education:
            # Use the highest/most recent education
            edu = education[0]
            degree = edu.get('degree', 'degree')
            field = edu.get('field', 'relevant field')
            institution = edu.get('institution', 'my educational institution')
            
            response = f"I hold a {degree} in {field} from {institution}. "
            response += "This education provided me with a strong foundation in theoretical knowledge and practical skills that are directly applicable to this position. "
            
            # Add information about continuing education if available
            if len(education) > 1:
                response += f"I've also completed {education[1].get('degree', 'additional coursework')} in {education[1].get('field', 'a related area')}. "
            
            response += "I believe in continuous learning and regularly update my skills through professional development opportunities."
            
            return response
        else:
            # Fallback response
            return "My educational background has equipped me with the knowledge and skills necessary for this role. I've supplemented my formal education with practical experience and continuous learning through professional development opportunities, allowing me to stay current with industry trends and best practices."
    
    def _generate_salary_response(self, question: str, job_info: Dict, 
                                user_profile: Dict) -> str:
        """Generate response to salary-related questions.
        
        Args:
            question: The question text
            job_info: Job information
            user_profile: User profile information
            
        Returns:
            str: Generated response
        """
        # Get user's salary expectations from preferences
        preferences = user_profile.get('preferences', {})
        min_salary = preferences.get('salary_min')
        max_salary = preferences.get('salary_max')
        
        # Get job's salary range if available
        job_salary = job_info.get('salary_range', {})
        job_min = job_salary.get('min')
        job_max = job_salary.get('max')
        
        if min_salary and max_salary:
            # User has specified salary range
            response = f"Based on my experience and the market value for this role, I'm looking for a salary in the range of ${min_salary:,.0f} to ${max_salary:,.0f}. "
            response += "However, I'm flexible and open to discussing compensation based on the overall benefits package and growth opportunities."
            
            return response
        elif job_min and job_max:
            # Job has specified salary range
            response = f"I've researched the market rates for this position, and I understand the typical range is around ${job_min:,.0f} to ${job_max:,.0f}. "
            response += "My expectations align with this range, considering my experience and the value I can bring to your organization. I'm also interested in the complete compensation package, including benefits and growth opportunities."
            
            return response
        else:
            # No specific ranges available
            return "My salary expectations are flexible and based on the total compensation package, including benefits and growth opportunities. I've researched market rates for similar positions and would be happy to discuss specific numbers that align with your company's compensation structure and the responsibilities of this role."
    
    def _generate_motivation_response(self, question: str, job_info: Dict, 
                                    user_profile: Dict) -> str:
        """Generate response to motivation-related questions.
        
        Args:
            question: The question text
            job_info: Job information
            user_profile: User profile information
            
        Returns:
            str: Generated response
        """
        company = job_info.get('company', 'your company')
        title = job_info.get('title', 'this position')
        
        response = f"I'm particularly interested in {title} at {company} because it aligns with my professional goals and strengths. "
        response += f"What attracts me most is the opportunity to apply my skills in a challenging environment while contributing to {company}'s mission. "
        response += "I've researched your organization and am impressed by your innovative approach and commitment to excellence. "
        response += "I believe my background in " + ", ".join(user_profile.get('personal_data', {}).get('skills', [])[:2]) + " makes me well-suited to make meaningful contributions to your team."
        
        return response
    
    def _generate_strength_weakness_response(self, question: str, job_analysis: JobAnalysis, 
                                           user_profile: Dict) -> str:
        """Generate response to strength/weakness questions.
        
        Args:
            question: The question text
            job_analysis: Job requirement analysis
            user_profile: User profile information
            
        Returns:
            str: Generated response
        """
        question_lower = question.lower()
        
        if "strength" in question_lower:
            # Strength question
            user_skills = user_profile.get('personal_data', {}).get('skills', [])
            
            # Find matching skills between user and job requirements
            matching_skills = []
            for skill in job_analysis.skills:
                if any(user_skill.lower() == skill.lower() for user_skill in user_skills):
                    matching_skills.append(skill)
            
            if matching_skills:
                primary_strength = matching_skills[0]
                response = f"One of my greatest strengths is my expertise in {primary_strength}. "
                response += "I've consistently applied this skill to deliver results and solve complex problems. "
                
                if len(matching_skills) > 1:
                    response += f"Additionally, my abilities in {matching_skills[1]} complement this strength and allow me to approach challenges from multiple perspectives. "
                
                response += "I also pride myself on my adaptability and commitment to continuous improvement, which has helped me stay effective in rapidly changing environments."
                
                return response
            else:
                # Fallback strength response
                return "My greatest strength is my ability to quickly adapt to new challenges and learn what's needed to be effective. I combine this adaptability with strong analytical skills and attention to detail, allowing me to identify solutions to complex problems. I'm also a collaborative team player who communicates effectively across different stakeholders and technical levels."
        
        elif "weakness" in question_lower:
            # Weakness question
            response = "I believe in continuous improvement, so I regularly reflect on areas where I can grow. "
            response += "One area I've been working on is delegating tasks more effectively. I tend to take on significant responsibility to ensure quality, but I've learned that empowering team members not only distributes the workload but also helps others develop their skills. "
            response += "To address this, I've implemented structured delegation processes and regular check-ins that allow me to maintain quality while developing my team's capabilities."
            
            return response
        
        else:
            # Generic strength/weakness response
            return "I approach my professional development by leveraging my strengths while continuously working on areas for improvement. My key strengths include problem-solving, adaptability, and effective communication. As for areas of development, I've been working on enhancing my project management skills by implementing more structured planning processes and utilizing specialized tools to track progress and dependencies more effectively."
    
    def _generate_availability_response(self, question: str, user_profile: Dict) -> str:
        """Generate response to availability questions.
        
        Args:
            question: The question text
            user_profile: User profile information
            
        Returns:
            str: Generated response
        """
        # Check if user has specified availability in preferences
        preferences = user_profile.get('preferences', {})
        notice_period = preferences.get('notice_period', '2 weeks')
        
        response = f"I could be available to start within {notice_period} of receiving an offer. "
        response += "I'm committed to ensuring a smooth transition from my current obligations and would be happy to discuss specific timing that works for your onboarding process."
        
        return response
    
    def _generate_generic_response(self, question: str, job_context: JobContext, 
                                 user_profile: Dict) -> str:
        """Generate response to generic questions.
        
        Args:
            question: The question text
            job_context: Context information about the job
            user_profile: User profile information
            
        Returns:
            str: Generated response
        """
        # Extract key information
        job_title = job_context.job.title
        company = job_context.job.company
        skills = job_context.analysis.skills[:3]
        
        # Generate a contextual response
        response = f"Regarding your question about {question.strip().lower()}, I believe my background aligns well with what you're looking for in a {job_title} candidate. "
        
        if skills:
            response += f"My experience with {', '.join(skills)} has prepared me to contribute effectively to {company}. "
        
        response += "I'm enthusiastic about this opportunity and confident that my skills and approach would be valuable to your team."
        
        return response
    
    def _generate_fallback_response(self, question: str, user_profile: Dict) -> str:
        """Generate fallback response when other methods fail.
        
        Args:
            question: The question text
            user_profile: User profile information
            
        Returns:
            str: Generated response
        """
        return "I appreciate this question about my background and qualifications. Based on my experience and skills, I believe I can provide value in this role through my combination of technical knowledge, problem-solving abilities, and collaborative approach. I'm happy to elaborate on specific aspects of my background that are most relevant to your needs."
    
    def _load_skill_keywords(self) -> List[str]:
        """Load list of common skills for detection.
        
        Returns:
            List[str]: List of skill keywords
        """
        # This would ideally load from a configuration file or database
        # For now, we'll use a hardcoded list of common technical skills
        return [
            "Python", "JavaScript", "Java", "C#", "C++", "Ruby", "PHP", "Swift", "Kotlin",
            "React", "Angular", "Vue", "Node.js", "Django", "Flask", "Spring", "ASP.NET",
            "SQL", "MongoDB", "PostgreSQL", "MySQL", "Oracle", "Redis", "Elasticsearch",
            "AWS", "Azure", "Google Cloud", "Docker", "Kubernetes", "Jenkins", "Git",
            "Machine Learning", "Data Analysis", "AI", "Deep Learning", "NLP",
            "Project Management", "Agile", "Scrum", "Kanban", "DevOps", "CI/CD",
            "UI/UX Design", "Responsive Design", "Mobile Development", "RESTful API",
            "GraphQL", "Microservices", "Serverless", "Blockchain", "Cybersecurity",
            "Network Security", "Penetration Testing", "Compliance", "GDPR",
            "Technical Writing", "Data Visualization", "Business Intelligence",
            "Leadership", "Team Management", "Strategic Planning", "Communication",
            "Problem Solving", "Critical Thinking", "Creativity", "Collaboration"
        ]
    
    def _load_education_keywords(self) -> List[str]:
        """Load list of common education terms for detection.
        
        Returns:
            List[str]: List of education keywords
        """
        # This would ideally load from a configuration file or database
        return [
            "Bachelor's", "Master's", "PhD", "Doctorate", "Associate's", "Diploma",
            "Certificate", "Degree", "Computer Science", "Engineering", "Business",
            "Mathematics", "Statistics", "Information Technology", "Data Science",
            "MBA", "Economics", "Finance", "Marketing", "Psychology", "Education"
        ]
    
    def _load_experience_patterns(self) -> Dict[str, List[str]]:
        """Load patterns for experience level detection.
        
        Returns:
            Dict[str, List[str]]: Dictionary of experience level patterns
        """
        # This would ideally load from a configuration file or database
        return {
            "entry": [
                r'entry[- ]level',
                r'junior',
                r'0-2 years',
                r'less than 2 years',
                r'no experience',
                r'recent graduate'
            ],
            "mid": [
                r'mid[- ]level',
                r'intermediate',
                r'2-5 years',
                r'3-5 years'
            ],
            "senior": [
                r'senior',
                r'lead',
                r'5\+? years',
                r'7\+? years',
                r'10\+? years',
                r'extensive experience'
            ]
        }


# Create a singleton instance
ai_service = AIService()