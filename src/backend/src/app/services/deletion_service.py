"""
Document Deletion Service
Handles soft delete, hard delete, and cleanup of all document-related data
"""
from typing import List, Optional
import logging
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, and_, or_, cast, String

from ..db import AsyncSessionLocal
from ..models.documents import Document, DocumentVersion, DocumentTag, Share, Comment
from ..models.workflows import Workflow, Task
from ..models.ai import AIJob, Embedding
from ..models.audit import AuditEvent
from ..services.storage import delete_file_from_minio
from ..services.settings_service import SettingsService
# Don't import embedding service at module level - import lazily in function to avoid importing OCR service
from ..services.retention import check_legal_hold
from ..config import settings

logger = logging.getLogger(__name__)


class DocumentDeletionService:
    """Service for handling document deletion operations"""
    
    @staticmethod
    async def get_purge_grace_period_days(session: Optional[AsyncSession] = None) -> int:
        """Get purge grace period in days from settings (default: 1 day)"""
        days = await SettingsService.get_setting(
            "purge_grace_period_days",
            default=1,
            session=session
        )
        return int(days) if days is not None else 1
    
    @staticmethod
    async def soft_delete_document(
        doc_id: int,
        user_id: int,
        session: AsyncSession
    ) -> Document:
        """Soft delete a document - mark as deleted and set purge date"""
        # Get document
        result = await session.execute(
            select(Document).where(
                and_(
                    Document.id == doc_id,
                    Document.deleted_at.is_(None)
                )
            )
        )
        doc = result.scalar_one_or_none()
        
        if not doc:
            raise ValueError(f"Document {doc_id} not found or already deleted")
        
        # Check legal hold
        if await check_legal_hold(doc_id, session):
            raise ValueError("Cannot delete document with active legal hold")
        
        # Cancel related AI jobs
        await DocumentDeletionService.cancel_related_jobs(doc_id, session)
        
        # Get purge grace period
        grace_period_days = await DocumentDeletionService.get_purge_grace_period_days(session)
        
        # Set soft delete fields
        doc.deleted_at = datetime.utcnow()
        doc.deleted_by = user_id
        doc.purge_at = datetime.utcnow() + timedelta(days=grace_period_days)
        
        await session.commit()
        await session.refresh(doc)
        
        # Log audit event
        await DocumentDeletionService._log_audit_event(
            actor_id=user_id,
            subject_type="document",
            subject_id=doc_id,
            action="soft_delete",
            metadata={
                "purge_at": doc.purge_at.isoformat(),
                "grace_period_days": grace_period_days
            },
            session=session
        )
        
        return doc
    
    @staticmethod
    async def hard_delete_document(
        doc_id: int,
        user_id: int,
        session: AsyncSession,
        force: bool = False
    ) -> bool:
        """Hard delete a document - permanently remove all related data"""
        # Get document (allow deleted documents if force=True)
        if force:
            result = await session.execute(
                select(Document).where(Document.id == doc_id)
            )
        else:
            result = await session.execute(
                select(Document).where(
                    and_(
                        Document.id == doc_id,
                        Document.deleted_at.isnot(None),
                        Document.purge_at <= datetime.utcnow()
                    )
                )
            )
        
        doc = result.scalar_one_or_none()
        
        if not doc:
            raise ValueError(f"Document {doc_id} not found or not ready for purge")
        
        # Check legal hold (even for force delete)
        if await check_legal_hold(doc_id, session):
            raise ValueError("Cannot delete document with active legal hold")
        
        # Get all versions before deletion
        versions_result = await session.execute(
            select(DocumentVersion).where(DocumentVersion.document_id == doc_id)
        )
        versions = versions_result.scalars().all()
        version_ids = [v.id for v in versions]
        
        # Delete storage files
        await DocumentDeletionService.delete_storage_files(doc, session)
        
        # Delete embeddings
        await DocumentDeletionService.delete_embeddings(doc_id, version_ids, session)
        
        # Delete database records
        await DocumentDeletionService.delete_database_records(doc, session)
        
        # Log audit event
        await DocumentDeletionService._log_audit_event(
            actor_id=user_id,
            subject_type="document",
            subject_id=doc_id,
            action="hard_delete",
            metadata={"force": force},
            session=session
        )
        
        return True
    
    @staticmethod
    async def restore_document(
        doc_id: int,
        user_id: int,
        session: AsyncSession
    ) -> Document:
        """Restore a soft-deleted document"""
        result = await session.execute(
            select(Document).where(
                and_(
                    Document.id == doc_id,
                    Document.deleted_at.isnot(None)
                )
            )
        )
        doc = result.scalar_one_or_none()
        
        if not doc:
            raise ValueError(f"Document {doc_id} not found or not deleted")
        
        # Clear soft delete fields
        doc.deleted_at = None
        doc.deleted_by = None
        doc.purge_at = None
        
        await session.commit()
        await session.refresh(doc)
        
        # Log audit event
        await DocumentDeletionService._log_audit_event(
            actor_id=user_id,
            subject_type="document",
            subject_id=doc_id,
            action="restore",
            metadata={},
            session=session
        )
        
        return doc
    
    @staticmethod
    async def cancel_related_jobs(doc_id: int, session: AsyncSession):
        """Cancel all AI jobs related to this document"""
        # Find all jobs for this document
        # Query all queued/processing jobs and filter in Python (more reliable for JSON fields)
        result = await session.execute(
            select(AIJob).where(
                AIJob.status.in_(["queued", "processing"])
            )
        )
        all_jobs = result.scalars().all()
        
        # Filter jobs that match this document
        jobs = []
        for job in all_jobs:
            if job.target:
                # Check both doc_id and document_id keys
                target_doc_id = job.target.get("doc_id") or job.target.get("document_id")
                if target_doc_id == doc_id:
                    jobs.append(job)
        
        for job in jobs:
            job.status = "cancelled"
            job.error = "Document deleted"
            job.release()  # Clear worker tracking
        
        if jobs:
            await session.commit()
            logger.info(f"Cancelled {len(jobs)} AI jobs for document {doc_id}")
    
    @staticmethod
    async def delete_storage_files(document: Document, session: AsyncSession):
        """Delete all storage files for document and its versions"""
        # Get all versions
        result = await session.execute(
            select(DocumentVersion).where(DocumentVersion.document_id == document.id)
        )
        versions = result.scalars().all()
        
        files_deleted = 0
        files_failed = 0
        
        for version in versions:
            # List of URIs to delete
            uris_to_delete = []
            
            if version.blob_uri:
                uris_to_delete.append(version.blob_uri)
            if version.ocr_uri:
                uris_to_delete.append(version.ocr_uri)
            if version.text_uri:
                uris_to_delete.append(version.text_uri)
            if version.thumbnail_uri:
                uris_to_delete.append(version.thumbnail_uri)
            
            # Delete each file
            for uri in uris_to_delete:
                # Remove minio:// prefix if present
                object_name = uri
                if object_name.startswith(f"minio://{settings.minio_bucket}/"):
                    object_name = object_name.replace(f"minio://{settings.minio_bucket}/", "")
                
                try:
                    success = await delete_file_from_minio(object_name)
                    if success:
                        files_deleted += 1
                    else:
                        files_failed += 1
                        logger.warning(f"Failed to delete file: {object_name}")
                except Exception as e:
                    files_failed += 1
                    logger.error(f"Error deleting file {object_name}: {e}", exc_info=True)
            
            # Delete renditions folder if exists
            try:
                # Try to delete renditions folder
                renditions_prefix = f"renditions/{document.id}/{version.id}/"
                # Note: MinIO doesn't have folders, but we can list and delete objects with prefix
                from ..services.storage import get_minio_client
                minio_client = get_minio_client()
                objects = minio_client.list_objects(
                    settings.minio_bucket,
                    prefix=renditions_prefix,
                    recursive=True
                )
                for obj in objects:
                    try:
                        minio_client.remove_object(settings.minio_bucket, obj.object_name)
                        files_deleted += 1
                    except Exception as e:
                        files_failed += 1
                        logger.error(f"Error deleting rendition {obj.object_name}: {e}", exc_info=True)
            except Exception as e:
                logger.error(f"Error listing renditions for document {document.id}: {e}", exc_info=True)
        
        logger.info(f"Deleted {files_deleted} files, {files_failed} failed for document {document.id}")
    
    @staticmethod
    async def delete_embeddings(doc_id: int, version_ids: List[int], session: AsyncSession):
        """Delete embeddings from vector store and database"""
        # Import embedding service lazily using importlib to avoid importing OCR service (which needs PIL)
        # This is important for purge worker which doesn't have OCR dependencies
        # Using importlib to import directly without going through __init__.py
        try:
            import importlib
            embedding_module = importlib.import_module('app.services.ai.embedding_service')
            embedding_service = embedding_module.get_embedding_service()
            if embedding_service and embedding_service.store and embedding_service.store.client:
                try:
                    # Get all points for this document from Qdrant
                    points_result = embedding_service.store.get(
                        where={"doc_id": doc_id},
                        limit=10000
                    )
                    
                    if points_result and points_result.get("ids") and len(points_result["ids"]) > 0:
                        ids_to_delete = points_result["ids"]
                        # Convert string IDs back to int/str as needed by Qdrant
                        point_ids = []
                        for id_str in ids_to_delete:
                            try:
                                # Try to convert to int if numeric
                                if id_str.startswith("embed-"):
                                    point_ids.append(int(id_str.split("-")[-1]))
                                else:
                                    point_ids.append(int(id_str))
                            except (ValueError, IndexError):
                                point_ids.append(id_str)
                        
                        # Delete by point IDs
                        from qdrant_client.models import PointIdsList
                        embedding_service.store.client.delete(
                            collection_name=embedding_service.store.collection_name,
                            points_selector=PointIdsList(points=point_ids)
                        )
                        logger.info(f"Deleted {len(point_ids)} embeddings from Qdrant for document {doc_id}")
                    else:
                        logger.debug(f"No embeddings found in Qdrant for document {doc_id}")
                except Exception as e:
                    logger.error(f"Error deleting embeddings from Qdrant: {e}", exc_info=True)
        except Exception as e:
            logger.error(f"Error accessing embedding service: {e}", exc_info=True)
        
        # Delete from database (Embedding table)
        try:
            if version_ids:
                result = await session.execute(
                    delete(Embedding).where(
                        or_(
                            Embedding.doc_id == doc_id,
                            Embedding.version_id.in_(version_ids)
                        )
                    )
                )
            else:
                result = await session.execute(
                    delete(Embedding).where(Embedding.doc_id == doc_id)
                )
            deleted_count = result.rowcount
            if deleted_count > 0:
                await session.commit()
                logger.info(f"Deleted {deleted_count} embedding records from database for document {doc_id}")
        except Exception as e:
            logger.error(f"Error deleting embeddings from database: {e}", exc_info=True)
    
    @staticmethod
    async def delete_database_records(document: Document, session: AsyncSession):
        """Delete all database records related to document (in correct order)"""
        # 1. Cancel AI jobs (already done, but ensure they're cancelled)
        await DocumentDeletionService.cancel_related_jobs(document.id, session)
        
        # 2. Delete Shares
        await session.execute(
            delete(Share).where(Share.document_id == document.id)
        )
        
        # 3. Delete Comments
        await session.execute(
            delete(Comment).where(Comment.document_id == document.id)
        )
        
        # 4. Delete Workflows (cascade will delete Tasks)
        await session.execute(
            delete(Workflow).where(Workflow.document_id == document.id)
        )
        
        # 5. Delete DocumentTags
        await session.execute(
            delete(DocumentTag).where(DocumentTag.document_id == document.id)
        )
        
        # 6. Delete Embeddings (DB records - vector store already deleted)
        await session.execute(
            delete(Embedding).where(Embedding.doc_id == document.id)
        )
        
        # 7. Delete DocumentVersions (cascade)
        await session.execute(
            delete(DocumentVersion).where(DocumentVersion.document_id == document.id)
        )
        
        # 8. Delete Document (hard delete)
        await session.delete(document)
        
        await session.commit()
        logger.info(f"Deleted all database records for document {document.id}")
    
    @staticmethod
    async def _log_audit_event(
        actor_id: int,
        subject_type: str,
        subject_id: int,
        action: str,
        metadata: dict,
        session: AsyncSession
    ):
        """Log audit event for deletion operation"""
        try:
            audit_event = AuditEvent(
                actor_id=actor_id,
                subject_type=subject_type,
                subject_id=subject_id,
                action=action,
                metadata_=metadata,
                timestamp=datetime.utcnow()
            )
            session.add(audit_event)
            await session.commit()
        except Exception as e:
            logger.error(f"Error logging audit event: {e}", exc_info=True)
            # Don't fail deletion if audit logging fails

