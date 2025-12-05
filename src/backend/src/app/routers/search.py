from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_

from ..db import get_session
from ..dependencies import get_current_user
from ..models.users import User
from ..models.documents import Document
from ..utils.response import success_response

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    mode: str = "hybrid"  # keyword, vector, hybrid
    group_id: Optional[int] = None
    filters: Optional[dict] = None
    limit: int = 20


@router.post("")
async def search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # Keyword search
    if request.mode in ["keyword", "hybrid"]:
        keyword_query = select(Document).where(
            and_(
                Document.owner_id == current_user.id,
                Document.deleted_at.is_(None),
                Document.title.ilike(f"%{request.query}%")
            )
        ).limit(request.limit)
        
        result = await session.execute(keyword_query)
        keyword_results = result.scalars().all()
    else:
        keyword_results = []
    
    # Vector search (placeholder - requires pgvector setup)
    if request.mode in ["vector", "hybrid"]:
        # TODO: Implement vector search with pgvector
        vector_results = []
    else:
        vector_results = []
    
    # Merge and deduplicate results
    all_results = {}
    for doc in keyword_results + vector_results:
        if doc.id not in all_results:
            all_results[doc.id] = {
                "id": doc.id,
                "title": doc.title,
                "mime": doc.mime,
                "size": doc.size,
                "created_at": doc.created_at.isoformat(),
                "snippet": doc.title  # TODO: Generate snippet from content
            }
    
    return success_response({
        "results": list(all_results.values()),
        "total": len(all_results)
    })


@router.post("/vector")
async def vector_search(
    request: SearchRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    # TODO: Implement vector search with embeddings
    return success_response({"results": []})

