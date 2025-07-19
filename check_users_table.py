#!/usr/bin/env python
"""
Script to check the structure of the users table.
"""
from app import create_app
from sqlalchemy import text
from models.database import db

app = create_app()

with app.app_context():
    # Check the structure of the users table
    result = db.session.execute(text("""
        SELECT column_name, data_type, is_nullable 
        FROM information_schema.columns 
        WHERE table_name = 'users' 
        ORDER BY ordinal_position
    """))
    
    print("Users table structure:")
    for row in result:
        print(f"  - {row[0]}: {row[1]} (Nullable: {row[2]})")