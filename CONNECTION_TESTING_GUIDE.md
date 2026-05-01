# Connection Testing & Status Tracking Implementation Guide

## Overview
The Local Audit Agent now includes comprehensive connection testing with real-time status tracking across all supported data sources.

## Implemented Features

### 1. Automatic Connection Testing
- **When**: Connections are automatically tested upon creation
- **Where**: `/backend/routers/hierarchy.py` - `POST /hierarchy/connections/`
- **What**: Tests connection viability and stores status in database

### 2. Manual Connection Testing
- **Where**: Company Management Page (`/companies/{id}`)
- **How**: Click the "Test" button on any connection card
- **Endpoint**: `POST /hierarchy/connections/{conn_id}/test`
- **Feedback**: Success/error message displayed and data refreshed

### 3. Status Tracking
Four-state connection status system:
- **✓ ACTIVE** (Green #00ff00) - Connection successful
- **✗ FAILED** (Red #ff0000) - Connection failed, error displayed
- **⊘ INACTIVE** (Orange #ffaa00) - Connection exists but not tested recently
- **? NOT_TESTED** (Gray #999999) - Never tested

### 4. Supported Connection Types

| Type | Testing Method | Use Case |
|------|---|---|
| **FILE** | Check existence, readability, size | CSV/Excel imports |
| **API** | HTTP HEAD request with 5s timeout | REST APIs |
| **POSTGRESQL** | SQLAlchemy connection + SELECT 1 | PostgreSQL databases |
| **SQL_SERVER** | ODBC driver + SELECT 1 | SQL Server databases |
| **ORACLE** | cx_oracle + SELECT 1 | Oracle databases |
| **MOCK_DB** | Always succeeds | Testing/demo |

## Testing This Feature

### Test Plan

#### 1. Dashboard View
1. Navigate to http://localhost:3000/
2. Login with admin@example.com / password
3. View "Data Connections" section
4. **Expected**: Should see connection names with status badges

#### 2. Create & Auto-Test Connection
1. Click on a company name to go to Company Management page
2. Create a new application (if needed)
3. Click "+ Add Connection"
4. Fill in connection details:
   - **Name**: Test Connection
   - **Type**: MOCK_DB (easiest for testing)
   - **Application**: Select one
   - **Connection String**: (leave empty for MOCK_DB)
5. Click "Save"
6. **Expected**: 
   - Connection created successfully
   - Status badge shows "✓ Active" (green)
   - "Last tested" timestamp is current

#### 3. Manual Connection Test
1. On the company page, find the connection you created
2. Click the "Test" button next to the connection
3. **Expected**:
   - Success message appears briefly
   - Status updates (should remain Active if successful)
   - "Last tested" timestamp updates

#### 4. Test Each Connection Type

**FILE Connection:**
1. Create FILE connection
2. Connection String: `/path/to/existing/file.csv`
3. Expected: ACTIVE if file exists and is readable

**API Connection:**
1. Create API connection
2. Connection String: `https://api.github.com`
3. Expected: ACTIVE (GitHub API is reachable)

**PostgreSQL Connection:**
1. Create POSTGRESQL connection
2. Connection String: `postgresql://postgres:password@localhost:5432/postgres`
3. Expected: ACTIVE if database is running

**SQL_SERVER Connection:**
1. Create SQL_SERVER connection
2. Connection String: `user:password@server:1433/database`
3. Expected: FAILED if not available (expected in dev environment)

**ORACLE Connection:**
1. Create ORACLE connection
2. Connection String: `user:password@localhost:1521/orcl`
3. Expected: FAILED if not available (expected in dev environment)

#### 5. Test Error Handling
1. Create a connection with invalid credentials or bad URL
2. Try to test it
3. **Expected**: 
   - Status shows "✗ Failed" (red)
   - Error message displays in red box
   - Error message is clear and helpful

#### 6. Dashboard Updates
1. Create a new connection via Company page
2. Navigate back to Dashboard
3. View "Data Connections" section
4. **Expected**: New connection appears with correct status

## Implementation Details

### Backend Service (`/backend/services/connection_tester.py`)

```python
test_connection(connection_type: str, connection_string: str) 
  → (ConnectionStatus, error_message)
```

**Features:**
- Type-specific testing logic for each connection type
- 5-second timeout for API connections
- Comprehensive error handling
- Error message truncation (max 200 chars)
- Returns tuple of (status enum, error string)

### Database Schema
```python
Connection model fields:
- status: Enum(ACTIVE, INACTIVE, FAILED, NOT_TESTED)
- status_message: Optional[str] (null if ACTIVE)
- last_tested_at: DateTime
```

### API Endpoints

**Create Connection** (Auto-Test):
```
POST /hierarchy/connections/
Request: {name, type, application_id, connection_string}
Response: Connection with status, status_message, last_tested_at
```

**Manual Test**:
```
POST /hierarchy/connections/{conn_id}/test
Response: {id, status, message, last_tested_at}
```

**Get Connections**:
```
GET /hierarchy/connections/
Response: [Connection with status fields...]
```

### Frontend Components

**Company Page** (`/companies/{id}`):
- Connection status badge with emoji icon
- Color-coded status indicator
- Last tested timestamp
- Error message display (if FAILED)
- Test button for manual retesting

**Dashboard** (`/`):
- Connection status in Data Connections section
- Status-based color coding
- Click through to Company page for details

## Troubleshooting

### Connection Test Timing Out
- File connections: Check file path exists and is readable
- API connections: Ensure URL is valid and endpoint is reachable
- DB connections: Verify connection string format and server availability

### "Module not found" Error
- If you see "requests" module error, the backend Docker image needs rebuilding:
  ```bash
  docker-compose down
  docker image rm local-audit-agent-backend
  docker-compose build backend
  docker-compose up -d
  ```

### Connection Status Not Updating
- Refresh the page with F5
- Check browser console for API errors
- Check backend logs: `docker-compose logs backend`

## Database Migration Notes
- Connection status fields are nullable for backward compatibility
- Existing connections will have `status = NOT_TESTED` initially
- First manual test will populate status fields

## Next Steps
- Implement connection pooling for frequently tested connections
- Add connection retry logic with exponential backoff
- Create bulk test endpoint for testing all connections at once
- Add connection history/audit trail
- Implement webhook notifications for status changes
