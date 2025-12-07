from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from .base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="user", nullable=False)  # admin, staff, user
    status = Column(String(50), default="active", nullable=False)  # active, inactive
    expires_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)

