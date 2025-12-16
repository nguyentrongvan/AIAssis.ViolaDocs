from sqlalchemy import Column, String, JSON, Boolean, Integer, ForeignKey, Index, DateTime
from datetime import datetime
from .base import Base


class SystemSettings(Base):
    """System settings stored in database"""
    __tablename__ = "system_settings"
    
    key = Column(String(100), primary_key=True, unique=True, nullable=False)
    value = Column(JSON, nullable=False)
    category = Column(String(50), nullable=False, index=True)
    description = Column(String(500), nullable=True)
    sensitive = Column(Boolean, default=False, nullable=False)
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    __table_args__ = (
        Index('idx_system_settings_category', 'category'),
    )

