#!/usr/bin/env python
"""
Script to test the Application model.
"""
import uuid
from app import create_app
from models.database import db
from models.application import Application, ApplicationStatus, Interview, InterviewStatus

app = create_app()

with app.app_context():
    try:
        # Check if we can create an Application instance
        app_id = str(uuid.uuid4())
        test_app = Application(
            id=app_id,
            user_id="test_user_id",
            job_id="test_job_id",
            status=ApplicationStatus.DRAFT,
            cover_letter="This is a test cover letter"
        )
        
        # Check if we can create an Interview instance
        interview_id = str(uuid.uuid4())
        test_interview = Interview(
            id=interview_id,
            application_id=app_id,
            scheduled_time=db.func.now(),
            interview_type="video",
            status=InterviewStatus.SCHEDULED
        )
        
        print("Successfully created Application and Interview instances")
        print(f"Application: {test_app}")
        print(f"Interview: {test_interview}")
        
        # Don't actually save to the database
        
    except Exception as e:
        print(f"Error testing models: {e}")