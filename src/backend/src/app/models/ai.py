from sqlalchemy import Column, Integer, String, JSON

from .base import BaseModel


class AIJob(BaseModel):
    __tablename__ = "ai_jobs"

    job_type = Column(String(50), nullable=False)  # ocr, embed, classify, qa
    target = Column(JSON, nullable=False)  # {doc_id, version_id, chunk_id}
    provider = Column(String(100), nullable=True)
    status = Column(String(50), default="queued")  # queued, processing, completed, failed
    input_ref = Column(JSON, nullable=True)
    output_ref = Column(JSON, nullable=True)
    error = Column(String(500), nullable=True)


class Embedding(BaseModel):
    __tablename__ = "embeddings"

    doc_id = Column(Integer, nullable=False)
    version_id = Column(Integer, nullable=True)
    chunk_id = Column(String(100), nullable=True)
    vector = Column(JSON, nullable=False)  # Array of floats
    chunk_ref = Column(JSON, nullable=True)  # Reference to chunk content
    provider = Column(String(100), nullable=True)
    group_id = Column(Integer, nullable=True)  # For document group scoping

