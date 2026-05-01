from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime, timezone
from core.database import get_db
from core.authorization import get_current_user_full, check_company_access
from models.hierarchy import Company, ApplicationInstance, Connection, ConnectionType, ConnectionStatus
from models.schedule import Schedule
from models.audit import AuditJob
from models.user import User
from services.connection_tester import test_connection

router = APIRouter(prefix="/hierarchy", tags=["Hierarchy"])

# --- Pydantic Schemas ---
class CompanyCreate(BaseModel):
    name: str

class CompanyUpdate(BaseModel):
    name: Optional[str] = None

class AppCreate(BaseModel):
    name: str
    company_id: int

class AppUpdate(BaseModel):
    name: Optional[str] = None

class ConnectionCreate(BaseModel):
    name: str
    type: ConnectionType
    application_id: int
    connection_string: Optional[str] = None

class ConnectionUpdate(BaseModel):
    name: Optional[str] = None
    type: Optional[ConnectionType] = None
    connection_string: Optional[str] = None

class ScheduleCreate(BaseModel):
    connection_id: int
    frequency: str
    target_schema: str

# --- Endpoints ---

@router.post("/companies")
def create_company(comp: CompanyCreate, current_user: User = Depends(get_current_user_full), db: Session = Depends(get_db)):
    # Only admins can create companies
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create companies"
        )
    db_comp = Company(name=comp.name)
    db.add(db_comp)
    db.commit()
    db.refresh(db_comp)
    return db_comp

@router.get("/companies")
def get_companies(current_user: User = Depends(get_current_user_full), db: Session = Depends(get_db)):
    # Admins see all companies, others see only their company
    if current_user.role == "admin":
        return db.query(Company).all()
    return [db.query(Company).filter(Company.id == current_user.company_id).first()]

@router.get("/companies/{company_id}")
def get_company(company_id: int, current_user: User = Depends(get_current_user_full), db: Session = Depends(get_db)):
    # Check authorization
    check_company_access(current_user.id, company_id, db)

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    return company

@router.put("/companies/{company_id}")
def update_company(company_id: int, data: CompanyUpdate, current_user: User = Depends(get_current_user_full), db: Session = Depends(get_db)):
    # Only admins can update companies
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update companies"
        )

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if data.name:
        company.name = data.name

    db.commit()
    db.refresh(company)
    return company

@router.delete("/companies/{company_id}")
def delete_company(company_id: int, current_user: User = Depends(get_current_user_full), db: Session = Depends(get_db)):
    # Only admins can delete companies
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete companies"
        )

    company = db.query(Company).filter(Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    db.delete(company)
    db.commit()

    return {"message": "Company deleted successfully"}

@router.post("/applications")
def create_application(app: AppCreate, current_user: User = Depends(get_current_user_full), db: Session = Depends(get_db)):
    # Check if user has access to the company
    check_company_access(current_user.id, app.company_id, db)

    db_app = ApplicationInstance(name=app.name, company_id=app.company_id)
    db.add(db_app)
    db.commit()
    db.refresh(db_app)
    return db_app

@router.get("/companies/{company_id}/applications")
def get_applications(company_id: int, current_user: User = Depends(get_current_user_full), db: Session = Depends(get_db)):
    # Check if user has access to the company
    check_company_access(current_user.id, company_id, db)

    return db.query(ApplicationInstance).filter(ApplicationInstance.company_id == company_id).all()

@router.get("/applications/{app_id}")
def get_application(app_id: int, current_user: User = Depends(get_current_user_full), db: Session = Depends(get_db)):
    app = db.query(ApplicationInstance).filter(ApplicationInstance.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Check authorization
    check_company_access(current_user.id, app.company_id, db)

    return app

@router.put("/applications/{app_id}")
def update_application(app_id: int, data: AppUpdate, current_user: User = Depends(get_current_user_full), db: Session = Depends(get_db)):
    app = db.query(ApplicationInstance).filter(ApplicationInstance.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Check authorization
    check_company_access(current_user.id, app.company_id, db)

    if data.name:
        app.name = data.name

    db.commit()
    db.refresh(app)
    return app

@router.delete("/applications/{app_id}")
def delete_application(app_id: int, current_user: User = Depends(get_current_user_full), db: Session = Depends(get_db)):
    app = db.query(ApplicationInstance).filter(ApplicationInstance.id == app_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    # Check authorization
    check_company_access(current_user.id, app.company_id, db)

    db.delete(app)
    db.commit()

    return {"message": "Application deleted successfully"}

@router.post("/connections")
def create_connection(conn: ConnectionCreate, current_user: User = Depends(get_current_user_full), db: Session = Depends(get_db)):
    # Get the application and check company access
    app = db.query(ApplicationInstance).filter(ApplicationInstance.id == conn.application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    check_company_access(current_user.id, app.company_id, db)

    # Test the connection
    status, message = test_connection(conn.type.value, conn.connection_string or "")

    db_conn = Connection(
        name=conn.name,
        type=conn.type,
        application_id=conn.application_id,
        connection_string=conn.connection_string,
        status=status,
        status_message=message if status == ConnectionStatus.FAILED else None,
        last_tested_at=datetime.now(timezone.utc)
    )
    db.add(db_conn)
    db.commit()
    db.refresh(db_conn)
    return db_conn

@router.get("/connections")
def get_connections(current_user: User = Depends(get_current_user_full), db: Session = Depends(get_db)):
    # Returns connections along with the status of their last audit
    # Filter by company if not admin
    if current_user.role == "admin":
        connections = db.query(Connection).all()
    else:
        # Get connections only from user's company
        connections = db.query(Connection).join(
            ApplicationInstance, Connection.application_id == ApplicationInstance.id
        ).filter(ApplicationInstance.company_id == current_user.company_id).all()

    results = []
    for c in connections:
        last_audit = db.query(AuditJob).filter(AuditJob.connection_id == c.id).order_by(AuditJob.created_at.desc()).first()
        results.append({
            "id": c.id,
            "name": c.name,
            "type": c.type.value if isinstance(c.type, ConnectionType) else c.type,
            "application_id": c.application_id,
            "application_name": c.application.name,
            "company_name": c.application.company.name,
            "connection_string": c.connection_string,
            "last_audit_status": last_audit.status if last_audit else "Not Setup",
            "last_audit_time": last_audit.created_at if last_audit else None,
            "connection_status": c.status.value if isinstance(c.status, ConnectionStatus) else c.status,
            "status_message": c.status_message,
            "last_tested_at": c.last_tested_at
        })
    return results

@router.get("/connections/{conn_id}")
def get_connection(conn_id: int, current_user: User = Depends(get_current_user_full), db: Session = Depends(get_db)):
    conn = db.query(Connection).filter(Connection.id == conn_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Check authorization
    check_company_access(current_user.id, conn.application.company_id, db)

    return {
        "id": conn.id,
        "name": conn.name,
        "type": conn.type.value if isinstance(conn.type, ConnectionType) else conn.type,
        "application_id": conn.application_id,
        "application_name": conn.application.name,
        "company_name": conn.application.company.name,
        "connection_string": conn.connection_string,
        "created_at": conn.created_at,
        "connection_status": conn.status.value if isinstance(conn.status, ConnectionStatus) else conn.status,
        "status_message": conn.status_message,
        "last_tested_at": conn.last_tested_at
    }

@router.put("/connections/{conn_id}")
def update_connection(conn_id: int, data: ConnectionUpdate, current_user: User = Depends(get_current_user_full), db: Session = Depends(get_db)):
    conn = db.query(Connection).filter(Connection.id == conn_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Check authorization
    check_company_access(current_user.id, conn.application.company_id, db)

    if data.name:
        conn.name = data.name
    if data.type:
        conn.type = data.type
    if data.connection_string:
        conn.connection_string = data.connection_string

    db.commit()
    db.refresh(conn)
    return conn

@router.delete("/connections/{conn_id}")
def delete_connection(conn_id: int, current_user: User = Depends(get_current_user_full), db: Session = Depends(get_db)):
    conn = db.query(Connection).filter(Connection.id == conn_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Check authorization
    check_company_access(current_user.id, conn.application.company_id, db)

    db.delete(conn)
    db.commit()

    return {"message": "Connection deleted successfully"}

@router.post("/connections/{conn_id}/test")
def test_connection_endpoint(conn_id: int, current_user: User = Depends(get_current_user_full), db: Session = Depends(get_db)):
    """Test an existing connection and update its status"""
    conn = db.query(Connection).filter(Connection.id == conn_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    # Check authorization
    check_company_access(current_user.id, conn.application.company_id, db)

    # Test the connection
    status, message = test_connection(conn.type.value, conn.connection_string or "")

    # Update the connection with test results
    conn.status = status
    conn.status_message = message if status == ConnectionStatus.FAILED else None
    conn.last_tested_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(conn)

    return {
        "id": conn.id,
        "status": conn.status,
        "message": message,
        "last_tested_at": conn.last_tested_at
    }

@router.post("/schedules")
def create_schedule(sched: ScheduleCreate, current_user: User = Depends(get_current_user_full), db: Session = Depends(get_db)):
    # Get the connection and check company access
    conn = db.query(Connection).filter(Connection.id == sched.connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    check_company_access(current_user.id, conn.application.company_id, db)

    db_sched = Schedule(
        connection_id=sched.connection_id,
        frequency=sched.frequency,
        target_schema=sched.target_schema
    )
    db.add(db_sched)
    db.commit()
    db.refresh(db_sched)
    return db_sched

@router.get("/schedules")
def get_schedules(current_user: User = Depends(get_current_user_full), db: Session = Depends(get_db)):
    # Filter by company if not admin
    if current_user.role == "admin":
        schedules = db.query(Schedule).all()
    else:
        # Get schedules only from user's company
        schedules = db.query(Schedule).join(
            Connection, Schedule.connection_id == Connection.id
        ).join(
            ApplicationInstance, Connection.application_id == ApplicationInstance.id
        ).filter(ApplicationInstance.company_id == current_user.company_id).all()

    results = []
    for s in schedules:
        results.append({
            "id": s.id,
            "frequency": s.frequency,
            "target_schema": s.target_schema,
            "connection_name": s.connection.name,
            "application_name": s.connection.application.name,
            "company_name": s.connection.application.company.name
        })
    return results
