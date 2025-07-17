# Deployment Guide for Job Application Agent

This document provides instructions for deploying the Job Application Agent in a production environment using Docker.

## Prerequisites

- Docker and Docker Compose installed on the host machine
- Access to a PostgreSQL database (or use the included Docker container)
- Basic understanding of Docker and containerization

## Configuration

1. Create a `.env.production` file based on the provided `.env.template`:

```bash
cp .env.template .env.production
```

2. Edit the `.env.production` file and set secure values for all environment variables:

```
# Generate a secure random key for SECRET_KEY and ENCRYPTION_KEY
SECRET_KEY=<generate_a_secure_random_key>
ENCRYPTION_KEY=<generate_a_secure_encryption_key>

# Set a secure password for the PostgreSQL database
POSTGRES_PASSWORD=<secure_database_password>

# Set your AI API key
AI_API_KEY=<your_ai_api_key>

# Other settings as needed
```

## Deployment

### Using Docker Compose

1. Build and start the containers:

```bash
docker-compose up -d
```

2. Initialize the database (first time only):

```bash
docker-compose exec web python -m scripts.init_db
```

3. Apply database migrations:

```bash
docker-compose exec web python -m scripts.migrate
```

### Manual Deployment

If you prefer to deploy the application manually:

1. Build the Docker image:

```bash
docker build -t job-application-agent .
```

2. Run the container:

```bash
docker run -d \
  --name job-application-agent \
  -p 5000:5000 \
  --env-file .env.production \
  -v ./instance:/app/instance \
  -v ./logs:/app/logs \
  -v ./uploads:/app/uploads \
  job-application-agent
```

## Database Backup and Recovery

### Creating a Backup

```bash
# Using Docker Compose
docker-compose run --rm backup python -m scripts.backup_db --action backup

# Manual backup
docker exec job-application-agent python -m scripts.backup_db --action backup
```

### Listing Available Backups

```bash
# Using Docker Compose
docker-compose run --rm backup python -m scripts.backup_db --action list

# Manual listing
docker exec job-application-agent python -m scripts.backup_db --action list
```

### Restoring from a Backup

```bash
# Using Docker Compose
docker-compose run --rm backup python -m scripts.backup_db --action restore

# Manual restore
docker exec job-application-agent python -m scripts.backup_db --action restore
```

## Monitoring and Maintenance

### Viewing Logs

```bash
# View logs from all containers
docker-compose logs

# View logs from a specific container
docker-compose logs web

# Follow logs in real-time
docker-compose logs -f
```

### Checking Container Status

```bash
docker-compose ps
```

### Restarting Services

```bash
# Restart all services
docker-compose restart

# Restart a specific service
docker-compose restart web
```

## Scaling

To scale the web service horizontally:

```bash
docker-compose up -d --scale web=3
```

Note: When scaling horizontally, you'll need to set up a load balancer in front of the web containers.

## Security Considerations

1. Always use strong, unique passwords for all services
2. Keep the `.env.production` file secure and limit access to it
3. Regularly update the Docker images and dependencies
4. Set up proper network security rules to restrict access to the application
5. Enable HTTPS by setting up a reverse proxy (like Nginx) with SSL/TLS certificates

## Troubleshooting

### Database Connection Issues

If the application cannot connect to the database:

1. Check that the database container is running: `docker-compose ps`
2. Verify the database credentials in `.env.production`
3. Check the database logs: `docker-compose logs db`

### Application Errors

If the application is not working correctly:

1. Check the application logs: `docker-compose logs web`
2. Verify that all required environment variables are set
3. Ensure that the database migrations have been applied

## Updating the Application

To update the application to a new version:

1. Pull the latest code changes
2. Rebuild the Docker image: `docker-compose build`
3. Restart the services: `docker-compose up -d`
4. Apply any new database migrations: `docker-compose exec web python -m scripts.migrate`