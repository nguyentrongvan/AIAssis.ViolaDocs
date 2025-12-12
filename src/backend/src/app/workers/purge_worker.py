"""
Purge Worker - Scheduled job to purge soft-deleted documents past their grace period.
"""
import asyncio
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy import select, and_

from ..config import settings
from ..db import get_session
from ..models.documents import Document, DocumentVersion
from ..models.audit import AuditEvent
from ..services.storage import delete_file_from_minio


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
            Document.purge_at < now,
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
        # Check for legal hold
        if doc.retention_policy_id:
            from ..models.retention import RetentionPolicy
            policy_result = await session.execute(
                select(RetentionPolicy).where(RetentionPolicy.id == doc.retention_policy_id)
            )
            policy = policy_result.scalar_one_or_none()
            if policy and policy.legal_hold:
                stats["skipped_legal_hold"] += 1
                continue
        
        if dry_run:
            stats["purged"] += 1
            continue
        
        try:
            # Delete all versions from storage
            versions_result = await session.execute(
                select(DocumentVersion).where(DocumentVersion.document_id == doc.id)
            )
            versions = versions_result.scalars().all()
            
            for version in versions:
                # Delete blob
                if version.blob_uri:
                    await delete_file_from_minio(version.blob_uri)
                # Delete OCR
                if version.ocr_uri:
                    await delete_file_from_minio(version.ocr_uri)
                # Delete text
                if version.text_uri:
                    await delete_file_from_minio(version.text_uri)
                # Delete thumbnail
                if version.thumbnail_uri:
                    await delete_file_from_minio(version.thumbnail_uri)
            
            # Delete document and versions from database
            await session.delete(doc)
            
            # Create audit event
            audit_event = AuditEvent(
                actor_id=1,  # System user
                subject_type="document",
                subject_id=doc.id,
                action="purge",
                metadata={"title": doc.title, "purged_at": now.isoformat()},
                timestamp=now
            )
            session.add(audit_event)
            
            stats["purged"] += 1
            
        except Exception as e:
            print(f"Error purging document {doc.id}: {e}")
            stats["errors"] += 1
    
    if not dry_run:
        await session.commit()
    
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

