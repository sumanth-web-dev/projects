"""
Skills service for managing skills assessments and recommendations.
"""
import datetime
import uuid
import random
from typing import Dict, List, Optional
from models.user import User
from models.database import db


class SkillsService:
    """Service for managing skills assessments."""
    
    def __init__(self):
        # Sample assessment questions by category
        self.assessment_questions = {
            'programming': [
                {
                    'text': 'What is the time complexity of binary search?',
                    'options': ['O(n)', 'O(log n)', 'O(n²)', 'O(1)'],
                    'correct': 1
                },
                {
                    'text': 'Which of the following is not a programming paradigm?',
                    'options': ['Object-oriented', 'Functional', 'Procedural', 'Algorithmic'],
                    'correct': 3
                },
                {
                    'text': 'What does SQL stand for?',
                    'options': ['Structured Query Language', 'Simple Query Language', 'Standard Query Language', 'System Query Language'],
                    'correct': 0
                }
            ],
            'web-development': [
                {
                    'text': 'Which HTML tag is used for the largest heading?',
                    'options': ['<h6>', '<h1>', '<header>', '<head>'],
                    'correct': 1
                },
                {
                    'text': 'What does CSS stand for?',
                    'options': ['Computer Style Sheets', 'Cascading Style Sheets', 'Creative Style Sheets', 'Colorful Style Sheets'],
                    'correct': 1
                },
                {
                    'text': 'Which JavaScript method is used to add an element to the end of an array?',
                    'options': ['push()', 'pop()', 'shift()', 'unshift()'],
                    'correct': 0
                }
            ],
            'data-science': [
                {
                    'text': 'What is the purpose of cross-validation in machine learning?',
                    'options': ['To increase model complexity', 'To evaluate model performance', 'To reduce dataset size', 'To speed up training'],
                    'correct': 1
                },
                {
                    'text': 'Which Python library is commonly used for data manipulation?',
                    'options': ['NumPy', 'Pandas', 'Matplotlib', 'Scikit-learn'],
                    'correct': 1
                },
                {
                    'text': 'What does API stand for?',
                    'options': ['Application Programming Interface', 'Advanced Programming Interface', 'Automated Programming Interface', 'Applied Programming Interface'],
                    'correct': 0
                }
            ],
            'soft-skills': [
                {
                    'text': 'What is the most important aspect of effective communication?',
                    'options': ['Speaking loudly', 'Active listening', 'Using complex vocabulary', 'Talking frequently'],
                    'correct': 1
                },
                {
                    'text': 'Which approach is best for resolving team conflicts?',
                    'options': ['Avoiding the issue', 'Taking sides', 'Open discussion and compromise', 'Escalating to management immediately'],
                    'correct': 2
                },
                {
                    'text': 'What is a key characteristic of effective leadership?',
                    'options': ['Micromanaging', 'Empowering team members', 'Making all decisions alone', 'Avoiding feedback'],
                    'correct': 1
                }
            ]
        }
    
    def get_assessment_stats(self, user_id: str) -> Dict:
        """Get assessment statistics for a user."""
        try:
            user = User.query.get(user_id)
            if not user:
                return {}
            
            personal_data = user.personal_data or {}
            assessments = personal_data.get('assessments', {})
            
            total_assessments = len(assessments)
            
            if total_assessments > 0:
                scores = [assessment.get('score', 0) for assessment in assessments.values()]
                average_score = sum(scores) / len(scores)
            else:
                average_score = 0
            
            # Count certifications (assessments with score >= 80)
            certifications_earned = sum(1 for assessment in assessments.values() 
                                      if assessment.get('score', 0) >= 80)
            
            return {
                'total_assessments': total_assessments,
                'average_score': round(average_score),
                'certifications_earned': certifications_earned
            }
        
        except Exception as e:
            return {
                'total_assessments': 0,
                'average_score': 0,
                'certifications_earned': 0
            }
    
    def get_assessment_history(self, user_id: str) -> List[Dict]:
        """Get assessment history for a user."""
        try:
            user = User.query.get(user_id)
            if not user:
                return []
            
            personal_data = user.personal_data or {}
            assessments = personal_data.get('assessments', {})
            
            history = []
            for category, assessment in assessments.items():
                score = assessment.get('score', 0)
                score_class = 'excellent' if score >= 90 else 'good' if score >= 70 else 'average' if score >= 50 else 'poor'
                
                history.append({
                    'id': assessment.get('id', category),
                    'category': category,
                    'score': score,
                    'score_class': score_class,
                    'completed_at': assessment.get('completed_at', datetime.datetime.utcnow())
                })
            
            # Sort by completion date (most recent first)
            history.sort(key=lambda x: x['completed_at'], reverse=True)
            
            return history
        
        except Exception as e:
            return []
    
    def get_skills_radar_data(self, user_id: str) -> Dict:
        """Get skills data for radar chart."""
        try:
            user = User.query.get(user_id)
            if not user:
                return {}
            
            personal_data = user.personal_data or {}
            assessments = personal_data.get('assessments', {})
            
            # Map assessment categories to radar chart categories
            radar_data = {
                'programming': assessments.get('programming', {}).get('score', 0),
                'web_development': assessments.get('web-development', {}).get('score', 0),
                'data_science': assessments.get('data-science', {}).get('score', 0),
                'soft_skills': assessments.get('soft-skills', {}).get('score', 0),
                'problem_solving': assessments.get('programming', {}).get('score', 0),  # Use programming as proxy
                'communication': assessments.get('soft-skills', {}).get('score', 0)  # Use soft-skills as proxy
            }
            
            return radar_data
        
        except Exception as e:
            return {
                'programming': 0,
                'web_development': 0,
                'data_science': 0,
                'soft_skills': 0,
                'problem_solving': 0,
                'communication': 0
            }
    
    def get_improvement_recommendations(self, user_id: str) -> List[Dict]:
        """Get improvement recommendations based on assessment results."""
        try:
            user = User.query.get(user_id)
            if not user:
                return []
            
            personal_data = user.personal_data or {}
            assessments = personal_data.get('assessments', {})
            
            recommendations = []
            
            # Check each skill area and provide recommendations for low scores
            skill_recommendations = {
                'programming': {
                    'threshold': 70,
                    'description': 'Improve your programming fundamentals with practice and study.',
                    'resources': [
                        {'title': 'LeetCode Practice', 'url': 'https://leetcode.com'},
                        {'title': 'Codecademy Programming Course', 'url': 'https://codecademy.com'}
                    ]
                },
                'web-development': {
                    'threshold': 70,
                    'description': 'Enhance your web development skills with modern frameworks and tools.',
                    'resources': [
                        {'title': 'FreeCodeCamp', 'url': 'https://freecodecamp.org'},
                        {'title': 'MDN Web Docs', 'url': 'https://developer.mozilla.org'}
                    ]
                },
                'data-science': {
                    'threshold': 70,
                    'description': 'Strengthen your data science knowledge with hands-on projects.',
                    'resources': [
                        {'title': 'Kaggle Learn', 'url': 'https://kaggle.com/learn'},
                        {'title': 'Coursera Data Science', 'url': 'https://coursera.org'}
                    ]
                },
                'soft-skills': {
                    'threshold': 75,
                    'description': 'Develop your communication and leadership abilities.',
                    'resources': [
                        {'title': 'Toastmasters International', 'url': 'https://toastmasters.org'},
                        {'title': 'LinkedIn Learning Soft Skills', 'url': 'https://linkedin.com/learning'}
                    ]
                }
            }
            
            for skill, config in skill_recommendations.items():
                assessment = assessments.get(skill, {})
                score = assessment.get('score', 0)
                
                if score < config['threshold']:
                    recommendations.append({
                        'skill': skill.replace('-', ' ').title(),
                        'description': config['description'],
                        'resources': config['resources']
                    })
            
            return recommendations
        
        except Exception as e:
            return []
    
    def start_assessment(self, user_id: str, category: str) -> Dict:
        """Start a new skills assessment."""
        try:
            if category not in self.assessment_questions:
                raise ValueError(f"Invalid assessment category: {category}")
            
            assessment_id = str(uuid.uuid4())
            questions = self.assessment_questions[category].copy()
            
            # Randomize question order
            random.shuffle(questions)
            
            # Remove correct answers from questions sent to client
            client_questions = []
            for i, question in enumerate(questions):
                client_questions.append({
                    'id': i,
                    'text': question['text'],
                    'options': question['options']
                })
            
            # Store assessment in session or temporary storage
            assessment_data = {
                'id': assessment_id,
                'category': category,
                'questions': questions,  # Keep full questions with answers for scoring
                'started_at': datetime.datetime.utcnow().isoformat(),
                'duration': self.get_assessment_duration(category)
            }
            
            # In a real implementation, you'd store this in Redis or database
            # For now, we'll return the data needed by the client
            
            return {
                'id': assessment_id,
                'category': category,
                'questions': client_questions,
                'duration': assessment_data['duration']
            }
        
        except Exception as e:
            raise e
    
    def submit_assessment(self, assessment_id: str, answers: List[int], user_id: str) -> Dict:
        """Submit assessment answers and calculate score."""
        try:
            # In a real implementation, you'd retrieve the assessment from storage
            # For now, we'll simulate scoring
            
            # Calculate score (placeholder implementation)
            correct_answers = 0
            total_questions = len(answers)
            
            # Simulate scoring - in reality, you'd compare with stored correct answers
            for answer in answers:
                if answer is not None and random.random() > 0.3:  # 70% chance of being correct
                    correct_answers += 1
            
            score = round((correct_answers / total_questions) * 100) if total_questions > 0 else 0
            
            # Store assessment result
            user = User.query.get(user_id)
            if user:
                personal_data = user.personal_data or {}
                if 'assessments' not in personal_data:
                    personal_data['assessments'] = {}
                
                # Determine category from assessment_id (in real implementation, get from storage)
                category = 'programming'  # Placeholder
                
                personal_data['assessments'][category] = {
                    'id': assessment_id,
                    'score': score,
                    'completed_at': datetime.datetime.utcnow().isoformat(),
                    'correct_answers': correct_answers,
                    'total_questions': total_questions
                }
                
                user.personal_data = personal_data
                db.session.commit()
            
            return {
                'score': score,
                'correct_answers': correct_answers,
                'total_questions': total_questions
            }
        
        except Exception as e:
            raise e
    
    def get_assessment_duration(self, category: str) -> int:
        """Get assessment duration in minutes."""
        durations = {
            'programming': 45,
            'web-development': 60,
            'data-science': 50,
            'soft-skills': 30
        }
        return durations.get(category, 45)
    
    def get_skill_level(self, score: int) -> str:
        """Get skill level based on score."""
        if score >= 90:
            return 'Expert'
        elif score >= 80:
            return 'Advanced'
        elif score >= 70:
            return 'Intermediate'
        elif score >= 60:
            return 'Beginner'
        else:
            return 'Novice'
    
    def generate_certificate(self, user_id: str, category: str) -> Optional[str]:
        """Generate certificate for completed assessment."""
        try:
            user = User.query.get(user_id)
            if not user:
                return None
            
            personal_data = user.personal_data or {}
            assessments = personal_data.get('assessments', {})
            
            if category not in assessments:
                return None
            
            assessment = assessments[category]
            score = assessment.get('score', 0)
            
            if score < 80:  # Minimum score for certification
                return None
            
            # Generate certificate (placeholder implementation)
            certificate_id = str(uuid.uuid4())
            
            # In a real implementation, you'd generate a PDF certificate
            # and store it in a file system or cloud storage
            
            return certificate_id
        
        except Exception as e:
            return None