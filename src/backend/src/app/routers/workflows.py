from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_session
from ..dependencies import get_current_user
from ..models.users import User
from ..models.workflows import Workflow, Task
from ..utils.response import success_response, error_response

router = APIRouter(prefix="/workflows", tags=["workflows"])


class WorkflowStart(BaseModel):
    document_id: int
    template: Optional[str] = None
    assignees: Optional[List[int]] = None


class TaskAction(BaseModel):
    action: str  # approve, reject, request_changes
    comment: Optional[str] = None


@router.post("")
async def start_workflow(
    payload: WorkflowStart,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    workflow = Workflow(
        document_id=payload.document_id,
        template=payload.template or "default",
        state="pending",
        assignees=payload.assignees or [current_user.id]
    )
    session.add(workflow)
    await session.flush()
    
    # Create tasks for assignees
    for assignee_id in workflow.assignees:
        task = Task(
            workflow_id=workflow.id,
            assignee_id=assignee_id,
            state="pending"
        )
        session.add(task)
    
    await session.commit()
    await session.refresh(workflow)
    
    return success_response({
        "workflow_id": workflow.id,
        "document_id": payload.document_id,
        "state": workflow.state
    })


@router.get("/{workflow_id}")
async def get_workflow(
    workflow_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Workflow).where(Workflow.id == workflow_id)
    )
    workflow = result.scalar_one_or_none()
    
    if not workflow:
        return error_response("Workflow not found", status_code=status.HTTP_404_NOT_FOUND)
    
    return success_response({
        "id": workflow.id,
        "document_id": workflow.document_id,
        "template": workflow.template,
        "state": workflow.state,
        "assignees": workflow.assignees
    })


@router.get("/tasks")
async def list_tasks(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(
        select(Task).where(Task.assignee_id == current_user.id)
        .order_by(Task.created_at.desc())
    )
    tasks = result.scalars().all()
    
    return success_response([{
        "id": t.id,
        "workflow_id": t.workflow_id,
        "state": t.state,
        "action": t.action,
        "comment": t.comment,
        "created_at": t.created_at.isoformat()
    } for t in tasks])


@router.post("/tasks/{task_id}/action")
async def task_action(
    task_id: int,
    payload: TaskAction,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()
    
    if not task:
        return error_response("Task not found", status_code=status.HTTP_404_NOT_FOUND)
    
    if task.assignee_id != current_user.id:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    task.action = payload.action
    task.comment = payload.comment
    task.state = "completed" if payload.action in ["approve", "reject"] else "pending"
    task.updated_at = datetime.utcnow()
    
    await session.commit()
    
    return success_response({
        "task_id": task_id,
        "action": payload.action,
        "state": task.state
    })

