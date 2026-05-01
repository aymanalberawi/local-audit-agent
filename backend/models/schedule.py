"""
Schedule Model - Represents recurring audit schedules
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from models.base import Base


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(Integer, primary_key=True, index=True)
    connection_id = Column(Integer, ForeignKey("connections.id"), nullable=False)
    standard_name = Column(String, nullable=False)  # e.g., "GDPR-UAE", "ISO-27001"
    frequency = Column(String, nullable=False)  # "daily", "weekly", "monthly"
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)

    # Status tracking
    is_active = Column(Boolean, default=True)
    next_run_at = Column(DateTime, nullable=False)
    last_run_at = Column(DateTime, nullable=True)
    last_task_id = Column(String, nullable=True)  # Celery task ID
    last_error = Column(Text, nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    connection = relationship("Connection", back_populates="schedules")
    company = relationship("Company", back_populates="schedules")

    # Allow table to exist in multiple definitions (alembic + model)
    __table_args__ = {'extend_existing': True}

    def __repr__(self):
        return f"<Schedule {self.id}: {self.standard_name} {self.frequency}>"
