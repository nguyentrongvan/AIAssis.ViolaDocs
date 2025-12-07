from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import relationship

from .base import BaseModel


class Workflow(BaseModel):
    __tablename__ = "workflows"

    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    template = Column(String(100), nullable=True)
    state = Column(String(50), default="pending")  # pending, in_progress, completed, rejected
    assignees = Column(JSON, nullable=True)  # List of user IDs
    due_at = Column(DateTime, nullable=True)

    tasks = relationship("Task", back_populates="workflow", cascade="all, delete-orphan")


class Task(BaseModel):
    __tablename__ = "tasks"

    workflow_id = Column(Integer, ForeignKey("workflows.id"), nullable=False)
    assignee_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    state = Column(String(50), default="pending")  # pending, completed
    action = Column(String(50), nullable=True)  # approve, reject, request_changes
    comment = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    workflow = relationship("Workflow", back_populates="tasks")

