# Database Setup and Management

This document provides instructions for setting up, initializing, and managing the database for the Job Application Agent.

## Database Overview

The Job Application Agent uses SQLite as its default database engine for development and testing. For production, it can be configured to use other database engines supported by SQLAlchemy.

### Database Models

The application uses the following main models:

1. **User** - Stores user profiles and job preferences
2. **Job** - Stores job listings and details
3. **Application** - Tracks job applications and their status

## Database Setup

### Initial Setup

To initialize the database for the first time:

```bash
# Initialize the database with all tables
python scripts/init_db.py init

# Seed the database with sample data (for development/testing)
python scripts/seed_data.py seed-all
```

### Database Commands

The `init_db.py` script provides several commands for database management:

```bash
# Show database information
python scripts/init_db.py info

# Initialize database and create tables
python scripts/init_db.py init

# Drop all tables (requires confirmation)
python scripts/init_db.py drop

# Reset database (drop and recreate all tables, requires confirmation)
python scripts/init_db.py reset

# Test database connection
python scripts/init_db.py test_connection
```

## Seed Data

The `seed_data.py` script provides commands for populating the database with sample data:

```bash
# Seed database with all sample data (users, jobs, applications)
python scripts/seed_data.py seed-all

# Seed only users
python scripts/seed_data.py seed-users

# Seed only jobs
python scripts/seed_data.py seed-jobs

# Clear all data from database
python scripts/seed_data.py clear-data

# Show database statistics
python scripts/seed_data.py show-stats
```

## Database Migrations

The application includes a migration system for managing database schema changes. Migrations are stored in the `migrations` directory.

### Migration Commands

```bash
# Show migration status
python scripts/migrate.py status

# Apply all pending migrations
python scripts/migrate.py migrate

# Apply a specific migration
python scripts/migrate.py apply MIGRATION_VERSION

# Rollback a specific migration (requires confirmation)
python scripts/migrate.py rollback MIGRATION_VERSION

# Create a new migration file
python scripts/migrate.py create migration_name
```

### Creating a New Migration

To create a new migration:

1. Run the create command:
   ```bash
   python scripts/migrate.py create add_new_feature
   ```

2. Edit the generated migration file in the `migrations` directory:
   ```python
   def up():
       """Apply the migration."""
       db.session.execute(text("""
           ALTER TABLE users ADD COLUMN new_column TEXT
       """))
       db.session.commit()

   def down():
       """Rollback the migration."""
       db.session.execute(text("""
           ALTER TABLE users DROP COLUMN new_column
       """))
       db.session.commit()
   ```

3. Apply the migration:
   ```bash
   python scripts/migrate.py migrate
   ```

## Configuration

Database configuration is managed in the `config.py` file. The application supports different configurations for development, testing, and production environments.

### Environment Variables

The following environment variables can be used to configure the database:

- `DATABASE_URL`: Full database connection URL (overrides default SQLite configuration)
- `ENCRYPTION_KEY`: Key used for encrypting sensitive user data

## Troubleshooting

### Common Issues

1. **Database connection errors**:
   - Ensure the database file exists and has proper permissions
   - Check that the database URL is correctly configured
   - Run `python scripts/init_db.py test_connection` to verify connectivity

2. **Migration errors**:
   - Check migration file syntax
   - Ensure migrations are applied in the correct order
   - Review database logs for detailed error messages

3. **Data seeding issues**:
   - Clear existing data before seeding: `python scripts/seed_data.py clear-data`
   - Check for validation errors in the seed data
   - Ensure all required models are properly imported