import sys
sys.path.insert(0, '/app')

from worker import run_audit_job

# Retry job ID 1 with connection 17 and standard BAHRAIN-PDPL
task = run_audit_job.delay(
    job_id=1,
    connection_id=17,
    schema_name="BAHRAIN-PDPL"
)

print(f"✅ Resubmitted audit job 1 to Celery")
print(f"Task ID: {task.id}")
print(f"Job ID: 1")
print(f"Connection: 17 (Oracle)")
print(f"Standard: BAHRAIN-PDPL")
