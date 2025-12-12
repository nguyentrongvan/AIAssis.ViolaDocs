from sqlalchemy import Column, Integer, String, Boolean
from sqlalchemy.orm import relationship

from .base import BaseModel


class RetentionPolicy(BaseModel):
    __tablename__ = "retention_policies"
    
    name = Column(String(150), nullable=False)
    duration_days = Column(Integer, nullable=False)  # Retention duration in days
    disposition = Column(String(50), nullable=False)  # delete, archive
    legal_hold = Column(Boolean, default=False, nullable=False)  # Prevent deletion if legal hold is active

