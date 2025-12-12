"""
Retention Worker - Scheduled job to check and apply retention policies.
"""
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_async_session
from ..services.retention import apply_retention_policies


async def run_retention_worker():
    """Run the retention worker (can be called from a scheduler)."""
    from ..db import AsyncSessionLocal
    
    async with AsyncSessionLocal() as session:
        try:
            stats = await apply_retention_policies(session)
            print(f"Retention worker completed: {stats}")
            return stats
        except Exception as e:
            print(f"Error in retention worker: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    # For testing
    asyncio.run(run_retention_worker())

