#!/bin/bash
set -e

echo "=== OCR Worker Entrypoint ==="
echo "Working directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Python version: $(python --version)"

# Run database migrations
echo "Running database migrations..."
cd /app
if ! alembic upgrade head; then
    echo "ERROR: Database migrations failed!"
    exit 1
fi
echo "Database migrations completed successfully."

# Check Python path
echo "Checking Python path..."
if [ -z "$PYTHONPATH" ]; then
    echo "WARNING: PYTHONPATH is not set, setting to /app/src"
    export PYTHONPATH=/app/src
fi

# Check if module exists
echo "Checking if app.workers.worker_main exists..."
if ! python -c "import app.workers.worker_main" 2>&1; then
    echo "ERROR: Cannot import app.workers.worker_main"
    echo "Python path: $PYTHONPATH"
    echo "Contents of /app/src:"
    ls -la /app/src/ || true
    echo "Contents of /app/src/app:"
    ls -la /app/src/app/ || true
    echo "Contents of /app/src/app/workers:"
    ls -la /app/src/app/workers/ || true
    exit 1
fi
echo "Module check passed."

# Start worker
echo "Starting OCR worker..."
exec python -m app.workers.worker_main
