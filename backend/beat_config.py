"""
Celery Beat Configuration - Defines recurring audit scheduling
"""
from celery.schedules import crontab
from celery import Celery
from datetime import timedelta

# Note: This configuration is used by celery-beat for scheduling
# In production, you would use Celery with a persistent schedule store

CELERY_BEAT_SCHEDULE = {
    # Run the schedule executor every 5 minutes
    'check-schedules': {
        'task': 'worker.check_and_execute_schedules',
        'schedule': timedelta(minutes=5),
        'options': {'queue': 'celery'}
    },
    # Optional: Cleanup old completed audits daily
    'cleanup-old-audits': {
        'task': 'worker.cleanup_old_audits',
        'schedule': crontab(hour=2, minute=0),  # 2 AM daily
        'options': {'queue': 'celery'}
    }
}

# Celery configuration
CELERY_TIMEZONE = 'UTC'
CELERY_ENABLE_UTC = True

# Task configuration
CELERY_TASK_SERIALIZER = 'json'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_RESULT_SERIALIZER = 'json'
CELERY_RESULT_BACKEND_TRANSPORT_OPTIONS = {
    'master_name': 'mymaster'
}

# Task timeout (24 hours for long-running audits)
CELERY_TASK_TIME_LIMIT = 86400
CELERY_TASK_SOFT_TIME_LIMIT = 82800  # 23 hours

# Number of retry attempts
CELERY_TASK_MAX_RETRIES = 3
CELERY_TASK_DEFAULT_RETRY_DELAY = 300  # 5 minutes
