from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..db import get_session
from ..dependencies import get_current_user
from ..models.users import User
from ..services.auth import (
    authenticate_user,
    create_access_token,
    create_refresh_token,
    get_password_hash,
    decode_token
)
from ..utils.response import success_response, error_response

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


@router.post("/login")
async def login(
    request: LoginRequest,
    session: AsyncSession = Depends(get_session)
):
    user = await authenticate_user(session, request.email, request.password)
    if not user:
        return error_response("Invalid email or password", status_code=status.HTTP_401_UNAUTHORIZED)
    
    access_token = create_access_token(data={"sub": str(user.id), "email": user.email})
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    
    return success_response({
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    })


@router.post("/refresh")
async def refresh(request: RefreshRequest):
    payload = decode_token(request.refresh_token)
    if not payload or payload.get("type") != "refresh":
        return error_response("Invalid refresh token", status_code=status.HTTP_401_UNAUTHORIZED)
    
    user_id = payload.get("sub")
    if not user_id:
        return error_response("Invalid token", status_code=status.HTTP_401_UNAUTHORIZED)
    
    access_token = create_access_token(data={"sub": user_id})
    return success_response({
        "access_token": access_token,
        "token_type": "bearer"
    })


@router.get("/me")
async def get_me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    return success_response({
        "id": current_user.id,
        "name": current_user.name,
        "email": current_user.email,
        "role": current_user.role,
        "status": current_user.status,
        "expires_at": current_user.expires_at.isoformat() if current_user.expires_at else None
    })


