#!/usr/bin/env python3
"""
Fix Alembic migration issues - handles missing revisions in database
"""
import sys
import os
sys.path.insert(0, '/app/src')

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from app.config import settings

def get_current_revision_from_db():
    """Get current revision from database"""
    try:
        engine = create_engine(settings.postgres_dsn)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
            row = result.fetchone()
            return row[0] if row else None
    except Exception as e:
        print(f"Error getting current revision from DB: {e}")
        return None

def get_all_revisions_from_files():
    """Get all revision IDs from migration files"""
    try:
        alembic_cfg = Config('/app/alembic.ini')
        script = ScriptDirectory.from_config(alembic_cfg)
        revisions = []
        for script_revision in script.walk_revisions():
            revisions.append(script_revision.revision)
        return revisions
    except Exception as e:
        print(f"Error getting revisions from files: {e}")
        return []

def fix_migration():
    """Fix migration issues"""
    print("Checking migration status...")
    
    # Get current revision from database
    db_revision = get_current_revision_from_db()
    print(f"Current database revision: {db_revision}")
    
    # Get all revisions from files
    file_revisions = get_all_revisions_from_files()
    print(f"Found {len(file_revisions)} migration files")
    
    # Check if database revision exists in files
    if db_revision and db_revision not in file_revisions:
        print(f"ERROR: Database revision '{db_revision}' not found in migration files!")
        print("Attempting to fix by removing invalid revision and stamping to latest...")
        
        try:
            # Delete the invalid revision from database
            engine = create_engine(settings.postgres_dsn)
            with engine.begin() as conn:  # Use begin() for auto-commit
                print(f"Removing invalid revision '{db_revision}' from database...")
                result = conn.execute(text("DELETE FROM alembic_version WHERE version_num = :rev"), {"rev": db_revision})
                deleted = result.rowcount
                print(f"Deleted {deleted} row(s) from alembic_version table")
            
            # Verify deletion
            with engine.connect() as conn:
                result = conn.execute(text("SELECT version_num FROM alembic_version LIMIT 1"))
                row = result.fetchone()
                if row:
                    print(f"WARNING: Still have revision '{row[0]}' in database after deletion")
                else:
                    print("Database alembic_version table is now empty - ready for stamping")
            
            # Get head revision
            alembic_cfg = Config('/app/alembic.ini')
            script = ScriptDirectory.from_config(alembic_cfg)
            head_revision = script.get_current_head()
            
            if head_revision:
                print(f"Stamping database to revision: {head_revision}")
                command.stamp(alembic_cfg, head_revision)
                print(f"Successfully stamped database to {head_revision}")
                return True
            else:
                print("ERROR: Could not determine head revision")
                return False
        except Exception as e:
            print(f"ERROR: Failed to fix database: {e}")
            import traceback
            traceback.print_exc()
            return False
    elif db_revision in file_revisions:
        print(f"Database revision '{db_revision}' exists in migration files - OK")
        return True
    else:
        print("No revision in database - will be set on first migration")
        return True

if __name__ == "__main__":
    try:
        if fix_migration():
            print("Migration fix completed successfully")
            sys.exit(0)
        else:
            print("Migration fix failed")
            sys.exit(1)
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

