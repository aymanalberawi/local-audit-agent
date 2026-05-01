from sqlalchemy.orm import Session
from models.audit import Finding
from typing import Dict, Any


def _finding_to_dict(f: Finding) -> Dict[str, Any]:
    return {
        "id": f.id,
        "job_id": f.job_id,
        "control_id": f.control_id,
        "issue_description": f.issue_description,
        "raw_data": f.raw_data,
        "created_at": f.created_at.isoformat() if f.created_at else None,
    }


def compare_snapshots(db: Session, old_job_id: int, new_job_id: int) -> Dict[str, Any]:
    """
    Compares two audit snapshots and calculates the delta.
    Returns serializable dicts — not SQLAlchemy model objects.
    """
    old_findings = db.query(Finding).filter(Finding.job_id == old_job_id).all()
    new_findings = db.query(Finding).filter(Finding.job_id == new_job_id).all()

    def finding_key(f: Finding) -> str:
        record_id = (
            f.raw_data.get('id') or
            f.raw_data.get('username') or
            f.raw_data.get('email') or
            str(f.raw_data)
        ) if f.raw_data else str(f.id)
        return f"{f.control_id}::{record_id}"

    old_map = {finding_key(f): f for f in old_findings}
    new_map = {finding_key(f): f for f in new_findings}

    old_keys = set(old_map.keys())
    new_keys = set(new_map.keys())

    resolved_keys = old_keys - new_keys
    new_issue_keys = new_keys - old_keys
    persistent_keys = old_keys & new_keys

    return {
        "summary": {
            "total_resolved": len(resolved_keys),
            "total_new": len(new_issue_keys),
            "total_persistent": len(persistent_keys),
        },
        "resolved": [_finding_to_dict(old_map[k]) for k in resolved_keys],
        "new_issues": [_finding_to_dict(new_map[k]) for k in new_issue_keys],
        "persistent": [_finding_to_dict(new_map[k]) for k in persistent_keys],
    }
