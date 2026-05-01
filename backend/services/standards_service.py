"""
Standards Management Service
Handles import/export of audit standards between JSON files and database
Provides unified interface for loading and managing standards
"""
import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy.orm import Session
from models.audit_scheme import AuditScheme, AuditRequirement, StandardVersion, StandardChangeLog
from datetime import datetime

logger = logging.getLogger(__name__)


class StandardsService:
    """
    Service for managing compliance standards
    Handles sync between JSON files and database records
    """

    # Standard locations (in order of preference)
    STANDARDS_PATHS = [
        Path("/standards"),  # Docker mount point
        Path(__file__).parent.parent.parent / "standards",  # Local development
    ]

    @staticmethod
    def find_standards_directory() -> Optional[Path]:
        """Find the standards directory"""
        for path in StandardsService.STANDARDS_PATHS:
            if path.exists() and path.is_dir():
                logger.info(f"Found standards directory: {path}")
                return path
        logger.warning("No standards directory found")
        return None

    @staticmethod
    def standard_name_to_filename(name: str) -> str:
        """
        Convert standard name to JSON filename
        Examples:
        - "ISO-27001" → "iso_27001.json"
        - "EU-GDPR" → "eu_gdpr.json"
        - "GDPR-UAE" → "gdpr_uae.json"
        """
        return f"{name.lower().replace('-', '_')}.json"

    @staticmethod
    def filename_to_standard_name(filename: str) -> str:
        """
        Convert JSON filename to standard name
        Examples:
        - "iso_27001.json" → "ISO-27001"
        - "eu_gdpr.json" → "EU-GDPR"
        """
        name_part = filename.replace(".json", "")
        # Convert underscores to hyphens and uppercase
        words = name_part.split("_")
        return "-".join(w.upper() for w in words)

    @staticmethod
    def load_json_standard(filename: str) -> Optional[Dict[str, Any]]:
        """
        Load a standard from JSON file
        Returns the full JSON content if found, None otherwise
        """
        standards_dir = StandardsService.find_standards_directory()
        if not standards_dir:
            return None

        filepath = standards_dir / filename
        if not filepath.exists():
            logger.warning(f"Standard file not found: {filepath}")
            return None

        try:
            with open(filepath, "r") as f:
                data = json.load(f)
                logger.info(f"Loaded standard from {filepath}")
                return data
        except Exception as e:
            logger.error(f"Failed to load standard from {filepath}: {e}")
            return None

    @staticmethod
    def save_json_standard(filename: str, data: Dict[str, Any]) -> bool:
        """
        Save a standard to JSON file
        Creates/overwrites the file
        Returns True if successful, False otherwise
        """
        standards_dir = StandardsService.find_standards_directory()
        if not standards_dir:
            logger.error("Cannot save standard: no standards directory found")
            return False

        filepath = standards_dir / filename
        try:
            # Pretty-print JSON with 2-space indentation
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved standard to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save standard to {filepath}: {e}")
            return False

    @staticmethod
    def validate_standard_json(json_data: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate JSON standard structure
        Returns (is_valid, error_message)
        """
        if not isinstance(json_data, dict):
            return False, "Standard must be a JSON object"

        if "standard" not in json_data:
            return False, "Missing 'standard' field"

        if "controls" not in json_data:
            return False, "Missing 'controls' field"

        if not isinstance(json_data["controls"], list):
            return False, "'controls' must be an array"

        # Validate each control
        for idx, control in enumerate(json_data["controls"]):
            if not isinstance(control, dict):
                return False, f"Control {idx} is not an object"

            # Accept either "name" or "requirement" field for control name
            if "id" not in control:
                return False, f"Control {idx} missing 'id'"

            if "name" not in control and "requirement" not in control:
                return False, f"Control {idx} missing 'name' or 'requirement'"

        return True, ""

    @staticmethod
    def import_standard_from_json(
        db: Session,
        json_data: Dict[str, Any],
        source_file: Optional[str] = None,
        user_id: Optional[int] = None,
    ) -> Tuple[bool, str, Optional[AuditScheme]]:
        """
        Import a standard from JSON data into the database
        Creates AuditScheme + AuditRequirement records
        Creates initial StandardVersion record
        Returns (success, message, scheme_or_none)
        """
        # Validate JSON structure
        is_valid, error_msg = StandardsService.validate_standard_json(json_data)
        if not is_valid:
            return False, error_msg, None

        try:
            standard_name = json_data["standard"]

            # Check if standard already exists
            existing = db.query(AuditScheme).filter(AuditScheme.name == standard_name).first()
            if existing:
                logger.info(f"Standard '{standard_name}' already exists, updating...")
                scheme = existing
            else:
                # Create new scheme
                scheme = AuditScheme(
                    name=standard_name,
                    description=json_data.get("full_name", ""),
                    version="1.0",
                    region=json_data.get("region"),
                    authority=json_data.get("authority"),
                    is_built_in=True,
                    source_file=source_file,
                )
                db.add(scheme)
                db.flush()  # Get scheme.id before adding requirements

            # Add/update requirements
            # First, clear existing requirements if updating
            if existing:
                db.query(AuditRequirement).filter(AuditRequirement.scheme_id == scheme.id).delete()
                db.flush()

            controls = json_data.get("controls", [])
            for control in controls:
                req = AuditRequirement(
                    scheme_id=scheme.id,
                    control_id=control["id"],
                    name=control.get("name", control.get("requirement", "")),
                    description=control.get("description", ""),
                    severity=control.get("severity", "MEDIUM"),
                    data_sources=control.get("data_sources"),
                    # Store the logic/requirement as query_template
                    query_template=control.get("logic", control.get("requirement", "")),
                )
                db.add(req)

            # Create StandardVersion record
            version = StandardVersion(
                scheme_id=scheme.id,
                version_number="1.0",
                source="json",
                source_file=source_file,
                created_by_user_id=user_id,
            )
            db.add(version)

            db.commit()
            logger.info(f"Successfully imported standard '{standard_name}' with {len(controls)} controls")
            return True, f"Imported {len(controls)} controls", scheme

        except Exception as e:
            db.rollback()
            logger.error(f"Failed to import standard: {e}")
            return False, str(e), None

    @staticmethod
    def initialize_from_json(db: Session, user_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Initialize database with all standards from JSON files
        Only imports if no standards exist in database
        Returns statistics: {imported: int, skipped: int, errors: list}
        """
        # Check if standards already exist
        existing_count = db.query(AuditScheme).count()
        if existing_count > 0:
            logger.info(f"Standards already exist in database ({existing_count}), skipping import")
            return {"imported": 0, "skipped": existing_count, "errors": []}

        standards_dir = StandardsService.find_standards_directory()
        if not standards_dir:
            logger.error("Cannot initialize: no standards directory found")
            return {"imported": 0, "skipped": 0, "errors": ["No standards directory found"]}

        stats = {"imported": 0, "skipped": 0, "errors": []}

        # Load all JSON files from standards directory
        json_files = sorted(standards_dir.glob("*.json"))
        logger.info(f"Found {len(json_files)} standard files to import")

        for json_file in json_files:
            try:
                json_data = StandardsService.load_json_standard(json_file.name)
                if not json_data:
                    stats["errors"].append(f"Failed to load {json_file.name}")
                    continue

                success, msg, scheme = StandardsService.import_standard_from_json(
                    db, json_data, source_file=json_file.name, user_id=user_id
                )

                if success:
                    stats["imported"] += 1
                    logger.info(f"✓ Imported {json_file.name}")
                else:
                    stats["errors"].append(f"{json_file.name}: {msg}")
                    logger.warning(f"✗ Failed to import {json_file.name}: {msg}")

            except Exception as e:
                stats["errors"].append(f"{json_file.name}: {str(e)}")
                logger.error(f"Error importing {json_file.name}: {e}")

        logger.info(f"Import complete: {stats['imported']} imported, {len(stats['errors'])} errors")
        return stats

    @staticmethod
    def export_standard_to_json(db: Session, scheme_id: int) -> Tuple[bool, str]:
        """
        Export a database standard to JSON file
        Creates/updates the corresponding JSON file
        Returns (success, message)
        """
        try:
            scheme = db.query(AuditScheme).filter(AuditScheme.id == scheme_id).first()
            if not scheme:
                return False, f"Standard with id {scheme_id} not found"

            # Build JSON structure
            json_data = {
                "standard": scheme.name,
                "full_name": scheme.description or scheme.name,
                "version": scheme.version or "1.0",
                "region": scheme.region or "GLOBAL",
                "authority": scheme.authority or "Unknown",
                "controls": [
                    {
                        "id": req.control_id,
                        "name": req.name,
                        "domain": req.description,  # Use description as domain
                        "requirement": req.name,
                        "description": req.description or "",
                        "logic": req.query_template or "",
                        "severity": req.severity,
                        "data_sources": req.data_sources,
                    }
                    for req in scheme.requirements
                ],
            }

            # Determine filename
            filename = StandardsService.standard_name_to_filename(scheme.name)

            # Save to JSON
            success = StandardsService.save_json_standard(filename, json_data)
            if success:
                logger.info(f"Exported standard '{scheme.name}' to {filename}")
                return True, f"Exported to {filename}"
            else:
                return False, "Failed to write JSON file"

        except Exception as e:
            logger.error(f"Failed to export standard {scheme_id}: {e}")
            return False, str(e)

    @staticmethod
    def list_available_standards(db: Session) -> List[Dict[str, Any]]:
        """
        List all available standards from database
        Returns list of standard metadata with control counts
        """
        schemes = db.query(AuditScheme).order_by(AuditScheme.name).all()

        return [
            {
                "id": s.id,
                "name": s.name,
                "version": s.version,
                "region": s.region,
                "authority": s.authority,
                "is_built_in": s.is_built_in,
                "control_count": len(s.requirements),
                "created_at": s.created_at.isoformat() if s.created_at else None,
                "updated_at": s.updated_at.isoformat() if s.updated_at else None,
            }
            for s in schemes
        ]

    @staticmethod
    def get_standard_with_controls(db: Session, standard_name: str) -> Optional[Dict[str, Any]]:
        """
        Get standard with all controls by name
        Returns full standard data or None if not found
        """
        scheme = db.query(AuditScheme).filter(AuditScheme.name == standard_name).first()
        if not scheme:
            return None

        return {
            "id": scheme.id,
            "name": scheme.name,
            "version": scheme.version,
            "region": scheme.region,
            "authority": scheme.authority,
            "is_built_in": scheme.is_built_in,
            "controls": [
                {
                    "id": req.control_id,
                    "name": req.name,
                    "description": req.description,
                    "severity": req.severity,
                    "domain": req.description,  # Same as description for compatibility
                    "requirement": req.name,
                    "logic": req.query_template,
                    "data_sources": req.data_sources,
                }
                for req in scheme.requirements
            ],
            "created_at": scheme.created_at.isoformat() if scheme.created_at else None,
            "updated_at": scheme.updated_at.isoformat() if scheme.updated_at else None,
        }

    @staticmethod
    def load_controls(db: Session, standard_name: str) -> List[Dict[str, Any]]:
        """
        Load controls from database for a standard by name
        Replaces the direct JSON loader from audit_engine.py
        Returns same format as before for backward compatibility
        """
        standard = StandardsService.get_standard_with_controls(db, standard_name)
        if not standard:
            logger.warning(f"Standard '{standard_name}' not found in database")
            return []

        controls = standard.get("controls", [])
        logger.info(f"Loaded {len(controls)} controls for standard '{standard_name}' from database")
        return controls
