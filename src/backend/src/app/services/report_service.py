"""Report generation service for aggregating and formatting report data."""
from datetime import datetime, timedelta
from typing import Optional, Dict, List, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, case, distinct, desc, asc, Integer
import json
from sqlalchemy.orm import joinedload

from ..models.users import User
from ..models.documents import Document, DocumentTag, Tag, Folder
from ..models.audit import AuditEvent
from ..models.workflows import Workflow, Task
from ..models.ai import AIJob, Embedding
from ..models.chat import ChatSession
from ..models.groups import DocumentGroup
from ..models.devices import Device


class ReportService:
    """Service for generating various reports."""
    
    @staticmethod
    async def generate_audit_report(
        session: AsyncSession,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        actor_id: Optional[int] = None,
        action: Optional[str] = None,
        document_id: Optional[int] = None,
        device_id: Optional[int] = None,
        page: int = 1,
        size: int = 50
    ) -> Dict[str, Any]:
        """Generate audit report with filters, aggregations, and pagination."""
        # Base query with joins
        query = select(
            AuditEvent,
            User.name.label("actor_name"),
            Document.title.label("document_title")
        ).outerjoin(
            User, AuditEvent.actor_id == User.id
        ).outerjoin(
            Document, and_(
                AuditEvent.subject_type == "document",
                AuditEvent.subject_id == Document.id
            )
        )
        
        # Apply filters
        conditions = []
        if from_date:
            conditions.append(AuditEvent.timestamp >= from_date)
        if to_date:
            conditions.append(AuditEvent.timestamp <= to_date)
        if actor_id:
            conditions.append(AuditEvent.actor_id == actor_id)
        if action:
            conditions.append(AuditEvent.action == action)
        if document_id:
            conditions.append(and_(
                AuditEvent.subject_type == "document",
                AuditEvent.subject_id == document_id
            ))
        if device_id:
            conditions.append(and_(
                AuditEvent.subject_type == "device",
                AuditEvent.subject_id == device_id
            ))
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # Get total count
        count_query = select(func.count(AuditEvent.id))
        if conditions:
            count_query = count_query.where(and_(*conditions))
        total_result = await session.execute(count_query)
        total = total_result.scalar() or 0
        
        # Get paginated items
        query = query.order_by(AuditEvent.timestamp.desc())
        query = query.offset((page - 1) * size).limit(size)
        result = await session.execute(query)
        rows = result.all()
        
        items = []
        for event, actor_name, document_title in rows:
            items.append({
                "id": event.id,
                "actor_id": event.actor_id,
                "actor_name": actor_name,
                "action": event.action,
                "subject_type": event.subject_type,
                "subject_id": event.subject_id,
                "document_title": document_title,
                "timestamp": event.timestamp.isoformat(),
                "created_at": event.created_at.isoformat(),
                "metadata": event.metadata_ or {}
            })
        
        # Aggregations
        agg_query = select(
            func.count(distinct(AuditEvent.actor_id)).label("unique_users"),
            func.count(distinct(
                case(
                    (AuditEvent.subject_type == "document", AuditEvent.subject_id),
                    else_=None
                )
            )).label("unique_documents"),
            func.count(AuditEvent.id).label("total")
        )
        if conditions:
            agg_query = agg_query.where(and_(*conditions))
        agg_result = await session.execute(agg_query)
        agg_row = agg_result.first()
        
        unique_users = agg_row.unique_users or 0
        unique_documents = agg_row.unique_documents or 0
        
        # Action counts
        action_query = select(
            AuditEvent.action,
            func.count(AuditEvent.id).label("count")
        )
        if conditions:
            action_query = action_query.where(and_(*conditions))
        action_query = action_query.group_by(AuditEvent.action)
        action_result = await session.execute(action_query)
        action_counts = {row.action: row.count for row in action_result.all()}
        
        # Timeline data (group by day)
        timeline_query = select(
            func.date(AuditEvent.timestamp).label("date"),
            func.count(AuditEvent.id).label("count")
        )
        if conditions:
            timeline_query = timeline_query.where(and_(*conditions))
        timeline_query = timeline_query.group_by(
            func.date(AuditEvent.timestamp)
        ).order_by(asc(func.date(AuditEvent.timestamp)))
        timeline_result = await session.execute(timeline_query)
        timeline_data = [
            {"date": row.date.isoformat(), "count": row.count}
            for row in timeline_result.all()
        ]
        
        # Top actors
        top_actors_query = select(
            AuditEvent.actor_id,
            User.name.label("name"),
            func.count(AuditEvent.id).label("count")
        ).join(User, AuditEvent.actor_id == User.id)
        if conditions:
            top_actors_query = top_actors_query.where(and_(*conditions))
        top_actors_query = top_actors_query.group_by(
            AuditEvent.actor_id, User.name
        ).order_by(desc(func.count(AuditEvent.id))).limit(10)
        top_actors_result = await session.execute(top_actors_query)
        top_actors = [
            {"user_id": row.actor_id, "name": row.name, "count": row.count}
            for row in top_actors_result.all()
        ]
        
        total_pages = (total + size - 1) // size if total > 0 else 1
        
        return {
            "total": total,
            "unique_users": unique_users,
            "unique_documents": unique_documents,
            "action_counts": action_counts,
            "timeline_data": timeline_data,
            "top_actors": top_actors,
            "items": items,
            "pagination": {
                "page": page,
                "size": size,
                "total_pages": total_pages,
                "total": total
            }
        }
    
    @staticmethod
    async def generate_usage_report(
        session: AsyncSession,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        rollup: str = "day",
        top_n: int = 10
    ) -> Dict[str, Any]:
        """Generate usage metrics report with time rollups and breakdowns."""
        # Default date range: last 30 days if not specified
        if not from_date:
            from_date = datetime.utcnow() - timedelta(days=30)
        if not to_date:
            to_date = datetime.utcnow()
        
        # Total documents and storage
        doc_query = select(
            func.count(Document.id).label("total_documents"),
            func.sum(Document.size).label("total_storage")
        ).where(Document.deleted_at.is_(None))
        
        if from_date:
            doc_query = doc_query.where(Document.created_at >= from_date)
        if to_date:
            doc_query = doc_query.where(Document.created_at <= to_date)
        
        doc_result = await session.execute(doc_query)
        doc_stats = doc_result.first()
        
        total_documents = doc_stats.total_documents or 0
        total_storage = doc_stats.total_storage or 0
        
        # Uploads count and size in date range
        uploads_query = select(
            func.count(Document.id).label("count"),
            func.sum(Document.size).label("size")
        ).where(
            and_(
                Document.deleted_at.is_(None),
                Document.created_at >= from_date,
                Document.created_at <= to_date
            )
        )
        uploads_result = await session.execute(uploads_query)
        uploads_row = uploads_result.first()
        uploads_count = uploads_row.count or 0
        uploads_size = uploads_row.size or 0
        
        # Chatbot sessions
        chat_query = select(func.count(ChatSession.id)).where(
            and_(
                ChatSession.created_at >= from_date,
                ChatSession.created_at <= to_date
            )
        )
        chat_result = await session.execute(chat_query)
        chatbot_sessions = chat_result.scalar() or 0
        
        # Queue depth (pending AI jobs)
        queue_query = select(func.count(AIJob.id)).where(
            AIJob.status.in_(["queued", "processing"])
        )
        queue_result = await session.execute(queue_query)
        queue_depth = queue_result.scalar() or 0
        
        # Search queries (from audit events)
        search_query = select(func.count(AuditEvent.id)).where(
            and_(
                AuditEvent.action == "search",
                AuditEvent.timestamp >= from_date,
                AuditEvent.timestamp <= to_date
            )
        )
        search_result = await session.execute(search_query)
        search_queries = search_result.scalar() or 0
        
        # Vector queries (from audit events - assuming action is "vector_search")
        vector_query = select(func.count(AuditEvent.id)).where(
            and_(
                AuditEvent.action == "vector_search",
                AuditEvent.timestamp >= from_date,
                AuditEvent.timestamp <= to_date
            )
        )
        vector_result = await session.execute(vector_query)
        vector_queries = vector_result.scalar() or 0
        
        # Time series data based on rollup
        if rollup == "hour":
            date_trunc = func.date_trunc("hour", Document.created_at)
        elif rollup == "week":
            date_trunc = func.date_trunc("week", Document.created_at)
        else:  # day
            date_trunc = func.date_trunc("day", Document.created_at)
        
        time_series_query = select(
            date_trunc.label("period"),
            func.count(Document.id).label("uploads"),
            func.sum(Document.size).label("storage")
        ).where(
            and_(
                Document.deleted_at.is_(None),
                Document.created_at >= from_date,
                Document.created_at <= to_date
            )
        ).group_by(date_trunc).order_by(asc(date_trunc))
        
        time_series_result = await session.execute(time_series_query)
        time_series = [
            {
                "date": row.period.isoformat(),
                "uploads": row.uploads,
                "storage": row.storage or 0
            }
            for row in time_series_result.all()
        ]
        
        # Breakdown by folder
        folder_query = select(
            Folder.id.label("folder_id"),
            Folder.name.label("name"),
            func.count(Document.id).label("count"),
            func.sum(Document.size).label("size")
        ).join(
            Document, Folder.id == Document.folder_id
        ).where(
            and_(
                Document.deleted_at.is_(None),
                Document.created_at >= from_date,
                Document.created_at <= to_date
            )
        ).group_by(Folder.id, Folder.name).order_by(
            desc(func.sum(Document.size))
        ).limit(top_n)
        
        folder_result = await session.execute(folder_query)
        folders = [
            {
                "folder_id": row.folder_id,
                "name": row.name,
                "count": row.count,
                "size": row.size or 0
            }
            for row in folder_result.all()
        ]
        
        # Breakdown by tag
        tag_query = select(
            Tag.id.label("tag_id"),
            Tag.name.label("name"),
            func.count(distinct(Document.id)).label("count"),
            func.sum(Document.size).label("size")
        ).join(
            DocumentTag, Tag.id == DocumentTag.tag_id
        ).join(
            Document, DocumentTag.document_id == Document.id
        ).where(
            and_(
                Document.deleted_at.is_(None),
                Document.created_at >= from_date,
                Document.created_at <= to_date
            )
        ).group_by(Tag.id, Tag.name).order_by(
            desc(func.sum(Document.size))
        ).limit(top_n)
        
        tag_result = await session.execute(tag_query)
        tags = [
            {
                "tag_id": row.tag_id,
                "name": row.name,
                "count": row.count,
                "size": row.size or 0
            }
            for row in tag_result.all()
        ]
        
        # Breakdown by group
        group_query = select(
            DocumentGroup.id.label("group_id"),
            DocumentGroup.name.label("name"),
            func.count(distinct(Document.id)).label("count"),
            func.sum(Document.size).label("size")
        ).join(
            DocumentGroup.documents
        ).where(
            and_(
                Document.deleted_at.is_(None),
                Document.created_at >= from_date,
                Document.created_at <= to_date
            )
        ).group_by(DocumentGroup.id, DocumentGroup.name).order_by(
            desc(func.sum(Document.size))
        ).limit(top_n)
        
        group_result = await session.execute(group_query)
        groups = [
            {
                "group_id": row.group_id,
                "name": row.name,
                "count": row.count,
                "size": row.size or 0
            }
            for row in group_result.all()
        ]
        
        # Breakdown by user (owner)
        user_query = select(
            User.id.label("user_id"),
            User.name.label("name"),
            func.count(Document.id).label("uploads"),
            func.sum(Document.size).label("size")
        ).join(
            Document, User.id == Document.owner_id
        ).where(
            and_(
                Document.deleted_at.is_(None),
                Document.created_at >= from_date,
                Document.created_at <= to_date
            )
        ).group_by(User.id, User.name).order_by(
            desc(func.sum(Document.size))
        ).limit(top_n)
        
        user_result = await session.execute(user_query)
        users = [
            {
                "user_id": row.user_id,
                "name": row.name,
                "uploads": row.uploads,
                "size": row.size or 0
            }
            for row in user_result.all()
        ]
        
        return {
            "total_documents": total_documents,
            "total_storage": total_storage,
            "uploads_count": uploads_count,
            "uploads_size": uploads_size,
            "search_queries": search_queries,
            "vector_queries": vector_queries,
            "chatbot_sessions": chatbot_sessions,
            "queue_depth": queue_depth,
            "time_series": time_series,
            "breakdown": {
                "folders": folders,
                "tags": tags,
                "groups": groups,
                "users": users
            }
        }
    
    @staticmethod
    async def generate_workflow_report(
        session: AsyncSession,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None,
        template: Optional[str] = None,
        assignee_id: Optional[int] = None
    ) -> Dict[str, Any]:
        """Generate workflow SLA report with durations and approval rates."""
        # Base query
        workflow_query = select(Workflow)
        conditions = []
        
        if from_date:
            conditions.append(Workflow.created_at >= from_date)
        if to_date:
            conditions.append(Workflow.created_at <= to_date)
        if template:
            conditions.append(Workflow.template == template)
        
        if conditions:
            workflow_query = workflow_query.where(and_(*conditions))
        
        workflow_result = await session.execute(workflow_query)
        workflows = workflow_result.scalars().all()
        
        total_workflows = len(workflows)
        completed = sum(1 for w in workflows if w.state == "completed")
        pending = sum(1 for w in workflows if w.state in ["pending", "in_progress"])
        rejected = sum(1 for w in workflows if w.state == "rejected")
        
        # Calculate overdue
        now = datetime.utcnow()
        overdue = sum(
            1 for w in workflows
            if w.due_at and w.due_at < now and w.state not in ["completed", "rejected"]
        )
        
        # Calculate task durations
        completion_times = []
        for w in workflows:
            if w.state == "completed":
                # Get last completed task
                task_query = select(Task).where(
                    and_(
                        Task.workflow_id == w.id,
                        Task.completed_at.isnot(None)
                    )
                ).order_by(desc(Task.completed_at)).limit(1)
                task_result = await session.execute(task_query)
                last_task = task_result.scalar_one_or_none()
                if last_task and last_task.completed_at:
                    duration = (last_task.completed_at - w.created_at).total_seconds() / 3600
                    completion_times.append(duration)
        
        durations = sorted(completion_times) if completion_times else []
        avg_duration = sum(durations) / len(durations) if durations else 0
        min_duration = durations[0] if durations else 0
        max_duration = durations[-1] if durations else 0
        median_duration = durations[len(durations) // 2] if durations else 0
        
        # Approval rates by template
        template_query = select(
            Workflow.template,
            func.count(Workflow.id).label("total"),
            func.sum(
                case((Workflow.state == "completed", 1), else_=0)
            ).label("completed")
        )
        if conditions:
            template_query = template_query.where(and_(*conditions))
        template_query = template_query.group_by(Workflow.template)
        template_result = await session.execute(template_query)
        
        approval_rates_by_template = []
        for row in template_result.all():
            if row.total > 0:
                rate = (row.completed or 0) / row.total
                approval_rates_by_template.append({
                    "template": row.template or "None",
                    "rate": round(rate, 3),
                    "total": row.total
                })
        
        # Approval rates by assignee
        assignee_query = select(
            Task.assignee_id,
            User.name.label("name"),
            func.count(Task.id).label("total"),
            func.sum(
                case((Task.state == "completed", 1), else_=0)
            ).label("completed")
        ).join(User, Task.assignee_id == User.id)
        
        if assignee_id:
            assignee_query = assignee_query.where(Task.assignee_id == assignee_id)
        
        # Join with workflows to apply date/template filters
        assignee_query = assignee_query.join(
            Workflow, Task.workflow_id == Workflow.id
        )
        if conditions:
            assignee_query = assignee_query.where(and_(*conditions))
        
        assignee_query = assignee_query.group_by(
            Task.assignee_id, User.name
        )
        assignee_result = await session.execute(assignee_query)
        
        approval_rates_by_assignee = []
        for row in assignee_result.all():
            if row.total > 0:
                rate = (row.completed or 0) / row.total
                approval_rates_by_assignee.append({
                    "assignee_id": row.assignee_id,
                    "name": row.name,
                    "rate": round(rate, 3),
                    "total": row.total
                })
        
        # Duration distribution (buckets)
        duration_buckets = {
            "0-24h": 0,
            "24-48h": 0,
            "48-72h": 0,
            "72h+": 0
        }
        for duration in durations:
            if duration < 24:
                duration_buckets["0-24h"] += 1
            elif duration < 48:
                duration_buckets["24-48h"] += 1
            elif duration < 72:
                duration_buckets["48-72h"] += 1
            else:
                duration_buckets["72h+"] += 1
        
        duration_distribution = [
            {"range": k, "count": v}
            for k, v in duration_buckets.items()
        ]
        
        # Overdue tasks details
        overdue_query = select(Task, Workflow, User.name.label("assignee_name")).join(
            Workflow, Task.workflow_id == Workflow.id
        ).join(User, Task.assignee_id == User.id).where(
            and_(
                Workflow.due_at.isnot(None),
                Workflow.due_at < now,
                Workflow.state.notin_(["completed", "rejected"]),
                Task.state == "pending"
            )
        )
        if conditions:
            overdue_query = overdue_query.where(and_(*conditions))
        overdue_query = overdue_query.order_by(asc(Workflow.due_at)).limit(20)
        overdue_result = await session.execute(overdue_query)
        
        overdue_tasks = []
        for task, workflow, assignee_name in overdue_result.all():
            overdue_tasks.append({
                "task_id": task.id,
                "workflow_id": workflow.id,
                "assignee_id": task.assignee_id,
                "assignee_name": assignee_name,
                "template": workflow.template,
                "due_at": workflow.due_at.isoformat() if workflow.due_at else None,
                "days_overdue": (now - workflow.due_at).days if workflow.due_at else 0
            })
        
        return {
            "total_workflows": total_workflows,
            "completed": completed,
            "pending": pending,
            "rejected": rejected,
            "overdue": overdue,
            "avg_duration_hours": round(avg_duration, 2),
            "min_duration_hours": round(min_duration, 2),
            "max_duration_hours": round(max_duration, 2),
            "median_duration_hours": round(median_duration, 2),
            "approval_rates": {
                "by_template": approval_rates_by_template,
                "by_assignee": approval_rates_by_assignee
            },
            "duration_distribution": duration_distribution,
            "overdue_tasks": overdue_tasks
        }
    
    @staticmethod
    async def generate_quality_report(
        session: AsyncSession,
        from_date: Optional[datetime] = None,
        to_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Generate data quality report with failures and issues."""
        # Default date range: last 30 days if not specified
        if not from_date:
            from_date = datetime.utcnow() - timedelta(days=30)
        if not to_date:
            to_date = datetime.utcnow()
        
        # Job failures by type
        failure_query = select(
            AIJob.job_type,
            func.count(AIJob.id).label("count")
        ).where(
            and_(
                AIJob.status == "failed",
                AIJob.created_at >= from_date,
                AIJob.created_at <= to_date
            )
        ).group_by(AIJob.job_type)
        
        failure_result = await session.execute(failure_query)
        failures_by_type = {row.job_type: row.count for row in failure_result.all()}
        
        index_failures = failures_by_type.get("embed", 0) + failures_by_type.get("ocr", 0)
        embedding_failures = failures_by_type.get("embed", 0)
        ocr_failures = failures_by_type.get("ocr", 0)
        
        # Stale documents (ready but no embeddings)
        # Count documents that are ready but don't have successful embed jobs
        ready_docs_query = select(func.count(Document.id)).where(
            and_(
                Document.deleted_at.is_(None),
                Document.status == "ready"
            )
        )
        ready_result = await session.execute(ready_docs_query)
        total_ready = ready_result.scalar() or 0
        
        # Count documents with successful embeddings - use Embedding table directly
        embedding_count_query = select(func.count(distinct(Embedding.doc_id)))
        embedding_count_result = await session.execute(embedding_count_query)
        docs_with_embeddings = embedding_count_result.scalar() or 0
        stale_documents = max(0, total_ready - docs_with_embeddings)
        
        # Purge backlog
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
        
        # Virus scan failures (if tracked in metadata or separate table)
        # For now, assume it's tracked in AIJob with job_type="virus_scan"
        virus_scan_query = select(func.count(AIJob.id)).where(
            and_(
                AIJob.job_type == "virus_scan",
                AIJob.status == "failed",
                AIJob.created_at >= from_date,
                AIJob.created_at <= to_date
            )
        )
        virus_scan_result = await session.execute(virus_scan_query)
        virus_scan_failures = virus_scan_result.scalar() or 0
        
        # Failure timeline
        failure_timeline_query = select(
            func.date(AIJob.created_at).label("date"),
            AIJob.job_type,
            func.count(AIJob.id).label("count")
        ).where(
            and_(
                AIJob.status == "failed",
                AIJob.created_at >= from_date,
                AIJob.created_at <= to_date
            )
        ).group_by(
            func.date(AIJob.created_at), AIJob.job_type
        ).order_by(asc(func.date(AIJob.created_at)))
        
        failure_timeline_result = await session.execute(failure_timeline_query)
        failure_timeline = [
            {
                "date": row.date.isoformat(),
                "type": row.job_type,
                "count": row.count
            }
            for row in failure_timeline_result.all()
        ]
        
        # Recent failures
        recent_failures_query = select(AIJob).where(
            and_(
                AIJob.status == "failed",
                AIJob.created_at >= from_date,
                AIJob.created_at <= to_date
            )
        ).order_by(desc(AIJob.created_at)).limit(20)
        
        recent_failures_result = await session.execute(recent_failures_query)
        recent_failures = []
        for job in recent_failures_result.scalars().all():
            doc_id = None
            try:
                if job.target:
                    if isinstance(job.target, dict):
                        doc_id = job.target.get("doc_id") or job.target.get("document_id")
                    elif isinstance(job.target, str):
                        target_dict = json.loads(job.target)
                        doc_id = target_dict.get("doc_id") or target_dict.get("document_id")
            except (AttributeError, TypeError, json.JSONDecodeError):
                pass
            
            recent_failures.append({
                "id": job.id,
                "job_type": job.job_type,
                "document_id": doc_id,
                "error": job.error or "Unknown error",
                "created_at": job.created_at.isoformat()
            })
        
        # Job status breakdown
        status_query = select(
            AIJob.status,
            func.count(AIJob.id).label("count")
        ).where(
            and_(
                AIJob.created_at >= from_date,
                AIJob.created_at <= to_date
            )
        ).group_by(AIJob.status)
        
        status_result = await session.execute(status_query)
        job_status_breakdown = {
            row.status: row.count
            for row in status_result.all()
        }
        
        return {
            "index_failures": index_failures,
            "embedding_failures": embedding_failures,
            "ocr_failures": ocr_failures,
            "stale_documents": stale_documents,
            "purge_backlog": purge_backlog,
            "virus_scan_failures": virus_scan_failures,
            "failure_timeline": failure_timeline,
            "recent_failures": recent_failures,
            "job_status_breakdown": job_status_breakdown
        }

