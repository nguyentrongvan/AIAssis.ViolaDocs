#!/usr/bin/env python
"""
Script to create the first admin user for ViolaDocs.
This script can be run after database migrations to create an initial admin account.
"""
import asyncio
import sys
from pathlib import Path

# Add src to path
backend_dir = Path(__file__).parent
src_dir = backend_dir / "src"
sys.path.insert(0, str(src_dir))

from sqlalchemy import select
from app.db import AsyncSessionLocal
from app.models.users import User
from app.services.auth import get_password_hash


async def create_admin():
    """Create the first admin user if it doesn't exist"""
    async with AsyncSessionLocal() as session:
        # Check if admin exists
        result = await session.execute(
            select(User).where(User.email == "admin@example.com")
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            print("❌ Admin user already exists!")
            print(f"   Email: {existing.email}")
            print(f"   Role: {existing.role}")
            return
        
        # Create admin user
        admin = User(
            name="Admin",
            email="admin@example.com",
            password_hash=get_password_hash("admin123"),
            role="admin",
            status="active",
            created_by=None
        )
        session.add(admin)
        await session.commit()
        await session.refresh(admin)
        
        print("✅ Admin user created successfully!")
        print("\n📋 Login credentials:")
        print("   Email: admin@example.com")
        print("   Password: admin123")
        print("\n⚠️  Please change the password after first login!")


if __name__ == "__main__":
    try:
        asyncio.run(create_admin())
    except Exception as e:
        print(f"❌ Error creating admin user: {e}")
        sys.exit(1)






