"""
Scheduler Routes - API endpoints for managing recurring audits
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from core.database import get_db
from core.security import get_current_user_with_db
from core.authorization import require_role, check_company_access
from models.schedule import Schedule
from models.hierarchy import Company
from services.scheduler_service import SchedulerService
from pydantic import BaseModel

router = APIRouter(prefix="/schedule", tags=["scheduler"])


# Pydantic models for request/response
class ScheduleCreate(BaseModel):
    connection_id: int
    standard_name: str
    frequency: str  # "daily", "weekly", "monthly"


class ScheduleUpdate(BaseModel):
    frequency: str = None
    is_active: bool = None


class ScheduleResponse(BaseModel):
    id: int
    connection_id: int
    standard_name: str
    frequency: str
    is_active: bool
    next_run_at: datetime
    last_run_at: datetime = None
    last_task_id: str = None
    last_error: str = None
    created_at: datetime

    class Config:
        from_attributes = True


@router.post("/create", response_model=ScheduleResponse)
async def create_schedule(
    schedule_data: ScheduleCreate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_with_db)
):
    """Create a new recurring audit schedule"""

    # Check that user has access to the connection's company
    from models.hierarchy import Connection
    connection = db.query(Connection).filter(
        Connection.id == schedule_data.connection_id
    ).first()

    if not connection:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connection not found"
        )

    # Verify user has access to this company
    if connection.application.company_id != current_user["company_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this connection"
        )


    # Create schedule
    try:
        schedule = SchedulerService.create_schedule(
            db=db,
            connection_id=schedule_data.connection_id,
            standard=schedule_data.standard_name,
            frequency=schedule_data.frequency,
            company_id=current_user["company_id"]
        )
        return schedule
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/list", response_model=List[ScheduleResponse])
async def list_schedules(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_with_db)
):
    """List all schedules for the current user's company"""

    schedules = SchedulerService.list_schedules(
        db=db,
        company_id=current_user["company_id"]
    )
    return schedules


@router.get("/{schedule_id}", response_model=ScheduleResponse)
async def get_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_with_db)
):
    """Get a specific schedule"""

    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    # Check authorization
    if schedule.company_id != current_user["company_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this schedule"
        )

    return schedule


@router.put("/{schedule_id}", response_model=ScheduleResponse)
async def update_schedule(
    schedule_id: int,
    schedule_data: ScheduleUpdate,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_with_db)
):
    """Update a schedule"""

    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    # Check authorization
    if schedule.company_id != current_user["company_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this schedule"
        )

    # Update schedule
    try:
        updated_schedule = SchedulerService.update_schedule(
            db=db,
            schedule_id=schedule_id,
            frequency=schedule_data.frequency,
            is_active=schedule_data.is_active
        )
        return updated_schedule
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.delete("/{schedule_id}")
async def delete_schedule(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_with_db)
):
    """Delete a schedule"""

    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    # Check authorization
    if schedule.company_id != current_user["company_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this schedule"
        )

    # Delete schedule
    SchedulerService.delete_schedule(db=db, schedule_id=schedule_id)

    return {"message": "Schedule deleted successfully"}


@router.post("/{schedule_id}/execute")
async def execute_schedule_now(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_with_db)
):
    """Execute a schedule immediately (for testing)"""

    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    # Check authorization
    if schedule.company_id != current_user["company_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to execute this schedule"
        )

    # Execute schedule
    try:
        task_id = SchedulerService.execute_schedule(db=db, schedule=schedule)
        if task_id:
            return {"message": "Schedule executed", "task_id": task_id}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to execute schedule"
            )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/{schedule_id}/status")
async def get_schedule_status(
    schedule_id: int,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user_with_db)
):
    """Get detailed status of a schedule"""

    schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()

    if not schedule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Schedule not found"
        )

    # Check authorization
    if schedule.company_id != current_user["company_id"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this schedule"
        )

    status_info = SchedulerService.get_schedule_status(db=db, schedule_id=schedule_id)
    return status_info
