#!/usr/bin/env python
"""
Script to record the migration as applied.
"""
from app import create_app
from sqlalchemy import text
from models.database import db

app = create_app()

with app.app_context():
    # Record migration as applied
    try:
        db.session.execute(text("""
            INSERT INTO schema_migrations (version, description, applied_at)
            VALUES ('20250719_create_application_table', 'Create Application table for job applications', CURRENT_TIMESTAMP)
        """))
        db.session.commit()
        print("Migration recorded as applied successfully.")
    except Exception as e:
        db.session.rollback()
        print(f"Error recording migration: {e}")