import json
import os
import logging
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import List, Dict, Optional, Any

logger = logging.getLogger(__name__)


def _json_serializable(obj: Any) -> Any:
    """Recursively convert non-serializable types (datetime, Decimal, bytes) to JSON-safe types."""
    if isinstance(obj, dict):
        return {k: _json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_json_serializable(v) for v in obj]
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, bytes):
        return obj.decode("utf-8", errors="replace")
    return obj



OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")  # Default to containerized URL
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama2:latest")  # Default to available model


def _get_selected_model(db=None) -> str:
    """Get the selected LLM model from settings or use default."""
    try:
        if db:
            from models.settings import ApplicationSettings
            setting = db.query(ApplicationSettings).filter(
                ApplicationSettings.setting_key == "llm_model"
            ).first()
            if setting and setting.setting_value:
                return setting.setting_value
    except Exception as e:
        logger.warning(f"Could not fetch model from settings: {e}")

    return OLLAMA_MODEL


def _call_ollama(prompt: str, model: str = None) -> str:
    """Direct HTTP call to Ollama API — no langchain required."""
    import requests as _req
    if not model:
        model = OLLAMA_MODEL

    try:
        # Increased timeout to 600 seconds (10 minutes) for slow models like qwen2.5-coder:32b
        resp = _req.post(
            f"{OLLAMA_URL}/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
            timeout=600
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except _req.exceptions.Timeout as e:
        logger.error(f"Ollama timeout with model {model} - request took longer than 600 seconds")
        error_msg = f"AI model {model} took too long to respond (timeout after 600 seconds). Try switching to a faster model in Settings (e.g., llama2:latest instead of qwen2.5-coder:32b)"
        raise TimeoutError(error_msg) from e
    except _req.exceptions.ConnectionError as e:
        logger.error(f"Failed to connect to Ollama at {OLLAMA_URL}")
        error_msg = f"Cannot reach Ollama at {OLLAMA_URL}. Ensure Ollama is running with 'ollama serve' and accessible from this container."
        raise ConnectionError(error_msg) from e
    except Exception as e:
        logger.error(f"Ollama error with model {model}: {str(e)}")
        raise


def _categorize_error(error: Exception) -> tuple[str, bool]:
    """
    Categorize an error to determine if it's retryable and what type it is.

    Returns:
        (error_type: str, is_retryable: bool)
    """
    error_str = str(error).lower()

    # Connection errors (retryable)
    if isinstance(error, ConnectionError) or "cannot reach ollama" in error_str:
        return ("OLLAMA_UNREACHABLE", True)

    # Timeout errors (retryable - may need to switch models)
    if isinstance(error, TimeoutError) or "timeout" in error_str:
        return ("OLLAMA_TIMEOUT", True)

    # File not found (not retryable - file path problem)
    if isinstance(error, FileNotFoundError) or "file not found" in error_str:
        return ("FILE_NOT_FOUND", False)

    # Database connection (retryable)
    if "database" in error_str or "connection" in error_str:
        return ("DATABASE_CONNECTION_ERROR", True)

    # Invalid data (not retryable)
    if "invalid" in error_str or "empty" in error_str:
        return ("INVALID_DATA", False)

    # Unknown error (assume retryable to be safe)
    return ("UNKNOWN_ERROR", True)


def _ollama_available() -> bool:
    """Check if Ollama is reachable."""
    import requests as _req
    try:
        _req.get(OLLAMA_URL, timeout=3)
        return True
    except Exception:
        return False


# ── Audit Logging ────────────────────────────────────────────────────────────

def _log_audit_event(
    job_id: int,
    log_type: str,
    message: str,
    details: Optional[Dict] = None,
    llm_prompt: Optional[str] = None,
    llm_response: Optional[str] = None,
    llm_reasoning: Optional[str] = None,
    control_id: Optional[str] = None,
    data_context: Optional[Dict] = None
) -> None:
    """
    Create an audit log entry for detailed execution tracking.

    Args:
        job_id: The audit job ID
        log_type: Type of log (discovery, data_extraction, audit, finding, system, error)
        message: Human-readable message
        details: Structured data (optional)
        llm_prompt: Full prompt sent to Ollama (optional)
        llm_response: Full response from Ollama (optional)
        llm_reasoning: Extracted reasoning from response (optional)
        control_id: Which control was being evaluated (optional)
        data_context: Data row being evaluated (optional)
    """
    try:
        from core.database import SessionLocal
        from models.audit import AuditLog

        db = SessionLocal()
        try:
            log = AuditLog(
                job_id=job_id,
                log_type=log_type,
                message=message,
                details=_json_serializable(details) if details else None,
                llm_prompt=llm_prompt,
                llm_response=llm_response,
                llm_reasoning=llm_reasoning,
                control_id=control_id,
                data_context=_json_serializable(data_context) if data_context else None
            )
            db.add(log)
            db.commit()
            logger.debug(f"[Job {job_id}] Logged: {log_type} - {message[:80]}")
        finally:
            db.close()
    except Exception as e:
        logger.error(f"[Job {job_id}] Failed to log event: {e}")


def _extract_reasoning(response: str) -> str:
    """
    Extract the reasoning/thinking part from an LLM response.

    Looks for common reasoning patterns and extracts meaningful insight
    rather than returning the entire response.
    """
    if not response:
        return ""

    # If response is very long, try to extract key reasoning
    lines = response.split('\n')
    reasoning_lines = []

    for line in lines:
        line_lower = line.lower()
        # Look for reasoning indicators
        if any(keyword in line_lower for keyword in [
            'because', 'therefore', 'thus', 'hence',
            'the data shows', 'this violates', 'this requires',
            'evidence', 'found', 'discovered', 'identified',
            'however', 'but', 'since'
        ]):
            reasoning_lines.append(line)

    if reasoning_lines:
        reasoning = '\n'.join(reasoning_lines[:5])  # Take up to 5 lines
        return reasoning.strip()

    # Fallback: return first 500 chars or first paragraph
    if len(response) > 500:
        # Try to break at a natural boundary
        first_para = response.split('\n\n')[0]
        return first_para[:500] if len(first_para) > 500 else first_para

    return response.strip()


# ── Standards Loader ─────────────────────────────────────────────────────────

def load_controls(standard_name: str, db=None) -> List[Dict]:
    """
    Load compliance controls from database (preferred) or JSON file (fallback).

    Args:
        standard_name: Name of the standard (e.g., "ISO-27001", "GDPR-UAE")
        db: SQLAlchemy database session (optional). If provided, loads from database.
            If not provided, falls back to JSON file loading.

    Returns:
        List of control dictionaries with id, name, description, logic, etc.
    """
    # Try database first if session is provided
    if db is not None:
        try:
            from services.standards_service import StandardsService
            controls = StandardsService.load_controls(db, standard_name)
            if controls:
                logger.info(f"Loaded {len(controls)} controls for '{standard_name}' from database")
                return controls
        except Exception as e:
            logger.warning(f"Failed to load standard '{standard_name}' from database: {e}")

    # Fallback to JSON file loading (for backward compatibility)
    filename = f"{standard_name.lower().replace('-', '_')}.json"

    # Try mounted /standards directory first (Docker)
    candidates = [
        Path("/standards") / filename,
        Path("/standards/gdpr_uae.json"),
        Path(__file__).parent.parent.parent / "standards" / filename,
        Path(__file__).parent.parent.parent / "standards" / "gdpr_uae.json",
    ]

    for path in candidates:
        if path.exists():
            try:
                with open(path) as f:
                    data = json.load(f)
                    controls = data.get("controls", [])
                    logger.info(f"Loaded {len(controls)} controls from JSON file {path}")
                    return controls
            except Exception as e:
                logger.error(f"Failed to load controls from {path}: {e}")

    logger.error(f"No controls found for standard: {standard_name}")
    return []


# ── Phase 1: Discovery ───────────────────────────────────────────────────────

def discover_relevant_datasets(
    schema: Dict[str, Any],
    controls: List[Dict],
    connection_type: str
) -> List[Dict[str, Any]]:
    """
    Ask the LLM which tables/columns from the schema are relevant to the controls.
    Caps the schema to 60 tables to avoid LLM context overflow.
    """
    controls_summary = "\n".join(
        f"- {c['id']}: {c['requirement']} — {c.get('description', '')} Logic: {c.get('logic','')}"
        for c in controls
    )

    # ── Cap schema size: filter to most likely relevant tables first ──────────
    tables = schema.get("tables", [])
    
    # Keywords from control requirements to pre-filter tables
    control_keywords = set()
    for c in controls:
        for word in (c.get('requirement','') + ' ' + c.get('description','')).lower().split():
            if len(word) > 3:
                control_keywords.add(word)
    
    # Score tables by how many column names match control keywords
    RELEVANCE_KEYWORDS = {
        "user", "role", "auth", "access", "permission", "login", "admin",
        "email", "dept", "department", "employee", "staff", "account",
        "log", "audit", "session", "privilege", "group", "password"
    }
    
    def table_score(t):
        col_names = " ".join(c["name"].lower() for c in t.get("columns", []))
        table_name = t["name"].lower()
        score = sum(1 for kw in RELEVANCE_KEYWORDS if kw in col_names or kw in table_name)
        return score

    tables_sorted = sorted(tables, key=table_score, reverse=True)
    top_tables = tables_sorted[:60]  # Send at most 60 tables to LLM

    schema_summary = json.dumps({"tables": top_tables}, indent=1)

    if not _ollama_available():
        logger.warning("Ollama not reachable — using top scored tables as keyword fallback")
        return [
            {"table": t["name"], "columns": [c["name"] for c in t.get("columns", [])]}
            for t in tables_sorted[:5]
        ]

    prompt = f"""You are an expert compliance auditor and data analyst.

You are about to audit a data source for the following compliance controls:
{controls_summary}

The data source has {len(tables)} total tables. Here are the {len(top_tables)} most likely relevant ones:
{schema_summary}

Your task: From the above list, identify which tables and columns contain data relevant to evaluating these controls.

Return ONLY a valid JSON array. No explanation. No markdown. Just the JSON.
Return at most 5 tables. Prioritize tables with user, role, access, auth, or employee data.
Example format:
[
  {{"table": "SY_USERS", "columns": ["USER_ID", "USER_ROLE", "DEPT_CODE"]}},
  {{"table": "AUTH_LOG", "columns": ["USER_ID", "ACTION", "TIMESTAMP"]}}
]

If no table is relevant, return an empty array: []"""

    try:
        text = _call_ollama(prompt)

        # Strip markdown code fences if present
        if "```" in text:
            parts = text.split("```")
            for part in parts:
                if part.startswith("json"):
                    part = part[4:]
                part = part.strip()
                if part.startswith("["):
                    text = part
                    break

        text = text.strip()
        if not text.startswith("["):
            idx = text.find("[")
            if idx >= 0:
                text = text[idx:]

        dataset_map = json.loads(text)
        logger.info(f"LLM identified {len(dataset_map)} relevant datasets")
        return dataset_map

    except Exception as e:
        logger.error(f"LLM discovery failed: {e}. Falling back to top scored tables.")
        return [
            {"table": t["name"], "columns": [c["name"] for c in t.get("columns", [])]}
            for t in tables_sorted[:3]
        ]



# ── Phase 2: Audit ───────────────────────────────────────────────────────────

def invoke_ollama(prompt: str, db=None) -> Dict:
    """Call the LLM to evaluate a single compliance control against a single record."""
    if not _ollama_available():
        return {"status": "ERROR", "reason": "Ollama not reachable"}

    try:
        # Get selected model from settings
        model = _get_selected_model(db)

        full_prompt = f"""You are a compliance auditor. Evaluate the data against the control requirement.

{prompt}

Respond with ONLY one of:
- "PASS: [reason]"
- "FAIL: [reason]"

Be concise."""
        text = _call_ollama(full_prompt, model=model)
        text_stripped = text.strip() if text else ""

        logger.info(f"🤖 LLM Response (len={len(text_stripped)}): {text_stripped[:200]}...")  # DEBUG: Log raw response with length

        # More flexible parsing: check if response contains "fail" (case-insensitive)
        text_upper = text_stripped.upper()
        text_lower = text_stripped.lower()

        # Check for FAIL response
        if text_upper.startswith("FAIL"):
            reason = text_stripped[5:].strip() if len(text_stripped) > 5 else text_stripped
            logger.info(f"✅ Parsed as FAIL: {reason[:100]}")
            return {"status": "FAIL", "reason": reason}
        elif text_upper.startswith("PASS"):
            reason = text_stripped[5:].strip() if len(text_stripped) > 5 else text_stripped
            logger.info(f"✅ Parsed as PASS: {reason[:100]}")
            return {"status": "PASS", "reason": reason}

        # If response contains "fail" or "violation" anywhere, treat as FAIL
        if "fail" in text_lower or "violation" in text_lower or "non-compliant" in text_lower or "does not" in text_lower or "no " in text_lower:
            logger.warning(f"⚠️ LLM response didn't start with FAIL but contains failure indicators (len={len(text_stripped)}): {text_stripped[:100]}")
            return {"status": "FAIL", "reason": text_stripped}

        # Default to PASS only if response clearly indicates compliance
        logger.debug(f"✅ LLM response parsed as PASS: {text_stripped[:100]}")
        return {"status": "PASS", "reason": text_stripped}
    except Exception as e:
        logger.error(f"LLM invoke error: {e}")
        return {"status": "ERROR", "reason": str(e)}


# ── Main Entry Point (called by Celery worker) ────────────────────────────────

def process_audit_batch(job_id: int, schema_name: str, data: list, celery_task=None, db=None) -> list:
    """
    Legacy entry point — kept for backward compatibility.
    Runs Phase 2 only against provided data.
    """
    controls = load_controls(schema_name, db=db)
    findings = []
    total = len(data)

    for i, record in enumerate(data):
        safe_record = _json_serializable(record)
        for control in controls:
            prompt = (
                f"Control: {control.get('id')} - {control.get('requirement')}\n"
                f"Description: {control.get('description')}\n"
                f"Logic: {control.get('logic')}\n"
                f"Data:\n{json.dumps(safe_record, indent=2)}"
            )
            result = invoke_ollama(prompt, db=db)
            if result.get("status") == "FAIL":
                findings.append({
                    "job_id": job_id,
                    "control_id": control.get("id"),
                    "issue_description": result.get("reason"),
                    "raw_data": safe_record
                })
        if celery_task:
            celery_task.update_state(state='PROGRESS', meta={'current': i + 1, 'total': total})

    _save_findings_to_db(job_id, findings)
    return findings


def run_full_audit(
    job_id: int,
    connection_id: int,
    standard_name: str,
    celery_task=None,
    resume_from_stage: str = None,
    resume_from_job_id: int = None
) -> int:
    """
    Full two-phase agentic audit:
    1. Check vector memory for cached schema mapping
    2. If not cached: run LLM discovery, cache result
    3. Fetch real data from each relevant dataset
    4. Run LLM audit per record per control
    5. Store findings in DB

    If resume_from_stage is provided, skips completed stages and resumes from that point.

    Returns the count of findings.
    """
    from core.database import SessionLocal
    from models.audit import AuditJob, Finding
    from models.hierarchy import Connection
    from services.memory_service import MemoryService
    from services.connectors.factory import ConnectorFactory
    from datetime import datetime

    db = SessionLocal()
    findings_list = []

    # If resuming, load previous findings to avoid re-auditing
    previous_findings = {}
    if resume_from_job_id:
        logger.info(f"[Job {job_id}] Resuming from job {resume_from_job_id}, stage: {resume_from_stage}")
        prev_findings = db.query(Finding).filter(Finding.job_id == resume_from_job_id).all()
        for f in prev_findings:
            key = f"{f.control_id}::{f.raw_data.get('id') if f.raw_data else str(f.id)}"
            previous_findings[key] = f

    try:
        # Update job status
        job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
        if job:
            job.status = "SCANNING"
            job.current_stage = "CHECKING_CACHE"
            job.progress_percentage = 0.0
            job.stage_details = "Checking vector memory for cached schema..."
            job.started_at = datetime.utcnow()
            db.commit()

        # ── Get connection config ─────────────────────────────────────────────
        conn_model = db.query(Connection).filter(Connection.id == connection_id).first()
        if not conn_model:
            raise ValueError(f"Connection {connection_id} not found")

        connection_type = conn_model.type.value
        connection_string = conn_model.connection_string or ""

        # ── Load controls ─────────────────────────────────────────────────────
        controls = load_controls(standard_name, db=db)
        if not controls:
            logger.warning(f"No controls found for standard: {standard_name}")

        # ── Phase 1: Memory Check ─────────────────────────────────────────────
        # Skip discovery if resuming from a later stage
        if resume_from_stage and resume_from_stage in ["LOADING_DATA", "AUDITING", "SAVING_RESULTS"]:
            logger.info(f"[Job {job_id}] Skipping discovery - resuming from {resume_from_stage}")
            _log_audit_event(
                job_id, 'system',
                f'Resuming from stage: {resume_from_stage}',
                details={'resume_from_stage': resume_from_stage, 'original_job': resume_from_job_id}
            )
            dataset_map = MemoryService.recall_schema_mapping(db, connection_id, standard_name)
            if not dataset_map:
                raise ValueError(f"Cannot resume - no cached schema found. Please retry from beginning.")
        else:
            _log_audit_event(
                job_id, 'system',
                'Starting audit job',
                details={'standard': standard_name, 'connection_id': connection_id}
            )

            dataset_map = MemoryService.recall_schema_mapping(db, connection_id, standard_name)

        if dataset_map:
            logger.info(f"[Job {job_id}] Phase 1 SKIPPED — using cached schema mapping from vector DB")
            _log_audit_event(
                job_id, 'discovery',
                f'Using cached schema mapping with {len(dataset_map)} tables',
                details={'table_count': len(dataset_map), 'source': 'cache'}
            )
            if job:
                job.current_stage = "LOADING_DATA"
                job.progress_percentage = 15.0
                job.stage_details = f"Using cached schema with {len(dataset_map)} tables"
                job.last_successful_stage = "CHECKING_CACHE"
                db.commit()
        else:
            logger.info(f"[Job {job_id}] Phase 1 START — discovering relevant datasets via LLM")
            _log_audit_event(
                job_id, 'discovery',
                'Starting LLM discovery to identify relevant tables',
                details={'connection_id': connection_id, 'standard': standard_name}
            )
            if job:
                job.current_stage = "DISCOVERING"
                job.progress_percentage = 5.0
                job.stage_details = "Running LLM discovery to identify relevant tables..."
                db.commit()

            if celery_task:
                celery_task.update_state(state='PROGRESS', meta={
                    'phase': 'discovery',
                    'current': 0,
                    'stage': 'DISCOVERING',
                    'progress_percentage': 5.0
                })

            # Open the real connection and introspect schema
            connector = ConnectorFactory.create_connector(connection_type, connection_string)
            schema = connector.discover_schema()

            # LLM identifies relevant datasets
            dataset_map = discover_relevant_datasets(schema, controls, connection_type)

            _log_audit_event(
                job_id, 'discovery',
                f'Discovered {len(dataset_map)} relevant tables via LLM',
                details={
                    'discovered_tables': [d.get('table') for d in dataset_map],
                    'total_schema_tables': len(schema.get('tables', []))
                }
            )

            # Store in vector memory for future audits
            if dataset_map:
                MemoryService.store_schema_mapping(db, connection_id, standard_name, dataset_map)
                _log_audit_event(
                    job_id, 'discovery',
                    f'Indexed {len(dataset_map)} tables in pgvector for future audits',
                    details={
                        'table_count': len(dataset_map),
                        'tables': list(dataset_map.keys()),
                        'indexed_in_pgvector': True
                    }
                )

            if job:
                job.current_stage = "LOADING_DATA"
                job.progress_percentage = 15.0
                job.stage_details = f"Discovered {len(dataset_map)} relevant tables"
                job.last_successful_stage = "DISCOVERING"
                db.commit()

            logger.info(f"[Job {job_id}] Phase 1 DONE — {len(dataset_map)} datasets identified")

        # ── Phase 2: Audit ────────────────────────────────────────────────────
        if job:
            job.status = "RUNNING"
            job.current_stage = "AUDITING"
            job.progress_percentage = 20.0
            db.commit()

        logger.info(f"[Job {job_id}] Phase 2 START — auditing {len(dataset_map)} datasets")

        connector = ConnectorFactory.create_connector(
            conn_model.type.value, conn_model.connection_string or ""
        )

        total_datasets = len(dataset_map)
        total_records = 0
        processed_records = 0

        # First pass: count total records to calculate progress accurately
        for dataset in dataset_map:
            table_name = dataset.get("table", "")
            columns = dataset.get("columns", [])
            records = connector.extract_table(table_name, columns)
            total_records += len(records)

        for ds_idx, dataset in enumerate(dataset_map):
            table_name = dataset.get("table", "")
            columns = dataset.get("columns", [])

            logger.info(f"[Job {job_id}] Auditing dataset: {table_name}")
            _log_audit_event(
                job_id, 'data_extraction',
                f'Loading data from table: {table_name}',
                details={'table_name': table_name, 'columns': columns}
            )
            records = connector.extract_table(table_name, columns)

            _log_audit_event(
                job_id, 'data_extraction',
                f'Loaded {len(records)} records from {table_name}',
                details={'table_name': table_name, 'record_count': len(records)}
            )

            if job:
                job.current_stage = "AUDITING"
                job.stage_details = f"Scanning table {ds_idx + 1}/{total_datasets} ({table_name}): {len(records)} records"
                job.last_processed_table = table_name
                job.last_successful_stage = "AUDITING"
                db.commit()

            for i, record in enumerate(records):
                processed_records += 1
                safe_record = _json_serializable(record)
                for control in controls:
                    control_id = control.get("id")

                    # Skip if already processed in previous audit (when resuming)
                    record_key = f"{control_id}::{safe_record.get('id') if isinstance(safe_record, dict) else str(i)}"
                    if record_key in previous_findings:
                        logger.debug(f"[Job {job_id}] Skipping already-audited: {record_key}")
                        _log_audit_event(
                            job_id, 'audit',
                            f'Skipped (already audited): control {control_id} on record {i + 1} in {table_name}',
                            control_id=control_id,
                            details={'table': table_name, 'record_index': i + 1, 'skipped': True}
                        )
                        # Re-use previous finding
                        prev_f = previous_findings[record_key]
                        finding = {
                            "job_id": job_id,
                            "control_id": prev_f.control_id,
                            "issue_description": prev_f.issue_description,
                            "raw_data": prev_f.raw_data
                        }
                        findings_list.append(finding)
                        continue

                    prompt = (
                        f"Control: {control_id} - {control.get('requirement')}\n"
                        f"Description: {control.get('description')}\n"
                        f"Logic: {control.get('logic')}\n"
                        f"Data:\n{json.dumps(safe_record, indent=2)}"
                    )
                    result = invoke_ollama(prompt, db=db)
                    llm_response = result.get("reason", "")
                    llm_reasoning = _extract_reasoning(llm_response) if result.get("status") else ""

                    # Log the audit evaluation
                    _log_audit_event(
                        job_id, 'audit',
                        f'Evaluated control {control_id} against record {i + 1} in {table_name}',
                        llm_prompt=prompt,
                        llm_response=llm_response,
                        llm_reasoning=llm_reasoning,
                        control_id=control_id,
                        data_context=safe_record,
                        details={
                            'table': table_name,
                            'record_index': i + 1,
                            'status': result.get("status")
                        }
                    )

                    if result.get("status") == "FAIL":
                        finding = {
                            "job_id": job_id,
                            "control_id": control_id,
                            "issue_description": llm_response,
                            "raw_data": safe_record
                        }
                        findings_list.append(finding)

                        # Log the finding creation
                        _log_audit_event(
                            job_id, 'finding',
                            f'Finding created for control {control_id}',
                            control_id=control_id,
                            data_context=safe_record,
                            details={
                                'table': table_name,
                                'record_index': i + 1,
                                'issue': llm_response
                            }
                        )

                        # Store finding summary in vector memory
                        try:
                            MemoryService.store_finding_summary(
                                db, connection_id, standard_name,
                                control_id, llm_response
                            )
                        except Exception:
                            pass  # Non-critical

            if celery_task:
                progress = 20 + (ds_idx + 1) / total_datasets * 70  # 20-90% during audit
                celery_task.update_state(state='PROGRESS', meta={
                    'phase': 'audit',
                    'current': ds_idx + 1,
                    'total': total_datasets,
                    'stage': 'AUDITING',
                    'progress_percentage': progress
                })

        # ── Save findings ─────────────────────────────────────────────────────
        if job:
            job.current_stage = "SAVING_RESULTS"
            job.progress_percentage = 90.0
            job.stage_details = f"Saving {len(findings_list)} findings to database..."
            job.last_successful_stage = "AUDITING"  # Auditing phase completed successfully
            db.commit()

        _log_audit_event(
            job_id, 'system',
            f'Saving {len(findings_list)} findings to database',
            details={'finding_count': len(findings_list)}
        )

        _save_findings_to_db(job_id, findings_list, db_session=db)
        logger.info(f"[Job {job_id}] Phase 2 DONE — {len(findings_list)} findings")

        # Final update
        job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
        if job:
            job.status = "COMPLETED"
            job.current_stage = "COMPLETED"
            job.progress_percentage = 100.0
            job.stage_details = f"Audit completed with {len(findings_list)} findings"
            job.last_successful_stage = "SAVING_RESULTS"  # All stages completed
            job.error_type = None
            job.is_retryable = False
            job.completed_at = datetime.utcnow()
            db.commit()

        _log_audit_event(
            job_id, 'system',
            f'Audit completed successfully with {len(findings_list)} findings',
            details={
                'status': 'COMPLETED',
                'finding_count': len(findings_list),
                'standard': standard_name
            }
        )

        if celery_task:
            celery_task.update_state(state='PROGRESS', meta={
                'phase': 'completed',
                'stage': 'COMPLETED',
                'progress_percentage': 100.0
            })

        return len(findings_list)

    except Exception as e:
        error_msg = str(e)
        error_type, is_retryable = _categorize_error(e)

        logger.error(f"[Job {job_id}] Audit failed ({error_type}): {error_msg}")
        _log_audit_event(
            job_id, 'error',
            f'Audit failed: {error_msg}',
            details={
                'error': error_msg,
                'error_type': error_type,
                'is_retryable': is_retryable
            }
        )
        try:
            job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
            if job:
                job.status = "FAILED"
                job.current_stage = "FAILED"
                job.progress_percentage = 100.0
                job.stage_details = f"Audit failed: {error_msg[:100]}"
                job.error_message = error_msg
                job.error_type = error_type
                job.is_retryable = is_retryable
                job.completed_at = datetime.utcnow()
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update job status: {db_error}")
        raise
    finally:
        db.close()


def _save_findings_to_db(job_id: int, findings: list, db_session=None) -> None:
    """Persist findings and update job status in the database."""
    from core.database import SessionLocal
    from models.audit import Finding, AuditJob
    from datetime import datetime

    close_after = False
    db = db_session
    if db is None:
        db = SessionLocal()
        close_after = True

    try:
        job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
        if job:
            job.status = "COMPLETED"
            job.current_stage = "COMPLETED"
            job.progress_percentage = 100.0
            job.stage_details = f"Audit completed with {len(findings)} findings"
            job.completed_at = datetime.utcnow()

        logger.info(f"💾 Saving {len(findings)} findings for job {job_id}")

        for i, f in enumerate(findings):
            try:
                db_finding = Finding(
                    job_id=f['job_id'],
                    control_id=f['control_id'],
                    issue_description=f['issue_description'],
                    raw_data=f['raw_data']
                )
                db.add(db_finding)
                logger.debug(f"   [{i+1}/{len(findings)}] Added finding: {f['control_id']} - {f['issue_description'][:50]}")
            except Exception as e:
                logger.error(f"   ❌ Error adding finding {i+1}: {e}")
                raise

        db.commit()
        logger.info(f"✅ Successfully saved {len(findings)} findings to database")
    except Exception as e:
        logger.error(f"❌ Error saving findings: {e}")
        db.rollback()
        raise
    finally:
        if close_after:
            db.close()


def run_file_audit(job_id: int, file_path: Optional[str], uploaded_file_id: Optional[str], standard_name: str, celery_task=None) -> int:
    """
    Run audit against a CSV or Excel file.

    Args:
        job_id: The audit job ID
        file_path: Absolute path to file on server filesystem
        uploaded_file_id: ID of uploaded file (stored in /tmp/audit_uploads)
        standard_name: Name of the standard to audit against
        celery_task: Celery task for progress updates

    Returns:
        Number of findings
    """
    from core.database import SessionLocal
    from models.audit import AuditJob

    db = SessionLocal()
    findings_list = []

    try:
        # Update job status
        job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
        if job:
            job.status = "SCANNING"
            job.current_stage = "LOADING_FILE"
            job.progress_percentage = 10.0
            job.stage_details = "Loading file..."
            job.started_at = datetime.utcnow()
            db.commit()

        _log_audit_event(job_id, 'system', "Starting file-based audit")

        # ── Load file data ────────────────────────────────────────────────────
        file_data = None
        actual_file_path = None

        if uploaded_file_id:
            # Reconstruct uploaded file path
            # Files are saved as: {user_id}_{file_id}.{ext}
            # Find the file in upload directory (same as where audit_engine.py is)
            upload_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
            upload_dir = os.path.abspath(upload_dir)  # Normalize path

            logger.info(f"Looking for uploaded file in: {upload_dir}")

            # Ensure upload directory exists
            if not os.path.exists(upload_dir):
                logger.error(f"Upload directory does not exist: {upload_dir}")
                try:
                    os.makedirs(upload_dir, exist_ok=True)
                    logger.info(f"Created missing upload directory: {upload_dir}")
                except Exception as e:
                    logger.error(f"Failed to create upload directory: {e}")
                    raise FileNotFoundError(f"Upload directory not found and could not be created: {upload_dir}")

            try:
                for filename in os.listdir(upload_dir):
                    if uploaded_file_id in filename:
                        actual_file_path = os.path.join(upload_dir, filename)
                        break
            except OSError as e:
                logger.error(f"Error accessing upload directory: {e}")
                raise FileNotFoundError(f"Cannot access upload directory: {upload_dir}")

            if not actual_file_path or not os.path.exists(actual_file_path):
                # List what files exist for debugging
                try:
                    existing_files = os.listdir(upload_dir)
                    logger.error(f"Looking for file with ID '{uploaded_file_id}'. Files in {upload_dir}: {existing_files}")
                except:
                    pass
                raise FileNotFoundError(f"Uploaded file not found: {uploaded_file_id}")
        else:
            actual_file_path = file_path
            if not os.path.exists(actual_file_path):
                raise FileNotFoundError(f"File not found: {file_path}")

        _log_audit_event(job_id, 'discovery', f"Reading file from: {actual_file_path}")

        # ── Read file based on extension ──────────────────────────────────────
        file_ext = os.path.splitext(actual_file_path)[1].lower()

        if file_ext == '.csv':
            import csv
            file_data = []
            with open(actual_file_path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    file_data.append(dict(row))

        elif file_ext in ['.xlsx', '.xls']:
            try:
                import openpyxl
                import pandas as pd
            except ImportError:
                raise ImportError("Excel support requires openpyxl and pandas")

            df = pd.read_excel(actual_file_path)
            file_data = df.to_dict('records')

        else:
            raise ValueError(f"Unsupported file format: {file_ext}. Supported: .csv, .xlsx, .xls")

        if not file_data:
            raise ValueError("File is empty or contains no valid data")

        _log_audit_event(
            job_id, 'discovery',
            f"Loaded {len(file_data)} records from file",
            details={"record_count": len(file_data), "file_type": file_ext}
        )

        # ── Load controls ─────────────────────────────────────────────────────
        controls = load_controls(standard_name, db=db)
        if not controls:
            logger.warning(f"No controls found for standard: {standard_name}")

        # Update job status
        if job:
            job.current_stage = "AUDITING"
            job.progress_percentage = 20.0
            job.stage_details = f"Running audit on {len(file_data)} records..."
            db.commit()

        _log_audit_event(
            job_id, 'discovery',
            f"Starting audit with {len(controls)} controls against {len(file_data)} records"
        )

        # ── Phase 2: Audit each record ────────────────────────────────────────
        total_records = len(file_data)

        for record_idx, record in enumerate(file_data):
            safe_record = _json_serializable(record)

            for control in controls:
                try:
                    control_id = control.get("id")
                    prompt = (
                        f"Control: {control_id} - {control.get('requirement', control.get('name', 'Unknown'))}\n"
                        f"Description: {control.get('description', '')}\n"
                        f"Logic: {control.get('logic', '')}\n"
                        f"Data:\n{json.dumps(safe_record, indent=2)}\n\n"
                        f"Does this data PASS or FAIL this control? Respond with: PASS or FAIL: reason"
                    )

                    result = invoke_ollama(prompt, db=db)

                    # Parse LLM response
                    if isinstance(result, dict):
                        status = result.get("status", "").upper()
                        reason = result.get("reason", "Control evaluation inconclusive")
                    else:
                        # Parse text response
                        result_str = str(result).strip().upper()
                        if "FAIL" in result_str:
                            status = "FAIL"
                            reason = result_str.split(":", 1)[1].strip() if ":" in result_str else "Control failed"
                        else:
                            status = "PASS"
                            reason = ""

                    # Extract reasoning from response
                    llm_reasoning = _extract_reasoning(reason) if reason else ""

                    # Record finding if failed
                    if status == "FAIL":
                        finding = {
                            "job_id": job_id,
                            "control_id": control_id,
                            "issue_description": reason,
                            "raw_data": safe_record
                        }
                        findings_list.append(finding)

                        _log_audit_event(
                            job_id, 'audit',
                            f"FAIL: {control_id} on record {record_idx + 1}",
                            llm_prompt=prompt,
                            llm_response=reason,
                            llm_reasoning=llm_reasoning,
                            control_id=control_id,
                            data_context=safe_record
                        )
                    else:
                        # Log PASS results as well
                        _log_audit_event(
                            job_id, 'audit',
                            f"PASS: {control_id} on record {record_idx + 1}",
                            llm_prompt=prompt,
                            llm_response=reason,
                            llm_reasoning=llm_reasoning,
                            control_id=control_id,
                            data_context=safe_record
                        )

                except Exception as e:
                    logger.error(f"Error evaluating control {control.get('id')}: {str(e)}")
                    _log_audit_event(
                        job_id, 'error',
                        f"Failed to evaluate control {control.get('id')}: {str(e)}",
                        control_id=control.get("id")
                    )

            # Update progress
            progress = 20 + (record_idx + 1) / total_records * 70
            if job:
                job.progress_percentage = progress
                db.commit()

            if celery_task:
                celery_task.update_state(
                    state='PROGRESS',
                    meta={
                        'current': record_idx + 1,
                        'total': total_records,
                        'findings': len(findings_list)
                    }
                )

        # ── Save findings ─────────────────────────────────────────────────────
        _log_audit_event(
            job_id, 'system',
            f"Audit complete. Found {len(findings_list)} findings across {total_records} records",
            details={"findings_count": len(findings_list), "records_audited": total_records}
        )

        _save_findings_to_db(job_id, findings_list, db_session=db)

        # Clean up uploaded file if it exists
        if uploaded_file_id and actual_file_path and os.path.exists(actual_file_path):
            try:
                os.remove(actual_file_path)
                logger.info(f"Cleaned up uploaded file: {actual_file_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up uploaded file: {e}")

        return len(findings_list)

    except Exception as e:
        error_msg = f"File audit failed: {str(e)}"
        error_type, is_retryable = _categorize_error(e)

        logger.error(f"[Job {job_id}] File audit failed ({error_type}): {error_msg}")
        _log_audit_event(
            job_id, 'error',
            error_msg,
            details={
                'error': str(e),
                'error_type': error_type,
                'is_retryable': is_retryable
            }
        )

        # Update job status to failed
        try:
            job = db.query(AuditJob).filter(AuditJob.id == job_id).first()
            if job:
                job.status = "FAILED"
                job.current_stage = "FAILED"
                job.progress_percentage = 100.0
                job.stage_details = f"File audit failed: {str(e)[:80]}"
                job.error_message = error_msg
                job.error_type = error_type
                job.is_retryable = is_retryable
                job.completed_at = datetime.utcnow()
                db.commit()
        except Exception as db_error:
            logger.error(f"Failed to update job status: {db_error}")

        raise

    finally:
        db.close()
