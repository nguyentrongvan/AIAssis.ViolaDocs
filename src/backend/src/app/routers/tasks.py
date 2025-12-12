from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_session
from ..dependencies import get_current_user
from ..models.users import User
from ..models.workflows import Task
from ..utils.response import success_response, error_response

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskAction(BaseModel):
    action: str  # approve, reject, request_changes
    comment: Optional[str] = None


@router.get("")
async def list_tasks(
    state: Optional[str] = Query(None, description="Filter by task state"),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get task inbox."""
    query = select(Task).where(Task.assignee_id == current_user.id)
    
    if state:
        query = query.where(Task.state == state)
    
    query = query.order_by(Task.created_at.desc())
    
    result = await session.execute(query)
    tasks = result.scalars().all()
    
    return success_response([{
        "id": t.id,
        "workflow_id": t.workflow_id,
        "assignee_id": t.assignee_id,
        "state": t.state,
        "action": t.action,
        "comment": t.comment,
        "created_at": t.created_at.isoformat()
    } for t in tasks])


@router.post("/{task_id}/action")
async def task_action(
    task_id: int,
    payload: TaskAction,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Perform action on task (approve/reject/request_changes)."""
    # Validate action
    valid_actions = ["approve", "reject", "request_changes"]
    if payload.action not in valid_actions:
        return error_response(
            f"Invalid action. Must be one of: {', '.join(valid_actions)}",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        return error_response("Task not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Check authorization - only assignee can act on task (or admin/staff)
    if task.assignee_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    # Update task
    task.action = payload.action
    task.comment = payload.comment
    
    # Update state based on action
    if payload.action == "approve":
        task.state = "approved"
    elif payload.action == "reject":
        task.state = "rejected"
    elif payload.action == "request_changes":
        task.state = "changes_requested"
    
    task.updated_at = datetime.utcnow()
    
    await session.commit()
    await session.refresh(task)
    
    return success_response({
        "task_id": task_id,
        "action": payload.action,
        "state": task.state,
        "comment": task.comment
    })




