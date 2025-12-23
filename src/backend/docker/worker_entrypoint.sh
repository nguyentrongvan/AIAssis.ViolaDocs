#!/bin/bash
set -e

echo "=== AI Worker Entrypoint ==="
echo "Working directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Python version: $(python --version)"

# Run database migrations
echo "Running database migrations..."
cd /app

# Try to fix migration issues first (if any)
if [ -f "/app/docker/fix_migration.py" ]; then
    echo "Checking for migration issues..."
    python /app/docker/fix_migration.py 2>&1 || echo "Migration fix script completed (may have warnings)"
fi

# Try to upgrade to head
if alembic upgrade head 2>&1; then
    echo "Database migrations completed successfully."
else
    MIGRATION_EXIT=$?
    echo "WARNING: Migration command returned error code: $MIGRATION_EXIT"
    
    # Check if error is about missing revision
    MIGRATION_OUTPUT=$(alembic upgrade head 2>&1)
    if echo "$MIGRATION_OUTPUT" | grep -q "Can't locate revision"; then
        echo "ERROR: Database has revision that doesn't exist in migration files."
        echo "Attempting automatic fix..."
        
        # Run fix script again with more verbose output
        if [ -f "/app/docker/fix_migration.py" ]; then
            python /app/docker/fix_migration.py 2>&1
            # Try upgrade again after fix
            if alembic upgrade head 2>&1; then
                echo "Database migrations completed successfully after fix."
            else
                echo "ERROR: Still failed after fix. Continuing anyway..."
            fi
        else
            echo "ERROR: Fix script not found. Continuing anyway..."
        fi
    else
        echo "ERROR: Database migrations failed with unknown error!"
        echo "Continuing anyway - application may not work correctly."
    fi
fi

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
echo "Starting AI worker..."
exec python -m app.workers.worker_main
