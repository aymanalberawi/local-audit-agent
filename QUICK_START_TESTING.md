# Quick Start: Testing Connection Testing Feature

## Prerequisites
✅ Backend running on http://localhost:8000
✅ Frontend running on http://localhost:3000
✅ Logged in with admin@example.com / password

## Test Scenario 1: View Connection Status on Dashboard (2 minutes)

### Steps:
1. Open http://localhost:3000/ in browser
2. You should see Dashboard with "Data Connections" section
3. Look at the connection list

### Expected Results:
- Each connection displays a **colored status badge**
- Status shows one of: ✓ Active, ✗ Failed, ⊘ Inactive, ? Not Tested
- Connection colors: 🟢 Green, 🔴 Red, 🟡 Orange, ⚫ Gray

### ✓ Test Passes If:
- Connections visible with status badges
- Colors match status (green = active, red = failed, etc.)

---

## Test Scenario 2: Create Connection with Auto-Testing (5 minutes)

### Steps:
1. From Dashboard, click on any **company name**
2. Scroll to "Data Connections" section
3. Click **"+ Add Connection"** button
4. Fill in the form:
   - **Name**: `Test Connection 1`
   - **Type**: `MOCK_DB` (easiest for testing)
   - **Application**: Select from dropdown
   - **Connection String**: Leave empty
5. Click **"Save"**

### Expected Results:
- Connection appears in the list immediately
- Status shows **✓ Active** (green badge)
- Shows "Last tested" with current timestamp

### ✓ Test Passes If:
- Connection created successfully
- Auto-test happens (no manual action needed)
- Status shows ACTIVE with timestamp

---

## Test Scenario 3: Manual Connection Testing (3 minutes)

### Steps:
1. On Company page, find the connection you just created
2. Locate the **"Test" button** (appears between connection details and Edit/Delete)
3. Click the **"Test"** button
4. Wait for response

### Expected Results:
- Brief success message appears
- Status remains **✓ Active**
- **"Last tested"** timestamp updates to current time

### ✓ Test Passes If:
- Test completes within 5 seconds
- Status updates with new timestamp
- No error messages appear

---

## Test Scenario 4: Test Different Connection Types (10 minutes)

### Test FILE Connection:
1. Create new connection:
   - **Name**: `Test File`
   - **Type**: `FILE`
   - **Connection String**: `/etc/hosts` (or similar readable file)
2. Click Save
3. **Expected**: Status = ✓ ACTIVE (file exists and readable)

### Test API Connection:
1. Create new connection:
   - **Name**: `Test API`
   - **Type**: `API`
   - **Connection String**: `https://api.github.com`
2. Click Save
3. **Expected**: Status = ✓ ACTIVE (GitHub API is reachable)

### Test POSTGRESQL Connection:
1. Create new connection:
   - **Name**: `Test Database`
   - **Type**: `POSTGRESQL`
   - **Connection String**: `postgresql://postgres:postgres@db:5432/postgres`
2. Click Save
3. **Expected**: Status = ✓ ACTIVE (if database running locally)

### Test MOCK_DB Connection:
1. Create new connection:
   - **Name**: `Test Mock`
   - **Type**: `MOCK_DB`
   - **Connection String**: (leave empty)
2. Click Save
3. **Expected**: Status = ✓ ACTIVE (always succeeds)

---

## Test Scenario 5: Error Handling (5 minutes)

### Test Invalid FILE:
1. Create connection:
   - **Name**: `Bad File`
   - **Type**: `FILE`
   - **Connection String**: `/nonexistent/file/path`
2. Click Save
3. **Expected Results**:
   - Status = ✗ FAILED (red badge)
   - Error message visible in red box
   - Message explains file not found

### Test Invalid API:
1. Create connection:
   - **Name**: `Bad API`
   - **Type**: `API`
   - **Connection String**: `https://invalid-api-that-does-not-exist.local`
2. Click Save
3. **Expected Results**:
   - Status = ✗ FAILED (red badge)
   - Error message displays
   - Message explains connection error

### Test Invalid Database:
1. Create connection:
   - **Name**: `Bad Database`
   - **Type**: `POSTGRESQL`
   - **Connection String**: `postgresql://wrong:password@nonexistent:5432/db`
2. Click Save
3. **Expected Results**:
   - Status = ✗ FAILED (red badge)
   - Error message shows connection error
   - Shows it's retryable (user can click Test later)

### ✓ Test Passes If:
- Failed connections show red badge
- Error messages are informative
- No system errors or crashes

---

## Test Scenario 6: Dashboard Reflects Changes (3 minutes)

### Steps:
1. Create connection(s) on Company page
2. Navigate back to Dashboard
3. Look at "Data Connections" section
4. Refresh page with F5

### Expected Results:
- New connections appear in list
- Status matches what was on Company page
- All status indicators are current

### ✓ Test Passes If:
- Dashboard shows all created connections
- Status information is accurate and current
- Real-time sync works

---

## Test Scenario 7: Connection Status Colors (2 minutes)

### Verify Color Coding:
1. Find connections with different statuses
2. Check each color matches its status:

| Status | Color | Icon |
|--------|-------|------|
| ACTIVE | 🟢 Green | ✓ |
| FAILED | 🔴 Red | ✗ |
| INACTIVE | 🟡 Orange | ⊘ |
| NOT_TESTED | ⚫ Gray | ? |

### ✓ Test Passes If:
- Colors are distinct and easy to identify
- All four status types show different colors
- Colors are consistent across pages

---

## Troubleshooting

### Problem: "Connection refused" errors
**Solution**: Ensure database is running
```bash
docker-compose ps
# Should show all services "Up"
```

### Problem: Status not updating
**Solution**: Refresh page with F5

### Problem: "requests" module error
**Solution**: Rebuild backend image
```bash
docker-compose down
docker-compose build backend
docker-compose up -d
```

### Problem: Can't create connection
**Solution**: Make sure you're logged in as admin

### Problem: Test button not visible
**Solution**: 
- Refresh page (F5)
- Clear browser cache
- Try different browser

---

## Success Criteria

✅ All 7 test scenarios pass
✅ No error messages or crashes
✅ Status updates correctly
✅ All connection types work
✅ Error handling works properly
✅ Colors are correct
✅ Dashboard reflects changes

## Expected Timeframe
- Total testing: 30-45 minutes
- Each scenario: 2-10 minutes

## Documentation Links
- Full guide: `CONNECTION_TESTING_GUIDE.md`
- Implementation details: `IMPLEMENTATION_SUMMARY.md`
- Backend logs: `docker-compose logs backend`

---

Ready to test? Start with **Test Scenario 1: View Connection Status on Dashboard**
