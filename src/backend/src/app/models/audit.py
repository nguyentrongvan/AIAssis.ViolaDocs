from sqlalchemy import Column, Integer, String, Text, JSON, DateTime

from .base import BaseModel


class AuditEvent(BaseModel):
    __tablename__ = "audit_events"

    actor_id = Column(Integer, nullable=False)
    subject_type = Column(String(50), nullable=False)  # document, user, device, etc.
    subject_id = Column(Integer, nullable=True)
    action = Column(String(100), nullable=False)  # create, update, delete, view, etc.
    metadata = Column(JSON, nullable=True)
    ip = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)
    timestamp = Column(DateTime, nullable=False)  # Same as created_at, for clarity in queries

