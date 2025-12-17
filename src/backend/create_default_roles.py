#!/usr/bin/env python
"""
Script to create default roles for ViolaDocs.
This script creates common roles with appropriate permissions.
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
from app.models.roles import Role


# Default roles with their user-level permissions
# Note: Document-level permissions (view/search/chat) are set when sharing documents, not in roles
DEFAULT_ROLES = [
    {
        "name": "viewer",
        "permissions": []  # No user-level permissions, only document-level view permission when shared
    },
    {
        "name": "searcher",
        "permissions": ["search"]  # User-level: can access search menu
    },
    {
        "name": "chatter",
        "permissions": ["chat"]  # User-level: can access chat menu
    },
    {
        "name": "uploader",
        "permissions": ["upload"]  # User-level: can access upload menu
    },
    {
        "name": "scanner",
        "permissions": ["scan"]  # User-level: can access scan menu
    },
    {
        "name": "deleter",
        "permissions": ["delete"]  # User-level: can access recycle bin menu
    },
    {
        "name": "editor",
        "permissions": ["upload", "search", "scan", "chat", "folder"]  # User-level: can access multiple menus
    },
    {
        "name": "manager",
        "permissions": ["upload", "search", "scan", "chat", "folder", "settings", "reports", "user"]  # All user-level permissions
    }
]


async def create_default_roles():
    """Create default roles if they don't exist"""
    async with AsyncSessionLocal() as session:
        created_count = 0
        skipped_count = 0
        
        for role_data in DEFAULT_ROLES:
            # Check if role exists
            result = await session.execute(
                select(Role).where(Role.name == role_data["name"])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"⏭️  Role '{role_data['name']}' already exists, skipping...")
                skipped_count += 1
                continue
            
            # Create role
            role = Role(
                name=role_data["name"],
                permissions=role_data["permissions"]
            )
            session.add(role)
            created_count += 1
            print(f"✅ Created role: {role_data['name']} with permissions: {', '.join(role_data['permissions'])}")
        
        await session.commit()
        
        print(f"\n📊 Summary:")
        print(f"   Created: {created_count} roles")
        print(f"   Skipped: {skipped_count} roles")
        print(f"   Total: {len(DEFAULT_ROLES)} roles")


if __name__ == "__main__":
    try:
        asyncio.run(create_default_roles())
    except Exception as e:
        print(f"❌ Error creating default roles: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

