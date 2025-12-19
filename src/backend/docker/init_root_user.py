#!/usr/bin/env python
"""
Script to initialize root user for ViolaDocs.
This script is called from backend_entrypoint.sh after migrations.

In dev mode (DEBUG=true): Uses fixed password from environment
In production mode (DEBUG=false): Generates random strong password
"""
import asyncio
import sys
import os
import secrets
import string
from pathlib import Path

# Add src to path
backend_dir = Path(__file__).parent.parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

from sqlalchemy import select
from app.db import AsyncSessionLocal
from app.models.users import User
from app.services.auth import get_password_hash
from app.config import settings


def generate_strong_password(length=24):
    """Generate a random strong password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for i in range(length))
    return password


async def init_root_user():
    """Initialize root user if it doesn't exist"""
    try:
        async with AsyncSessionLocal() as session:
            # Check if root user exists
            result = await session.execute(
                select(User).where(User.email == settings.root_user_email)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"✅ Root user already exists: {settings.root_user_email}")
                return True
            
            # Check if any maintainer exists
            result = await session.execute(
                select(User).where(User.is_maintainer == True)
            )
            maintainer_exists = result.scalar_one_or_none()
            
            if maintainer_exists:
                print("✅ Maintainer user already exists, skipping root user creation")
                return True
            
            # Determine password based on mode
            if settings.debug:
                # Dev mode: Use fixed password from environment
                root_password = settings.root_user_password
                print("📝 Development mode: Using configured password")
            else:
                # Production mode: Generate random strong password
                root_password = generate_strong_password(32)
                print("🔐 Production mode: Generated random strong password")
            
            # Create root user
            root_user = User(
                name=settings.root_user_name,
                email=settings.root_user_email,
                password_hash=get_password_hash(root_password),
                role="admin",
                status="active",
                is_maintainer=True,  # Root user is maintainer
                created_by=None
            )
            session.add(root_user)
            await session.commit()
            await session.refresh(root_user)
            
            print(f"✅ Root user created successfully: {settings.root_user_email}")
            print(f"   Name: {settings.root_user_name}")
            print(f"   Password: {root_password}")
            
            # In production, also save password to file for admin access
            if not settings.debug:
                # Try to save to data directory (mounted volume) or app directory
                data_dir = Path("/app/data")
                if not data_dir.exists():
                    data_dir = Path("/app")
                
                password_file = data_dir / "root_password.txt"
                try:
                    data_dir.mkdir(parents=True, exist_ok=True)
                    with open(password_file, 'w') as f:
                        f.write(f"Root User Credentials\n")
                        f.write(f"====================\n")
                        f.write(f"Email: {settings.root_user_email}\n")
                        f.write(f"Password: {root_password}\n")
                        f.write(f"\n⚠️  IMPORTANT: Change this password immediately after first login!\n")
                        f.write(f"⚠️  Delete this file after saving the password securely.\n")
                    print(f"💾 Password saved to: {password_file}")
                    print("⚠️  Please save this password securely and delete the file!")
                except Exception as e:
                    print(f"⚠️  Could not save password to file: {e}")
                    print(f"   Password is: {root_password}")
                    print("   Please save this password immediately!")
            
            print("⚠️  Please change the password after first login!")
            return True
            
    except Exception as e:
        # Check if error is due to missing tables (database not migrated yet)
        error_str = str(e).lower()
        if "does not exist" in error_str or "undefinedtable" in error_str or "relation" in error_str:
            print(f"⚠️  Database tables not found: {e}")
            print("   Root user will be created automatically after migrations.")
            return False
        else:
            print(f"❌ Error creating root user: {e}")
            import traceback
            traceback.print_exc()
            return False


if __name__ == "__main__":
    try:
        success = asyncio.run(init_root_user())
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

