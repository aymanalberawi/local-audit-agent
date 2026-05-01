"""Standards management routes"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from core.database import get_db
from services.standards_service import StandardsService
from models.audit_scheme import AuditScheme, AuditRequirement

router = APIRouter(prefix="/standards", tags=["standards"])


@router.get("/", response_model=List[Dict[str, Any]])
async def list_standards(db: Session = Depends(get_db)):
    """List all available standards with metadata and control counts"""
    try:
        standards = StandardsService.list_available_standards(db)
        return standards
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to list standards: {str(e)}"
        )


@router.get("/{standard_id}", response_model=Dict[str, Any])
async def get_standard(standard_id: int, db: Session = Depends(get_db)):
    """Get a standard with all its controls"""
    try:
        scheme = db.query(AuditScheme).filter(AuditScheme.id == standard_id).first()
        if not scheme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Standard with ID {standard_id} not found"
            )

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
                    "data_sources": req.data_sources,
                    "query_template": req.query_template,
                }
                for req in scheme.requirements
            ],
            "created_at": scheme.created_at.isoformat() if scheme.created_at else None,
            "updated_at": scheme.updated_at.isoformat() if scheme.updated_at else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve standard: {str(e)}"
        )


@router.get("/by-name/{standard_name}", response_model=Dict[str, Any])
async def get_standard_by_name(standard_name: str, db: Session = Depends(get_db)):
    """Get a standard by name with all its controls"""
    try:
        standard = StandardsService.get_standard_with_controls(db, standard_name)
        if not standard:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Standard '{standard_name}' not found"
            )
        return standard
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve standard: {str(e)}"
        )


@router.post("/{standard_id}/sync/to-json", response_model=Dict[str, str])
async def sync_standard_to_json(standard_id: int, db: Session = Depends(get_db)):
    """Export a database standard back to JSON file"""
    try:
        success, message = StandardsService.export_standard_to_json(db, standard_id)
        if success:
            return {"status": "success", "message": message}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=message
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync standard to JSON: {str(e)}"
        )


@router.post("/{standard_id}/sync/from-json", response_model=Dict[str, str])
async def sync_standard_from_json(standard_id: int, db: Session = Depends(get_db)):
    """Reload a standard from its JSON file"""
    try:
        scheme = db.query(AuditScheme).filter(AuditScheme.id == standard_id).first()
        if not scheme:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Standard with ID {standard_id} not found"
            )

        if not scheme.source_file:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This standard does not have a source JSON file"
            )

        # Load the JSON file
        json_data = StandardsService.load_json_standard(scheme.source_file)
        if not json_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Could not load JSON file: {scheme.source_file}"
            )

        # Validate and reimport
        is_valid, error_msg = StandardsService.validate_standard_json(json_data)
        if not is_valid:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"JSON validation failed: {error_msg}"
            )

        # Reimport (will update existing scheme)
        success, msg, _ = StandardsService.import_standard_from_json(
            db, json_data, source_file=scheme.source_file
        )
        if success:
            return {"status": "success", "message": f"Reloaded from {scheme.source_file}"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=msg
            )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to sync standard from JSON: {str(e)}"
        )


@router.post("/import/all", response_model=Dict[str, Any])
async def import_all_standards(db: Session = Depends(get_db)):
    """Import all JSON standards (used for initialization)"""
    try:
        stats = StandardsService.initialize_from_json(db)
        if stats["errors"]:
            return {
                "status": "partial",
                "imported": stats["imported"],
                "skipped": stats["skipped"],
                "errors": stats["errors"]
            }
        return {
            "status": "success",
            "imported": stats["imported"],
            "skipped": stats["skipped"],
            "errors": []
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import standards: {str(e)}"
        )
