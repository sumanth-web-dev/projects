#!/usr/bin/env python
"""
Database migration CLI for the Job Application Agent.
"""
import os
import sys
import click
from flask import Flask
from app import create_app
from models.migrations import migration_manager


@click.group()
def cli():
    """Database migration commands."""
    pass


@cli.command('status')
def status():
    """Show migration status."""
    app = create_app()
    with app.app_context():
        status = migration_manager.status()
        click.echo(f"Applied migrations: {status['applied_count']}")
        click.echo(f"Pending migrations: {status['pending_count']}")
        
        if status['pending_count'] > 0:
            click.echo("\nPending migrations:")
            for version in status['pending_migrations']:
                click.echo(f"  - {version}")


@cli.command('upgrade')
def upgrade():
    """Apply all pending migrations."""
    app = create_app()
    with app.app_context():
        success = migration_manager.migrate()
        if success:
            click.echo("All migrations applied successfully.")
        else:
            click.echo("Migration failed - some migrations may not have been applied.")
            sys.exit(1)


@cli.command('apply')
@click.argument('version')
def apply(version):
    """Apply a specific migration."""
    app = create_app()
    with app.app_context():
        success = migration_manager.apply_migration(version)
        if success:
            click.echo(f"Migration {version} applied successfully.")
        else:
            click.echo(f"Failed to apply migration {version}.")
            sys.exit(1)


@cli.command('rollback')
@click.argument('version')
def rollback(version):
    """Rollback a specific migration."""
    app = create_app()
    with app.app_context():
        success = migration_manager.rollback_migration(version)
        if success:
            click.echo(f"Migration {version} rolled back successfully.")
        else:
            click.echo(f"Failed to roll back migration {version}.")
            sys.exit(1)


if __name__ == '__main__':
    cli()