"""
Scheduler Service - Manages recurring audit jobs using Celery Beat
"""
from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy.orm import Session
from models.schedule import Schedule
from models.hierarchy import Connection
from models.audit import AuditJob
from worker import celery_app
import logging

logger = logging.getLogger(__name__)


class SchedulerService:
    """Service for managing recurring audit schedules"""

    @staticmethod
    def create_schedule(
        db: Session,
        connection_id: int,
        standard: str,
        frequency: str,  # "daily", "weekly", "monthly"
        company_id: int
    ) -> Schedule:
        """Create a new recurring audit schedule"""

        # Calculate next run time based on frequency
        now = datetime.utcnow()
        if frequency == "daily":
            next_run = now + timedelta(days=1)
        elif frequency == "weekly":
            next_run = now + timedelta(weeks=1)
        elif frequency == "monthly":
            next_run = now + timedelta(days=30)
        else:
            next_run = now + timedelta(days=1)

        schedule = Schedule(
            connection_id=connection_id,
            standard_name=standard,
            frequency=frequency,
            company_id=company_id,
            next_run_at=next_run,
            is_active=True,
            created_at=now
        )

        db.add(schedule)
        db.commit()
        db.refresh(schedule)

        logger.info(f"Created schedule {schedule.id} for connection {connection_id}")
        return schedule

    @staticmethod
    def get_due_schedules(db: Session) -> List[Schedule]:
        """Get all schedules that are due to run"""
        now = datetime.utcnow()
        due_schedules = db.query(Schedule).filter(
            Schedule.is_active == True,
            Schedule.next_run_at <= now
        ).all()
        return due_schedules

    @staticmethod
    def execute_schedule(db: Session, schedule: Schedule) -> str:
        """Execute a schedule and create an audit job"""
        try:
            # Get the connection
            connection = db.query(Connection).filter(
                Connection.id == schedule.connection_id
            ).first()

            if not connection:
                logger.error(f"Connection {schedule.connection_id} not found")
                schedule.last_error = "Connection not found"
                db.commit()
                return None

            # Create audit job
            audit_job = AuditJob(
                connection_id=schedule.connection_id,
                standard_name=schedule.standard_name,
                status="PENDING",
                company_id=schedule.company_id,
                scheduled_from=schedule.id
            )

            db.add(audit_job)
            db.commit()
            db.refresh(audit_job)

            # Queue the audit task
            task = celery_app.send_task(
                'worker.run_audit_job',
                args=[audit_job.id, schedule.connection_id],
                kwargs={
                    'schema_name': schedule.standard_name
                }
            )


            # Update schedule
            schedule.last_run_at = datetime.utcnow()
            schedule.last_task_id = task.id
            schedule.last_error = None

            # Calculate next run time
            if schedule.frequency == "daily":
                schedule.next_run_at = schedule.last_run_at + timedelta(days=1)
            elif schedule.frequency == "weekly":
                schedule.next_run_at = schedule.last_run_at + timedelta(weeks=1)
            elif schedule.frequency == "monthly":
                schedule.next_run_at = schedule.last_run_at + timedelta(days=30)

            db.commit()

            logger.info(f"Executed schedule {schedule.id}, created audit job {audit_job.id}")
            return task.id

        except Exception as e:
            logger.error(f"Error executing schedule {schedule.id}: {str(e)}")
            schedule.last_error = str(e)
            db.commit()
            return None

    @staticmethod
    def update_schedule(
        db: Session,
        schedule_id: int,
        frequency: Optional[str] = None,
        is_active: Optional[bool] = None
    ) -> Schedule:
        """Update an existing schedule"""
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()

        if not schedule:
            raise ValueError(f"Schedule {schedule_id} not found")

        if frequency:
            schedule.frequency = frequency
        if is_active is not None:
            schedule.is_active = is_active

        db.commit()
        db.refresh(schedule)

        logger.info(f"Updated schedule {schedule_id}")
        return schedule

    @staticmethod
    def delete_schedule(db: Session, schedule_id: int) -> bool:
        """Delete a schedule"""
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()

        if not schedule:
            return False

        db.delete(schedule)
        db.commit()

        logger.info(f"Deleted schedule {schedule_id}")
        return True

    @staticmethod
    def list_schedules(db: Session, company_id: int) -> List[Schedule]:
        """List all schedules for a company"""
        schedules = db.query(Schedule).filter(
            Schedule.company_id == company_id
        ).all()
        return schedules

    @staticmethod
    def get_schedule_status(db: Session, schedule_id: int) -> dict:
        """Get detailed status of a schedule"""
        schedule = db.query(Schedule).filter(Schedule.id == schedule_id).first()

        if not schedule:
            return None

        return {
            "id": schedule.id,
            "connection_id": schedule.connection_id,
            "standard_name": schedule.standard_name,
            "frequency": schedule.frequency,
            "is_active": schedule.is_active,
            "next_run_at": schedule.next_run_at,
            "last_run_at": schedule.last_run_at,
            "last_task_id": schedule.last_task_id,
            "last_error": schedule.last_error,
            "created_at": schedule.created_at
        }
