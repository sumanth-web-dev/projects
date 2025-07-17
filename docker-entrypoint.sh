#!/bin/bash
set -e

# Apply database migrations
echo "Applying database migrations..."
python -m scripts.migrate

# Check if we need to initialize the database
if [ "$INITIALIZE_DB" = "true" ]; then
    echo "Initializing database..."
    python -m scripts.init_db
fi

# Check if we need to seed the database with test data
if [ "$SEED_DB" = "true" ]; then
    echo "Seeding database with test data..."
    python -m scripts.seed_data
fi

# Execute the CMD from the Dockerfile
exec "$@"