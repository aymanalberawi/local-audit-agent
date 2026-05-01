from sqlalchemy import Column, Integer, String, JSON, ForeignKey, DateTime, Float, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.base import Base

class AuditJob(Base):
    __tablename__ = "audit_jobs"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("connections.id"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id"))
    standard_name = Column(String)
    status = Column(String, default="PENDING")

    # Progress tracking
    current_stage = Column(String, default="PENDING")  # PENDING, CHECKING_CACHE, DISCOVERING, LOADING_DATA, AUDITING, SAVING_RESULTS, COMPLETED, FAILED
    progress_percentage = Column(Float, default=0.0)  # 0-100
    stage_details = Column(String, nullable=True)  # Human-readable details like "Discovered 3 tables, scanning 50 records"
    error_message = Column(Text, nullable=True)  # Error details if audit fails

    # Error & Retry tracking
    error_type = Column(String, nullable=True)  # OLLAMA_TIMEOUT, OLLAMA_UNREACHABLE, CONNECTION_FAILED, FILE_NOT_FOUND, etc.
    is_retryable = Column(Boolean, default=True)  # Whether this error can be retried
    last_successful_stage = Column(String, nullable=True)  # Stage that completed successfully before failure
    last_processed_table = Column(String, nullable=True)  # Last table processed (for resuming audits)
    retry_count = Column(Integer, default=0)  # Track number of retries
    max_retries = Column(Integer, default=3)  # Max retry attempts

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    retried_from_job_id = Column(Integer, ForeignKey("audit_jobs.id"), nullable=True)  # Reference to original failed job

    connection = relationship("Connection", back_populates="audit_jobs")
    company = relationship("Company")

class Finding(Base):
    __tablename__ = "findings"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("audit_jobs.id"))
    control_id = Column(String)
    issue_description = Column(String)
    raw_data = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("AuditJob")


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("audit_jobs.id"), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    # Log type and message
    log_type = Column(String, nullable=False)  # 'discovery', 'data_extraction', 'audit', 'finding', 'system', 'error'
    message = Column(Text, nullable=False)  # Human-readable message
    details = Column(JSON, nullable=True)  # Structured data (table names, counts, etc.)

    # LLM interaction fields
    llm_prompt = Column(Text, nullable=True)  # Full prompt sent to Ollama
    llm_response = Column(Text, nullable=True)  # Full response from Ollama
    llm_reasoning = Column(Text, nullable=True)  # Extracted reasoning from response

    # Context for the log entry
    control_id = Column(String, nullable=True)  # Which control was being evaluated
    data_context = Column(JSON, nullable=True)  # Data row being evaluated

    # Relationships
    job = relationship("AuditJob")
