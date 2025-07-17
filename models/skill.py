"""
Skill model for the Job Application Agent.
"""
import json
from datetime import datetime
from typing import Dict, List, Optional
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, Float, ForeignKey
from sqlalchemy.orm import relationship
from models.database import db


class Skill(db.Model):
    """Model for skills in the system."""
    
    __tablename__ = 'skills'
    
    id = Column(String(36), primary_key=True)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def __init__(self, id: str, name: str, description: Optional[str] = None, category: Optional[str] = None):
        """Initialize Skill instance."""
        self.id = id
        self.name = name
        self.description = description
        self.category = category
    
    def to_dict(self) -> Dict:
        """Convert skill to dictionary representation."""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class UserSkill(db.Model):
    """Model for user skills."""
    
    __tablename__ = 'user_skills'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    skill_id = Column(String(36), ForeignKey('skills.id'), nullable=False)
    proficiency_level = Column(Integer, default=1, nullable=False)  # 1-5 scale
    years_experience = Column(Float, nullable=True)
    is_verified = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", backref="skills")
    skill = relationship("Skill")
    
    def __init__(self, id: str, user_id: str, skill_id: str, proficiency_level: int = 1, **kwargs):
        """Initialize UserSkill instance."""
        self.id = id
        self.user_id = user_id
        self.skill_id = skill_id
        self.proficiency_level = proficiency_level
        
        # Set optional fields from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self, include_skill: bool = True) -> Dict:
        """Convert user skill to dictionary representation."""
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'skill_id': self.skill_id,
            'proficiency_level': self.proficiency_level,
            'years_experience': self.years_experience,
            'is_verified': self.is_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_skill and self.skill:
            result['skill'] = self.skill.to_dict()
        
        return result


class SkillAssessment(db.Model):
    """Model for skill assessments."""
    
    __tablename__ = 'skill_assessments'
    
    id = Column(String(36), primary_key=True)
    skill_id = Column(String(36), ForeignKey('skills.id'), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    difficulty_level = Column(Integer, default=1, nullable=False)  # 1-5 scale
    time_limit_minutes = Column(Integer, nullable=True)
    passing_score = Column(Float, nullable=True)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    skill = relationship("Skill")
    questions = relationship("AssessmentQuestion", back_populates="assessment", cascade="all, delete-orphan")
    attempts = relationship("AssessmentAttempt", back_populates="assessment", cascade="all, delete-orphan")
    
    # JSON fields
    _meta_data = Column('meta_data', Text, nullable=True)
    
    def __init__(self, id: str, skill_id: str, name: str, **kwargs):
        """Initialize SkillAssessment instance."""
        self.id = id
        self.skill_id = skill_id
        self.name = name
        
        # Set optional fields from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @property
    def meta_data(self) -> Dict:
        """Get meta data as dictionary."""
        if not self._meta_data:
            return {}
        try:
            return json.loads(self._meta_data)
        except json.JSONDecodeError:
            return {}
    
    @meta_data.setter
    def meta_data(self, data: Dict):
        """Set meta data from dictionary."""
        if data:
            self._meta_data = json.dumps(data)
        else:
            self._meta_data = None
    
    def to_dict(self, include_questions: bool = False) -> Dict:
        """Convert assessment to dictionary representation."""
        result = {
            'id': self.id,
            'skill_id': self.skill_id,
            'name': self.name,
            'description': self.description,
            'difficulty_level': self.difficulty_level,
            'time_limit_minutes': self.time_limit_minutes,
            'passing_score': self.passing_score,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'meta_data': self.meta_data
        }
        
        if include_questions:
            result['questions'] = [question.to_dict() for question in self.questions]
        
        return result


class AssessmentQuestion(db.Model):
    """Model for assessment questions."""
    
    __tablename__ = 'assessment_questions'
    
    id = Column(String(36), primary_key=True)
    assessment_id = Column(String(36), ForeignKey('skill_assessments.id'), nullable=False)
    question_text = Column(Text, nullable=False)
    question_type = Column(String(50), nullable=False)  # Multiple choice, True/False, etc.
    points = Column(Float, default=1.0, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    assessment = relationship("SkillAssessment", back_populates="questions")
    options = relationship("QuestionOption", back_populates="question", cascade="all, delete-orphan")
    
    # JSON fields
    _meta_data = Column('meta_data', Text, nullable=True)
    
    def __init__(self, id: str, assessment_id: str, question_text: str, question_type: str, **kwargs):
        """Initialize AssessmentQuestion instance."""
        self.id = id
        self.assessment_id = assessment_id
        self.question_text = question_text
        self.question_type = question_type
        
        # Set optional fields from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @property
    def meta_data(self) -> Dict:
        """Get meta data as dictionary."""
        if not self._meta_data:
            return {}
        try:
            return json.loads(self._meta_data)
        except json.JSONDecodeError:
            return {}
    
    @meta_data.setter
    def meta_data(self, data: Dict):
        """Set meta data from dictionary."""
        if data:
            self._meta_data = json.dumps(data)
        else:
            self._meta_data = None
    
    def to_dict(self, include_options: bool = True) -> Dict:
        """Convert question to dictionary representation."""
        result = {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'question_text': self.question_text,
            'question_type': self.question_type,
            'points': self.points,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'meta_data': self.meta_data
        }
        
        if include_options:
            result['options'] = [option.to_dict() for option in self.options]
        
        return result


class QuestionOption(db.Model):
    """Model for question options."""
    
    __tablename__ = 'question_options'
    
    id = Column(String(36), primary_key=True)
    question_id = Column(String(36), ForeignKey('assessment_questions.id'), nullable=False)
    option_text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    question = relationship("AssessmentQuestion", back_populates="options")
    
    def __init__(self, id: str, question_id: str, option_text: str, is_correct: bool = False):
        """Initialize QuestionOption instance."""
        self.id = id
        self.question_id = question_id
        self.option_text = option_text
        self.is_correct = is_correct
    
    def to_dict(self, include_is_correct: bool = False) -> Dict:
        """Convert option to dictionary representation."""
        result = {
            'id': self.id,
            'question_id': self.question_id,
            'option_text': self.option_text,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }
        
        # Only include is_correct for admin views
        if include_is_correct:
            result['is_correct'] = self.is_correct
        
        return result


class AssessmentAttempt(db.Model):
    """Model for user assessment attempts."""
    
    __tablename__ = 'assessment_attempts'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    assessment_id = Column(String(36), ForeignKey('skill_assessments.id'), nullable=False)
    start_time = Column(DateTime, default=datetime.utcnow, nullable=False)
    end_time = Column(DateTime, nullable=True)
    score = Column(Float, nullable=True)
    passed = Column(Boolean, nullable=True)
    
    # Relationships
    user = relationship("User")
    assessment = relationship("SkillAssessment", back_populates="attempts")
    answers = relationship("UserAnswer", back_populates="attempt", cascade="all, delete-orphan")
    
    def __init__(self, id: str, user_id: str, assessment_id: str):
        """Initialize AssessmentAttempt instance."""
        self.id = id
        self.user_id = user_id
        self.assessment_id = assessment_id
    
    def complete(self, score: float, passed: bool):
        """Complete the assessment attempt."""
        self.end_time = datetime.utcnow()
        self.score = score
        self.passed = passed
    
    def to_dict(self, include_answers: bool = False) -> Dict:
        """Convert attempt to dictionary representation."""
        result = {
            'id': self.id,
            'user_id': self.user_id,
            'assessment_id': self.assessment_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'score': self.score,
            'passed': self.passed
        }
        
        if include_answers:
            result['answers'] = [answer.to_dict() for answer in self.answers]
        
        return result


class UserAnswer(db.Model):
    """Model for user answers to assessment questions."""
    
    __tablename__ = 'user_answers'
    
    id = Column(String(36), primary_key=True)
    attempt_id = Column(String(36), ForeignKey('assessment_attempts.id'), nullable=False)
    question_id = Column(String(36), ForeignKey('assessment_questions.id'), nullable=False)
    selected_option_id = Column(String(36), ForeignKey('question_options.id'), nullable=True)
    text_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    points_awarded = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    attempt = relationship("AssessmentAttempt", back_populates="answers")
    question = relationship("AssessmentQuestion")
    selected_option = relationship("QuestionOption")
    
    def __init__(self, id: str, attempt_id: str, question_id: str, **kwargs):
        """Initialize UserAnswer instance."""
        self.id = id
        self.attempt_id = attempt_id
        self.question_id = question_id
        
        # Set optional fields from kwargs
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self) -> Dict:
        """Convert user answer to dictionary representation."""
        return {
            'id': self.id,
            'attempt_id': self.attempt_id,
            'question_id': self.question_id,
            'selected_option_id': self.selected_option_id,
            'text_answer': self.text_answer,
            'is_correct': self.is_correct,
            'points_awarded': self.points_awarded,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }