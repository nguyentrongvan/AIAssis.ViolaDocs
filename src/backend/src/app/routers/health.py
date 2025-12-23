from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from datetime import datetime, timedelta

from ..utils.response import success_response
from ..services.ai import get_embedding_service
from ..db import get_session
from ..models.ai import AIJob

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check():
    return success_response({"status": "ok"})


@router.get("/health/embedding")
async def embedding_health_check():
    """Check embedding service health status"""
    embedding_service = get_embedding_service()
    if embedding_service:
        health_status = embedding_service.health_check()
        return success_response(health_status)
    else:
        return success_response({
            "available": False,
            "embedder": None,
            "store": None,
            "errors": ["Embedding service not configured"]
        })


@router.get("/health/workers")
async def workers_health_check(session: AsyncSession = Depends(get_session)):
    """Check AI worker health status"""
    # Get active workers (jobs with recent heartbeat)
    heartbeat_threshold = datetime.utcnow() - timedelta(minutes=2)
    
    # Count jobs by worker
    result = await session.execute(
        select(
            AIJob.worker_id,
            func.count(AIJob.id).label('total_jobs'),
            func.sum(func.case((AIJob.status == 'processing', 1), else_=0)).label('processing_jobs'),
            func.max(AIJob.last_heartbeat).label('last_heartbeat')
        )
        .where(
            and_(
                AIJob.worker_id.isnot(None),
                AIJob.job_type == 'ocr',
                AIJob.status == 'processing'
            )
        )
        .group_by(AIJob.worker_id)
    )
    active_workers = result.all()
    
    # Get job statistics
    stats_result = await session.execute(
        select(
            func.count(AIJob.id).label('total'),
            func.sum(func.case((AIJob.status == 'queued', 1), else_=0)).label('queued'),
            func.sum(func.case((AIJob.status == 'processing', 1), else_=0)).label('processing'),
            func.sum(func.case((AIJob.status == 'completed', 1), else_=0)).label('completed'),
            func.sum(func.case((AIJob.status == 'failed', 1), else_=0)).label('failed')
        )
        .where(AIJob.job_type == 'ocr')
    )
    stats = stats_result.first()
    
    workers = []
    for worker in active_workers:
        workers.append({
            "worker_id": worker.worker_id,
            "active_jobs": worker.processing_jobs or 0,
            "total_jobs": worker.total_jobs or 0,
            "last_heartbeat": worker.last_heartbeat.isoformat() if worker.last_heartbeat else None,
            "is_healthy": worker.last_heartbeat and worker.last_heartbeat > heartbeat_threshold if worker.last_heartbeat else False
        })
    
    return success_response({
        "active_workers": len(workers),
        "workers": workers,
        "job_stats": {
            "total": stats.total or 0,
            "queued": stats.queued or 0,
            "processing": stats.processing or 0,
            "completed": stats.completed or 0,
            "failed": stats.failed or 0
        }
    })






