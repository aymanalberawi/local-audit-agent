import sys
import os

# Ensure /app is in the path for imports
sys.path.insert(0, '/app')
os.chdir('/app')

from celery import Celery
from core.config import settings
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

celery_app = Celery(
    "audit_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL
)

celery_app.conf.task_routes = {
    "worker.run_audit_job": "main-queue",
    "worker.check_and_execute_schedules": "scheduler-queue"
}

# Configure worker to listen to multiple queues
from kombu import Queue, Exchange

celery_app.conf.task_queues = (
    Queue('celery', Exchange('celery'), routing_key='celery'),
    Queue('main-queue', Exchange('main-queue'), routing_key='main-queue'),
    Queue('scheduler-queue', Exchange('scheduler-queue'), routing_key='scheduler-queue'),
)

try:
    from beat_config import CELERY_BEAT_SCHEDULE
    celery_app.conf.beat_schedule = CELERY_BEAT_SCHEDULE
except Exception as e:
    logger.warning(f"Could not load beat schedule: {e}")


@celery_app.task(name="worker.run_audit_job", bind=True)
def run_audit_job(
    self,
    job_id: int,
    connection_id: int = None,
    schema_name: str = "GDPR-UAE",
    data: list = None,
    file_path: str = None,
    uploaded_file_id: str = None,
    resume_from_stage: str = None,
    resume_from_job_id: int = None
):
    """
    Background task to run a full two-phase agentic audit.

    If connection_id is provided → runs full two-phase audit (discovery + audit).
    If file_path or uploaded_file_id is provided → runs audit against file data.
    If data is provided (legacy) → runs phase 2 only against provided data.
    If resume_from_stage is provided → resumes from that stage, skipping completed work.
    """
    if file_path or uploaded_file_id:
        # File-based audit
        from services.audit_engine import run_file_audit
        self.update_state(state='PROGRESS', meta={'phase': 'starting', 'current': 0})
        findings_count = run_file_audit(job_id, file_path, uploaded_file_id, schema_name, celery_task=self)
        return {"status": "COMPLETED", "findings_count": findings_count}
    elif connection_id is not None:
        # Full agentic audit using real connection (possibly with resume)
        from services.audit_engine import run_full_audit
        self.update_state(state='PROGRESS', meta={'phase': 'starting', 'current': 0})
        findings_count = run_full_audit(
            job_id,
            connection_id,
            schema_name,
            celery_task=self,
            resume_from_stage=resume_from_stage,
            resume_from_job_id=resume_from_job_id
        )
        return {"status": "COMPLETED", "findings_count": findings_count}
    else:
        # Legacy: run against provided data list
        from services.audit_engine import process_audit_batch
        self.update_state(state='PROGRESS', meta={'current': 0, 'total': len(data or [])})
        findings = process_audit_batch(job_id, schema_name, data or [], self)
        return {"status": "COMPLETED", "findings_count": len(findings)}


@celery_app.task(name="worker.check_and_execute_schedules")
def check_and_execute_schedules():
    """Periodic task to check and execute due schedules. Runs every 5 minutes."""
    from core.database import SessionLocal
    from models.schedule import Schedule
    from services.scheduler_service import SchedulerService

    db = SessionLocal()
    try:
        due_schedules = SchedulerService.get_due_schedules(db)
        executed_count = 0
        for schedule in due_schedules:
            try:
                task_id = SchedulerService.execute_schedule(db, schedule)
                if task_id:
                    executed_count += 1
                    logger.info(f"Executed schedule {schedule.id}, task_id: {task_id}")
            except Exception as e:
                logger.error(f"Error executing schedule {schedule.id}: {str(e)}")

        logger.info(f"Schedule check complete. Executed {executed_count} schedules.")
        return {"executed": executed_count, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error in check_and_execute_schedules: {str(e)}")
        return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    finally:
        db.close()


@celery_app.task(name="worker.cleanup_old_audits")
def cleanup_old_audits(days: int = 90):
    """Periodic task to cleanup old completed audits. Runs daily at 2AM."""
    from core.database import SessionLocal
    from models.audit import AuditJob
    from datetime import timedelta

    db = SessionLocal()
    try:
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        deleted_count = db.query(AuditJob).filter(
            AuditJob.status == "COMPLETED",
            AuditJob.created_at < cutoff_date
        ).delete()
        db.commit()
        logger.info(f"Cleanup complete. Deleted {deleted_count} old audits.")
        return {"deleted": deleted_count, "timestamp": datetime.utcnow().isoformat()}
    except Exception as e:
        logger.error(f"Error in cleanup_old_audits: {str(e)}")
        return {"error": str(e), "timestamp": datetime.utcnow().isoformat()}
    finally:
        db.close()
