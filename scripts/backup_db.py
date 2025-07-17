"""
Database backup and recovery script for the Job Application Agent.
This script provides functionality to backup and restore the database.
"""
import os
import sys
import time
import argparse
import subprocess
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('backup_db')

# Constants
BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backups')
BACKUP_RETENTION_DAYS = 7  # Keep backups for 7 days by default


def ensure_backup_dir():
    """Ensure the backup directory exists."""
    if not os.path.exists(BACKUP_DIR):
        os.makedirs(BACKUP_DIR, exist_ok=True)
        logger.info(f"Created backup directory: {BACKUP_DIR}")


def get_database_url():
    """Get the database URL from environment variables."""
    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        logger.error("DATABASE_URL environment variable not set")
        sys.exit(1)
    return db_url


def is_postgres_url(db_url):
    """Check if the database URL is for PostgreSQL."""
    return db_url.startswith('postgresql://') or db_url.startswith('postgres://')


def backup_postgres(db_url):
    """Backup PostgreSQL database."""
    # Parse the database URL
    # Format: postgresql://username:password@host:port/dbname
    db_url = db_url.replace('postgresql://', '')
    db_url = db_url.replace('postgres://', '')
    
    # Split the URL into components
    credentials, rest = db_url.split('@')
    username, password = credentials.split(':')
    host_port, dbname = rest.split('/')
    
    if ':' in host_port:
        host, port = host_port.split(':')
    else:
        host = host_port
        port = '5432'
    
    # Create a timestamp for the backup file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUP_DIR, f"{dbname}_{timestamp}.sql")
    
    # Set environment variables for pg_dump
    env = os.environ.copy()
    env['PGPASSWORD'] = password
    
    # Execute pg_dump command
    cmd = [
        'pg_dump',
        '-h', host,
        '-p', port,
        '-U', username,
        '-F', 'c',  # Custom format (compressed)
        '-b',  # Include large objects
        '-v',  # Verbose
        '-f', backup_file,
        dbname
    ]
    
    try:
        logger.info(f"Starting backup of PostgreSQL database {dbname} to {backup_file}")
        process = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        logger.info(f"Backup completed successfully: {backup_file}")
        return backup_file
    except subprocess.CalledProcessError as e:
        logger.error(f"Backup failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        return None


def backup_sqlite(db_url):
    """Backup SQLite database."""
    # Parse the database URL
    # Format: sqlite:///path/to/database.db
    db_path = db_url.replace('sqlite:///', '')
    
    if not os.path.exists(db_path):
        logger.error(f"SQLite database file not found: {db_path}")
        return None
    
    # Create a timestamp for the backup file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(BACKUP_DIR, f"sqlite_backup_{timestamp}.db")
    
    try:
        logger.info(f"Starting backup of SQLite database {db_path} to {backup_file}")
        
        # Use SQLite's .backup command via a temporary script
        import sqlite3
        
        # Connect to the source database
        conn = sqlite3.connect(db_path)
        
        # Create a backup
        backup_conn = sqlite3.connect(backup_file)
        conn.backup(backup_conn)
        
        # Close connections
        backup_conn.close()
        conn.close()
        
        logger.info(f"Backup completed successfully: {backup_file}")
        return backup_file
    except Exception as e:
        logger.error(f"Backup failed: {e}")
        return None


def restore_postgres(db_url, backup_file):
    """Restore PostgreSQL database from backup."""
    # Parse the database URL
    db_url = db_url.replace('postgresql://', '')
    db_url = db_url.replace('postgres://', '')
    
    # Split the URL into components
    credentials, rest = db_url.split('@')
    username, password = credentials.split(':')
    host_port, dbname = rest.split('/')
    
    if ':' in host_port:
        host, port = host_port.split(':')
    else:
        host = host_port
        port = '5432'
    
    # Set environment variables for pg_restore
    env = os.environ.copy()
    env['PGPASSWORD'] = password
    
    # Execute pg_restore command
    cmd = [
        'pg_restore',
        '-h', host,
        '-p', port,
        '-U', username,
        '-d', dbname,
        '-v',  # Verbose
        '--clean',  # Clean (drop) database objects before recreating
        '--if-exists',  # Use IF EXISTS when dropping objects
        backup_file
    ]
    
    try:
        logger.info(f"Starting restore of PostgreSQL database {dbname} from {backup_file}")
        process = subprocess.run(cmd, env=env, check=True, capture_output=True, text=True)
        logger.info("Restore completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Restore failed: {e}")
        logger.error(f"Error output: {e.stderr}")
        return False


def restore_sqlite(db_url, backup_file):
    """Restore SQLite database from backup."""
    # Parse the database URL
    db_path = db_url.replace('sqlite:///', '')
    
    try:
        logger.info(f"Starting restore of SQLite database {db_path} from {backup_file}")
        
        # If the database file exists, create a backup before overwriting
        if os.path.exists(db_path):
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            pre_restore_backup = os.path.join(BACKUP_DIR, f"pre_restore_backup_{timestamp}.db")
            
            import sqlite3
            
            # Connect to the source database
            conn = sqlite3.connect(db_path)
            
            # Create a backup
            backup_conn = sqlite3.connect(pre_restore_backup)
            conn.backup(backup_conn)
            
            # Close connections
            backup_conn.close()
            conn.close()
            
            logger.info(f"Created pre-restore backup: {pre_restore_backup}")
        
        # Copy the backup file to the database path
        import shutil
        shutil.copy2(backup_file, db_path)
        
        logger.info("Restore completed successfully")
        return True
    except Exception as e:
        logger.error(f"Restore failed: {e}")
        return False


def cleanup_old_backups():
    """Remove backups older than BACKUP_RETENTION_DAYS."""
    if not os.path.exists(BACKUP_DIR):
        return
    
    current_time = time.time()
    retention_seconds = BACKUP_RETENTION_DAYS * 24 * 60 * 60
    
    for filename in os.listdir(BACKUP_DIR):
        file_path = os.path.join(BACKUP_DIR, filename)
        
        # Skip if not a file
        if not os.path.isfile(file_path):
            continue
        
        # Check if file is older than retention period
        file_age = current_time - os.path.getmtime(file_path)
        if file_age > retention_seconds:
            try:
                os.remove(file_path)
                logger.info(f"Removed old backup: {filename}")
            except Exception as e:
                logger.error(f"Failed to remove old backup {filename}: {e}")


def list_backups():
    """List available backups."""
    if not os.path.exists(BACKUP_DIR):
        logger.info("No backups found (backup directory does not exist)")
        return []
    
    backups = []
    for filename in os.listdir(BACKUP_DIR):
        file_path = os.path.join(BACKUP_DIR, filename)
        if os.path.isfile(file_path):
            size_mb = os.path.getsize(file_path) / (1024 * 1024)
            mod_time = datetime.fromtimestamp(os.path.getmtime(file_path))
            backups.append({
                'filename': filename,
                'path': file_path,
                'size_mb': round(size_mb, 2),
                'modified': mod_time.strftime('%Y-%m-%d %H:%M:%S')
            })
    
    # Sort by modification time (newest first)
    backups.sort(key=lambda x: x['modified'], reverse=True)
    
    if backups:
        logger.info(f"Found {len(backups)} backups:")
        for i, backup in enumerate(backups, 1):
            logger.info(f"{i}. {backup['filename']} ({backup['size_mb']} MB) - {backup['modified']}")
    else:
        logger.info("No backups found")
    
    return backups


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description='Database backup and recovery tool')
    parser.add_argument('--action', choices=['backup', 'restore', 'list'], default='backup',
                        help='Action to perform (default: backup)')
    parser.add_argument('--file', help='Backup file to restore (for restore action)')
    parser.add_argument('--retention', type=int, default=BACKUP_RETENTION_DAYS,
                        help=f'Number of days to keep backups (default: {BACKUP_RETENTION_DAYS})')
    
    args = parser.parse_args()
    
    # Ensure backup directory exists
    ensure_backup_dir()
    
    if args.action == 'list':
        list_backups()
        return
    
    # Get database URL
    db_url = get_database_url()
    
    if args.action == 'backup':
        # Perform backup based on database type
        if is_postgres_url(db_url):
            backup_file = backup_postgres(db_url)
        else:
            backup_file = backup_sqlite(db_url)
        
        if backup_file:
            # Clean up old backups
            cleanup_old_backups()
    
    elif args.action == 'restore':
        if not args.file:
            backups = list_backups()
            if not backups:
                logger.error("No backups available to restore")
                return
            
            try:
                choice = input("Enter the number of the backup to restore: ")
                index = int(choice) - 1
                if 0 <= index < len(backups):
                    backup_file = backups[index]['path']
                else:
                    logger.error("Invalid selection")
                    return
            except (ValueError, IndexError):
                logger.error("Invalid selection")
                return
        else:
            backup_file = args.file
            if not os.path.exists(backup_file):
                logger.error(f"Backup file not found: {backup_file}")
                return
        
        # Confirm restore
        confirm = input(f"Are you sure you want to restore from {os.path.basename(backup_file)}? "
                        f"This will overwrite the current database. (y/N): ")
        if confirm.lower() != 'y':
            logger.info("Restore cancelled")
            return
        
        # Perform restore based on database type
        if is_postgres_url(db_url):
            restore_postgres(db_url, backup_file)
        else:
            restore_sqlite(db_url, backup_file)


if __name__ == '__main__':
    main()