#!/usr/bin/env python3
"""
Database initialization script for the Job Application Agent.
"""
import os
import sys
import click
from flask import Flask

# Add the parent directory to the path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config, DevelopmentConfig, ProductionConfig, TestingConfig
from models.database import init_db, create_tables, drop_tables, reset_database, get_db_info


def create_app_for_db(config_name='development'):
    """Create Flask app instance for database operations."""
    app = Flask(__name__)
    
    config_map = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig
    }
    
    config_class = config_map.get(config_name, DevelopmentConfig)
    config_instance = config_class()
    app.config.from_object(config_instance)
    
    # Initialize database
    init_db(app)
    
    return app


@click.group()
def cli():
    """Database management CLI."""
    pass


@cli.command()
@click.option('--config', default='development', help='Configuration to use (development, production, testing)')
def init(config):
    """Initialize the database and create all tables."""
    app = create_app_for_db(config)
    create_tables(app)
    click.echo(f"Database initialized successfully with {config} configuration.")


@cli.command()
@click.option('--config', default='development', help='Configuration to use (development, production, testing)')
@click.confirmation_option(prompt='Are you sure you want to drop all tables?')
def drop(config):
    """Drop all database tables."""
    app = create_app_for_db(config)
    drop_tables(app)
    click.echo("All tables dropped successfully.")


@cli.command()
@click.option('--config', default='development', help='Configuration to use (development, production, testing)')
@click.confirmation_option(prompt='Are you sure you want to reset the database?')
def reset(config):
    """Reset the database by dropping and recreating all tables."""
    app = create_app_for_db(config)
    reset_database(app)
    click.echo("Database reset successfully.")


@cli.command()
@click.option('--config', default='development', help='Configuration to use (development, production, testing)')
def info(config):
    """Show database information and connection status."""
    app = create_app_for_db(config)
    db_info = get_db_info(app)
    
    click.echo(f"Database Information ({config} configuration):")
    click.echo(f"Status: {db_info.get('status', 'unknown')}")
    
    if db_info.get('status') == 'connected':
        click.echo(f"Database URI: {db_info.get('database_uri')}")
        click.echo(f"Engine: {db_info.get('engine')}")
        tables = db_info.get('tables', [])
        if tables:
            click.echo(f"Tables: {', '.join(tables)}")
        else:
            click.echo("No tables found.")
    elif db_info.get('status') == 'error':
        click.echo(f"Error: {db_info.get('error')}")


@cli.command()
@click.option('--config', default='development', help='Configuration to use (development, production, testing)')
def test_connection(config):
    """Test database connection."""
    app = create_app_for_db(config)
    
    try:
        with app.app_context():
            from models.database import db
            from sqlalchemy import text
            # Try to execute a simple query using SQLAlchemy 2.0 syntax
            result = db.session.execute(text("SELECT 1 as test")).fetchone()
            if result and result[0] == 1:
                click.echo("✓ Database connection successful!")
                return True
            else:
                click.echo("✗ Database connection failed - unexpected result")
                return False
    except Exception as e:
        click.echo(f"✗ Database connection failed: {str(e)}")
        return False


if __name__ == '__main__':
    cli()