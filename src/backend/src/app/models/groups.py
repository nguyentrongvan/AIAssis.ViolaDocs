from sqlalchemy import Column, Integer, String, Text, JSON, Table, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base, BaseModel

# Association tables for many-to-many relationships
document_group_documents = Table(
    "document_group_documents",
    Base.metadata,
    Column("group_id", Integer, ForeignKey("document_groups.id"), primary_key=True),
    Column("document_id", Integer, ForeignKey("documents.id"), primary_key=True)
)

document_group_folders = Table(
    "document_group_folders",
    Base.metadata,
    Column("group_id", Integer, ForeignKey("document_groups.id"), primary_key=True),
    Column("folder_id", Integer, ForeignKey("folders.id"), primary_key=True)
)

document_group_tags = Table(
    "document_group_tags",
    Base.metadata,
    Column("group_id", Integer, ForeignKey("document_groups.id"), primary_key=True),
    Column("tag_id", Integer, ForeignKey("tags.id"), primary_key=True)
)


class DocumentGroup(BaseModel):
    __tablename__ = "document_groups"

    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    owners = Column(JSON, nullable=True, default=[])  # Array of user IDs
    allowed_roles = Column(JSON, nullable=True, default=[])  # Array of role names
    allowed_users = Column(JSON, nullable=True, default=[])  # Array of user IDs
    chatbot_policy = Column(JSON, nullable=True, default={})  # Policy for chatbot access
    
    # Many-to-many relationships
    documents = relationship("Document", secondary=document_group_documents, backref="groups")
    folders = relationship("Folder", secondary=document_group_folders, backref="groups")
    tags = relationship("Tag", secondary=document_group_tags, backref="groups")

