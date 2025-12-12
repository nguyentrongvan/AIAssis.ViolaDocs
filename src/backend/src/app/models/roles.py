from sqlalchemy import Column, Integer, String, JSON, Table, ForeignKey
from sqlalchemy.orm import relationship

from .base import Base, BaseModel

# Association table for many-to-many relationship between User and Role
user_role = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id"), primary_key=True),
    Column("role_id", Integer, ForeignKey("roles.id"), primary_key=True)
)


class Role(BaseModel):
    __tablename__ = "roles"
    
    name = Column(String(100), unique=True, nullable=False)
    permissions = Column(JSON, nullable=False, default=[])  # Array of permission strings
    
    # Many-to-many relationship with User
    users = relationship("User", secondary=user_role, back_populates="roles")

