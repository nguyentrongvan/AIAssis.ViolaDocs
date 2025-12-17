from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from ..db import get_session
from ..dependencies import get_current_admin_user, require_permission_or_staff
from ..models.users import User
from ..models.documents import Document
from ..models.audit import AuditEvent
from ..models.workflows import Workflow, Task
from ..models.ai import AIJob
from ..models.chat import ChatSession
from ..utils.response import success_response

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/audit")
async def get_audit_report(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    actor_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    current_user: User = Depends(require_permission_or_staff("reports")),
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
    current_user: User = Depends(require_permission_or_staff("reports")),
    session: AsyncSession = Depends(get_session)
):
    """Get usage metrics report."""
    from_date_obj = datetime.fromisoformat(from_date) if from_date else None
    to_date_obj = datetime.fromisoformat(to_date) if to_date else None
    
    # Documents count and size
    doc_query = select(
        func.count(Document.id).label("total_documents"),
        func.sum(Document.size).label("total_size")
    ).where(Document.deleted_at.is_(None))
    
    if from_date_obj:
        doc_query = doc_query.where(Document.created_at >= from_date_obj)
    if to_date_obj:
        doc_query = doc_query.where(Document.created_at <= to_date_obj)
    
    doc_result = await session.execute(doc_query)
    doc_stats = doc_result.first()
    
    # Pending tasks
    task_query = select(func.count(Task.id)).where(Task.state == "pending")
    task_result = await session.execute(task_query)
    pending_tasks = task_result.scalar() or 0
    
    # Recent uploads (last 7 days)
    recent_date = datetime.utcnow() - timedelta(days=7)
    recent_query = select(func.count(Document.id)).where(
        and_(
            Document.deleted_at.is_(None),
            Document.created_at >= recent_date
        )
    )
    recent_result = await session.execute(recent_query)
    recent_uploads = recent_result.scalar() or 0
    
    # Chatbot sessions
    chat_query = select(func.count(ChatSession.id))
    if from_date_obj:
        chat_query = chat_query.where(ChatSession.created_at >= from_date_obj)
    if to_date_obj:
        chat_query = chat_query.where(ChatSession.created_at <= to_date_obj)
    chat_result = await session.execute(chat_query)
    chatbot_sessions = chat_result.scalar() or 0
    
    return success_response({
        "total_documents": doc_stats.total_documents or 0,
        "total_size": doc_stats.total_size or 0,
        "pending_tasks": pending_tasks,
        "recent_uploads": recent_uploads,
        "chatbot_sessions": chatbot_sessions
    })


@router.get("/workflow")
async def get_workflow_report(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    current_user: User = Depends(require_permission_or_staff("reports")),
    session: AsyncSession = Depends(get_session)
):
    """Get workflow SLA report."""
    from_date_obj = datetime.fromisoformat(from_date) if from_date else None
    to_date_obj = datetime.fromisoformat(to_date) if to_date else None
    
    # Base query
    workflow_query = select(Workflow)
    if from_date_obj:
        workflow_query = workflow_query.where(Workflow.created_at >= from_date_obj)
    if to_date_obj:
        workflow_query = workflow_query.where(Workflow.created_at <= to_date_obj)
    
    workflow_result = await session.execute(workflow_query)
    workflows = workflow_result.scalars().all()
    
    total_workflows = len(workflows)
    completed = sum(1 for w in workflows if w.state == "completed")
    pending = sum(1 for w in workflows if w.state in ["pending", "in_progress"])
    
    # Calculate overdue (workflows with due_at in the past and not completed)
    now = datetime.utcnow()
    overdue = sum(1 for w in workflows if w.due_at and w.due_at < now and w.state != "completed")
    
    # Calculate average completion time
    completion_times = []
    for w in workflows:
        if w.state == "completed":
            # Get tasks to find completion time
            task_result = await session.execute(
                select(Task).where(
                    and_(
                        Task.workflow_id == w.id,
                        Task.completed_at.isnot(None)
                    )
                ).order_by(Task.completed_at.desc()).limit(1)
            )
            last_task = task_result.scalar_one_or_none()
            if last_task and last_task.completed_at:
                duration = (last_task.completed_at - w.created_at).total_seconds() / 3600  # hours
                completion_times.append(duration)
    
    avg_completion_time = sum(completion_times) / len(completion_times) if completion_times else 0
    
    return success_response({
        "total_workflows": total_workflows,
        "completed": completed,
        "pending": pending,
        "overdue": overdue,
        "avg_completion_time_hours": round(avg_completion_time, 2)
    })


@router.get("/quality")
async def get_quality_report(
    current_user: User = Depends(require_permission_or_staff("reports")),
    session: AsyncSession = Depends(get_session)
):
    """Get data quality report."""
    # Index/embedding failures
    failure_query = select(func.count(AIJob.id)).where(
        and_(
            AIJob.status == "failed",
            AIJob.job_type.in_(["embed", "ocr"])
        )
    )
    failure_result = await session.execute(failure_query)
    index_failures = failure_result.scalar() or 0
    
    embedding_failures_query = select(func.count(AIJob.id)).where(
        and_(
            AIJob.status == "failed",
            AIJob.job_type == "embed"
        )
    )
    embedding_failures_result = await session.execute(embedding_failures_query)
    embedding_failures = embedding_failures_result.scalar() or 0
    
    # Stale documents (ready but no embeddings)
    stale_query = select(func.count(Document.id)).where(
        and_(
            Document.deleted_at.is_(None),
            Document.status == "ready"
        )
    )
    stale_result = await session.execute(stale_query)
    total_ready = stale_result.scalar() or 0
    
    # Count documents with embeddings (simplified - would need to check actual embeddings)
    # For now, estimate based on completed embed jobs
    embed_success_query = select(func.count(AIJob.id)).where(
        and_(
            AIJob.status == "completed",
            AIJob.job_type == "embed"
        )
    )
    embed_success_result = await session.execute(embed_success_query)
    documents_with_embeddings = embed_success_result.scalar() or 0
    stale_documents = max(0, total_ready - documents_with_embeddings)
    
    # Purge backlog (documents with purge_at in the past)
    now = datetime.utcnow()
    purge_query = select(func.count(Document.id)).where(
        and_(
            Document.purge_at.isnot(None),
            Document.purge_at < now,
            Document.deleted_at.isnot(None)
        )
    )
    purge_result = await session.execute(purge_query)
    purge_backlog = purge_result.scalar() or 0
    
    return success_response({
        "index_failures": index_failures,
        "embedding_failures": embedding_failures,
        "stale_documents": stale_documents,
        "purge_backlog": purge_backlog
    })






