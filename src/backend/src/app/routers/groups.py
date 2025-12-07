from typing import Optional
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_session
from ..dependencies import get_current_user, get_current_admin_user
from ..models.users import User
from ..models.groups import DocumentGroup
from ..utils.response import success_response, error_response

router = APIRouter(prefix="/groups", tags=["groups"])


class GroupCreate(BaseModel):
    name: str
    description: Optional[str] = None
    chatbot_policy: Optional[dict] = None


@router.post("")
async def create_group(
    payload: GroupCreate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    group = DocumentGroup(
        name=payload.name,
        description=payload.description,
        chatbot_policy=payload.chatbot_policy or {}
    )
    session.add(group)
    await session.commit()
    await session.refresh(group)
    
    return success_response({
        "id": group.id,
        "name": group.name,
        "description": group.description
    })


@router.get("")
async def list_groups(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(DocumentGroup))
    groups = result.scalars().all()
    
    return success_response([{
        "id": g.id,
        "name": g.name,
        "description": g.description,
        "document_count": 0,  # TODO: Count documents
        "member_count": 0  # TODO: Count members
    } for g in groups])


@router.delete("/{group_id}")
async def delete_group(
    group_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(DocumentGroup).where(DocumentGroup.id == group_id))
    group = result.scalar_one_or_none()
    
    if not group:
        return error_response("Group not found", status_code=status.HTTP_404_NOT_FOUND)
    
    await session.delete(group)
    await session.commit()
    
    return success_response({"id": group_id, "deleted": True})

