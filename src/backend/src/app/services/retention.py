from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_

from ..models.documents import Document
from ..models.retention import RetentionPolicy


async def apply_retention_policies(session: AsyncSession) -> dict:
    """Apply retention policies to documents and set purge_at dates."""
    # Get all active retention policies
    policies_result = await session.execute(select(RetentionPolicy))
    policies = policies_result.scalars().all()
    
    stats = {
        "policies_processed": len(policies),
        "documents_updated": 0,
        "legal_hold_protected": 0
    }
    
    for policy in policies:
        # Calculate purge date based on policy duration
        duration = timedelta(days=policy.duration_days)
        
        # Get documents with this retention policy that don't have purge_at set
        docs_query = select(Document).where(
            and_(
                Document.retention_policy_id == policy.id,
                Document.purge_at.is_(None),
                Document.deleted_at.is_(None)
            )
        )
        docs_result = await session.execute(docs_query)
        docs = docs_result.scalars().all()
        
        for doc in docs:
            # Check if document has legal hold (via retention policy)
            if policy.legal_hold:
                stats["legal_hold_protected"] += 1
                continue  # Skip documents with legal hold
            
            # Set purge_at based on document creation date + retention duration
            purge_date = doc.created_at + duration
            doc.purge_at = purge_date
            stats["documents_updated"] += 1
    
    await session.commit()
    return stats


async def check_legal_hold(document_id: int, session: AsyncSession) -> bool:
    """Check if a document is protected by legal hold."""
    doc_result = await session.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = doc_result.scalar_one_or_none()
    
    if not doc or not doc.retention_policy_id:
        return False
    
    policy_result = await session.execute(
        select(RetentionPolicy).where(RetentionPolicy.id == doc.retention_policy_id)
    )
    policy = policy_result.scalar_one_or_none()
    
    if not policy:
        return False
    
    return policy.legal_hold

