from datetime import datetime
from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import secrets

from ..db import get_session
from ..dependencies import get_current_admin_user
from ..models.users import User
from ..models.devices import Device
from ..utils.response import success_response, error_response

router = APIRouter(prefix="/devices", tags=["devices"])


class DeviceCreate(BaseModel):
    name: str
    location: str
    capabilities: list[str] = []


@router.post("")
async def create_device(
    payload: DeviceCreate,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    device = Device(
        name=payload.name,
        location=payload.location,
        capabilities=payload.capabilities,
        status="offline"
    )
    session.add(device)
    await session.commit()
    await session.refresh(device)
    
    return success_response({
        "id": device.id,
        "name": device.name,
        "location": device.location,
        "status": device.status
    })


@router.get("")
async def list_devices(
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Device))
    devices = result.scalars().all()
    
    return success_response([{
        "id": d.id,
        "name": d.name,
        "location": d.location,
        "status": d.status,
        "last_seen": d.last_seen.isoformat() if d.last_seen else None
    } for d in devices])


@router.post("/{device_id}/issue-key")
async def issue_device_key(
    device_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    
    if not device:
        return error_response("Device not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Generate device key
    device_key = secrets.token_urlsafe(32)
    device.public_key = device_key  # Store hashed in production
    device.updated_at = datetime.utcnow()
    
    await session.commit()
    
    return success_response({
        "device_id": device_id,
        "key": device_key  # Return plain key (should be hashed in production)
    })


@router.delete("/{device_id}")
async def delete_device(
    device_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    result = await session.execute(select(Device).where(Device.id == device_id))
    device = result.scalar_one_or_none()
    
    if not device:
        return error_response("Device not found", status_code=status.HTTP_404_NOT_FOUND)
    
    await session.delete(device)
    await session.commit()
    
    return success_response({"id": device_id, "deleted": True})


