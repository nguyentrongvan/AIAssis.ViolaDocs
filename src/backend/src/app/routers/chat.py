import uuid
from typing import Optional, List, Dict, Any
from datetime import datetime, date as date_type
from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_session
from ..dependencies import get_current_user, require_permission
from ..models.users import User
from ..models.chat import ChatSession
from ..models.groups import DocumentGroup, document_group_documents
from ..models.documents import Document, DocumentTag, Tag
from ..services.ai import get_llm_service, get_embedding_service
from ..services.ai.embedding_service import EmbeddingModelUnavailableError
from ..services.permission_service import (
    filter_accessible_documents, 
    check_document_access,
    get_user_accessible_documents_query
)
from ..utils.response import success_response, error_response
from ..config import settings
from sqlalchemy import select, and_, or_, func

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
    filters: Optional[Dict[str, Any]] = None
    selected_document_ids: Optional[List[int]] = None


class ChatResponse(BaseModel):
    answer: str
    citations: List[dict]
    session_id: str


@router.post("")
async def chat(
    request: ChatRequest,
    current_user: User = Depends(require_permission("chat")),
    session: AsyncSession = Depends(get_session)
):
    """Chat with RAG system."""
    # Validate message
    if not request.message or not request.message.strip():
        return error_response(
            "Message cannot be empty",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    llm_service = get_llm_service()
    if not llm_service:
        return error_response(
            "LLM provider not configured",
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE
        )
    
    # Verify selected_document_ids permissions if provided
    if request.selected_document_ids:
        for doc_id in request.selected_document_ids:
            doc_result = await session.execute(
                select(Document).where(Document.id == doc_id)
            )
            doc = doc_result.scalar_one_or_none()
            if not doc:
                return error_response(
                    f"Document {doc_id} not found",
                    status_code=status.HTTP_404_NOT_FOUND
                )
            
            # Check chat permission
            has_access, _, reason = await check_document_access(
                session, current_user, doc, "chat"
            )
            if not has_access:
                return error_response(
                    f"Access denied to document {doc_id}: {reason}",
                    status_code=status.HTTP_403_FORBIDDEN
                )
    
    # Verify group access if group_id provided
    if request.group_id:
        group_result = await session.execute(
            select(DocumentGroup).where(DocumentGroup.id == request.group_id)
        )
        group = group_result.scalar_one_or_none()
        
        if not group:
            return error_response("Document group not found", status_code=status.HTTP_404_NOT_FOUND)
        
        # Check access to group
        has_access = False
        if current_user.id in (group.owners or []):
            has_access = True
        elif current_user.role in (group.allowed_roles or []):
            has_access = True
        elif current_user.id in (group.allowed_users or []):
            has_access = True
        elif current_user.role in ["admin", "staff"]:
            has_access = True
        
        if not has_access:
            return error_response("Access denied to document group", status_code=status.HTTP_403_FORBIDDEN)
    
    redis_client = await get_redis()
    
    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())
    context = []
    
    try:
        if redis_client:
            session_key = f"chat:session:{session_id}"
            # Get chat history from cache
            history = await redis_client.lrange(session_key, 0, -1)
            context = [msg.decode() if isinstance(msg, bytes) else msg for msg in history[-10:]]  # Last 10 messages
    except Exception as e:
        # Redis not available or error - continue without cache
        print(f"Redis error (continuing without cache): {e}")
        context = []
    
    # Get user accessible documents with "chat" permission
    base_query = select(Document).where(
        and_(
            Document.deleted_at.is_(None),
            Document.status == "ready"
        )
    )
    
    accessible_query = await get_user_accessible_documents_query(
        session, current_user, base_query
    )
    
    # Apply group_id filter if provided
    # Documents are linked to groups through document_group_documents table
    if request.group_id:
        accessible_query = accessible_query.join(
            document_group_documents,
            Document.id == document_group_documents.c.document_id
        ).where(
            document_group_documents.c.group_id == request.group_id
        ).distinct()
    
    # Apply filters if provided
    if request.filters:
        # Tags filter
        if request.filters.get("tags"):
            tag_names = request.filters["tags"]
            if isinstance(tag_names, str):
                tag_names = [t.strip() for t in tag_names.split(",") if t.strip()]
            if tag_names:
                accessible_query = accessible_query.join(
                    DocumentTag, Document.id == DocumentTag.document_id
                ).join(
                    Tag, DocumentTag.tag_id == Tag.id
                ).where(
                    Tag.name.in_(tag_names)
                ).distinct()
        
        # Type filter
        if request.filters.get("type"):
            type_filter = request.filters["type"]
            accessible_query = accessible_query.where(Document.mime.like(f"%{type_filter}%"))
        
        # Date filters
        if request.filters.get("date_from"):
            try:
                date_from_str = request.filters["date_from"]
                date_from_obj = datetime.fromisoformat(date_from_str.replace("Z", "+00:00"))
                accessible_query = accessible_query.where(Document.created_at >= date_from_obj)
            except (ValueError, TypeError):
                pass
        
        if request.filters.get("date_to"):
            try:
                date_to_str = request.filters["date_to"]
                date_to_obj = datetime.fromisoformat(date_to_str.replace("Z", "+00:00"))
                accessible_query = accessible_query.where(Document.created_at <= date_to_obj)
            except (ValueError, TypeError):
                pass
    
    # Execute query to get accessible documents
    result = await session.execute(accessible_query)
    accessible_docs = result.scalars().unique().all()
    accessible_doc_ids = [doc.id for doc in accessible_docs]
    
    # Get group IDs for each document (query separately to avoid async relationship issues)
    doc_group_map = {}
    if accessible_doc_ids:
        group_mapping_result = await session.execute(
            select(
                document_group_documents.c.document_id,
                document_group_documents.c.group_id
            ).where(
                document_group_documents.c.document_id.in_(accessible_doc_ids)
            )
        )
        group_mappings = group_mapping_result.all()
        for mapping in group_mappings:
            doc_id = mapping.document_id
            group_id = mapping.group_id
            if doc_id not in doc_group_map:
                doc_group_map[doc_id] = []
            doc_group_map[doc_id].append(group_id)
    
    # Apply selected_document_ids filter if provided
    if request.selected_document_ids:
        # Intersection: only documents that are both accessible AND selected
        accessible_doc_ids = [doc_id for doc_id in accessible_doc_ids if doc_id in request.selected_document_ids]
    
    # Retrieve relevant documents from vector store
    doc_contexts = []
    citations = []
    warning = None
    
    if accessible_doc_ids:
        embedding_service = get_embedding_service()
        if embedding_service and embedding_service.is_available():
            try:
                # Load RAG settings for top_k
                from ..services.settings_service import SettingsService
                top_k = await SettingsService.get_setting(
                    "rag_top_k",
                    default=20,
                    session=session
                )
                
                query_embedding = embedding_service.generate_embedding(request.message)
                
                # Build search filters
                # Qdrant supports $in operator, so we can filter by accessible_doc_ids directly
                search_filters = {}
                if request.group_id:
                    search_filters["group_id"] = request.group_id
                if accessible_doc_ids:
                    # Qdrant supports list values for $in operator
                    search_filters["doc_id"] = accessible_doc_ids
                
                # Query vector store with configurable top_k
                vector_result = embedding_service.query_embeddings(
                    query_embedding=query_embedding,
                    where=search_filters if search_filters else None,
                    top_k=top_k
                )
                
                # Process Qdrant results - handle chunks
                # Group chunks by doc_id and aggregate
                doc_chunks_map = {}  # doc_id -> list of chunks with scores
                doc_scores = {}  # Map doc_id to best similarity score
                
                if vector_result and vector_result.get("metadatas"):
                    # Extract chunks with their scores
                    all_chunk_results = []
                    for idx, metas in enumerate(vector_result["metadatas"]):
                        for meta_idx, meta in enumerate(metas):
                            doc_id = meta.get("doc_id")
                            if doc_id:
                                # Get distance/score
                                distance = None
                                if vector_result.get("distances") and idx < len(vector_result["distances"]):
                                    distances_list = vector_result["distances"][idx]
                                    if isinstance(distances_list, list) and meta_idx < len(distances_list):
                                        distance = distances_list[meta_idx]
                                        # Ensure distance is a number, not a list
                                        if isinstance(distance, list):
                                            distance = distance[0] if len(distance) > 0 else None
                                    elif not isinstance(distances_list, list):
                                        distance = distances_list
                                
                                score = None
                                if distance is not None:
                                    # Convert distance to similarity score (1 - distance for cosine)
                                    score = max(0, 1 - distance)
                                
                                chunk_text = meta.get("chunk_text")
                                chunk_index = meta.get("chunk_index")
                                
                                all_chunk_results.append({
                                    "doc_id": int(doc_id),
                                    "score": score,
                                    "chunk_text": chunk_text,
                                    "chunk_index": chunk_index,
                                    "meta": meta
                                })
                    
                    # Filter by accessible_doc_ids and group by doc_id
                    filtered_chunks = [
                        r for r in all_chunk_results
                        if r["doc_id"] in accessible_doc_ids
                    ]
                    
                    # Group chunks by doc_id
                    for chunk_result in filtered_chunks:
                        doc_id = chunk_result["doc_id"]
                        if doc_id not in doc_chunks_map:
                            doc_chunks_map[doc_id] = []
                        doc_chunks_map[doc_id].append(chunk_result)
                        
                        # Track best score per document
                        if chunk_result["score"] is not None:
                            if doc_id not in doc_scores or chunk_result["score"] > doc_scores[doc_id]:
                                doc_scores[doc_id] = chunk_result["score"]
                    
                    # Sort documents by best score and get top 5
                    sorted_doc_ids = sorted(
                        doc_chunks_map.keys(),
                        key=lambda d: doc_scores.get(d, 0),
                        reverse=True
                    )[:5]
                    
                    if sorted_doc_ids:
                        # Get documents from database
                        docs_result = await session.execute(
                            select(Document).where(
                                and_(
                                    Document.id.in_(sorted_doc_ids),
                                    Document.deleted_at.is_(None),
                                    Document.status == "ready"
                                )
                            )
                        )
                        all_docs = docs_result.scalars().all()
                        
                        # Verify permissions again (defense in depth)
                        docs = await filter_accessible_documents(session, current_user, all_docs, "chat")
                        
                        # Check for documents without embeddings
                        docs_without_embedding = []
                        if request.selected_document_ids:
                            selected_without_embedding = [
                                doc_id for doc_id in request.selected_document_ids
                                if doc_id not in sorted_doc_ids and doc_id in accessible_doc_ids
                            ]
                            if selected_without_embedding:
                                docs_without_embedding = selected_without_embedding
                        
                        if docs_without_embedding:
                            warning = f"Some selected documents don't have embeddings yet ({len(docs_without_embedding)} documents)"
                        
                        # Aggregate chunks per document for context
                        from ..models.documents import DocumentVersion
                        for doc in docs:
                            doc_id = doc.id
                            chunks_for_doc = doc_chunks_map.get(doc_id, [])
                            
                            # Sort chunks by score (descending) and take top chunks
                            chunks_for_doc.sort(
                                key=lambda c: c["score"] if c["score"] is not None else 0,
                                reverse=True
                            )
                            
                            # Aggregate chunk texts
                            chunk_texts = []
                            for chunk_result in chunks_for_doc:
                                chunk_text = chunk_result.get("chunk_text")
                                if chunk_text:
                                    chunk_texts.append(chunk_text)
                            
                            # If we have chunks, use them; otherwise fallback to full document text
                            if chunk_texts:
                                # Combine chunks with separator
                                aggregated_text = "\n\n".join(chunk_texts)
                                # Limit total context length (use first ~2000 chars)
                                doc_contexts.append(aggregated_text[:2000])
                                
                                # Create citation with chunk snippet
                                best_chunk = chunks_for_doc[0] if chunks_for_doc else None
                                snippet = best_chunk.get("chunk_text", "")[:200] if best_chunk else ""
                                
                                citation = {
                                    "document_id": doc.id,
                                    "doc_id": doc.id,
                                    "title": doc.title,
                                    "snippet": snippet,
                                    "chunk_count": len(chunks_for_doc)
                                }
                            else:
                                # Fallback: get full document text (backward compatibility)
                                version_result = await session.execute(
                                    select(DocumentVersion)
                                    .where(DocumentVersion.document_id == doc.id)
                                    .order_by(DocumentVersion.version_no.desc())
                                    .limit(1)
                                )
                                version = version_result.scalar_one_or_none()
                                
                                if version and version.text_uri:
                                    from ..services.diff import get_text_from_uri
                                    text_content = await get_text_from_uri(version.text_uri)
                                    if text_content:
                                        doc_contexts.append(text_content[:500])
                                        
                                        citation = {
                                            "document_id": doc.id,
                                            "doc_id": doc.id,
                                            "title": doc.title,
                                            "snippet": text_content[:200]
                                        }
                                    else:
                                        continue
                                else:
                                    continue
                            
                            # Add score if available
                            if doc.id in doc_scores:
                                citation["score"] = doc_scores[doc.id]
                            
                            citations.append(citation)
                
            except EmbeddingModelUnavailableError as e:
                # If embedding service is unavailable, continue without vector search
                print(f"Embedding service unavailable: {e}")
                warning = "Vector search unavailable. Answering without document context."
    
    # Generate response using LLM service with prompts and get token usage
    # Use async version to load prompts from settings
    if hasattr(llm_service, 'chat_with_usage_async'):
        answer, token_usage = await llm_service.chat_with_usage_async(request.message, context=doc_contexts, session=session)
    else:
        answer, token_usage = llm_service.chat_with_usage(request.message, context=doc_contexts)
    token_in = token_usage.get("token_in", 0)
    token_out = token_usage.get("token_out", 0)
    
    # Store in cache
    try:
        if redis_client:
            session_key = f"chat:session:{session_id}"
            await redis_client.lpush(session_key, f"user:{request.message}", f"assistant:{answer}")
            await redis_client.expire(session_key, 3600 * 24)  # 24 hours
    except Exception as e:
        # Redis not available or error - continue without cache
        print(f"Redis error (continuing without cache): {e}")
    
    # Store in database for audit
    chat_session_result = await session.execute(
        select(ChatSession).where(ChatSession.session_id == session_id)
    )
    chat_session = chat_session_result.scalar_one_or_none()
    
    if not chat_session:
        chat_session = ChatSession(
            user_id=current_user.id,
            group_id=request.group_id,
            session_id=session_id,
            messages=[],
            token_in_total=0,
            token_out_total=0
        )
        session.add(chat_session)
    
    # Add messages to session with token tracking
    messages = chat_session.messages or []
    messages.append({
        "role": "user",
        "content": request.message,
        "timestamp": datetime.utcnow().isoformat(),
        "token_in": 0,  # User messages don't count as input tokens for LLM
        "token_out": 0
    })
    messages.append({
        "role": "assistant",
        "content": answer,
        "citations": citations,
        "timestamp": datetime.utcnow().isoformat(),
        "token_in": token_in,
        "token_out": token_out
    })
    chat_session.messages = messages[-20:]  # Keep last 20 messages
    
    # Update total token counts for session
    chat_session.token_in_total = (chat_session.token_in_total or 0) + token_in
    chat_session.token_out_total = (chat_session.token_out_total or 0) + token_out
    
    await session.commit()
    await session.refresh(chat_session)
    
    response_data = {
        "answer": answer,
        "citations": citations,
        "session_id": session_id
    }
    
    if warning:
        response_data["warning"] = warning
    
    return success_response(response_data)


@router.get("/available-documents")
async def get_available_documents(
    group_id: Optional[int] = Query(None),
    tags: Optional[str] = Query(None, description="Comma-separated tag names"),
    type: Optional[str] = Query(None, description="MIME type filter"),
    date_from: Optional[str] = Query(None, description="ISO date string"),
    date_to: Optional[str] = Query(None, description="ISO date string"),
    current_user: User = Depends(require_permission("chat")),
    session: AsyncSession = Depends(get_session)
):
    """Get list of documents available for chat (user owns or has chat permission)."""
    # Base query: documents not deleted, status ready
    base_query = select(Document).where(
        and_(
            Document.deleted_at.is_(None),
            Document.status == "ready"
        )
    )
    
    # Get accessible documents với "chat" permission
    accessible_query = await get_user_accessible_documents_query(
        session, current_user, base_query
    )
    
    # Apply group_id filter if provided
    # Documents are linked to groups through document_group_documents table
    if group_id:
        accessible_query = accessible_query.join(
            document_group_documents,
            Document.id == document_group_documents.c.document_id
        ).where(
            document_group_documents.c.group_id == group_id
        ).distinct()
    
    # Apply tags filter
    if tags:
        tag_names = [t.strip() for t in tags.split(",") if t.strip()]
        if tag_names:
            # Join with DocumentTag and Tag
            accessible_query = accessible_query.join(
                DocumentTag, Document.id == DocumentTag.document_id
            ).join(
                Tag, DocumentTag.tag_id == Tag.id
            ).where(
                Tag.name.in_(tag_names)
            ).distinct()
    
    # Apply type filter
    if type:
        accessible_query = accessible_query.where(Document.mime.like(f"%{type}%"))
    
    # Apply date filters
    if date_from:
        try:
            date_from_obj = datetime.fromisoformat(date_from.replace("Z", "+00:00"))
            accessible_query = accessible_query.where(Document.created_at >= date_from_obj)
        except ValueError:
            pass  # Invalid date format, ignore
    
    if date_to:
        try:
            date_to_obj = datetime.fromisoformat(date_to.replace("Z", "+00:00"))
            accessible_query = accessible_query.where(Document.created_at <= date_to_obj)
        except ValueError:
            pass  # Invalid date format, ignore
    
    # Execute query
    result = await session.execute(accessible_query)
    accessible_docs = result.scalars().all()
    accessible_doc_ids = [doc.id for doc in accessible_docs]
    
    # Get group IDs for each document (query separately to avoid async relationship issues)
    doc_group_map = {}
    if accessible_doc_ids:
        group_mapping_result = await session.execute(
            select(
                document_group_documents.c.document_id,
                document_group_documents.c.group_id
            ).where(
                document_group_documents.c.document_id.in_(accessible_doc_ids)
            )
        )
        group_mappings = group_mapping_result.all()
        for mapping in group_mappings:
            doc_id = mapping.document_id
            group_id = mapping.group_id
            if doc_id not in doc_group_map:
                doc_group_map[doc_id] = []
            doc_group_map[doc_id].append(group_id)
    
    # Check embedding existence for each document
    embedding_service = get_embedding_service()
    documents_list = []
    
    # Get all document IDs that have embeddings in Qdrant
    docs_with_embeddings = set()
    if embedding_service:
        print(f"[get_available_documents] Checking embedding service availability...")
        is_available = embedding_service.is_available()
        has_store = bool(embedding_service.store)
        has_client = bool(embedding_service.store and embedding_service.store.client)
        store_type = "Qdrant"
        
        print(f"[get_available_documents] Embedding service status:")
        print(f"  - Available: {is_available}")
        print(f"  - Has store: {has_store}")
        print(f"  - Has client: {has_client}")
        print(f"  - Store type: {store_type}")
        
        if is_available and has_store and has_client:
            try:
                # Check collection count first - use QdrantVectorStore.count() method
                collection_count = embedding_service.store.count()
                print(f"[get_available_documents] Collection count: {collection_count}")
                
                # Handle special case: -1 means collection has data but exact count unavailable
                if collection_count == -1:
                    print(f"[get_available_documents] Collection has data but exact count unavailable, proceeding to get embeddings")
                    collection_count = 1  # Set to > 0 to proceed
                
                if collection_count > 0:
                    # Get all embeddings from Qdrant using store.get() method
                    all_embeddings_result = embedding_service.store.get(where=None, limit=10000)
                    
                    if all_embeddings_result and all_embeddings_result.get("metadatas"):
                        # Qdrant returns payloads (metadatas) as a list of dicts
                        sample_metas = []
                        for idx, meta in enumerate(all_embeddings_result["metadatas"]):
                            if not meta:
                                continue
                            doc_id = meta.get("doc_id")
                            if doc_id is not None:
                                try:
                                    # Handle both string and int doc_id
                                    doc_id_int = int(doc_id) if isinstance(doc_id, str) else doc_id
                                    docs_with_embeddings.add(doc_id_int)
                                    if idx < 3:  # Sample first 3
                                        sample_metas.append({"doc_id_raw":doc_id,"doc_id_type":type(doc_id).__name__,"doc_id_int":doc_id_int})
                                except (ValueError, TypeError) as e:
                                    # Skip invalid doc_id values
                                    print(f"[get_available_documents] Skipping invalid doc_id: {doc_id} (error: {e})")
                                    pass
                        
                        print(f"[get_available_documents] Found {len(docs_with_embeddings)} unique documents with embeddings")
                        if sample_metas:
                            print(f"[get_available_documents] Sample metadata: {sample_metas}")
                    else:
                        print(f"[get_available_documents] No metadata found in collection result")
                else:
                    print(f"[get_available_documents] Collection is empty")
                    all_embeddings_result = None
            except Exception as e:
                print(f"[get_available_documents] ERROR: Error checking embeddings: {e}")
                import traceback
                traceback.print_exc()
                # If check fails, we'll assume no documents have embeddings
        else:
            print(f"[get_available_documents] WARNING: Embedding service not fully available (available={is_available}, has_store={has_store}, has_collection={has_collection})")
    else:
        print(f"[get_available_documents] WARNING: Embedding service is None")
    
    # Process each accessible document
    sample_docs = []
    docs_with_embedding_count = 0
    for doc in accessible_docs:
        # Determine if document is shared (not owned by user)
        is_shared = doc.owner_id != current_user.id
        
        # Check if this document has embedding
        has_embedding = doc.id in docs_with_embeddings
        if has_embedding:
            docs_with_embedding_count += 1
        
        # Get group IDs for this document from the pre-queried map
        doc_group_ids = doc_group_map.get(doc.id, [])
        
        # Sample first 3 documents for logging
        if len(sample_docs) < 3:
            sample_docs.append({
                "id": doc.id,
                "title": doc.title[:50] if doc.title else None,
                "has_embedding": has_embedding
            })
        
        documents_list.append({
            "id": doc.id,
            "title": doc.title,
            "mime": doc.mime,
            "created_at": doc.created_at.isoformat() if doc.created_at else None,
            "has_embedding": has_embedding,
            "group_ids": doc_group_ids,  # List of group IDs
            "group_id": doc_group_ids[0] if doc_group_ids else None,  # First group for backward compatibility
            "owner_id": doc.owner_id,
            "is_shared": is_shared
        })
    
    print(f"[get_available_documents] Document processing summary:")
    print(f"  - Total accessible documents: {len(accessible_docs)}")
    print(f"  - Documents with embeddings: {docs_with_embedding_count}")
    print(f"  - Documents without embeddings: {len(accessible_docs) - docs_with_embedding_count}")
    if sample_docs:
        print(f"  - Sample documents: {sample_docs}")
    
    return success_response({
        "documents": documents_list,
        "total": len(documents_list)
    })


@router.get("/history")
async def get_chat_history(
    group_id: Optional[int] = Query(None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Load chat history from database."""
    query = select(ChatSession).where(ChatSession.user_id == current_user.id)
    
    if group_id:
        query = query.where(ChatSession.group_id == group_id)
    
    query = query.order_by(ChatSession.created_at.desc()).limit(50)
    
    result = await session.execute(query)
    sessions = result.scalars().all()
    
    sessions_list = [{
        "session_id": s.session_id,
        "group_id": s.group_id,
        "message_count": len(s.messages or []),
        "created_at": s.created_at.isoformat(),
        "updated_at": s.updated_at.isoformat()
    } for s in sessions]
    
    return success_response(sessions_list)


@router.get("/session/{session_id}")
async def get_session_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Get session history from database."""
    chat_session_result = await session.execute(
        select(ChatSession).where(ChatSession.session_id == session_id)
    )
    chat_session = chat_session_result.scalar_one_or_none()
    
    if not chat_session:
        return error_response("Chat session not found", status_code=status.HTTP_404_NOT_FOUND)
    
    if chat_session.user_id != current_user.id:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    messages = chat_session.messages or []
    
    return success_response({
        "session_id": session_id,
        "group_id": chat_session.group_id,
        "messages": messages,
        "feedback": chat_session.feedback,
        "handoff_id": chat_session.handoff_id,
        "created_at": chat_session.created_at.isoformat(),
        "updated_at": chat_session.updated_at.isoformat()
    })


class FeedbackRequest(BaseModel):
    rating: str  # positive, negative
    comment: Optional[str] = None


class HandoffRequest(BaseModel):
    reason: str
    context: Optional[dict] = None


class SourceAccessRequest(BaseModel):
    source_ids: List[int]
    access_type: str = "preview"  # preview, download


@router.post("/session/{session_id}/feedback")
async def submit_feedback(
    session_id: str,
    request: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Submit feedback for chat session."""
    # Validate rating
    if request.rating not in ["positive", "negative"]:
        return error_response(
            "Rating must be 'positive' or 'negative'",
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    # Store feedback in database
    chat_session_result = await session.execute(
        select(ChatSession).where(ChatSession.session_id == session_id)
    )
    chat_session = chat_session_result.scalar_one_or_none()
    
    if not chat_session:
        return error_response("Chat session not found", status_code=status.HTTP_404_NOT_FOUND)
    
    if chat_session.user_id != current_user.id:
        return error_response("Access denied", status_code=status.HTTP_403_FORBIDDEN)
    
    chat_session.feedback = {
        "rating": request.rating,
        "comment": request.comment,
        "submitted_at": datetime.utcnow().isoformat()
    }
    
    await session.commit()
    await session.refresh(chat_session)
    
    return success_response({
        "session_id": session_id,
        "rating": request.rating,
        "comment": request.comment,
        "submitted_at": datetime.utcnow().isoformat()
    })


@router.post("/session/{session_id}/handoff")
async def handoff_to_human(
    session_id: str,
    request: HandoffRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Escalate chat session to human agent."""
    # TODO: Create support ticket or assign to staff
    # For now, just return success
    return success_response({
        "session_id": session_id,
        "handoff_id": str(uuid.uuid4()),
        "reason": request.reason,
        "status": "pending",
        "created_at": datetime.utcnow().isoformat()
    })


@router.post("/session/{session_id}/source-access")
async def request_source_access(
    session_id: str,
    request: SourceAccessRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    """Request access to source documents."""
    from ..models.documents import Document
    from ..services.storage import generate_presigned_download_url
    from datetime import timedelta
    
    # Get documents and verify access using permission service
    accessible_docs = []
    for doc_id in request.source_ids:
        doc_result = await session.execute(
            select(Document).where(
                and_(
                    Document.id == doc_id,
                    Document.deleted_at.is_(None)
                )
            )
        )
        doc = doc_result.scalar_one_or_none()
        
        if doc:
            # Check view access (for preview) or view access (for download)
            # Both preview and download require view permission
            has_access, _, _ = await check_document_access(session, current_user, doc, "view")
            
            if has_access:
                # Generate presigned URL if access_type is download
                url = None
                if request.access_type == "download" and doc.versions:
                    # Get latest version blob_uri
                    from ..models.documents import DocumentVersion
                    version_result = await session.execute(
                        select(DocumentVersion)
                        .where(DocumentVersion.document_id == doc.id)
                        .order_by(DocumentVersion.version_no.desc())
                        .limit(1)
                    )
                    version = version_result.scalar_one_or_none()
                    if version and version.blob_uri:
                        url = generate_presigned_download_url(version.blob_uri, expires=timedelta(hours=1))
                
                accessible_docs.append({
                    "document_id": doc.id,
                    "title": doc.title,
                    "url": url,
                    "access_type": request.access_type
                })
    
    return success_response({
        "session_id": session_id,
        "sources": accessible_docs
    })

