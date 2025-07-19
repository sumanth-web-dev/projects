"""
Database migration system for the Job Application Agent.
"""
import os
import json
from datetime import datetime
from typing import List, Dict, Any
from flask import current_app
from models.database import db


class Migration:
    """Base migration class."""
    
    def __init__(self, version: str, description: str):
        self.version = version
        self.description = description
        self.timestamp = datetime.utcnow()
    
    def up(self):
        """Apply the migration."""
        raise NotImplementedError("Migration must implement up() method")
    
    def down(self):
        """Rollback the migration."""
        raise NotImplementedError("Migration must implement down() method")


class MigrationManager:
    """Manages database migrations."""
    
    def __init__(self, app=None):
        self.app = app
        self.migrations_dir = 'migrations'
        self.migrations_table = 'schema_migrations'
        
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize migration manager with Flask app."""
        self.app = app
        # Use absolute path to migrations directory in the app root
        self.migrations_dir = os.path.join(app.root_path, 'migrations')
        
        # Ensure migrations directory exists
        os.makedirs(self.migrations_dir, exist_ok=True)
        
        # Create migrations table if it doesn't exist
        with app.app_context():
            self._create_migrations_table()
    
    def _create_migrations_table(self):
        """Create the schema_migrations table to track applied migrations."""
        try:
            from sqlalchemy import text
            db.session.execute(text(f"""
                CREATE TABLE IF NOT EXISTS {self.migrations_table} (
                    version TEXT PRIMARY KEY,
                    description TEXT NOT NULL,
                    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """))
            db.session.commit()
        except Exception as e:
            print(f"Error creating migrations table: {e}")
            db.session.rollback()
    
    def get_applied_migrations(self) -> List[str]:
        """Get list of applied migration versions."""
        try:
            from sqlalchemy import text
            result = db.session.execute(text(f"SELECT version FROM {self.migrations_table} ORDER BY version"))
            return [row[0] for row in result]
        except Exception:
            return []
    
    def get_pending_migrations(self) -> List[Dict[str, Any]]:
        """Get list of pending migrations."""
        applied = set(self.get_applied_migrations())
        all_migrations = self._discover_migrations()
        
        pending = []
        for migration_info in all_migrations:
            if migration_info['version'] not in applied:
                pending.append(migration_info)
        
        return sorted(pending, key=lambda x: x['version'])
    
    def _discover_migrations(self) -> List[Dict[str, Any]]:
        """Discover all migration files."""
        migrations = []
        
        if not os.path.exists(self.migrations_dir):
            return migrations
        
        for filename in os.listdir(self.migrations_dir):
            if filename.endswith('.py') and filename != '__init__.py':
                version = filename.replace('.py', '')
                migration_path = os.path.join(self.migrations_dir, filename)
                
                # Try to extract description from file
                description = self._extract_migration_description(migration_path)
                
                migrations.append({
                    'version': version,
                    'description': description,
                    'filename': filename,
                    'path': migration_path
                })
        
        return migrations
    
    def _extract_migration_description(self, migration_path: str) -> str:
        """Extract description from migration file."""
        try:
            with open(migration_path, 'r') as f:
                content = f.read()
                # Look for description in docstring or comment
                lines = content.split('\n')
                for line in lines[:10]:  # Check first 10 lines
                    if 'description' in line.lower() and ('=' in line or ':' in line):
                        return line.split('=')[-1].split(':')[-1].strip().strip('"\'')
            return "No description"
        except Exception:
            return "No description"
    
    def apply_migration(self, version: str) -> bool:
        """Apply a specific migration."""
        migration_info = None
        for m in self._discover_migrations():
            if m['version'] == version:
                migration_info = m
                break
        
        if not migration_info:
            print(f"Migration {version} not found")
            return False
        
        try:
            # Execute migration file
            migration_globals = {'db': db}
            with open(migration_info['path'], 'r') as f:
                exec(f.read(), migration_globals)
            
            # Call the up function if it exists
            if 'up' in migration_globals:
                migration_globals['up']()
            
            # Record migration as applied using SQLAlchemy 2.0 syntax
            from sqlalchemy import text
            db.session.execute(text(f"""
                INSERT INTO {self.migrations_table} (version, description)
                VALUES (:version, :description)
            """), {'version': version, 'description': migration_info['description']})
            
            db.session.commit()
            print(f"Applied migration: {version} - {migration_info['description']}")
            return True
            
        except Exception as e:
            print(f"Error applying migration {version}: {e}")
            db.session.rollback()
            return False
    
    def rollback_migration(self, version: str) -> bool:
        """Rollback a specific migration."""
        migration_info = None
        for m in self._discover_migrations():
            if m['version'] == version:
                migration_info = m
                break
        
        if not migration_info:
            print(f"Migration {version} not found")
            return False
        
        try:
            # Execute migration file
            migration_globals = {'db': db}
            with open(migration_info['path'], 'r') as f:
                exec(f.read(), migration_globals)
            
            # Call the down function if it exists
            if 'down' in migration_globals:
                migration_globals['down']()
            
            # Remove migration record using SQLAlchemy 2.0 syntax
            from sqlalchemy import text
            db.session.execute(text(f"""
                DELETE FROM {self.migrations_table} WHERE version = :version
            """), {'version': version})
            
            db.session.commit()
            print(f"Rolled back migration: {version} - {migration_info['description']}")
            return True
            
        except Exception as e:
            print(f"Error rolling back migration {version}: {e}")
            db.session.rollback()
            return False
    
    def migrate(self) -> bool:
        """Apply all pending migrations."""
        pending = self.get_pending_migrations()
        
        if not pending:
            print("No pending migrations")
            return True
        
        print(f"Applying {len(pending)} pending migrations...")
        
        success = True
        for migration in pending:
            if not self.apply_migration(migration['version']):
                success = False
                break
        
        if success:
            print("All migrations applied successfully")
        else:
            print("Migration failed - some migrations may not have been applied")
        
        return success
    
    def status(self) -> Dict[str, Any]:
        """Get migration status."""
        applied = self.get_applied_migrations()
        pending = self.get_pending_migrations()
        
        return {
            'applied_count': len(applied),
            'pending_count': len(pending),
            'applied_migrations': applied,
            'pending_migrations': [m['version'] for m in pending]
        }


# Global migration manager instance
migration_manager = MigrationManager()