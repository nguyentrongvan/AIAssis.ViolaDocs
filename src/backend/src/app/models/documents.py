from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, Text, Boolean, JSON, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

from .base import BaseModel


class Document(BaseModel):
    __tablename__ = "documents"
    
    title = Column(String(500), nullable=False)
    source = Column(String(50), nullable=False)  # web, scan, api
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=True)
    mime = Column(String(100), nullable=False)
    size = Column(Integer, nullable=False)
    checksum = Column(String(64), nullable=True)
    status = Column(String(50), default="processing")  # processing, ready, failed
    retention_policy_id = Column(Integer, ForeignKey("retention_policies.id"), nullable=True)
    sensitivity = Column(String(50), nullable=True)
    
    # Soft delete
    deleted_at = Column(DateTime, nullable=True)
    deleted_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    purge_at = Column(DateTime, nullable=True)
    
    versions = relationship("DocumentVersion", back_populates="document", cascade="all, delete-orphan")


class DocumentVersion(BaseModel):
    __tablename__ = "document_versions"
    
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    version_no = Column(Integer, nullable=False)
    blob_uri = Column(String(1000), nullable=False)
    ocr_uri = Column(String(1000), nullable=True)
    text_uri = Column(String(1000), nullable=True)
    thumbnail_uri = Column(String(1000), nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    checksum = Column(String(64), nullable=True)
    size = Column(Integer, nullable=False)
    status = Column(String(50), default="processing")
    
    # Lineage
    device_id = Column(Integer, ForeignKey("devices.id"), nullable=True)
    job_id = Column(String(100), nullable=True)
    
    # Provider info
    provider_info = Column(JSON, nullable=True)
    
    # Metadata snapshot
    metadata_snapshot = Column(JSON, nullable=True)
    
    document = relationship("Document", back_populates="versions")


class Tag(BaseModel):
    __tablename__ = "tags"
    
    name = Column(String(100), unique=True, nullable=False)


class DocumentTag(BaseModel):
    __tablename__ = "document_tags"
    
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    tag_id = Column(Integer, ForeignKey("tags.id"), nullable=False)


class Folder(BaseModel):
    __tablename__ = "folders"
    
    name = Column(String(255), nullable=False)
    parent_id = Column(Integer, ForeignKey("folders.id"), nullable=True)  # Hierarchical structure
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Self-referential relationship for parent-child
    parent = relationship("Folder", remote_side="Folder.id", backref="children")
    documents = relationship("Document", backref="folder")


class Share(BaseModel):
    __tablename__ = "shares"
    
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    target_type = Column(String(50), nullable=False)  # user, role, link
    target_id = Column(Integer, nullable=True)
    share_token = Column(String(64), unique=True, nullable=True)  # Token for share links
    expires_at = Column(DateTime, nullable=True)
    permissions = Column(JSON, nullable=True)  # read, write, delete


class FolderShare(BaseModel):
    __tablename__ = "folder_shares"
    
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=False)
    target_type = Column(String(50), nullable=False)  # user, role
    target_id = Column(Integer, nullable=True)  # user_id or role_id
    expires_at = Column(DateTime, nullable=True)
    
    # Relationship to Folder
    folder = relationship("Folder", backref="shares")


class Comment(BaseModel):
    __tablename__ = "comments"
    
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    version_id = Column(Integer, ForeignKey("document_versions.id"), nullable=True)  # Optional: comment on specific version
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    content = Column(Text, nullable=False)
    type = Column(String(50), default="comment", nullable=False)  # comment, annotation
    position = Column(JSON, nullable=True)  # For annotations: page, x, y, width, height, etc.


# Annotation uses the same table as Comment, differentiated by type field
# No separate class needed - use Comment with type='annotation'






