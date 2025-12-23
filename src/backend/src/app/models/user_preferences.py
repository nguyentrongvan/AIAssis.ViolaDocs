from sqlalchemy import Column, String, Boolean, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import relationship
from .base import BaseModel


class UserPreferences(BaseModel):
    """User-specific preferences for theme and UI customization"""
    __tablename__ = "user_preferences"
    
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)
    primary_color = Column(String(7), nullable=True)  # Hex color, e.g., "#3E2FA6"
    font_size = Column(String(20), nullable=True, default="medium")  # small, medium, large
    border_radius = Column(String(20), nullable=True, default="medium")  # small, medium, large
    animation_speed = Column(String(20), nullable=True, default="normal")  # normal, fast, slow
    compact_mode = Column(Boolean, default=False, nullable=False)
    
    # Relationship
    user = relationship("User", backref="preferences")
    
    __table_args__ = (
        UniqueConstraint('user_id', name='uq_user_preferences_user_id'),
    )



