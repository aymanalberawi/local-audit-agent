#!/bin/bash

# Test script to debug findings not showing in audit results
# This script will:
# 1. Run an audit on the mock database
# 2. Wait for completion
# 3. Check the debug endpoint to see what findings were created
# 4. Check the findings endpoint to see what's returned

set -e

API_URL="http://localhost:8000"
ADMIN_EMAIL="admin@example.com"
ADMIN_PASSWORD="password"

echo "🔧 Testing Findings Debug..."
echo ""

# Step 1: Get auth token
echo "1️⃣ Getting auth token..."
TOKEN_RESPONSE=$(curl -s -X POST "$API_URL/auth/login" \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASSWORD\"}")

TOKEN=$(echo $TOKEN_RESPONSE | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)
if [ -z "$TOKEN" ]; then
  echo "❌ Failed to get auth token"
  echo "Response: $TOKEN_RESPONSE"
  exit 1
fi
echo "✅ Got token: ${TOKEN:0:20}..."
echo ""

# Step 2: List connections to find mock database
echo "2️⃣ Finding mock database connection..."
CONNECTIONS=$(curl -s -X GET "$API_URL/hierarchy/connections" \
  -H "Authorization: Bearer $TOKEN")

echo "Connections: $CONNECTIONS" | head -c 200
echo ""

# Extract first connection ID (usually mock database)
CONN_ID=$(echo $CONNECTIONS | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
if [ -z "$CONN_ID" ]; then
  echo "❌ No connections found"
  exit 1
fi
echo "✅ Using connection ID: $CONN_ID"
echo ""

# Step 3: Start an audit
echo "3️⃣ Starting audit on GDPR_UAE standard..."
AUDIT_RESPONSE=$(curl -s -X POST "$API_URL/audit/jobs" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"connection_id\":$CONN_ID,\"standard_name\":\"GDPR_UAE\"}")

echo "Audit Response: $AUDIT_RESPONSE"
JOB_ID=$(echo $AUDIT_RESPONSE | grep -o '"job_id":[0-9]*' | cut -d':' -f2)
if [ -z "$JOB_ID" ]; then
  JOB_ID=$(echo $AUDIT_RESPONSE | grep -o '"id":[0-9]*' | head -1 | cut -d':' -f2)
fi

if [ -z "$JOB_ID" ]; then
  echo "❌ Failed to create audit job"
  exit 1
fi
echo "✅ Created audit job: $JOB_ID"
echo ""

# Step 4: Wait for completion
echo "4️⃣ Waiting for audit to complete (max 2 minutes)..."
ATTEMPTS=0
MAX_ATTEMPTS=24  # 2 minutes with 5 second checks

while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
  PROGRESS=$(curl -s -X GET "$API_URL/audit/jobs/$JOB_ID/progress" \
    -H "Authorization: Bearer $TOKEN")

  STATUS=$(echo $PROGRESS | grep -o '"status":"[^"]*' | head -1 | cut -d'"' -f4)
  PERCENT=$(echo $PROGRESS | grep -o '"progress_percentage":[0-9.]*' | cut -d':' -f2)

  printf "\r⏳ Status: $STATUS | Progress: $PERCENT%%"

  if [ "$STATUS" = "COMPLETED" ] || [ "$STATUS" = "FAILED" ]; then
    echo ""
    echo ""
    break
  fi

  ATTEMPTS=$((ATTEMPTS + 1))
  sleep 5
done

if [ $ATTEMPTS -eq $MAX_ATTEMPTS ]; then
  echo ""
  echo "❌ Audit timeout"
  exit 1
fi

echo "✅ Audit completed with status: $STATUS"
echo ""

# Step 5: Check debug endpoint
echo "5️⃣ Checking audit debug info..."
DEBUG=$(curl -s -X GET "$API_URL/audit/jobs/$JOB_ID/debug" \
  -H "Authorization: Bearer $TOKEN")

echo "Debug Info:"
echo "$DEBUG" | jq '.' 2>/dev/null || echo "$DEBUG"
echo ""

# Step 6: Check findings endpoint
echo "6️⃣ Checking findings endpoint..."
FINDINGS=$(curl -s -X GET "$API_URL/audit/jobs/$JOB_ID/findings" \
  -H "Authorization: Bearer $TOKEN")

echo "Findings:"
echo "$FINDINGS" | jq '.' 2>/dev/null || echo "$FINDINGS"
echo ""

# Step 7: Check audit summary (sample data)
echo "7️⃣ Checking audit summary (sample data with violations)..."
SUMMARY=$(curl -s -X GET "$API_URL/audit/jobs/$JOB_ID/summary" \
  -H "Authorization: Bearer $TOKEN")

echo "Summary (first 500 chars):"
echo "$SUMMARY" | head -c 500
echo ""
echo ""

echo "✅ Test complete!"
echo ""
echo "📊 Summary:"
echo "- Job ID: $JOB_ID"
echo "- Final Status: $STATUS"
echo "- Findings Count: $(echo $FINDINGS | grep -o '"id":' | wc -l)"
echo "- Debug Data: Check output above"
