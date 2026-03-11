#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# Wait for database if needed (optional for local, important for cloud)
# echo "Waiting for database..."
# sleep 5

# Apply database migrations
echo "Applying database migrations..."
python manage.py migrate --noinput

# Create superuser if it doesn't exist
echo "Checking superuser..."
python create_superuser_automatic.py

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Start the application
echo "Starting application..."
# Check if PORT is set (Render) or use default 8000
PORT=${PORT:-8000}

# Start keep_alive in background
python keep_alive.py &

# Start Daphne
exec daphne -b 0.0.0.0 -p "$PORT" config.asgi:application
