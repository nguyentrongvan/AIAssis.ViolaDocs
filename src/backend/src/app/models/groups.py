from sqlalchemy import Column, Integer, String, Text, JSON

from .base import BaseModel


class DocumentGroup(BaseModel):
    __tablename__ = "document_groups"

    name = Column(String(150), nullable=False)
    description = Column(Text, nullable=True)
    chatbot_policy = Column(JSON, nullable=True, default={})  # Policy for chatbot access

