from sqlalchemy import Column, DateTime, Integer, String, JSON

from .base import BaseModel


class Device(BaseModel):
    __tablename__ = "devices"

    name = Column(String(150), nullable=False)
    location = Column(String(255), nullable=True)
    capabilities = Column(JSON, nullable=True)  # List of strings
    status = Column(String(50), default="offline")  # online, offline
    last_seen = Column(DateTime, nullable=True)
    public_key = Column(String(255), nullable=True)  # Device authentication key

