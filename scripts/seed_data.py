#!/usr/bin/env python3
"""
Database seed data script for the Job Application Agent.
Creates sample data for testing and development purposes.
"""
import os
import sys
import uuid
from datetime import datetime, timedelta
import click
from flask import Flask

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config, DevelopmentConfig, ProductionConfig, TestingConfig
from models.database import init_db, db
from models.user import User
from models.job import Job
from models.application import Application, ApplicationStatus


def create_app_for_seeding(config_name='development'):
    """Create Flask app instance for seeding operations."""
    app = Flask(__name__)
    
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    
    config_class = config_map.get(config_name, DevelopmentConfig)
    config_instance = config_class()
    app.config.from_object(config_instance)
    
    # Initialize database
    init_db(app)
    
    return app


def create_sample_users():
    """Create sample users for testing."""
    users_data = [
        {
            'id': str(uuid.uuid4()),
            'email': 'john.doe@example.com',
            'personal_data': {
                'first_name': 'John',
                'last_name': 'Doe',
                'phone': '+1-555-0123',
                'address': '123 Main St, San Francisco, CA 94102',
                'linkedin_url': 'https://linkedin.com/in/johndoe',
                'github_url': 'https://github.com/johndoe'
            },
            'preferences': {
                'job_titles': ['Software Engineer', 'Full Stack Developer', 'Backend Developer'],
                'locations': ['San Francisco, CA', 'Remote', 'New York, NY'],
                'salary_min': 80000,
                'salary_max': 150000,
                'experience_levels': ['mid', 'senior'],
                'remote_options': ['remote', 'hybrid'],
                'job_types': ['full-time']
            }
        },
        {
            'id': str(uuid.uuid4()),
            'email': 'jane.smith@example.com',
            'personal_data': {
                'first_name': 'Jane',
                'last_name': 'Smith',
                'phone': '+1-555-0456',
                'address': '456 Oak Ave, Austin, TX 78701',
                'linkedin_url': 'https://linkedin.com/in/janesmith',
                'portfolio_url': 'https://janesmith.dev'
            },
            'preferences': {
                'job_titles': ['Frontend Developer', 'UI/UX Developer', 'React Developer'],
                'locations': ['Austin, TX', 'Remote', 'Seattle, WA'],
                'salary_min': 70000,
                'salary_max': 130000,
                'experience_levels': ['entry', 'mid'],
                'remote_options': ['remote', 'onsite'],
                'job_types': ['full-time', 'contract']
            }
        },
        {
            'id': str(uuid.uuid4()),
            'email': 'mike.johnson@example.com',
            'personal_data': {
                'first_name': 'Mike',
                'last_name': 'Johnson',
                'phone': '+1-555-0789',
                'address': '789 Pine St, Denver, CO 80202',
                'linkedin_url': 'https://linkedin.com/in/mikejohnson'
            },
            'preferences': {
                'job_titles': ['Data Scientist', 'Machine Learning Engineer', 'AI Engineer'],
                'locations': ['Denver, CO', 'Remote', 'Boston, MA'],
                'salary_min': 90000,
                'salary_max': 180000,
                'experience_levels': ['senior'],
                'remote_options': ['remote', 'hybrid'],
                'job_types': ['full-time']
            }
        }
    ]
    
    users = []
    for user_data in users_data:
        user = User(
            id=user_data['id'],
            email=user_data['email']
        )
        user.personal_data = user_data['personal_data']
        user.preferences = user_data['preferences']
        users.append(user)
        db.session.add(user)
    
    return users


def create_sample_jobs():
    """Create sample job listings for testing."""
    jobs_data = [
        {
            'id': str(uuid.uuid4()),
            'title': 'Senior Software Engineer',
            'company': 'TechCorp Inc.',
            'location': 'San Francisco, CA',
            'description': 'We are looking for a Senior Software Engineer to join our growing team. You will be responsible for designing and implementing scalable web applications using modern technologies.',
            'requirements': [
                '5+ years of software development experience',
                'Proficiency in Python, JavaScript, or Java',
                'Experience with cloud platforms (AWS, GCP, Azure)',
                'Strong problem-solving skills',
                'Bachelor\'s degree in Computer Science or related field'
            ],
            'salary_min': 120000,
            'salary_max': 160000,
            'source_website': 'linkedin',
            'source_url': 'https://linkedin.com/jobs/view/123456789',
            'external_id': 'LI_123456789',
            'posted_date': datetime.utcnow() - timedelta(days=2),
            'job_type': 'full-time',
            'experience_level': 'senior',
            'remote_option': 'hybrid'
        },
        {
            'id': str(uuid.uuid4()),
            'title': 'Frontend Developer',
            'company': 'StartupXYZ',
            'location': 'Austin, TX',
            'description': 'Join our dynamic startup as a Frontend Developer! You\'ll work on cutting-edge user interfaces using React and modern web technologies.',
            'requirements': [
                '3+ years of frontend development experience',
                'Expert knowledge of React, HTML5, CSS3',
                'Experience with TypeScript',
                'Familiarity with modern build tools',
                'Portfolio of previous work'
            ],
            'salary_min': 80000,
            'salary_max': 110000,
            'source_website': 'indeed',
            'source_url': 'https://indeed.com/viewjob?jk=abcd1234',
            'external_id': 'IND_abcd1234',
            'posted_date': datetime.utcnow() - timedelta(days=1),
            'job_type': 'full-time',
            'experience_level': 'mid',
            'remote_option': 'onsite'
        },
        {
            'id': str(uuid.uuid4()),
            'title': 'Data Scientist',
            'company': 'DataTech Solutions',
            'location': 'Remote',
            'description': 'We\'re seeking a talented Data Scientist to help us extract insights from large datasets and build predictive models.',
            'requirements': [
                'PhD or Master\'s in Data Science, Statistics, or related field',
                'Strong programming skills in Python and R',
                'Experience with machine learning frameworks',
                'Knowledge of SQL and database systems',
                'Excellent communication skills'
            ],
            'salary_min': 100000,
            'salary_max': 140000,
            'source_website': 'glassdoor',
            'source_url': 'https://glassdoor.com/job-listing/data-scientist-xyz789',
            'external_id': 'GD_xyz789',
            'posted_date': datetime.utcnow() - timedelta(days=3),
            'job_type': 'full-time',
            'experience_level': 'senior',
            'remote_option': 'remote'
        },
        {
            'id': str(uuid.uuid4()),
            'title': 'Full Stack Developer',
            'company': 'WebDev Agency',
            'location': 'New York, NY',
            'description': 'Looking for a versatile Full Stack Developer to work on diverse client projects using various technologies.',
            'requirements': [
                '4+ years of full stack development experience',
                'Proficiency in both frontend and backend technologies',
                'Experience with databases and API development',
                'Knowledge of version control systems',
                'Ability to work in a fast-paced environment'
            ],
            'salary_min': 90000,
            'salary_max': 130000,
            'source_website': 'linkedin',
            'source_url': 'https://linkedin.com/jobs/view/987654321',
            'external_id': 'LI_987654321',
            'posted_date': datetime.utcnow() - timedelta(days=5),
            'job_type': 'full-time',
            'experience_level': 'mid',
            'remote_option': 'hybrid'
        },
        {
            'id': str(uuid.uuid4()),
            'title': 'Machine Learning Engineer',
            'company': 'AI Innovations',
            'location': 'Seattle, WA',
            'description': 'Join our AI team to develop and deploy machine learning models at scale. Work with cutting-edge technologies in a collaborative environment.',
            'requirements': [
                'Master\'s degree in Computer Science, ML, or related field',
                'Experience with TensorFlow, PyTorch, or similar frameworks',
                'Strong background in statistics and mathematics',
                'Experience with cloud ML platforms',
                '3+ years of ML engineering experience'
            ],
            'salary_min': 130000,
            'salary_max': 180000,
            'source_website': 'indeed',
            'source_url': 'https://indeed.com/viewjob?jk=ml5678',
            'external_id': 'IND_ml5678',
            'posted_date': datetime.utcnow() - timedelta(days=4),
            'job_type': 'full-time',
            'experience_level': 'senior',
            'remote_option': 'remote'
        },
        {
            'id': str(uuid.uuid4()),
            'title': 'Junior Web Developer',
            'company': 'Local Web Studio',
            'location': 'Denver, CO',
            'description': 'Great opportunity for a junior developer to grow their skills in a supportive environment. Work on various web projects for local businesses.',
            'requirements': [
                '1-2 years of web development experience',
                'Knowledge of HTML, CSS, JavaScript',
                'Basic understanding of responsive design',
                'Eagerness to learn new technologies',
                'Portfolio of personal or academic projects'
            ],
            'salary_min': 50000,
            'salary_max': 70000,
            'source_website': 'other',
            'source_url': 'https://localwebstudio.com/careers/junior-dev',
            'external_id': 'LWS_junior001',
            'posted_date': datetime.utcnow() - timedelta(days=1),
            'job_type': 'full-time',
            'experience_level': 'entry',
            'remote_option': 'onsite'
        }
    ]
    
    jobs = []
    for job_data in jobs_data:
        job = Job(
            id=job_data['id'],
            title=job_data['title'],
            company=job_data['company'],
            source_website=job_data['source_website'],
            source_url=job_data['source_url']
        )
        
        # Set all other attributes
        for key, value in job_data.items():
            if key not in ['id', 'title', 'company', 'source_website', 'source_url']:
                setattr(job, key, value)
        
        jobs.append(job)
        db.session.add(job)
    
    return jobs


def create_sample_applications(users, jobs):
    """Create sample applications for testing."""
    applications_data = [
        {
            'user_index': 0,  # John Doe
            'job_index': 0,   # Senior Software Engineer
            'status': ApplicationStatus.SUBMITTED,
            'submitted_at': datetime.utcnow() - timedelta(days=1),
            'materials_used': {
                'resume_version': 'senior_engineer_resume_v2.pdf',
                'cover_letter_version': 'techcorp_cover_letter.pdf'
            },
            'custom_responses': {
                'Why do you want to work at TechCorp?': 'I am excited about TechCorp\'s innovative approach to solving complex technical challenges and would love to contribute to your mission.',
                'Describe your experience with cloud platforms': 'I have 3+ years of experience with AWS, including EC2, S3, Lambda, and RDS. I\'ve architected and deployed several production applications.'
            },
            'application_method': 'automated',
            'confirmation_details': {
                'confirmation_id': 'TC_APP_789123',
                'confirmation_url': 'https://techcorp.com/applications/789123'
            }
        },
        {
            'user_index': 1,  # Jane Smith
            'job_index': 1,   # Frontend Developer
            'status': ApplicationStatus.IN_REVIEW,
            'submitted_at': datetime.utcnow() - timedelta(hours=12),
            'materials_used': {
                'resume_version': 'frontend_resume_v1.pdf',
                'cover_letter_version': 'startup_cover_letter.pdf',
                'portfolio_link': 'https://janesmith.dev'
            },
            'custom_responses': {
                'What interests you about frontend development?': 'I love creating intuitive user experiences and bringing designs to life through clean, efficient code.',
                'Tell us about your React experience': 'I have built several React applications including e-commerce sites and dashboard interfaces, with a focus on performance and accessibility.'
            },
            'application_method': 'automated'
        },
        {
            'user_index': 2,  # Mike Johnson
            'job_index': 2,   # Data Scientist
            'status': ApplicationStatus.PENDING,
            'materials_used': {
                'resume_version': 'data_scientist_resume_v3.pdf',
                'cover_letter_version': 'datatech_cover_letter.pdf'
            },
            'application_method': 'automated'
        },
        {
            'user_index': 0,  # John Doe
            'job_index': 3,   # Full Stack Developer
            'status': ApplicationStatus.REJECTED,
            'submitted_at': datetime.utcnow() - timedelta(days=7),
            'materials_used': {
                'resume_version': 'fullstack_resume_v1.pdf',
                'cover_letter_version': 'webdev_cover_letter.pdf'
            },
            'custom_responses': {
                'Why are you interested in agency work?': 'I enjoy the variety of projects and technologies that agency work offers, and I thrive in fast-paced environments.'
            },
            'application_method': 'automated',
            'confirmation_details': {
                'confirmation_id': 'WDA_APP_456789'
            }
        },
        {
            'user_index': 2,  # Mike Johnson
            'job_index': 4,   # Machine Learning Engineer
            'status': ApplicationStatus.INTERVIEW_SCHEDULED,
            'submitted_at': datetime.utcnow() - timedelta(days=3),
            'materials_used': {
                'resume_version': 'ml_engineer_resume_v2.pdf',
                'cover_letter_version': 'ai_innovations_cover_letter.pdf'
            },
            'custom_responses': {
                'Describe your ML experience': 'I have 4+ years of experience building and deploying ML models in production, with expertise in computer vision and NLP.',
                'What excites you about AI?': 'The potential to solve complex real-world problems and create systems that can learn and adapt fascinates me.'
            },
            'application_method': 'automated',
            'confirmation_details': {
                'confirmation_id': 'AI_APP_321654',
                'interview_scheduled': 'true',
                'interview_date': (datetime.utcnow() + timedelta(days=2)).isoformat()
            }
        },
        {
            'user_index': 1,  # Jane Smith
            'job_index': 5,   # Junior Web Developer
            'status': ApplicationStatus.FAILED,
            'error_log': 'Failed to submit application: Website form validation error - missing required field',
            'materials_used': {
                'resume_version': 'junior_resume_v1.pdf'
            },
            'application_method': 'automated',
            'retry_count': '2',
            'error_count': '3'
        }
    ]
    
    applications = []
    for app_data in applications_data:
        user = users[app_data['user_index']]
        job = jobs[app_data['job_index']]
        
        application = Application(
            id=str(uuid.uuid4()),
            job_id=job.id,
            user_id=user.id,
            status=app_data['status']
        )
        
        # Set other attributes
        for key, value in app_data.items():
            if key not in ['user_index', 'job_index', 'status']:
                if hasattr(application, key):
                    setattr(application, key, value)
        
        applications.append(application)
        db.session.add(application)
        
        # Update job application count
        job.increment_application_count()
    
    return applications


@click.group()
def cli():
    """Database seeding CLI."""
    pass


@cli.command()
@click.option('--config', default='development', help='Configuration to use (development, production, testing)')
def seed_all(config):
    """Seed database with all sample data."""
    app = create_app_for_seeding(config)
    
    with app.app_context():
        click.echo("Creating sample users...")
        users = create_sample_users()
        
        click.echo("Creating sample jobs...")
        jobs = create_sample_jobs()
        
        click.echo("Creating sample applications...")
        applications = create_sample_applications(users, jobs)
        
        try:
            db.session.commit()
            click.echo(f"✓ Successfully seeded database with:")
            click.echo(f"  - {len(users)} users")
            click.echo(f"  - {len(jobs)} jobs")
            click.echo(f"  - {len(applications)} applications")
        except Exception as e:
            db.session.rollback()
            click.echo(f"✗ Error seeding database: {str(e)}")
            raise


@cli.command()
@click.option('--config', default='development', help='Configuration to use (development, production, testing)')
def seed_users(config):
    """Seed database with sample users only."""
    app = create_app_for_seeding(config)
    
    with app.app_context():
        click.echo("Creating sample users...")
        users = create_sample_users()
        
        try:
            db.session.commit()
            click.echo(f"✓ Successfully created {len(users)} sample users")
        except Exception as e:
            db.session.rollback()
            click.echo(f"✗ Error creating users: {str(e)}")
            raise


@cli.command()
@click.option('--config', default='development', help='Configuration to use (development, production, testing)')
def seed_jobs(config):
    """Seed database with sample jobs only."""
    app = create_app_for_seeding(config)
    
    with app.app_context():
        click.echo("Creating sample jobs...")
        jobs = create_sample_jobs()
        
        try:
            db.session.commit()
            click.echo(f"✓ Successfully created {len(jobs)} sample jobs")
        except Exception as e:
            db.session.rollback()
            click.echo(f"✗ Error creating jobs: {str(e)}")
            raise


@cli.command()
@click.option('--config', default='development', help='Configuration to use (development, production, testing)')
def clear_data(config):
    """Clear all data from database."""
    app = create_app_for_seeding(config)
    
    with app.app_context():
        try:
            # Delete in order to respect foreign key constraints
            db.session.query(Application).delete()
            db.session.query(Job).delete()
            db.session.query(User).delete()
            db.session.commit()
            click.echo("✓ Successfully cleared all data from database")
        except Exception as e:
            db.session.rollback()
            click.echo(f"✗ Error clearing data: {str(e)}")
            raise


@cli.command()
@click.option('--config', default='development', help='Configuration to use (development, production, testing)')
def show_stats(config):
    """Show database statistics."""
    app = create_app_for_seeding(config)
    
    with app.app_context():
        try:
            user_count = db.session.query(User).count()
            job_count = db.session.query(Job).count()
            app_count = db.session.query(Application).count()
            
            click.echo("Database Statistics:")
            click.echo(f"  Users: {user_count}")
            click.echo(f"  Jobs: {job_count}")
            click.echo(f"  Applications: {app_count}")
            
            if app_count > 0:
                status_counts = db.session.query(
                    Application.status, 
                    db.func.count(Application.id)
                ).group_by(Application.status).all()
                
                click.echo("  Application Status Breakdown:")
                for status, count in status_counts:
                    click.echo(f"    {status.value}: {count}")
                    
        except Exception as e:
            click.echo(f"✗ Error getting statistics: {str(e)}")


if __name__ == '__main__':
    cli()