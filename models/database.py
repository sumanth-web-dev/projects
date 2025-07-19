"""
Database connection and configuration for the Job Application Agent.
"""
import os
import logging
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import event, text
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError
import sqlite3

# Initialize SQLAlchemy instance
db = SQLAlchemy()


# Set up logging
logger = logging.getLogger(__name__)


def init_db(app):
    """Initialize database with Flask app."""
    db.init_app(app)
    
    # Configure SQLite-specific settings
    configure_sqlite_settings(app)
    
    return db


def configure_sqlite_settings(app):
    """Configure SQLite-specific database settings."""
    
    @event.listens_for(Engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        """Set SQLite pragmas for better performance and data integrity."""
        if isinstance(dbapi_connection, sqlite3.Connection):
            cursor = dbapi_connection.cursor()
            try:
                # Enable foreign key constraints
                cursor.execute("PRAGMA foreign_keys=ON")
                
                # Set journal mode to WAL for better concurrency
                cursor.execute("PRAGMA journal_mode=WAL")
                
                # Set synchronous mode to NORMAL for better performance
                cursor.execute("PRAGMA synchronous=NORMAL")
                
                # Set cache size (negative value means KB, positive means pages)
                cursor.execute("PRAGMA cache_size=-64000")  # 64MB cache
                
                # Set temp store to memory for better performance
                cursor.execute("PRAGMA temp_store=MEMORY")
                
                # Set busy timeout to 30 seconds
                cursor.execute("PRAGMA busy_timeout=30000")
                
                logger.debug("SQLite pragmas configured successfully")
            except Exception as e:
                logger.error(f"Error setting SQLite pragmas: {e}")
            finally:
                cursor.close()


def create_tables(app):
    """Create all database tables."""
    with app.app_context():
        db.create_all()
        print("Database tables created successfully.")


def drop_tables(app):
    """Drop all database tables."""
    with app.app_context():
        db.drop_all()
        print("Database tables dropped successfully.")


def reset_database(app):
    """Reset database by dropping and recreating all tables."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        print("Database reset successfully.")


def get_db_info(app):
    """Get database information and connection status."""
    with app.app_context():
        try:
            # Test database connection using SQLAlchemy 2.0 syntax
            from sqlalchemy import text
            result = db.session.execute(text("SELECT 1")).fetchone()
            if result:
                db_path = app.config['SQLALCHEMY_DATABASE_URI']
                # Get table names using inspector
                from sqlalchemy import inspect
                inspector = inspect(db.engine)
                table_names = inspector.get_table_names()
                
                return {
                    'status': 'connected',
                    'database_uri': db_path,
                    'engine': str(db.engine),
                    'tables': table_names
                }
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e)
            }