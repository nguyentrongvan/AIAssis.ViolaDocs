from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from ..db import get_session
from ..dependencies import get_current_admin_user
from ..models.users import User
from ..models.documents import Document
from ..models.audit import AuditEvent
from ..utils.response import success_response

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/audit")
async def get_audit_report(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    actor_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    query = select(AuditEvent)
    
    if from_date:
        query = query.where(AuditEvent.timestamp >= datetime.fromisoformat(from_date))
    if to_date:
        query = query.where(AuditEvent.timestamp <= datetime.fromisoformat(to_date))
    if actor_id:
        query = query.where(AuditEvent.actor_id == actor_id)
    if action:
        query = query.where(AuditEvent.action == action)
    
    query = query.order_by(AuditEvent.timestamp.desc()).limit(1000)
    
    result = await session.execute(query)
    events = result.scalars().all()
    
    return success_response({
        "items": [{
            "id": e.id,
            "actor_id": e.actor_id,
            "action": e.action,
            "subject_type": e.subject_type,
            "subject_id": e.subject_id,
            "timestamp": e.timestamp.isoformat(),
            "metadata": e.metadata
        } for e in events],
        "total": len(events)
    })


@router.get("/usage")
async def get_usage_report(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    query = select(
        func.count(Document.id).label("total_documents"),
        func.sum(Document.size).label("total_size")
    ).where(Document.deleted_at.is_(None))
    
    if from_date:
        query = query.where(Document.created_at >= datetime.fromisoformat(from_date))
    if to_date:
        query = query.where(Document.created_at <= datetime.fromisoformat(to_date))
    
    result = await session.execute(query)
    stats = result.first()
    
    return success_response({
        "total_documents": stats.total_documents or 0,
        "total_size": stats.total_size or 0,
        "pending_tasks": 0,  # TODO: Count from tasks
        "recent_uploads": 0  # TODO: Count recent uploads
    })


@router.get("/workflow")
async def get_workflow_report(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    # TODO: Implement workflow SLA report
    return success_response({
        "total_workflows": 0,
        "completed": 0,
        "pending": 0,
        "overdue": 0,
        "avg_completion_time": 0
    })


@router.get("/quality")
async def get_quality_report(
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    # TODO: Implement data quality report
    return success_response({
        "index_failures": 0,
        "embedding_failures": 0,
        "stale_documents": 0,
        "purge_backlog": 0
    })

