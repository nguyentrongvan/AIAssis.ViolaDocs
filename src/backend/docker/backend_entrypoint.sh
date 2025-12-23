#!/bin/bash
# Don't use set -e here, we want to handle errors gracefully
set +e

echo "=== ViolaDocs Backend Entrypoint ==="
echo "Working directory: $(pwd)"
echo "Python path: $PYTHONPATH"
echo "Python version: $(python --version)"

# Set Python path if not set
if [ -z "$PYTHONPATH" ]; then
    echo "Setting PYTHONPATH to /app/src"
    export PYTHONPATH=/app/src
fi

# Wait for database to be ready with retry
echo "Waiting for database to be ready..."
MAX_RETRIES=30
RETRY_COUNT=0
DB_READY=0

while [ $RETRY_COUNT -lt $MAX_RETRIES ]; do
    if python -c "
import sys
sys.path.insert(0, '/app/src')
from sqlalchemy import create_engine, text
from app.config import settings
try:
    engine = create_engine(settings.postgres_dsn)
    with engine.connect() as conn:
        conn.execute(text('SELECT 1'))
    print('Database is ready!')
    sys.exit(0)
except Exception as e:
    print(f'Database not ready: {e}')
    sys.exit(1)
" 2>&1; then
        echo "✅ Database is ready!"
        DB_READY=1
        break
    else
        RETRY_COUNT=$((RETRY_COUNT + 1))
        if [ $RETRY_COUNT -lt $MAX_RETRIES ]; then
            echo "Database is unavailable - sleeping (attempt $RETRY_COUNT/$MAX_RETRIES)..."
            sleep 2
        fi
    fi
done

if [ $DB_READY -eq 0 ]; then
    echo "❌ ERROR: Database is not ready after $MAX_RETRIES attempts!"
    echo "   Continuing anyway - migrations and user creation will retry..."
fi

# Run database migrations
echo ""
echo "Running database migrations..."
cd /app

# Try to fix migration issues first (if any)
if [ -f "/app/docker/fix_migration.py" ]; then
    echo "Checking for migration issues..."
    python /app/docker/fix_migration.py 2>&1 || echo "Migration fix script completed (may have warnings)"
fi

MIGRATION_SUCCESS=0
# Try to upgrade to head
if alembic upgrade head 2>&1; then
    echo "✅ Database migrations completed successfully."
    MIGRATION_SUCCESS=1
else
    MIGRATION_EXIT=$?
    echo "⚠️  WARNING: Migration command returned error code: $MIGRATION_EXIT"
    
    # Check if error is about missing revision
    MIGRATION_OUTPUT=$(alembic upgrade head 2>&1)
    if echo "$MIGRATION_OUTPUT" | grep -q "Can't locate revision"; then
        echo "⚠️  ERROR: Database has revision that doesn't exist in migration files."
        echo "   Attempting automatic fix..."
        
        # Run fix script again with more verbose output
        if [ -f "/app/docker/fix_migration.py" ]; then
            python /app/docker/fix_migration.py 2>&1
            # Try upgrade again after fix
            if alembic upgrade head 2>&1; then
                echo "✅ Database migrations completed successfully after fix."
                MIGRATION_SUCCESS=1
            else
                echo "⚠️  WARNING: Still failed after fix. Continuing anyway..."
            fi
        else
            echo "⚠️  WARNING: Fix script not found. Continuing anyway..."
        fi
    else
        echo "⚠️  WARNING: Database migrations may have failed or already up to date."
        echo "   Continuing anyway..."
    fi
fi

# Initialize root user
echo ""
echo "Initializing root user..."
echo "Mode: $([ "${DEBUG:-false}" = "true" ] && echo "DEVELOPMENT" || echo "PRODUCTION")"
if python /app/docker/init_root_user.py 2>&1; then
    echo "✅ Root user initialization completed."
    if [ "${DEBUG:-false}" != "true" ]; then
        echo ""
        echo "🔐 PRODUCTION MODE: Root password has been generated and saved."
        echo "   Check /app/data/root_password.txt inside container or backend_data volume"
        echo "   To view: docker-compose exec backend cat /app/data/root_password.txt"
    fi
else
    echo "⚠️  WARNING: Root user initialization failed or user already exists."
    echo "   Continuing anyway - user may be created on app startup..."
fi

# Start the application (always start, even if previous steps had warnings)
echo ""
echo "Starting ViolaDocs backend server..."
echo "=========================================="
exec uvicorn app.main:app --host 0.0.0.0 --port 8000

