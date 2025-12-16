from sqlalchemy import Column, Integer, String, JSON, DateTime
from datetime import datetime, timedelta

from .base import BaseModel


class AIJob(BaseModel):
    __tablename__ = "ai_jobs"

    job_type = Column(String(50), nullable=False)  # ocr, embed, classify, qa
    target = Column(JSON, nullable=False)  # {doc_id, version_id, chunk_id}
    provider = Column(String(100), nullable=True)
    status = Column(String(50), default="queued")  # queued, processing, completed, failed, cancelled
    input_ref = Column(JSON, nullable=True)
    output_ref = Column(JSON, nullable=True)
    error = Column(String(500), nullable=True)
    
    # Worker tracking
    worker_id = Column(String(100), nullable=True)  # ID of worker processing this job
    claimed_at = Column(DateTime, nullable=True)  # When job was claimed by worker
    last_heartbeat = Column(DateTime, nullable=True)  # Last heartbeat from worker
    retry_count = Column(Integer, default=0, nullable=False)  # Number of retries
    max_retries = Column(Integer, default=3, nullable=False)  # Maximum retries allowed
    
    def claim(self, worker_id: str):
        """Claim this job for processing by a worker"""
        self.worker_id = worker_id
        self.claimed_at = datetime.utcnow()
        self.status = "processing"
        self.last_heartbeat = datetime.utcnow()
    
    def release(self):
        """Release this job (worker stopped processing)"""
        self.worker_id = None
        self.claimed_at = None
        self.last_heartbeat = None
        if self.status == "processing":
            self.status = "queued"
    
    def is_stuck(self, timeout_minutes: int = 10) -> bool:
        """Check if job is stuck (claimed but no heartbeat for timeout period)"""
        if not self.claimed_at or not self.worker_id:
            return False
        if self.status != "processing":
            return False
        
        timeout = timedelta(minutes=timeout_minutes)
        if self.last_heartbeat:
            return datetime.utcnow() - self.last_heartbeat > timeout
        else:
            # No heartbeat at all, consider stuck
            return datetime.utcnow() - self.claimed_at > timeout
    
    def update_heartbeat(self):
        """Update heartbeat timestamp"""
        self.last_heartbeat = datetime.utcnow()
    
    def can_retry(self) -> bool:
        """Check if job can be retried"""
        return self.retry_count < self.max_retries
    
    def increment_retry(self):
        """Increment retry count"""
        self.retry_count += 1


class Embedding(BaseModel):
    __tablename__ = "embeddings"

    doc_id = Column(Integer, nullable=False)
    version_id = Column(Integer, nullable=True)
    chunk_id = Column(String(100), nullable=True)
    vector = Column(JSON, nullable=False)  # Array of floats
    chunk_ref = Column(JSON, nullable=True)  # Reference to chunk content
    provider = Column(String(100), nullable=True)
    group_id = Column(Integer, nullable=True)  # For document group scoping

