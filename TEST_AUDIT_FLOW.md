# Test Audit Flow - Step by Step

## Prerequisites
- Docker containers running: `docker-compose up -d`
- All containers healthy: `docker-compose ps` (all showing "Up")
- Ollama is running: `curl http://localhost:11434/api/tags`

---

## Complete Test Flow

### Phase 1: Verify Ollama Connection

#### Step 1: Check Ollama is Running
```bash
# Check container status
docker-compose ps | grep ollama

# Expected output:
# 00-llm-ollama-engine    Up (healthy)
```

#### Step 2: Verify Ollama API Works
```bash
# From your host machine
curl http://localhost:11434/api/tags

# Expected output (JSON with model list):
{
  "models": [
    {
      "name": "llama2:latest",
      "size": 3826087936,
      "digest": "...",
      "details": {...}
    }
  ]
}
```

#### Step 3: Check Backend Configuration
```bash
# Verify backend has correct OLLAMA_URL
docker-compose exec backend bash -c 'echo $OLLAMA_URL'

# Expected output:
# http://ollama:11434
```

---

### Phase 2: Test Audit Creation

#### Step 1: Open Application
```
Browser: http://localhost:3000
Login: admin@example.com / password
```

#### Step 2: Navigate to Audits
```
Left menu → Audits tab
```

#### Step 3: Create New Audit
```
Click: [+ Create New Audit]
Select:
  - Connection: Mock Database
  - Standard: GDPR_UAE
  
Click: [Start Audit]
```

---

### Phase 3: Monitor Audit Execution

#### Step 1: Watch Backend Logs
```bash
# In new terminal, watch logs
docker-compose logs backend -f
```

#### Step 2: Look for These Log Messages
```
✅ Good signs:
  "🤖 LLM Response (len=XXX): FAIL: ..."
  "✅ Parsed as FAIL: The user..."
  "💾 Saving X findings for job Y"
  "✅ Successfully saved X findings to database"

❌ Bad signs:
  "500 Server Error"
  "Failed to connect to Ollama"
  "Read timed out"
  "Cannot reach http://host.docker.internal"
```

#### Step 3: Monitor Audit Progress
Back in browser, watch the audit status:
```
Status progression:
  PENDING → SCANNING → RUNNING → COMPLETED
Progress: 0% → 20% → 50% → 90% → 100%
```

---

### Phase 4: Verify Findings

#### Step 1: Wait for Completion
```
Status: COMPLETED ✅
Progress: 100%
```

#### Step 2: Click "View Results"
```
You should see:
  - 🔍 Compliance Findings (X)
  - List of findings with:
    * Control ID (ACC-01, AUTH-01, etc.)
    * Severity badge (CRITICAL/HIGH/MEDIUM/LOW)
    * Issue description
    * [View evidence] link
```

#### Step 3: Verify Findings Count
```
Expected:
  CRITICAL: 2-3 findings
  HIGH: 1-2 findings
  MEDIUM: 0-1 findings
  LOW: 0-1 findings
  TOTAL: 5+ findings

If you see:
  "No findings - All controls passed!" ❌
  
Then something's wrong - check logs
```

---

### Phase 5: Test PDF Export

#### Step 1: In Results View, Look for Button
```
You should see:
  [📄 Download PDF Report] [← Back to History]
```

#### Step 2: Click Download Button
```
Click: [📄 Download PDF Report]

Expected:
  ✅ File downloads: audit-report-{jobId}.pdf
  ✅ Success message: "PDF report downloaded successfully!"
```

#### Step 3: Verify PDF Content
```
Open the PDF file and check:
  ✅ Page 1: Cover page with Report ID
  ✅ Page 2: Executive Summary with statistics
  ✅ Page 3+: Detailed findings
  ✅ Last pages: Audit evidence/logs
```

---

## Complete Test Checklist

### Ollama Connection ✓
- [ ] Container running: `docker-compose ps | grep ollama`
- [ ] API responds: `curl http://localhost:11434/api/tags`
- [ ] Backend config correct: `docker-compose exec backend bash -c 'echo $OLLAMA_URL'`

### Audit Creation ✓
- [ ] Can login to UI
- [ ] Can navigate to Audits tab
- [ ] Can create audit with Mock Database + GDPR_UAE
- [ ] Audit status changes from PENDING → COMPLETED

### Audit Execution ✓
- [ ] Backend logs show "🤖 LLM Response" messages
- [ ] Backend logs show "✅ Parsed as FAIL" or "✅ Parsed as PASS"
- [ ] Backend logs show "💾 Saving X findings"
- [ ] Backend logs show "✅ Successfully saved X findings"
- [ ] NO 500 errors in logs
- [ ] NO "host.docker.internal" errors

### Findings Display ✓
- [ ] Can click "View Results" without errors
- [ ] Findings section shows finding count
- [ ] Findings list is not empty (if violations found)
- [ ] Each finding shows control ID and severity
- [ ] Browser console shows "✅ Loaded X findings"

### PDF Export ✓
- [ ] Download button visible in results view
- [ ] Can click download button
- [ ] PDF file downloads to computer
- [ ] PDF file opens in reader
- [ ] PDF has cover page
- [ ] PDF has executive summary
- [ ] PDF has findings details
- [ ] PDF has remediation steps

---

## Troubleshooting by Symptom

### Symptom 1: "500 Server Error - host.docker.internal"
```
Error: 500 Server Error: Internal Server Error for url: 
  http://host.docker.internal:11434/api/generate

Solution:
  1. Stop containers: docker-compose down
  2. Check config.py line 11-12 has "http://ollama:11434"
  3. Check audit_engine.py line 28 has "http://ollama:11434"
  4. Start containers: docker-compose up -d
  5. Verify: docker-compose exec backend bash -c 'echo $OLLAMA_URL'
```

### Symptom 2: "No findings - All controls passed!"
```
Problem: Findings not being created

Diagnostics:
  1. Check backend logs: docker-compose logs backend | grep "Parsed"
  2. Check debug endpoint: curl http://localhost:8000/audit/jobs/1/debug
  3. Backend should show findings_summary.total_count > 0

Solutions:
  1. Verify Ollama is responding to requests
  2. Check LLM response format in logs
  3. Verify findings table in database has records
```

### Symptom 3: "Can't download PDF"
```
Problem: PDF download button not working

Diagnostics:
  1. Check browser console (F12): Any errors?
  2. Check audit status: Must be COMPLETED
  3. Check authorization: Must be logged in
  4. Check backend logs: Any PDF generation errors?

Solutions:
  1. Refresh page
  2. Make sure audit is COMPLETED
  3. Clear browser cache
  4. Check backend logs for errors
```

### Symptom 4: "Timeout waiting for Ollama"
```
Error: Read timed out. (read timeout=600)

Solution:
  1. Model is slow: Try llama2:latest instead
  2. Ollama not responding: Check `docker-compose ps`
  3. Network issue: Check `docker network ls`
```

---

## Performance Expectations

### Timeline
```
Audit Creation:   2 seconds
Cache Check:      1 second
LLM Discovery:    5-10 seconds
Data Loading:     2-5 seconds
Audit Execution:  30-120 seconds (depends on model & data)
Findings Save:    2 seconds
Total Time:       40-150 seconds (1-2.5 minutes)
```

### Success Indicators
```
Backend Logs:
  "🤖 LLM Response" - Model responding
  "✅ Parsed as FAIL" - Violations detected
  "💾 Saving X findings" - Persisting to DB
  "✅ Successfully saved" - Complete

Frontend:
  "✅ Loaded X findings" in console
  Findings displayed in UI
  PDF button clickable
```

---

## Database Verification

### Check Findings in Database
```bash
# Access PostgreSQL
docker-compose exec db psql -U admin -d audit_saas

# Check findings
SELECT COUNT(*) FROM findings WHERE job_id = 1;

# Should return: count > 0
```

### Check Audit Job Status
```bash
# Via API
curl http://localhost:8000/audit/jobs/1/debug \
  -H "Authorization: Bearer TOKEN"

# Look for:
# "findings_summary": { "total_count": 5 }
```

---

## Success = All Green ✅

When everything works:

```
✅ Ollama API responds (curl test)
✅ Audit completes with COMPLETED status
✅ Backend logs show LLM responses and finding creation
✅ Findings display in UI (not empty)
✅ PDF downloads successfully
✅ PDF opens and shows all sections
✅ Browser console shows "✅ Loaded X findings"
✅ No 500 errors, timeouts, or connection errors
```

---

## Quick Reference

### Key Commands
```bash
# Check status
docker-compose ps

# View logs
docker-compose logs backend -f

# Restart
docker-compose restart backend

# Full restart
docker-compose down
docker-compose up -d

# Test Ollama
curl http://localhost:11434/api/tags

# Check URL configuration
docker-compose exec backend bash -c 'echo $OLLAMA_URL'
```

### Key Endpoints
```
Frontend:     http://localhost:3000
Backend:      http://localhost:8000
Ollama:       http://localhost:11434
pgAdmin:      http://localhost:5050
Database:     localhost:5432
```

### Expected Findings
```
With Sample Data (Mock Database + GDPR_UAE):
  - ACC-01: Admin access without logging (CRITICAL)
  - ACC-02: Access control gaps (CRITICAL)
  - AUTH-01: Weak authentication (HIGH)
  - DLP-01: Data protection issues (MEDIUM)
  - SEC-01: Security gaps (MEDIUM)
  - Plus 1-2 more depending on sample data
```

---

## Still Having Issues?

1. **Check logs**: `docker-compose logs backend -f`
2. **Check config**: `docker-compose exec backend bash -c 'echo $OLLAMA_URL'`
3. **Check network**: `docker network ls` & `docker inspect audit-network`
4. **Restart fresh**: `docker-compose down -v && docker-compose up -d`
5. **Check container health**: All should show "Up (healthy)" not "Unhealthy"

---

**Status**: ✅ Ready to test
**Last Updated**: May 2026
**Expected Result**: All tests pass with findings and PDF download working
