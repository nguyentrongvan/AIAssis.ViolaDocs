#!/bin/bash
set -e

echo "=== ViolaDocs Backend Entrypoint ==="
echo "Working directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Python version: $(python --version)"

# Set Python path if not set
if [ -z "$PYTHONPATH" ]; then
    echo "Setting PYTHONPATH to /app/src"
    export PYTHONPATH=/app/src
fi

# Wait for database to be ready
echo "Waiting for database to be ready..."
until python -c "
import sys
sys.path.insert(0, '/app/src')
from sqlalchemy import create_engine
from app.config import settings
try:
    engine = create_engine(settings.postgres_dsn)
    with engine.connect() as conn:
        conn.execute('SELECT 1')
    print('Database is ready!')
except Exception as e:
    print(f'Database not ready: {e}')
    sys.exit(1)
" 2>/dev/null; do
    echo "Database is unavailable - sleeping"
    sleep 2
done

# Run database migrations
echo "Running database migrations..."
cd /app
if ! alembic upgrade head; then
    echo "ERROR: Database migrations failed!"
    exit 1
fi
echo "Database migrations completed successfully."

# Check if root user exists, create if not (handled by main.py startup)
echo "Root user will be auto-created on startup if not exists"

# Start the application
echo "Starting ViolaDocs backend server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

