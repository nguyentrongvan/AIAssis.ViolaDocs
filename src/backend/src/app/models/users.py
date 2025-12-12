from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Boolean
from sqlalchemy.orm import relationship
from .base import BaseModel


class User(BaseModel):
    __tablename__ = "users"

    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(50), default="user", nullable=False)  # admin, staff, user (legacy field, kept for backward compatibility)
    status = Column(String(50), default="active", nullable=False)  # active, inactive
    expires_at = Column(DateTime, nullable=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    locale = Column(String(10), nullable=True)  # e.g., "en", "vi"
    time_zone = Column(String(50), nullable=True)  # e.g., "Asia/Ho_Chi_Minh"
    is_maintainer = Column(Boolean, default=False, nullable=False)  # Root admin/maintainer flag for system config access
    
    # Many-to-many relationship with Role
    roles = relationship("Role", secondary="user_roles", back_populates="users")

