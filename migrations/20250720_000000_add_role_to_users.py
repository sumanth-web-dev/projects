"""
Migration: add_role_to_users
Created: 2025-07-20T00:00:00
Description: Add 'role' column to users table
"""

from models.database import db
from sqlalchemy import text

def up():
    """Apply the migration."""
    db.session.execute(text("""
        ALTER TABLE users ADD COLUMN role VARCHAR(50);
    """))
    db.session.commit()

def down():
    """Rollback the migration."""
    db.session.execute(text("""
        ALTER TABLE users DROP COLUMN IF EXISTS role;
    """))
    db.session.commit()
