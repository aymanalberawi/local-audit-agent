"""
Audit Scheme and Requirement models for structured compliance audits
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Enum as SQLEnum, JSON, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from models.base import Base


class AuditScheme(Base):
    """
    Represents a compliance framework (e.g., SOX, GDPR, ISO-27001)
    """
    __tablename__ = "audit_schemes"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)  # e.g., "SOX", "GDPR"
    description = Column(Text, nullable=True)
    version = Column(String(50), nullable=True)  # e.g., "1.0" (current version)
    is_built_in = Column(Boolean, default=False)  # True if imported from JSON
    region = Column(String(100), nullable=True)  # e.g., "EU", "GLOBAL", "UAE"
    authority = Column(String(255), nullable=True)  # e.g., "ISO", "NIST"
    source_file = Column(String(255), nullable=True)  # e.g., "iso_27001.json"
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    requirements = relationship("AuditRequirement", back_populates="scheme", cascade="all, delete-orphan")
    versions = relationship("StandardVersion", back_populates="scheme", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AuditScheme {self.name}>"


class AuditRequirement(Base):
    """
    Represents a specific control/requirement within a scheme
    e.g., "SOX-404: Internal Control Assessment"
    """
    __tablename__ = "audit_requirements"

    id = Column(Integer, primary_key=True)
    scheme_id = Column(Integer, ForeignKey("audit_schemes.id"), nullable=False)
    control_id = Column(String(100), nullable=False)  # e.g., "SOX-404", "GDPR-5.1"
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    severity = Column(String(50), default="MEDIUM")  # CRITICAL, HIGH, MEDIUM, LOW
    data_sources = Column(Text, nullable=True)  # JSON list of relevant data source patterns
    query_template = Column(Text, nullable=True)  # SQL/query template for checking requirement
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    scheme = relationship("AuditScheme", back_populates="requirements")
    results = relationship("RequirementResult", back_populates="requirement", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<AuditRequirement {self.control_id}>"


class RequirementResultStatus(str, enum.Enum):
    """Status of a requirement result"""
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    PASSED = "PASSED"
    FAILED = "FAILED"
    ERROR = "ERROR"


class RequirementResult(Base):
    """
    Stores the result of executing a single requirement within an audit job
    """
    __tablename__ = "requirement_results"

    id = Column(Integer, primary_key=True)
    job_id = Column(Integer, ForeignKey("audit_jobs.id"), nullable=False)
    requirement_id = Column(Integer, ForeignKey("audit_requirements.id"), nullable=False)
    status = Column(SQLEnum(RequirementResultStatus), default=RequirementResultStatus.PENDING)
    finding_count = Column(Integer, default=0)
    summary = Column(Text, nullable=True)  # Brief summary of result
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    requirement = relationship("AuditRequirement", back_populates="results")
    findings = relationship("RequirementFinding", back_populates="result", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<RequirementResult job={self.job_id} req={self.requirement_id} status={self.status}>"


class RequirementFinding(Base):
    """
    Individual findings for a requirement result
    """
    __tablename__ = "requirement_findings"

    id = Column(Integer, primary_key=True)
    result_id = Column(Integer, ForeignKey("requirement_results.id"), nullable=False)
    severity = Column(String(50), nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    evidence = Column(Text, nullable=True)  # Raw data/evidence from database
    affected_rows = Column(Integer, default=0)  # Number of affected records
    remediation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    result = relationship("RequirementResult", back_populates="findings")

    def __repr__(self):
        return f"<RequirementFinding {self.title}>"


class StandardVersion(Base):
    """
    Tracks version history of audit standards/schemes
    Allows version control and audit trails for standards
    """
    __tablename__ = "standard_versions"

    id = Column(Integer, primary_key=True)
    scheme_id = Column(Integer, ForeignKey("audit_schemes.id"), nullable=False)
    version_number = Column(String(50), nullable=False)  # e.g., "1.0", "2.0"
    created_at = Column(DateTime, default=datetime.utcnow)
    created_by_user_id = Column(Integer, nullable=True)  # FK to user table (optional)

    # Track if this version came from JSON import
    source = Column(String(50), default="custom")  # "json" or "custom"
    source_file = Column(String(255), nullable=True)  # e.g., "iso_27001.json"

    # Relationships
    scheme = relationship("AuditScheme", back_populates="versions")
    changes = relationship("StandardChangeLog", back_populates="version", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<StandardVersion scheme={self.scheme_id} v={self.version_number}>"


class StandardChangeLog(Base):
    """
    Audit trail for changes made to standards/schemes
    Tracks what changed, who changed it, and when
    """
    __tablename__ = "standard_change_logs"

    id = Column(Integer, primary_key=True)
    version_id = Column(Integer, ForeignKey("standard_versions.id"), nullable=False)
    changed_by_user_id = Column(Integer, nullable=False)  # FK to user table
    changed_at = Column(DateTime, default=datetime.utcnow)

    # Type of change: control_added, control_removed, control_modified, metadata_updated
    change_type = Column(String(50), nullable=False)

    # JSON details of the change
    # Format: {
    #   "control_id": "ISO-5.1",
    #   "field": "description",
    #   "old_value": "...",
    #   "new_value": "..."
    # }
    details = Column(JSON, nullable=True)

    # Relationships
    version = relationship("StandardVersion", back_populates="changes")

    def __repr__(self):
        return f"<StandardChangeLog version={self.version_id} type={self.change_type}>"
