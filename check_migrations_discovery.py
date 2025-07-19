#!/usr/bin/env python
"""
Script to check migration discovery.
"""
from app import create_app
from models.migrations import migration_manager

app = create_app()

with app.app_context():
    # Initialize the migration manager
    migration_manager.init_app(app)
    
    # Print the migrations directory path
    print(f"Migrations directory: {migration_manager.migrations_dir}")
    
    # Discover migrations
    migrations = migration_manager._discover_migrations()
    print(f"\nDiscovered migrations: {len(migrations)}")
    for m in migrations:
        print(f"  - {m['version']}: {m['description']} ({m['path']})")