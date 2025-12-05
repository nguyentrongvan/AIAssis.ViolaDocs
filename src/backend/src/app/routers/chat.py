import uuid
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..dependencies import get_current_user
from ..models.users import User
from ..services.ai import get_llm_service
from ..utils.response import success_response, error_response
from ..config import settings

router = APIRouter(prefix="/chat", tags=["chat"])

try:
    import redis.asyncio as redis
    _redis_client: Optional[redis.Redis] = None
except ImportError:
    redis = None
    _redis_client = None


async def get_redis():
    if not redis:
        return None
    global _redis_client
    if _redis_client is None:
        _redis_client = await redis.from_url(settings.redis_url)
    return _redis_client


class ChatRequest(BaseModel):
    message: str
    group_id: Optional[int] = None
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    answer: str
    citations: List[dict]
    session_id: str


@router.post("")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    llm_service = get_llm_service()
    if not llm_service:
        return error_response("LLM provider not configured")
    
    redis_client = await get_redis()
    
    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())
    context = []
    
    if redis_client:
        session_key = f"chat:session:{session_id}"
        # Get chat history from cache
        history = await redis_client.lrange(session_key, 0, -1)
        context = [msg.decode() if isinstance(msg, bytes) else msg for msg in history[-10:]]  # Last 10 messages
    
    # TODO: Retrieve relevant documents from vector store based on query and group_id
    # For now, use empty context
    doc_contexts = []
    
    # Generate response using LLM service with prompts
    answer = llm_service.chat(request.message, context=doc_contexts)
    
    # Store in cache
    if redis_client:
        session_key = f"chat:session:{session_id}"
        await redis_client.lpush(session_key, f"user:{request.message}", f"assistant:{answer}")
        await redis_client.expire(session_key, 3600 * 24)  # 24 hours
    
    # TODO: Store in database for audit
    # TODO: Extract citations from retrieved documents
    
    return success_response({
        "answer": answer,
        "citations": [],
        "session_id": session_id
    })


@router.get("/history")
async def get_chat_history(
    group_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # TODO: Load chat history from database
    return success_response({
        "sessions": [],
        "messages": []
    })


@router.get("/session/{session_id}")
async def get_session_history(
    session_id: str,
    current_user: User = Depends(get_current_user)
):
    redis_client = await get_redis()
    messages = []
    
    if redis_client:
        session_key = f"chat:session:{session_id}"
        history = await redis_client.lrange(session_key, 0, -1)
        
        for msg in history:
            msg_str = msg.decode() if isinstance(msg, bytes) else msg
            if msg_str.startswith("user:"):
                messages.append({"role": "user", "content": msg_str[5:]})
            elif msg_str.startswith("assistant:"):
                messages.append({"role": "assistant", "content": msg_str[10:]})
    
    return success_response({
        "session_id": session_id,
        "messages": messages
    })

