"""
Purge Worker - Scheduled job to purge soft-deleted documents past their grace period.
"""
import asyncio
import logging
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..config import settings
from ..db import get_session
from ..models.documents import Document
from ..services.deletion_service import DocumentDeletionService

logger = logging.getLogger(__name__)


async def purge_documents(session: AsyncSession, dry_run: bool = False, batch_size: int = 100) -> dict:
    """
    Purge documents that have purge_at date in the past.
    
    Args:
        session: Database session
        dry_run: If True, only report what would be purged without actually deleting
        batch_size: Maximum number of documents to process in one run
    
    Returns:
        Dictionary with purge statistics
    """
    now = datetime.utcnow()
    
    logger.info(f"Starting purge worker (dry_run={dry_run}, batch_size={batch_size})")
    
    # Find documents ready for purging (limit to batch_size)
    query = select(Document).where(
        and_(
            Document.purge_at.isnot(None),
            Document.purge_at <= now,
            Document.deleted_at.isnot(None)  # Only purge soft-deleted documents
        )
    ).limit(batch_size)
    
    result = await session.execute(query)
    documents_to_purge = result.scalars().all()
    
    logger.info(f"Found {len(documents_to_purge)} documents ready for purging")
    
    stats = {
        "found": len(documents_to_purge),
        "purged": 0,
        "errors": 0,
        "skipped_legal_hold": 0
    }
    
    for doc in documents_to_purge:
        if dry_run:
            logger.debug(f"Would purge document {doc.id} (dry run)")
            stats["purged"] += 1
            continue
        
        try:
            logger.info(f"Purging document {doc.id} (purge_at: {doc.purge_at})")
            
            # Use DocumentDeletionService to hard delete
            # This handles all cleanup: storage files, embeddings, database records, audit logging
            await DocumentDeletionService.hard_delete_document(
                doc_id=doc.id,
                user_id=1,  # System user
                session=session,
                force=False  # Respect purge_at date
            )
            stats["purged"] += 1
            logger.info(f"Successfully purged document {doc.id}")
            
        except ValueError as e:
            # Legal hold or other validation error
            if "legal hold" in str(e).lower():
                logger.warning(f"Skipping document {doc.id} due to legal hold")
                stats["skipped_legal_hold"] += 1
            else:
                logger.error(f"Error purging document {doc.id}: {e}")
                stats["errors"] += 1
        except Exception as e:
            logger.error(f"Error purging document {doc.id}: {e}", exc_info=True)
            stats["errors"] += 1
    
    logger.info(f"Purge worker completed: {stats}")
    return stats


async def run_purge_worker(dry_run: bool = False, batch_size: int = 100):
    """
    Run the purge worker (can be called from a scheduler).
    
    Args:
        dry_run: If True, only report what would be purged without actually deleting
        batch_size: Maximum number of documents to process in one run
    
    Returns:
        Dictionary with purge statistics
    """
    from ..db import AsyncSessionLocal
    
    async with AsyncSessionLocal() as session:
        try:
            stats = await purge_documents(session, dry_run=dry_run, batch_size=batch_size)
            return stats
        except Exception as e:
            logger.error(f"Error in purge worker: {e}", exc_info=True)
            await session.rollback()
            raise


if __name__ == "__main__":
    # For testing
    asyncio.run(run_purge_worker(dry_run=True))

