#!/usr/bin/env python
"""
Script to reset admin user password.
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


async def reset_admin_password():
    """Reset admin user password to admin123"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(User).where(User.email == "admin@example.com")
        )
        user = result.scalar_one_or_none()
        
        if not user:
            print("❌ Admin user not found!")
            print("   Run create_admin.py first to create admin user.")
            return
        
        # Reset password to admin123
        user.password_hash = get_password_hash("admin123")
        await session.commit()
        
        print("✅ Password reset successfully!")
        print("\n📋 Login credentials:")
        print("   Email: admin@example.com")
        print("   Password: admin123")
        print("\n⚠️  Please change the password after first login!")


if __name__ == "__main__":
    try:
        asyncio.run(reset_admin_password())
    except Exception as e:
        print(f"❌ Error resetting password: {e}")
        sys.exit(1)

