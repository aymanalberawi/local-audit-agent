from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
import os
import uuid
from core.database import get_db
from core.authorization import get_current_user_full
from models.user import User
from models.audit import AuditJob, Finding, AuditLog
from models.hierarchy import Connection, ApplicationInstance
from celery.result import AsyncResult
from services.delta_engine import compare_snapshots
from services.report_generator import AuditReportGenerator

logger = logging.getLogger(__name__)

# Lazy imports to prevent Celery/LLM loading at import time
def _get_celery_app():
    from worker import celery_app
    return celery_app

def _get_run_audit_job():
    from worker import run_audit_job
    return run_audit_job

router = APIRouter(prefix="/audit", tags=["Audit"])

# Temporary file upload directory
# Use /app/uploads which is in the mounted backend directory (guaranteed to be writable)
UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
if not os.path.exists(UPLOAD_DIR):
    try:
        os.makedirs(UPLOAD_DIR, exist_ok=True)
        logger.info(f"Created upload directory: {UPLOAD_DIR}")
    except Exception as e:
        logger.warning(f"Could not create upload directory: {e}, using /tmp fallback")
        UPLOAD_DIR = "/tmp/audit_uploads"
        os.makedirs(UPLOAD_DIR, exist_ok=True)


class AuditStartRequest(BaseModel):
    connection_id: int
    standard: str = "GDPR-UAE"
    file_path: Optional[str] = None
    uploaded_file_id: Optional[str] = None


@router.post("/upload")
async def upload_audit_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user_full)
):
    """Upload a CSV or Excel file for audit."""
    # Validate file type
    allowed_extensions = {'.csv', '.xlsx', '.xls'}
    file_ext = os.path.splitext(file.filename)[1].lower()

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"File type not allowed. Supported: {', '.join(allowed_extensions)}"
        )

    try:
        # Generate unique file ID
        file_id = str(uuid.uuid4())

        # Save file with user_id prefix for tracking
        safe_filename = f"{current_user.id}_{file_id}{file_ext}"
        file_path = os.path.join(UPLOAD_DIR, safe_filename)

        # Save file
        contents = await file.read()
        with open(file_path, 'wb') as f:
            f.write(contents)

        logger.info(f"File uploaded: {file_id} by user {current_user.id}")

        return {
            "success": True,
            "file_id": file_id,
            "filename": file.filename,
            "size": len(contents)
        }
    except Exception as e:
        logger.error(f"File upload error: {str(e)}")
        raise HTTPException(status_code=500, detail="File upload failed")


@router.post("/start")
async def start_audit_job(
    request: AuditStartRequest,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db)
):
    """Start a new two-phase agentic audit against a real connection."""
    # Validate connection exists and belongs to user's company
    conn = db.query(Connection).filter(Connection.id == request.connection_id).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Connection not found")

    app = db.query(ApplicationInstance).filter(ApplicationInstance.id == conn.application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if current_user.role != "admin" and app.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Access denied to this connection")

    # Create the audit job record
    new_job = AuditJob(
        connection_id=request.connection_id,
        standard_name=request.standard,
        status="PENDING",
        company_id=current_user.company_id
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Dispatch to Celery with real connection_id
    run_audit_job = _get_run_audit_job()

    # Build task arguments
    task_kwargs = {
        "job_id": new_job.id,
        "connection_id": request.connection_id,
        "schema_name": request.standard
    }

    # Add file parameter if provided
    if request.file_path:
        task_kwargs["file_path"] = request.file_path
    elif request.uploaded_file_id:
        task_kwargs["uploaded_file_id"] = request.uploaded_file_id

    task = run_audit_job.delay(**task_kwargs)

    return {
        "message": "Audit job started",
        "task_id": task.id,
        "job_id": new_job.id,
        "connection_id": request.connection_id,
        "standard": request.standard
    }


@router.get("/jobs")
async def list_audit_jobs(
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db)
):
    """List all real audit jobs for the current user's company."""
    if current_user.role == "admin":
        jobs = db.query(AuditJob).order_by(AuditJob.created_at.desc()).all()
    else:
        jobs = db.query(AuditJob).filter(
            AuditJob.company_id == current_user.company_id
        ).order_by(AuditJob.created_at.desc()).all()

    results = []
    for job in jobs:
        # Enrich with connection info
        conn = db.query(Connection).filter(Connection.id == job.connection_id).first()
        results.append({
            "id": job.id,
            "standard_name": job.standard_name,
            "status": job.status,
            "created_at": job.created_at.isoformat() if job.created_at else None,
            "connection_id": job.connection_id,
            "connection_name": conn.name if conn else None,
            "connection_type": conn.type.value if conn else None,
        })

    return results


@router.get("/jobs/{job_id}")
async def get_audit_job(
    job_id: int,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db)
):
    """Get details of a specific audit job."""
    job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found")

    if current_user.role != "admin" and job.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    return job


@router.get("/jobs/{job_id}/progress")
async def get_audit_progress(
    job_id: int,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db)
):
    """Get detailed progress information for an audit job."""
    job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found")

    if current_user.role != "admin" and job.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Define the stages in order - different paths for file audits vs full audits
    # Check if this is a file-based audit by looking at the current stage
    is_file_audit = job.current_stage in ["LOADING_FILE", "FAILED", "COMPLETED"]

    if is_file_audit:
        # File-based audit stages
        stages = [
            {"name": "PENDING", "label": "Pending", "description": "Waiting to start"},
            {"name": "LOADING_FILE", "label": "Loading File", "description": "Reading file data"},
            {"name": "AUDITING", "label": "Running Audits", "description": "Executing compliance checks"},
            {"name": "SAVING_RESULTS", "label": "Saving Results", "description": "Storing findings in database"},
            {"name": "COMPLETED", "label": "Completed", "description": "Audit finished successfully"},
        ]
    else:
        # Full audit stages (connection-based)
        stages = [
            {"name": "PENDING", "label": "Pending", "description": "Waiting to start"},
            {"name": "CHECKING_CACHE", "label": "Checking Cache", "description": "Checking vector memory for cached schema"},
            {"name": "DISCOVERING", "label": "Discovering Tables", "description": "Using LLM to identify relevant tables"},
            {"name": "LOADING_DATA", "label": "Loading Data", "description": "Fetching data from identified tables"},
            {"name": "AUDITING", "label": "Running Audits", "description": "Executing compliance checks against data"},
            {"name": "SAVING_RESULTS", "label": "Saving Results", "description": "Storing findings in database"},
            {"name": "COMPLETED", "label": "Completed", "description": "Audit finished successfully"},
        ]

    # Mark stages as completed, current, or pending
    current_stage_idx = next((i for i, s in enumerate(stages) if s["name"] == job.current_stage), -1)
    stages_with_status = []
    for i, stage in enumerate(stages):
        if i < current_stage_idx:
            status = "completed"
        elif i == current_stage_idx:
            status = "current"
        else:
            status = "pending"
        stages_with_status.append({**stage, "status": status})

    result = {
        "job_id": job.id,
        "status": job.status,
        "current_stage": job.current_stage,
        "progress_percentage": job.progress_percentage,
        "stage_details": job.stage_details,
        "started_at": job.started_at.isoformat() if job.started_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "stages": stages_with_status,
    }

    # Include error details if audit failed
    if job.error_message:
        result["error_message"] = job.error_message
    if job.error_type:
        result["error_type"] = job.error_type
    if job.is_retryable is not None:
        result["is_retryable"] = job.is_retryable
    if job.last_successful_stage:
        result["last_successful_stage"] = job.last_successful_stage

    return result


@router.get("/jobs/{job_id}/findings")
async def get_audit_findings(
    job_id: int,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db)
):
    """Get all real findings for a completed audit job."""
    job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found")

    if current_user.role != "admin" and job.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    findings = db.query(Finding).filter(Finding.job_id == job_id).all()

    return [
        {
            "id": f.id,
            "control_id": f.control_id,
            "issue_description": f.issue_description,
            "raw_data": f.raw_data,
            "created_at": f.created_at.isoformat() if f.created_at else None,
            "severity": _infer_severity(f.control_id),
        }
        for f in findings
    ]


def _infer_severity(control_id: str) -> str:
    """Map control IDs to severity levels based on naming convention."""
    cid = (control_id or "").upper()
    if cid.startswith("ACC") or cid.startswith("AUTH") or cid.startswith("PRIV"):
        return "CRITICAL"
    if cid.startswith("DLP") or cid.startswith("SEC") or cid.startswith("ENC"):
        return "HIGH"
    if cid.startswith("LOG") or cid.startswith("MON"):
        return "MEDIUM"
    return "LOW"


@router.get("/jobs/{job_id}/debug")
async def debug_audit_job(
    job_id: int,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db)
):
    """DEBUG ENDPOINT: Show detailed database info for a job (findings, logs, status)."""
    from models.audit import AuditLog

    job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found")

    if current_user.role != "admin" and job.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get all findings
    findings = db.query(Finding).filter(Finding.job_id == job_id).all()

    # Get all audit logs
    logs = db.query(AuditLog).filter(AuditLog.job_id == job_id).order_by(AuditLog.timestamp).all()

    return {
        "job_info": {
            "id": job.id,
            "status": job.status,
            "current_stage": job.current_stage,
            "progress_percentage": job.progress_percentage,
            "stage_details": job.stage_details,
            "error_type": job.error_type,
            "error_message": job.error_message,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        },
        "findings_summary": {
            "total_count": len(findings),
            "findings": [
                {
                    "id": f.id,
                    "control_id": f.control_id,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                    "issue_description": f.issue_description[:100] if f.issue_description else None,
                }
                for f in findings
            ]
        },
        "logs_summary": {
            "total_count": len(logs),
            "by_type": {
                "discovery": len([l for l in logs if l.log_type == "discovery"]),
                "data_extraction": len([l for l in logs if l.log_type == "data_extraction"]),
                "audit": len([l for l in logs if l.log_type == "audit"]),
                "finding": len([l for l in logs if l.log_type == "finding"]),
                "system": len([l for l in logs if l.log_type == "system"]),
                "error": len([l for l in logs if l.log_type == "error"]),
            },
            "recent_logs": [
                {
                    "timestamp": l.timestamp.isoformat() if l.timestamp else None,
                    "log_type": l.log_type,
                    "message": l.message[:200],
                    "control_id": l.control_id,
                    "details": l.details,
                }
                for l in logs[-20:]  # Last 20 logs
            ]
        }
    }


@router.get("/jobs/{job_id}/export/pdf")
async def export_audit_pdf(
    job_id: int,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db)
):
    """Export audit results as a professional PDF report."""
    # Get audit job
    job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found")

    # Check authorization
    if current_user.role != "admin" and job.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get findings
    findings = db.query(Finding).filter(Finding.job_id == job_id).all()
    findings_data = [
        {
            "id": f.id,
            "control_id": f.control_id,
            "issue_description": f.issue_description,
            "raw_data": f.raw_data,
            "severity": _infer_severity(f.control_id),
        }
        for f in findings
    ]

    # Get audit logs for evidence
    logs = db.query(AuditLog).filter(AuditLog.job_id == job_id).order_by(AuditLog.timestamp).all()
    logs_data = [
        {
            "timestamp": l.timestamp.isoformat() if l.timestamp else None,
            "log_type": l.log_type,
            "message": l.message,
            "control_id": l.control_id,
            "details": l.details,
        }
        for l in logs
    ]

    # Get connection info
    conn = db.query(Connection).filter(Connection.id == job.connection_id).first()
    connection_name = conn.name if conn else "Unknown"

    # Get company info
    company = job.company
    company_name = company.name if company else current_user.company.name if current_user.company else "Unknown"

    # Prepare job data
    job_data = {
        "standard_name": job.standard_name,
        "status": job.status,
        "created_at": job.created_at.isoformat() if job.created_at else None,
        "completed_at": job.completed_at.isoformat() if job.completed_at else None,
        "connection_name": connection_name,
    }

    # Generate PDF
    try:
        report_generator = AuditReportGenerator()
        pdf_bytes = report_generator.generate_report(
            job_id=job_id,
            job_data=job_data,
            findings=findings_data,
            audit_logs=logs_data,
            company_name=company_name,
            connection_name=connection_name,
        )

        # Return PDF file
        return FileResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=audit-report-{job_id}.pdf"
            }
        )
    except Exception as e:
        logger.error(f"Error generating PDF report: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to generate PDF: {str(e)}")


@router.get("/status/{task_id}")
async def get_audit_status(
    task_id: str,
    current_user: User = Depends(get_current_user_full),
):
    """Get the Celery task status of an audit job."""
    celery_app = _get_celery_app()
    task_result = AsyncResult(task_id, app=celery_app)

    response = {
        "task_id": task_id,
        "status": task_result.status,
    }

    if task_result.state == 'PROGRESS':
        response['progress'] = task_result.info
    elif task_result.state == 'SUCCESS':
        response['result'] = task_result.result

    return response


@router.get("/delta")
async def get_audit_delta(
    old_job_id: int,
    new_job_id: int,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db)
):
    """Compare two audit jobs and return the delta (resolved, new, persistent findings)."""
    old_job = db.query(AuditJob).filter(AuditJob.id == old_job_id).first()
    new_job = db.query(AuditJob).filter(AuditJob.id == new_job_id).first()

    if not old_job or not new_job:
        raise HTTPException(status_code=404, detail="One or both jobs not found")

    if current_user.role != "admin":
        if old_job.company_id != current_user.company_id or new_job.company_id != current_user.company_id:
            raise HTTPException(status_code=403, detail="Access denied to one or both jobs")

    delta = compare_snapshots(db, old_job_id, new_job_id)
    return {"message": "Delta comparison successful", "data": delta}


@router.post("/jobs/{job_id}/retry")
async def retry_failed_audit(
    job_id: int,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db)
):
    """Retry a failed audit job. Creates a new job linked to the original failed job."""
    original_job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
    if not original_job:
        raise HTTPException(status_code=404, detail="Audit job not found")

    # Check authorization
    if current_user.role != "admin" and original_job.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Can only retry failed jobs
    if original_job.status != "FAILED":
        raise HTTPException(status_code=400, detail=f"Can only retry FAILED jobs. Current status: {original_job.status}")

    # Check if retryable
    if original_job.is_retryable is False:
        raise HTTPException(
            status_code=400,
            detail=f"This audit cannot be retried due to: {original_job.error_message}"
        )

    # Check retry limit
    if original_job.retry_count >= original_job.max_retries:
        raise HTTPException(
            status_code=400,
            detail=f"Maximum retries ({original_job.max_retries}) exceeded. Please check the error and fix the issue before retrying."
        )

    # Create new audit job with same parameters
    new_job = AuditJob(
        connection_id=original_job.connection_id,
        company_id=original_job.company_id,
        standard_name=original_job.standard_name,
        status="PENDING",
        retried_from_job_id=job_id  # Link to original job
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Queue the retry job
    run_audit_job = _get_run_audit_job()
    task = run_audit_job.delay(
        job_id=new_job.id,
        connection_id=original_job.connection_id,
        schema_name=original_job.standard_name
    )

    # Update original job with retry count
    original_job.retry_count += 1
    db.commit()

    return {
        "message": f"Audit job retried (attempt {original_job.retry_count + 1}/{original_job.max_retries + 1})",
        "original_job_id": job_id,
        "new_job_id": new_job.id,
        "task_id": task.id,
        "reason": original_job.error_type,
        "error": original_job.error_message
    }


@router.post("/jobs/{job_id}/resume")
async def resume_failed_audit(
    job_id: int,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db)
):
    """
    Resume a failed audit from the last successful stage.
    Creates a new job that skips already-processed tables and continues from where it failed.
    """
    original_job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
    if not original_job:
        raise HTTPException(status_code=404, detail="Audit job not found")

    # Check authorization
    if current_user.role != "admin" and original_job.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Can only resume failed jobs
    if original_job.status != "FAILED":
        raise HTTPException(status_code=400, detail=f"Can only resume FAILED jobs. Current status: {original_job.status}")

    # Check if it has a last successful stage
    if not original_job.last_successful_stage:
        raise HTTPException(
            status_code=400,
            detail="Cannot resume - no successful stages completed. Please retry instead."
        )

    # Create new audit job with same parameters
    new_job = AuditJob(
        connection_id=original_job.connection_id,
        company_id=original_job.company_id,
        standard_name=original_job.standard_name,
        status="PENDING",
        retried_from_job_id=job_id,  # Link to original job
        last_successful_stage=original_job.last_successful_stage  # Resume from this stage
    )
    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    # Queue the resume job
    run_audit_job = _get_run_audit_job()
    task = run_audit_job.delay(
        job_id=new_job.id,
        connection_id=original_job.connection_id,
        schema_name=original_job.standard_name,
        resume_from_stage=original_job.last_successful_stage,
        resume_from_job_id=job_id
    )

    return {
        "message": f"Audit job resumed from stage: {original_job.last_successful_stage}",
        "original_job_id": job_id,
        "new_job_id": new_job.id,
        "task_id": task.id,
        "reason": original_job.error_type,
        "error": original_job.error_message,
        "last_successful_stage": original_job.last_successful_stage,
        "last_processed_table": original_job.last_processed_table
    }


@router.post("/jobs/{job_id}/cancel")
async def cancel_audit_job(
    job_id: int,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """Cancel a running or pending audit job."""
    job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found")

    if current_user.role != "admin" and job.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Can only cancel if not already completed or failed
    if job.status in ["COMPLETED", "FAILED", "CANCELLED"]:
        raise HTTPException(status_code=400, detail=f"Cannot cancel audit with status: {job.status}")

    # Try to revoke the Celery task if it exists
    if job.id:
        try:
            celery_app = _get_celery_app()
            # Find the task by job_id (we'd need to store task_id in the database)
            # For now, we'll just update the job status
            logger.info(f"Attempting to cancel task for job {job_id}")
        except Exception as e:
            logger.warning(f"Could not revoke Celery task: {e}")

    # Update job status to CANCELLED
    job.status = "CANCELLED"
    job.current_stage = "CANCELLED"
    job.stage_details = "Audit job cancelled by user"
    from datetime import datetime
    job.completed_at = datetime.utcnow()
    db.commit()

    return {
        "message": "Audit job cancelled successfully",
        "job_id": job.id,
        "status": job.status
    }


@router.get("/jobs/{job_id}/logs")
async def get_audit_logs(
    job_id: int,
    limit: int = 50,
    offset: int = 0,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db)
):
    """Get audit execution logs for a specific audit job with pagination."""
    # Validate limit
    limit = min(limit, 5000)  # Cap at 5000 to allow loading many logs at once
    if limit < 1:
        limit = 1
    if offset < 0:
        offset = 0

    # Check that job exists and user has access
    job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found")

    if current_user.role != "admin" and job.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get total count
    total = db.query(AuditLog).filter(AuditLog.job_id == job_id).count()

    # Get paginated logs ordered by timestamp ASC (oldest first - chronological order)
    logs = db.query(AuditLog).filter(
        AuditLog.job_id == job_id
    ).order_by(AuditLog.timestamp.asc()).offset(offset).limit(limit).all()

    # Format response
    logs_data = [
        {
            "id": log.id,
            "job_id": log.job_id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "log_type": log.log_type,
            "message": log.message,
            "details": log.details,
            "llm_prompt": log.llm_prompt,
            "llm_response": log.llm_response,
            "llm_reasoning": log.llm_reasoning,
            "control_id": log.control_id,
            "data_context": log.data_context,
        }
        for log in logs
    ]

    return {
        "logs": logs_data,
        "total": total,
        "offset": offset,
        "limit": limit,
        "has_more": (offset + limit) < total,
    }


@router.get("/jobs/{job_id}/summary")
async def get_audit_summary(
    job_id: int,
    current_user: User = Depends(get_current_user_full),
    db: Session = Depends(get_db)
):
    """Get audit summary with overview description and sample data."""
    job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Audit job not found")

    if current_user.role != "admin" and job.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # Get connection info
    conn = db.query(Connection).filter(Connection.id == job.connection_id).first()

    # Build overview description
    connection_type = conn.type.value if conn and hasattr(conn.type, 'value') else (conn.type if conn else "Unknown")
    overview = f"""This audit evaluated {conn.name if conn else 'a data source'} ({connection_type}) against the {job.standard_name} compliance standard.
The audit performed a comprehensive review of controls and requirements to ensure adherence to regulatory guidelines.
Data was analyzed to identify control violations and security gaps. The findings below document all discovered issues requiring remediation."""

    # Get sample data from audit logs (data_context field)
    audit_logs = db.query(AuditLog).filter(
        AuditLog.job_id == job_id,
        AuditLog.log_type == 'audit',
        AuditLog.data_context.isnot(None)
    ).limit(10).all()

    sample_data = []
    sample_columns = set()

    for log in audit_logs:
        if log.data_context:
            sample_data.append({
                "control_id": log.control_id,
                "data": log.data_context
            })
            # Collect all unique column names
            if isinstance(log.data_context, dict):
                sample_columns.update(log.data_context.keys())

    # Convert set to sorted list for consistent column ordering
    sample_columns = sorted(list(sample_columns))

    return {
        "overview": overview,
        "sample_data": sample_data,
        "columns": sample_columns,
        "total_records_sampled": len(sample_data),
        "connection_name": conn.name if conn else "Unknown",
        "connection_type": connection_type,
        "standard_name": job.standard_name,
        "audit_date": job.created_at.isoformat() if job.created_at else None,
    }
