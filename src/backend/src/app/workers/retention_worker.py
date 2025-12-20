"""
Retention Worker - Scheduled job to check and apply retention policies.
"""
import asyncio
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_async_session
from ..services.retention import apply_retention_policies

logger = logging.getLogger(__name__)


async def run_retention_worker():
    """Run the retention worker (can be called from a scheduler)."""
    from ..db import AsyncSessionLocal
    
    async with AsyncSessionLocal() as session:
        try:
            stats = await apply_retention_policies(session)
            logger.info(f"Retention worker completed: {stats}")
            return stats
        except Exception as e:
            logger.error(f"Error in retention worker: {e}", exc_info=True)
            await session.rollback()
            raise


if __name__ == "__main__":
    # For testing
    asyncio.run(run_retention_worker())

