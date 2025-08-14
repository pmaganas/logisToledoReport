#!/bin/bash
set -e

echo "Starting Sesame Report Generator..."

# Wait for PostgreSQL to be ready
echo "Waiting for PostgreSQL..."
while ! nc -z db 5432; do
  sleep 1
done
echo "PostgreSQL is ready!"

# Initialize database
echo "Initializing database..."
python -c "
from app import app, db
with app.app_context():
    db.create_all()
    print('Database tables created successfully')
"

# Start the application
echo "Starting Gunicorn server..."
exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers ${WEB_CONCURRENCY:-4} \
    --timeout 120 \
    --reload \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    main:app