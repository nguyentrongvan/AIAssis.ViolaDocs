from typing import Optional
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
import csv
import io

from ..db import get_session
from ..dependencies import get_current_admin_user
from ..models.users import User
from ..models.audit import AuditEvent
from ..utils.response import success_response, error_response
from fastapi.responses import StreamingResponse

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("")
async def get_audit_logs(
    actor_id: Optional[int] = Query(None),
    subject_type: Optional[str] = Query(None),
    subject_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Get audit logs with filters (admin only)."""
    query = select(AuditEvent)
    
    # Apply filters
    if actor_id:
        query = query.where(AuditEvent.actor_id == actor_id)
    if subject_type:
        query = query.where(AuditEvent.subject_type == subject_type)
    if subject_id:
        query = query.where(AuditEvent.subject_id == subject_id)
    if action:
        query = query.where(AuditEvent.action == action)
    if from_date:
        from_dt = datetime.fromisoformat(from_date.replace('Z', '+00:00'))
        query = query.where(AuditEvent.timestamp >= from_dt)
    if to_date:
        to_dt = datetime.fromisoformat(to_date.replace('Z', '+00:00'))
        query = query.where(AuditEvent.timestamp <= to_dt)
    
    # Order and paginate
    query = query.order_by(AuditEvent.timestamp.desc()).offset(skip).limit(limit)
    
    result = await session.execute(query)
    events = result.scalars().all()
    
    return success_response({
        "items": [{
            "id": e.id,
            "actor_id": e.actor_id,
            "subject_type": e.subject_type,
            "subject_id": e.subject_id,
            "action": e.action,
            "timestamp": e.timestamp.isoformat(),
            "metadata": e.metadata_ if hasattr(e, 'metadata_') else e.metadata if hasattr(e, 'metadata') else None,
            "ip": e.ip,
            "user_agent": e.user_agent
        } for e in events],
        "total": len(events)
    })


class ExportRequest(BaseModel):
    from_date: Optional[str] = None
    to_date: Optional[str] = None
    format: str = "csv"  # csv, json
    actor_id: Optional[int] = None
    action: Optional[str] = None
    subject_type: Optional[str] = None
    subject_id: Optional[int] = None


@router.post("/export")
async def export_audit_logs(
    request: ExportRequest,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Export audit logs (admin only)."""
    query = select(AuditEvent)
    
    # Apply filters
    if request.actor_id:
        query = query.where(AuditEvent.actor_id == request.actor_id)
    if request.subject_type:
        query = query.where(AuditEvent.subject_type == request.subject_type)
    if request.subject_id:
        query = query.where(AuditEvent.subject_id == request.subject_id)
    if request.action:
        query = query.where(AuditEvent.action == request.action)
    if request.from_date:
        from_dt = datetime.fromisoformat(request.from_date.replace('Z', '+00:00'))
        query = query.where(AuditEvent.timestamp >= from_dt)
    if request.to_date:
        to_dt = datetime.fromisoformat(request.to_date.replace('Z', '+00:00'))
        query = query.where(AuditEvent.timestamp <= to_dt)
    
    query = query.order_by(AuditEvent.timestamp.desc())
    
    result = await session.execute(query)
    events = result.scalars().all()
    
    if request.format == "csv":
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["id", "actor_id", "subject_type", "subject_id", "action", "timestamp", "ip", "user_agent", "metadata"])
        
        for e in events:
            metadata_str = str(e.metadata_ if hasattr(e, 'metadata_') else e.metadata if hasattr(e, 'metadata') else None)
            writer.writerow([
                e.id,
                e.actor_id,
                e.subject_type,
                e.subject_id,
                e.action,
                e.timestamp.isoformat(),
                e.ip or "",
                e.user_agent or "",
                metadata_str
            ])
        
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=audit_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"}
        )
    else:
        # JSON format
        return success_response({
            "items": [{
                "id": e.id,
                "actor_id": e.actor_id,
                "subject_type": e.subject_type,
                "subject_id": e.subject_id,
                "action": e.action,
                "timestamp": e.timestamp.isoformat(),
                "metadata": e.metadata_ if hasattr(e, 'metadata_') else e.metadata if hasattr(e, 'metadata') else None,
                "ip": e.ip,
                "user_agent": e.user_agent
            } for e in events],
            "total": len(events)
        })

