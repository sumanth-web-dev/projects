#!/usr/bin/env python
"""
Script to check migration status.
"""
from app import create_app
from sqlalchemy import text
from models.database import db

app = create_app()

with app.app_context():
    # Check if our migration was recorded
    result = db.session.execute(text('SELECT * FROM schema_migrations'))
    rows = result.fetchall()
    print('Applied migrations:')
    for row in rows:
        print(f"Version: {row[0]}, Description: {row[1]}, Applied at: {row[2]}")
    
    # Check if our tables were created
    result = db.session.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name IN ('applications', 'interviews')"))
    tables = result.fetchall()
    print('\nCreated tables:')
    for table in tables:
        print(f"- {table[0]}")
        
    # Check table structure
    for table_name in ['applications', 'interviews']:
        print(f"\nStructure of {table_name}:")
        result = db.session.execute(text(f"SELECT column_name, data_type, is_nullable FROM information_schema.columns WHERE table_name = '{table_name}' ORDER BY ordinal_position"))
        columns = result.fetchall()
        for col in columns:
            print(f"  - {col[0]}: {col[1]} (Nullable: {col[2]})")