from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, or_, and_

from ..db import get_session
from ..dependencies import get_current_user, get_current_admin_user, require_permission
from ..models.users import User
from ..models.documents import Document
from ..services.ai import get_embedding_service
from ..services.ai.embedding_service import EmbeddingModelUnavailableError
from ..services.permission_service import get_user_accessible_documents_query, filter_accessible_documents
from ..utils.response import success_response, error_response

router = APIRouter(prefix="/search", tags=["search"])


class SearchRequest(BaseModel):
    query: str
    mode: str = "hybrid"  # keyword, vector, hybrid
    group_id: Optional[int] = None
    filters: Optional[dict] = None
    limit: int = 20


class VectorSearchRequest(BaseModel):
    query: str
    top_k: int = 10
    filters: Optional[dict] = None


@router.post("")
async def search(
    request: SearchRequest,
    current_user: User = Depends(require_permission("search")),
    session: AsyncSession = Depends(get_session)
):
    """Hybrid search (keyword + vector)."""
    # Validate mode
    if request.mode not in ["keyword", "vector", "hybrid"]:
        return error_response(
            "Invalid mode. Must be 'keyword', 'vector', or 'hybrid'",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate query
    if not request.query or not request.query.strip():
        return success_response({
            "results": [],
            "total": 0
        })
    
    keyword_results = []
    vector_results = []
    
    # Keyword search
    if request.mode in ["keyword", "hybrid"]:
        # Use permission service to get accessible documents query (includes shared documents)
        base_query = select(Document).where(Document.title.ilike(f"%{request.query}%"))
        keyword_query = await get_user_accessible_documents_query(session, current_user, base_query)
        
        # Apply filters
        if request.filters:
            if "mime" in request.filters:
                keyword_query = keyword_query.where(Document.mime == request.filters["mime"])
            if "status" in request.filters:
                keyword_query = keyword_query.where(Document.status == request.filters["status"])
        
        keyword_query = keyword_query.limit(request.limit * 2)  # Get more to filter by permission
        
        result = await session.execute(keyword_query)
        all_docs = result.scalars().all()
        
        # Filter to only include documents with "search" permission
        keyword_results = await filter_accessible_documents(session, current_user, all_docs, "search")
        keyword_results = keyword_results[:request.limit]  # Limit to requested amount
    
    # Vector search via Qdrant
    vector_results = []
    if request.mode in ["vector", "hybrid"]:
        embedding_service = get_embedding_service()
        if embedding_service and embedding_service.is_available():
            try:
                # Generate query embedding
                query_embedding = embedding_service.generate_embedding(request.query)
                search_filters = {"owner_id": current_user.id}
                if request.group_id:
                    search_filters["group_id"] = request.group_id
                vector_result = embedding_service.query_embeddings(
                    query_embedding=query_embedding,
                    where=search_filters,
                    top_k=request.limit
                )
                
                # Process Qdrant results
                doc_ids = []
                if vector_result and vector_result.get("metadatas"):
                    for metas in vector_result["metadatas"]:
                        for meta in metas:
                            doc_id = meta.get("doc_id")
                            if doc_id:
                                doc_ids.append(doc_id)
                if doc_ids:
                    # Get documents from database
                    docs_result = await session.execute(
                        select(Document).where(
                            and_(
                                Document.id.in_(doc_ids),
                                Document.deleted_at.is_(None)
                            )
                        )
                    )
                    all_docs = docs_result.scalars().all()
                    # Filter to only include documents with "search" permission
                    vector_results = await filter_accessible_documents(session, current_user, all_docs, "search")
            except EmbeddingModelUnavailableError as e:
                # If embedding service is unavailable, return error for vector-only mode
                if request.mode == "vector":
                    return error_response(
                        f"Vector search is unavailable: {str(e)}. "
                        f"Please use 'hybrid' or 'keyword' mode, or configure Ollama embedding model.",
                        status_code=status.HTTP_503_SERVICE_UNAVAILABLE
                    )
                # For hybrid mode, continue with keyword search only
                vector_results = []
        else:
            # If embedding service not available and mode is vector-only, return error
            if request.mode == "vector":
                return error_response(
                    "Vector search is unavailable. Please configure Ollama embedding model or use 'hybrid' or 'keyword' mode.",
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            # For hybrid mode, continue with keyword search only
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
    request: VectorSearchRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Vector search only."""
    embedding_service = get_embedding_service()
    if not embedding_service or not embedding_service.is_available():
        return error_response(
            "Vector search not available. Embedding service not configured or model not available. "
            "Please configure Ollama and ensure the embedding model is pulled.",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    # Generate query embedding
    try:
        query_embedding = embedding_service.generate_embedding(request.query)
    except EmbeddingModelUnavailableError as e:
        return error_response(
            f"Vector search unavailable: {str(e)}",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    search_filters = {"owner_id": current_user.id}
    if request.filters and isinstance(request.filters, dict):
        if "group_id" in request.filters:
            search_filters["group_id"] = request.filters["group_id"]
    
    vector_result = embedding_service.query_embeddings(
        query_embedding=query_embedding,
        where=search_filters,
        top_k=request.top_k
    )
    
    doc_ids = []
    if vector_result and vector_result.get("metadatas"):
        for metas in vector_result["metadatas"]:
            for meta in metas:
                doc_id = meta.get("doc_id")
                if doc_id:
                    doc_ids.append(doc_id)
    
    docs = []
    if doc_ids:
        # Get documents from database
        docs_result = await session.execute(
            select(Document).where(
                and_(
                    Document.id.in_(doc_ids),
                    Document.deleted_at.is_(None)
                )
            )
        )
        all_docs = docs_result.scalars().all()
        # Filter to only include documents with "search" permission
        docs = await filter_accessible_documents(session, current_user, all_docs, "search")
    
    results = [{
        "id": doc.id,
        "title": doc.title,
        "mime": doc.mime,
        "size": doc.size,
        "created_at": doc.created_at.isoformat(),
        "snippet": doc.title
    } for doc in docs]
    
    return success_response({
        "results": results,
        "total": len(results)
    })


@router.post("/index/reindex")
async def reindex_all(
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Reindex all documents (admin only)."""
    # Note: Existing pgvector data is no longer used; this triggers fresh
    # embedding jobs to populate the Qdrant vector store.
    # Get all documents that need reindexing
    result = await session.execute(
        select(Document).where(
            and_(
                Document.deleted_at.is_(None),
                Document.status == "ready"
            )
        )
    )
    documents = result.scalars().all()
    
    # Create embedding jobs for all documents
    from ..models.ai import AIJob
    job_count = 0
    for doc in documents:
        # Get latest version
        from ..models.documents import DocumentVersion
        version_result = await session.execute(
            select(DocumentVersion)
            .where(DocumentVersion.document_id == doc.id)
            .order_by(DocumentVersion.version_no.desc())
            .limit(1)
        )
        version = version_result.scalar_one_or_none()
        
        if version and version.text_uri:
            # Check if embedding job already exists
            existing_job_result = await session.execute(
                select(AIJob).where(
                    and_(
                        AIJob.job_type == "embed",
                        AIJob.target["version_id"].astext == str(version.id),
                        AIJob.status.in_(["queued", "processing", "completed"])
                    )
                )
            )
            existing_job = existing_job_result.scalar_one_or_none()
            
            if not existing_job:
                embed_job = AIJob(
                    job_type="embed",
                    target={"document_id": doc.id, "version_id": version.id},
                    provider="openai",
                    status="queued"
                )
                session.add(embed_job)
                job_count += 1
    
    await session.commit()
    
    return success_response({
        "message": f"Reindexing initiated for {job_count} documents",
        "job_count": job_count
    })


@router.post("/index/reindex/{document_id}")
async def reindex_document(
    document_id: int,
    current_user: User = Depends(get_current_admin_user),
    session: AsyncSession = Depends(get_session)
):
    """Reindex single document (admin only)."""
    # Get document
    doc_result = await session.execute(
        select(Document).where(
            and_(
                Document.id == document_id,
                Document.deleted_at.is_(None)
            )
        )
    )
    doc = doc_result.scalar_one_or_none()
    
    if not doc:
        return error_response("Document not found", status_code=status.HTTP_404_NOT_FOUND)
    
    # Get latest version
    from ..models.documents import DocumentVersion
    version_result = await session.execute(
        select(DocumentVersion)
        .where(DocumentVersion.document_id == doc.id)
        .order_by(DocumentVersion.version_no.desc())
        .limit(1)
    )
    version = version_result.scalar_one_or_none()
    
    if not version or not version.text_uri:
        return error_response(
            "Document version or OCR text not available",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Create embedding job
    from ..models.ai import AIJob
    embed_job = AIJob(
        job_type="embed",
        target={"document_id": doc.id, "version_id": version.id},
        provider="openai",
        status="queued"
    )
    session.add(embed_job)
    await session.commit()
    await session.refresh(embed_job)
    
    return success_response({
        "message": "Reindexing job created",
        "job_id": embed_job.id
    })

