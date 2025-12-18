from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession
import csv
import io
import json

from ..db import get_session
from ..dependencies import require_permission_or_staff
from ..models.users import User
from ..services.report_service import ReportService
from ..utils.response import success_response

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/audit")
async def get_audit_report(
    from_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    to_date: Optional[str] = Query(None, description="End date (ISO format)"),
    actor_id: Optional[int] = Query(None, description="Filter by actor user ID"),
    action: Optional[str] = Query(None, description="Filter by action type"),
    document_id: Optional[int] = Query(None, description="Filter by document ID"),
    device_id: Optional[int] = Query(None, description="Filter by device ID"),
    page: int = Query(1, ge=1, description="Page number"),
    size: int = Query(50, ge=1, le=1000, description="Page size"),
    current_user: User = Depends(require_permission_or_staff("reports")),
    session: AsyncSession = Depends(get_session)
):
    """Get audit report with filters, aggregations, and pagination."""
    from_date_obj = datetime.fromisoformat(from_date) if from_date else None
    to_date_obj = datetime.fromisoformat(to_date) if to_date else None
    
    report_data = await ReportService.generate_audit_report(
        session=session,
        from_date=from_date_obj,
        to_date=to_date_obj,
        actor_id=actor_id,
        action=action,
        document_id=document_id,
        device_id=device_id,
        page=page,
        size=size
    )
    
    return success_response(report_data)


@router.get("/usage")
async def get_usage_report(
    from_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    to_date: Optional[str] = Query(None, description="End date (ISO format)"),
    rollup: str = Query("day", regex="^(hour|day|week)$", description="Time rollup granularity"),
    top_n: int = Query(10, ge=1, le=100, description="Number of top items in breakdowns"),
    current_user: User = Depends(require_permission_or_staff("reports")),
    session: AsyncSession = Depends(get_session)
):
    """Get usage metrics report with time rollups and breakdowns."""
    from_date_obj = datetime.fromisoformat(from_date) if from_date else None
    to_date_obj = datetime.fromisoformat(to_date) if to_date else None
    
    report_data = await ReportService.generate_usage_report(
        session=session,
        from_date=from_date_obj,
        to_date=to_date_obj,
        rollup=rollup,
        top_n=top_n
    )
    
    return success_response(report_data)


@router.get("/workflow")
async def get_workflow_report(
    from_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    to_date: Optional[str] = Query(None, description="End date (ISO format)"),
    template: Optional[str] = Query(None, description="Filter by workflow template"),
    assignee_id: Optional[int] = Query(None, description="Filter by assignee user ID"),
    current_user: User = Depends(require_permission_or_staff("reports")),
    session: AsyncSession = Depends(get_session)
):
    """Get workflow SLA report with durations and approval rates."""
    from_date_obj = datetime.fromisoformat(from_date) if from_date else None
    to_date_obj = datetime.fromisoformat(to_date) if to_date else None
    
    report_data = await ReportService.generate_workflow_report(
        session=session,
        from_date=from_date_obj,
        to_date=to_date_obj,
        template=template,
        assignee_id=assignee_id
    )
    
    return success_response(report_data)


@router.get("/quality")
async def get_quality_report(
    from_date: Optional[str] = Query(None, description="Start date (ISO format)"),
    to_date: Optional[str] = Query(None, description="End date (ISO format)"),
    current_user: User = Depends(require_permission_or_staff("reports")),
    session: AsyncSession = Depends(get_session)
):
    """Get data quality report with failures and issues."""
    from_date_obj = datetime.fromisoformat(from_date) if from_date else None
    to_date_obj = datetime.fromisoformat(to_date) if to_date else None
    
    report_data = await ReportService.generate_quality_report(
        session=session,
        from_date=from_date_obj,
        to_date=to_date_obj
    )
    
    return success_response(report_data)


@router.post("/audit/export")
async def export_audit_report(
    from_date: Optional[str] = Query(None),
    to_date: Optional[str] = Query(None),
    actor_id: Optional[int] = Query(None),
    action: Optional[str] = Query(None),
    document_id: Optional[int] = Query(None),
    device_id: Optional[int] = Query(None),
    format: str = Query("csv", regex="^(csv|json)$", description="Export format"),
    current_user: User = Depends(require_permission_or_staff("reports")),
    session: AsyncSession = Depends(get_session)
):
    """Export audit report to CSV or JSON."""
    from_date_obj = datetime.fromisoformat(from_date) if from_date else None
    to_date_obj = datetime.fromisoformat(to_date) if to_date else None
    
    # Get all data (no pagination for export)
    report_data = await ReportService.generate_audit_report(
        session=session,
        from_date=from_date_obj,
        to_date=to_date_obj,
        actor_id=actor_id,
        action=action,
        document_id=document_id,
        device_id=device_id,
        page=1,
        size=10000  # Large limit for export
    )
    
    if format == "csv":
        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow([
            "ID", "Timestamp", "Actor ID", "Actor Name", "Action",
            "Subject Type", "Subject ID", "Document Title", "Metadata"
        ])
        
        # Write rows
        for item in report_data["items"]:
            writer.writerow([
                item["id"],
                item["timestamp"],
                item["actor_id"],
                item.get("actor_name", ""),
                item["action"],
                item["subject_type"],
                item["subject_id"],
                item.get("document_title", ""),
                json.dumps(item.get("metadata", {}))
            ])
        
        return Response(
            content=output.getvalue(),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=audit_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.csv"
            }
        )
    else:
        # Generate JSON
        return Response(
            content=json.dumps(report_data, indent=2),
            media_type="application/json",
            headers={
                "Content-Disposition": f"attachment; filename=audit_report_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.json"
            }
        )
