from sqlalchemy import Column, Integer, String, Text, JSON, ForeignKey
from sqlalchemy.orm import relationship
import uuid

from .base import BaseModel


class ChatSession(BaseModel):
    __tablename__ = "chat_sessions"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("document_groups.id"), nullable=True)
    session_id = Column(String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    messages = Column(JSON, nullable=False, default=[])  # Array of message objects
    feedback = Column(JSON, nullable=True)  # User feedback if provided
    handoff_id = Column(String(100), nullable=True)  # Support ticket ID if escalated
    token_in_total = Column(Integer, nullable=False, default=0)  # Total input tokens for session
    token_out_total = Column(Integer, nullable=False, default=0)  # Total output tokens for session
    
    user = relationship("User", backref="chat_sessions")
    group = relationship("DocumentGroup", backref="chat_sessions")

