"""Test standards integration with audit engine and database"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from models.base import Base
from models.audit_scheme import AuditScheme, AuditRequirement
from services.standards_service import StandardsService
from core.database import get_db
import json
from pathlib import Path


# Create in-memory test database
TEST_DB_URL = "sqlite:///:memory:"


@pytest.fixture
def test_db():
    """Create test database and tables"""
    engine = create_engine(TEST_DB_URL)
    Base.metadata.create_all(bind=engine)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    yield db
    db.close()


def test_standards_validation():
    """Test JSON standard validation"""
    valid_standard = {
        "standard": "TEST-STANDARD",
        "controls": [
            {"id": "TEST-001", "name": "Test Control 1"},
            {"id": "TEST-002", "requirement": "Test Control 2"}
        ]
    }

    is_valid, msg = StandardsService.validate_standard_json(valid_standard)
    assert is_valid, f"Valid standard rejected: {msg}"

    # Test missing required fields
    invalid_missing_standard = {
        "controls": []
    }
    is_valid, msg = StandardsService.validate_standard_json(invalid_missing_standard)
    assert not is_valid
    assert "standard" in msg.lower()

    # Test missing control fields
    invalid_control = {
        "standard": "TEST",
        "controls": [
            {"name": "No ID field"}
        ]
    }
    is_valid, msg = StandardsService.validate_standard_json(invalid_control)
    assert not is_valid


def test_standards_import(test_db: Session):
    """Test importing standard from JSON into database"""
    test_standard = {
        "standard": "TEST-STANDARD-IMPORT",
        "full_name": "Test Standard for Import",
        "region": "GLOBAL",
        "authority": "Test Authority",
        "controls": [
            {
                "id": "TEST-001",
                "name": "Access Control",
                "description": "Manage user access",
                "severity": "HIGH",
                "logic": "Check user permissions"
            },
            {
                "id": "TEST-002",
                "requirement": "Data Protection",
                "description": "Protect sensitive data",
                "severity": "CRITICAL",
                "logic": "Encrypt data"
            }
        ]
    }

    success, msg, scheme = StandardsService.import_standard_from_json(
        test_db, test_standard, source_file="test_standard.json"
    )

    assert success, f"Import failed: {msg}"
    assert scheme is not None
    assert scheme.name == "TEST-STANDARD-IMPORT"
    assert scheme.region == "GLOBAL"
    assert scheme.is_built_in == True

    # Verify controls were imported
    requirements = test_db.query(AuditRequirement).filter(
        AuditRequirement.scheme_id == scheme.id
    ).all()
    assert len(requirements) == 2
    assert requirements[0].control_id == "TEST-001"
    assert requirements[0].name == "Access Control"
    assert requirements[1].control_id == "TEST-002"
    # Verify that "requirement" field is used as name
    assert requirements[1].name == "Data Protection"


def test_standards_list_available(test_db: Session):
    """Test listing available standards"""
    # Import a test standard
    test_standard = {
        "standard": "ISO-TEST",
        "controls": [
            {"id": "ISO-001", "name": "Test Control"}
        ]
    }
    StandardsService.import_standard_from_json(test_db, test_standard)

    # List standards
    standards = StandardsService.list_available_standards(test_db)

    assert len(standards) == 1
    assert standards[0]["name"] == "ISO-TEST"
    assert standards[0]["control_count"] == 1
    assert standards[0]["is_built_in"] == True


def test_standards_get_with_controls(test_db: Session):
    """Test retrieving standard with all controls"""
    test_standard = {
        "standard": "HIPAA-TEST",
        "full_name": "HIPAA Test Framework",
        "region": "US",
        "controls": [
            {
                "id": "HIPAA-001",
                "name": "Privacy Rule",
                "description": "Protect patient privacy",
                "severity": "CRITICAL"
            }
        ]
    }
    StandardsService.import_standard_from_json(test_db, test_standard)

    # Get standard by name
    standard = StandardsService.get_standard_with_controls(test_db, "HIPAA-TEST")

    assert standard is not None
    assert standard["name"] == "HIPAA-TEST"
    assert len(standard["controls"]) == 1
    assert standard["controls"][0]["id"] == "HIPAA-001"


def test_load_controls_from_db(test_db: Session):
    """Test loading controls from database using StandardsService"""
    test_standard = {
        "standard": "PCI-DSS-TEST",
        "controls": [
            {"id": "PCI-001", "name": "Network Segmentation"},
            {"id": "PCI-002", "name": "Access Control"}
        ]
    }
    StandardsService.import_standard_from_json(test_db, test_standard)

    # Load controls
    controls = StandardsService.load_controls(test_db, "PCI-DSS-TEST")

    assert len(controls) == 2
    assert controls[0]["id"] == "PCI-001"
    assert controls[0]["name"] == "Network Segmentation"
    assert controls[1]["id"] == "PCI-002"


def test_standards_filename_conversion():
    """Test conversion between standard names and filenames"""
    # Name to filename
    filename = StandardsService.standard_name_to_filename("ISO-27001")
    assert filename == "iso_27001.json"

    filename = StandardsService.standard_name_to_filename("EU-GDPR")
    assert filename == "eu_gdpr.json"

    # Filename to name
    name = StandardsService.filename_to_standard_name("iso_27001.json")
    assert name == "ISO-27001"

    name = StandardsService.filename_to_standard_name("eu_gdpr.json")
    assert name == "EU-GDPR"


def test_standards_with_requirement_field(test_db: Session):
    """Test that 'requirement' field is properly used as 'name'"""
    # Test standard with 'requirement' instead of 'name'
    test_standard = {
        "standard": "GDPR-PARTIAL",
        "controls": [
            {
                "id": "GDPR-001",
                "requirement": "Lawfulness, Fairness, and Transparency",
                "description": "Article 5 compliance"
            }
        ]
    }

    success, msg, scheme = StandardsService.import_standard_from_json(test_db, test_standard)

    assert success
    requirements = test_db.query(AuditRequirement).filter(
        AuditRequirement.scheme_id == scheme.id
    ).all()

    assert len(requirements) == 1
    # 'requirement' should be used as 'name'
    assert requirements[0].name == "Lawfulness, Fairness, and Transparency"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
