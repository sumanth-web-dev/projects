#!/usr/bin/env python3
"""
Database migration management script for the Job Application Agent.
"""
import os
import sys
import click
from datetime import datetime

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config, DevelopmentConfig, ProductionConfig, TestingConfig
from models.database import init_db
from models.migrations import migration_manager
from flask import Flask


def create_app_for_migrations(config_name='development'):
    """Create Flask app instance for migration operations."""
    app = Flask(__name__)
    
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    
    config_class = config_map.get(config_name, DevelopmentConfig)
    config_instance = config_class()
    app.config.from_object(config_instance)
    
    # Initialize database and migrations
    init_db(app)
    migration_manager.init_app(app)
    
    return app


@click.group()
def cli():
    """Database migration management CLI."""
    pass


@cli.command()
@click.option('--config', default='development', help='Configuration to use (development, production, testing)')
def status(config):
    """Show migration status."""
    app = create_app_for_migrations(config)
    
    with app.app_context():
        status_info = migration_manager.status()
        
        click.echo(f"Migration Status ({config} configuration):")
        click.echo(f"Applied migrations: {status_info['applied_count']}")
        click.echo(f"Pending migrations: {status_info['pending_count']}")
        
        if status_info['applied_migrations']:
            click.echo("\nApplied migrations:")
            for migration in status_info['applied_migrations']:
                click.echo(f"  ✓ {migration}")
        
        if status_info['pending_migrations']:
            click.echo("\nPending migrations:")
            for migration in status_info['pending_migrations']:
                click.echo(f"  - {migration}")
        
        if not status_info['applied_migrations'] and not status_info['pending_migrations']:
            click.echo("No migrations found.")


@cli.command()
@click.option('--config', default='development', help='Configuration to use (development, production, testing)')
def migrate(config):
    """Apply all pending migrations."""
    app = create_app_for_migrations(config)
    
    with app.app_context():
        success = migration_manager.migrate()
        if success:
            click.echo("✓ All migrations applied successfully!")
        else:
            click.echo("✗ Migration failed!")
            sys.exit(1)


@cli.command()
@click.argument('version')
@click.option('--config', default='development', help='Configuration to use (development, production, testing)')
def apply(version, config):
    """Apply a specific migration."""
    app = create_app_for_migrations(config)
    
    with app.app_context():
        success = migration_manager.apply_migration(version)
        if success:
            click.echo(f"✓ Migration {version} applied successfully!")
        else:
            click.echo(f"✗ Failed to apply migration {version}!")
            sys.exit(1)


@cli.command()
@click.argument('version')
@click.option('--config', default='development', help='Configuration to use (development, production, testing)')
@click.confirmation_option(prompt='Are you sure you want to rollback this migration?')
def rollback(version, config):
    """Rollback a specific migration."""
    app = create_app_for_migrations(config)
    
    with app.app_context():
        success = migration_manager.rollback_migration(version)
        if success:
            click.echo(f"✓ Migration {version} rolled back successfully!")
        else:
            click.echo(f"✗ Failed to rollback migration {version}!")
            sys.exit(1)


@cli.command()
@click.argument('name')
def create(name):
    """Create a new migration file."""
    # Generate timestamp-based version
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    version = f"{timestamp}_{name}"
    
    # Create migrations directory if it doesn't exist
    migrations_dir = 'migrations'
    os.makedirs(migrations_dir, exist_ok=True)
    
    # Create migration file
    migration_file = os.path.join(migrations_dir, f"{version}.py")
    
    migration_template = f'''"""
Migration: {name}
Created: {datetime.now().isoformat()}
Description: {name.replace('_', ' ').title()}
"""

from models.database import db
from sqlalchemy import text


def up():
    """Apply the migration."""
    # Add your migration code here
    # Example:
    # db.session.execute(text("""
    #     CREATE TABLE example (
    #         id INTEGER PRIMARY KEY,
    #         name TEXT NOT NULL
    #     )
    # """))
    # db.session.commit()
    pass


def down():
    """Rollback the migration."""
    # Add your rollback code here
    # Example:
    # db.session.execute(text("DROP TABLE IF EXISTS example"))
    # db.session.commit()
    pass
'''
    
    with open(migration_file, 'w') as f:
        f.write(migration_template)
    
    click.echo(f"Created migration file: {migration_file}")
    click.echo(f"Migration version: {version}")


if __name__ == '__main__':
    cli()