from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from models.base import Base

class ConnectionType(str, enum.Enum):
    FILE = "FILE"
    API = "API"
    POSTGRESQL = "POSTGRESQL"
    SQL_SERVER = "SQL_SERVER"
    ORACLE = "ORACLE"
    MOCK_DB = "MOCK_DB"

class ConnectionStatus(str, enum.Enum):
    ACTIVE = "ACTIVE"
    INACTIVE = "INACTIVE"
    FAILED = "FAILED"
    NOT_TESTED = "NOT_TESTED"

class Company(Base):
    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    applications = relationship("ApplicationInstance", back_populates="company", cascade="all, delete-orphan")
    schedules = relationship("Schedule", back_populates="company", cascade="all, delete-orphan")

class ApplicationInstance(Base):
    __tablename__ = "application_instances"

    id = Column(Integer, primary_key=True, index=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="applications")
    connections = relationship("Connection", back_populates="application", cascade="all, delete-orphan")

class Connection(Base):
    __tablename__ = "connections"

    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("application_instances.id"), nullable=False)
    name = Column(String, nullable=False)
    type = Column(Enum(ConnectionType), nullable=False)
    connection_string = Column(String) # e.g. URL or DB URI
    status = Column(Enum(ConnectionStatus), default=ConnectionStatus.NOT_TESTED)
    status_message = Column(String, nullable=True)  # Error message if status is FAILED
    last_tested_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    application = relationship("ApplicationInstance", back_populates="connections")
    schedules = relationship("Schedule", back_populates="connection", cascade="all, delete-orphan")
    audit_jobs = relationship("AuditJob", back_populates="connection")
