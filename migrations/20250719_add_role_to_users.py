"""
Migration to add role column to users table.
Description: Add role column to users table
"""
from sqlalchemy import text
from models.database import db


def up():
    """Apply the migration."""
    # Add role column to users table with default value 'user'
    db.session.execute(text("""
        ALTER TABLE users
        ADD COLUMN role VARCHAR(50) NOT NULL DEFAULT 'user'
    """))
    
    db.session.commit()
    print("Added role column to users table")


def down():
    """Rollback the migration."""
    # Drop the role column from users table
    db.session.execute(text("""
        ALTER TABLE users
        DROP COLUMN IF EXISTS role
    """))
    
    db.session.commit()
    print("Dropped role column from users table")