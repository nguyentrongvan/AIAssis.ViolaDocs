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




@router.post("")
async def start_workflow(
    payload: WorkflowStart,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Start workflow on document."""
    from ..models.documents import Document
    
    # Verify document exists
    doc_result = await session.execute(
        select(Document).where(
            and_(
                Document.id == payload.document_id,
                Document.deleted_at.is_(None)
            )
        )
    )
    doc = doc_result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Verify user has access to document
    if doc.owner_id != current_user.id and current_user.role not in ["admin", "staff"]:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
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
        "id": workflow.id,
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



