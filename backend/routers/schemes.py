"""
Routes for managing audit schemes and requirements
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from core.database import get_db
from core.authorization import get_current_user_full
from models.user import User
from models.audit_scheme import AuditScheme, AuditRequirement

router = APIRouter(prefix="/schemes", tags=["Audit Schemes"])


# Pydantic Schemas
class RequirementCreate(BaseModel):
    control_id: str
    name: str
    description: Optional[str] = None
    severity: str = "MEDIUM"
    data_sources: Optional[str] = None
    query_template: Optional[str] = None


class RequirementUpdate(BaseModel):
    control_id: Optional[str] = None
    name: Optional[str] = None
    description: Optional[str] = None
    severity: Optional[str] = None
    data_sources: Optional[str] = None
    query_template: Optional[str] = None


class SchemeCreate(BaseModel):
    name: str
    description: Optional[str] = None
    version: Optional[str] = None


class SchemeUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None


# Endpoints
@router.post("/")
def create_scheme(
    scheme: SchemeCreate,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db),
):
    """Create a new audit scheme (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create schemes")

    # Check if scheme already exists
    existing = db.query(AuditScheme).filter(AuditScheme.name == scheme.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Scheme already exists")

    db_scheme = AuditScheme(
        name=scheme.name,
        description=scheme.description,
        version=scheme.version,
    )
    db.add(db_scheme)
    db.commit()
    db.refresh(db_scheme)

    return {
        "id": db_scheme.id,
        "name": db_scheme.name,
        "description": db_scheme.description,
        "version": db_scheme.version,
        "created_at": db_scheme.created_at,
    }


@router.get("/")
def list_schemes(
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db),
):
    """List all audit schemes"""
    schemes = db.query(AuditScheme).order_by(AuditScheme.name).all()

    return [
        {
            "id": s.id,
            "name": s.name,
            "description": s.description,
            "version": s.version,
            "requirement_count": len(s.requirements),
            "created_at": s.created_at,
        }
        for s in schemes
    ]


@router.get("/{scheme_id}")
def get_scheme(
    scheme_id: int,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db),
):
    """Get a specific scheme with all its requirements"""
    scheme = db.query(AuditScheme).filter(AuditScheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    return {
        "id": scheme.id,
        "name": scheme.name,
        "description": scheme.description,
        "version": scheme.version,
        "requirements": [
            {
                "id": req.id,
                "control_id": req.control_id,
                "name": req.name,
                "description": req.description,
                "severity": req.severity,
                "data_sources": req.data_sources,
                "query_template": req.query_template,
                "created_at": req.created_at,
            }
            for req in scheme.requirements
        ],
        "created_at": scheme.created_at,
    }


@router.put("/{scheme_id}")
def update_scheme(
    scheme_id: int,
    scheme: SchemeUpdate,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db),
):
    """Update a scheme (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update schemes")

    db_scheme = db.query(AuditScheme).filter(AuditScheme.id == scheme_id).first()
    if not db_scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    if scheme.name:
        db_scheme.name = scheme.name
    if scheme.description is not None:
        db_scheme.description = scheme.description
    if scheme.version:
        db_scheme.version = scheme.version

    db.commit()
    db.refresh(db_scheme)

    return {
        "id": db_scheme.id,
        "name": db_scheme.name,
        "description": db_scheme.description,
        "version": db_scheme.version,
        "created_at": db_scheme.created_at,
    }


@router.delete("/{scheme_id}")
def delete_scheme(
    scheme_id: int,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db),
):
    """Delete a scheme (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete schemes")

    scheme = db.query(AuditScheme).filter(AuditScheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    db.delete(scheme)
    db.commit()

    return {"message": "Scheme deleted successfully"}


# Requirement Endpoints
@router.post("/{scheme_id}/requirements")
def create_requirement(
    scheme_id: int,
    requirement: RequirementCreate,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db),
):
    """Add a requirement to a scheme (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can create requirements")

    scheme = db.query(AuditScheme).filter(AuditScheme.id == scheme_id).first()
    if not scheme:
        raise HTTPException(status_code=404, detail="Scheme not found")

    db_req = AuditRequirement(
        scheme_id=scheme_id,
        control_id=requirement.control_id,
        name=requirement.name,
        description=requirement.description,
        severity=requirement.severity,
        data_sources=requirement.data_sources,
        query_template=requirement.query_template,
    )
    db.add(db_req)
    db.commit()
    db.refresh(db_req)

    return {
        "id": db_req.id,
        "control_id": db_req.control_id,
        "name": db_req.name,
        "description": db_req.description,
        "severity": db_req.severity,
        "created_at": db_req.created_at,
    }


@router.put("/{scheme_id}/requirements/{req_id}")
def update_requirement(
    scheme_id: int,
    req_id: int,
    requirement: RequirementUpdate,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db),
):
    """Update a requirement (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can update requirements")

    req = db.query(AuditRequirement).filter(
        AuditRequirement.id == req_id,
        AuditRequirement.scheme_id == scheme_id,
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    if requirement.control_id:
        req.control_id = requirement.control_id
    if requirement.name:
        req.name = requirement.name
    if requirement.description is not None:
        req.description = requirement.description
    if requirement.severity:
        req.severity = requirement.severity
    if requirement.data_sources is not None:
        req.data_sources = requirement.data_sources
    if requirement.query_template is not None:
        req.query_template = requirement.query_template

    db.commit()
    db.refresh(req)

    return {
        "id": req.id,
        "control_id": req.control_id,
        "name": req.name,
        "description": req.description,
        "severity": req.severity,
        "created_at": req.created_at,
    }


@router.delete("/{scheme_id}/requirements/{req_id}")
def delete_requirement(
    scheme_id: int,
    req_id: int,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db),
):
    """Delete a requirement (admin only)"""
    if current_user.role != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete requirements")

    req = db.query(AuditRequirement).filter(
        AuditRequirement.id == req_id,
        AuditRequirement.scheme_id == scheme_id,
    ).first()
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    db.delete(req)
    db.commit()

    return {"message": "Requirement deleted successfully"}
