"""
Migration to create the Application table.
Description: Create Application table for job applications
"""
from sqlalchemy import Column, String, DateTime, Text, Boolean, Integer, Float, ForeignKey
from sqlalchemy import text
from models.database import db
from datetime import datetime
from models.application import ApplicationStatus, InterviewStatus


def up():
    """Apply the migration."""
    # Create the applications table
    db.session.execute(text("""
        CREATE TABLE applications (
            id VARCHAR(36) PRIMARY KEY,
            user_id VARCHAR(36) NOT NULL,
            job_id VARCHAR(36) NOT NULL,
            status VARCHAR(50) NOT NULL DEFAULT 'draft' CHECK (status IN ('draft', 'submitted', 'reviewed', 'interview', 'rejected', 'accepted')),
            cover_letter TEXT,
            resume_path TEXT,
            application_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1,
            feedback TEXT,
            interview_date TIMESTAMP,
            meta_data TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (job_id) REFERENCES jobs(id) ON DELETE CASCADE
        )
    """))
    
    # Create index on user_id and job_id
    db.session.execute(text("""
        CREATE INDEX idx_applications_user_id ON applications(user_id)
    """))
    
    db.session.execute(text("""
        CREATE INDEX idx_applications_job_id ON applications(job_id)
    """))
    
    # Create index on status for quick filtering
    db.session.execute(text("""
        CREATE INDEX idx_applications_status ON applications(status)
    """))
    
    # Create the interviews table
    db.session.execute(text("""
        CREATE TABLE interviews (
            id VARCHAR(36) PRIMARY KEY,
            application_id VARCHAR(36) NOT NULL,
            scheduled_time TIMESTAMP NOT NULL,
            duration_minutes INTEGER NOT NULL DEFAULT 60,
            location VARCHAR(255),
            interview_type VARCHAR(50) NOT NULL DEFAULT 'phone',
            interviewer_name VARCHAR(255),
            interviewer_title VARCHAR(255),
            notes TEXT,
            status VARCHAR(50) NOT NULL DEFAULT 'scheduled' CHECK (status IN ('scheduled', 'completed', 'cancelled', 'rescheduled')),
            feedback TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (application_id) REFERENCES applications(id) ON DELETE CASCADE
        )
    """))
    
    # Create index on application_id
    db.session.execute(text("""
        CREATE INDEX idx_interviews_application_id ON interviews(application_id)
    """))
    
    # Create index on scheduled_time for quick date-based queries
    db.session.execute(text("""
        CREATE INDEX idx_interviews_scheduled_time ON interviews(scheduled_time)
    """))
    
    db.session.commit()
    print("Created applications and interviews tables with indexes")


def down():
    """Rollback the migration."""
    # Drop the interviews table first (due to foreign key constraints)
    db.session.execute(text("DROP TABLE IF EXISTS interviews"))
    
    # Drop the applications table
    db.session.execute(text("DROP TABLE IF EXISTS applications"))
    
    db.session.commit()
    print("Dropped interviews and applications tables")