# File Connection Testing Guide

## Issues Fixed

### 1. **Enum Serialization Issue**
**Problem**: The connection type enum was not being properly serialized to JSON, causing the frontend to not recognize FILE type connections.

**Fix**: Updated `backend/routers/hierarchy.py` to explicitly extract enum values:
```python
"type": c.type.value if isinstance(c.type, ConnectionType) else c.type
```

**Impact**: Frontend can now correctly identify FILE connections and show the file upload toggle.

---

### 2. **File Connection Testing Issue**
**Problem**: FILE connection tests were failing if the file didn't exist at connection creation time, causing connections to show error status. However, for FILE connections, the file is provided during audit creation, not during connection setup.

**Fix**: Updated `backend/services/connection_tester.py` to allow FILE connections without requiring the file to exist at test time.

**Impact**: FILE connections now show ACTIVE status when created, and users can upload/provide files when creating audits.

---

### 3. **File Audit Progress Tracking**
**Problem**: The progress endpoint had hardcoded stages for full audits only (CHECKING_CACHE, DISCOVERING, LOADING_DATA). FILE audits use different stages (LOADING_FILE), causing all stages to show as pending.

**Fix**: Updated `backend/routers/audit.py` to detect file-based audits and show appropriate stages:
- File audits: PENDING → LOADING_FILE → AUDITING → SAVING_RESULTS → COMPLETED
- Full audits: PENDING → CHECKING_CACHE → DISCOVERING → LOADING_DATA → AUDITING → SAVING_RESULTS → COMPLETED

**Impact**: File audit progress now displays correctly in the UI.

---

## Testing Workflow

### Step 1: Login
1. Navigate to http://localhost:3000/login
2. Use credentials:
   - Email: `admin@example.com`
   - Password: `password`

### Step 2: Create a Company and Application (First Time Only)
1. Click "Setup" or navigate to /onboarding
2. Create a company (e.g., "Test Company")
3. Create an application (e.g., "Test App")
4. Create a FILE connection:
   - **Name**: "Test Files" or any name
   - **Type**: "Excel/CSV File"
   - **Path**: Leave empty or enter "/tmp/test.csv" (file doesn't need to exist!)
   - Click "Create Connection"
   - **Result**: Should show "Connection created successfully!" and connection should show ACTIVE status

### Step 3: Create an Audit with File Upload
1. Navigate to Audits page
2. Click "Create Audit" tab
3. Select your FILE connection from the dropdown
4. **Toggle should appear** with two buttons:
   - "File System Path" (for server-side files)
   - "Upload File" (for user uploads)
5. Click "Upload File"
6. Drag/drop or click to select a CSV/Excel file
7. Select an audit standard
8. Click "Create Audit"
9. **Expected result**: 
   - File should upload successfully
   - Audit job should start
   - Progress should show FILE audit stages
   - Results should display after completion

### Step 4: Create an Audit with File Path
1. Navigate to Audits page
2. Click "Create Audit" tab
3. Select your FILE connection
4. Toggle should be on "File System Path"
5. Enter a valid file path (e.g., `/var/data/users.csv`)
6. Click "Create Audit"
7. **Expected result**: Audit starts and processes the file from the specified path

---

## Test File

A test CSV file is included: `C:\local-audit-agent\test_data.csv`

```csv
user_id,username,email,is_admin,created_at
1,john_doe,john@example.com,false,2026-01-15
2,jane_smith,jane@example.com,true,2026-02-20
3,bob_wilson,bob@example.com,false,2026-03-10
4,alice_johnson,alice@example.com,false,2026-04-01
5,charlie_brown,charlie@example.com,false,2026-04-15
```

This file will be processed by the audit engine to check compliance against selected standards.

---

## Expected Behavior After Fixes

### Connection Creation
✅ FILE connections created successfully  
✅ Connections show ACTIVE status (not error)  
✅ Connection can be tested without requiring file to exist  

### Audit Creation
✅ FILE connection selected → upload toggle appears  
✅ Can toggle between "File System Path" and "Upload File"  
✅ File upload works without errors  
✅ File path input works for server-side files  

### Audit Execution
✅ File is loaded correctly (CSV or Excel)  
✅ Controls are evaluated against file data  
✅ Progress shows FILE audit stages  
✅ Findings are saved correctly  
✅ Results can be viewed after completion  

### Error Handling
✅ Invalid file formats rejected  
✅ Missing files show appropriate error message  
✅ Empty files rejected  
✅ Large files handled gracefully  

---

## API Endpoints for Testing

### Get Connections
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/hierarchy/connections
```

Expected response shows connections with `"type": "FILE"` (string, not object).

### Upload File
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test_data.csv" \
  http://localhost:8000/audit/upload
```

Expected response:
```json
{
  "success": true,
  "file_id": "uuid-string",
  "filename": "test_data.csv",
  "size": 250
}
```

### Start Audit with Uploaded File
```bash
curl -X POST \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "connection_id": 1,
    "standard": "GDPR-UAE",
    "uploaded_file_id": "FILE_ID_FROM_UPLOAD"
  }' \
  http://localhost:8000/audit/start
```

### Get Audit Progress
```bash
curl -H "Authorization: Bearer YOUR_TOKEN" \
  http://localhost:8000/audit/jobs/1/progress
```

Expected response shows FILE audit stages.

---

## Troubleshooting

### Issue: Upload toggle not showing
**Solution**: 
1. Verify FILE connection is created and selected
2. Check browser console for errors
3. Verify backend enum fix is applied (check docker logs)

### Issue: "Invalid file format" error
**Solution**:
1. Ensure file is .csv, .xlsx, or .xls
2. Check file has valid data (not empty)
3. Verify file encoding (UTF-8 recommended)

### Issue: Connection shows error status
**Solution**:
1. This should be fixed by the file connection tester update
2. Restart backend: `docker-compose restart backend`
3. Create new FILE connection (files don't need to exist)

### Issue: Audit stuck on LOADING_FILE stage
**Solution**:
1. Check worker logs: `docker logs audit_worker --tail 50`
2. Verify file exists at specified path
3. Check file has valid CSV/Excel format

---

## Next Steps

After verifying all fixes work:
1. Test with multiple file formats (CSV, XLSX, XLS)
2. Test with various data types and sizes
3. Test error cases (invalid files, missing files, etc.)
4. Verify findings are generated correctly
5. Test file cleanup after audit completion
