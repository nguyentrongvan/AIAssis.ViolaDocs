"""
Purge Worker - Scheduled job to purge soft-deleted documents past their grace period.
"""
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..config import settings
from ..db import get_session
from ..models.documents import Document
from ..services.deletion_service import DocumentDeletionService


async def purge_documents(session: AsyncSession, dry_run: bool = False) -> dict:
    """
    Purge documents that have purge_at date in the past.
    
    Args:
        session: Database session
        dry_run: If True, only report what would be purged without actually deleting
    
    Returns:
        Dictionary with purge statistics
    """
    now = datetime.utcnow()
    
    # Find documents ready for purging
    query = select(Document).where(
        and_(
            Document.purge_at.isnot(None),
            Document.purge_at <= now,
            Document.deleted_at.isnot(None)  # Only purge soft-deleted documents
        )
    )
    
    result = await session.execute(query)
    documents_to_purge = result.scalars().all()
    
    stats = {
        "found": len(documents_to_purge),
        "purged": 0,
        "errors": 0,
        "skipped_legal_hold": 0
    }
    
    for doc in documents_to_purge:
        if dry_run:
            stats["purged"] += 1
            continue
        
        try:
            # Use DocumentDeletionService to hard delete
            # This handles all cleanup: storage files, embeddings, database records, audit logging
            await DocumentDeletionService.hard_delete_document(
                doc_id=doc.id,
                user_id=1,  # System user
                session=session,
                force=False  # Respect purge_at date
            )
            stats["purged"] += 1
            
        except ValueError as e:
            # Legal hold or other validation error
            if "legal hold" in str(e).lower():
                stats["skipped_legal_hold"] += 1
            else:
                print(f"Error purging document {doc.id}: {e}")
                stats["errors"] += 1
        except Exception as e:
            print(f"Error purging document {doc.id}: {e}")
            import traceback
            traceback.print_exc()
            stats["errors"] += 1
    
    return stats


async def run_purge_worker(dry_run: bool = False):
    """Run the purge worker (can be called from a scheduler)."""
    from ..db import AsyncSessionLocal
    
    async with AsyncSessionLocal() as session:
        try:
            stats = await purge_documents(session, dry_run=dry_run)
            print(f"Purge worker completed: {stats}")
            return stats
        except Exception as e:
            print(f"Error in purge worker: {e}")
            await session.rollback()
            raise


if __name__ == "__main__":
    # For testing
    asyncio.run(run_purge_worker(dry_run=True))

