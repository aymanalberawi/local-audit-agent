# Ollama Connection Fix - 500 Server Error

## Problem
```
500 Server Error: Internal Server Error for url: http://host.docker.internal:11434/api/generate
```

## Root Cause
The code was using `host.docker.internal` which doesn't work in Docker containers. It should use `ollama` (the container service name) instead.

## What Was Fixed

### Files Updated:
1. **`backend/core/config.py`** (line 11-12)
   - ❌ Before: `OLLAMA_URL: str = "http://host.docker.internal:11434"`
   - ✅ After: `OLLAMA_URL: str = "http://ollama:11434"`
   - Also changed default model to `llama2:latest` (commonly available)

2. **`backend/services/audit_engine.py`** (line 28)
   - ❌ Before: `OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://host.docker.internal:11434")`
   - ✅ After: `OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://ollama:11434")`

## How to Fix

### Step 1: Restart Docker Containers
```bash
# Stop all containers
docker-compose down

# Start fresh (will pick up new configuration)
docker-compose up -d

# Verify Ollama is running
docker-compose ps | grep ollama
```

### Step 2: Verify Connection
```bash
# Check if Ollama is healthy
curl http://localhost:11434/api/tags

# Should return JSON list of models like:
# {"models":[{"name":"llama2:latest","size":3826087936}]}
```

### Step 3: Test an Audit
1. Go to Audits tab
2. Create new audit (Mock Database + GDPR_UAE)
3. Monitor backend logs:
   ```bash
   docker-compose logs backend -f
   ```
4. Look for success logs:
   ```
   ✅ Parsed as FAIL: The user has admin access...
   ```

## Why This Happened

In Docker:
- ❌ `host.docker.internal` - Points to host machine (outside containers)
- ❌ `localhost` - Points to the container itself
- ✅ `ollama` - Points to the ollama container service via Docker DNS

The docker-compose.yml had the correct URL (`http://ollama:11434`), but the fallback defaults in the Python code were wrong.

## Verification

### Check Backend Configuration
```bash
docker-compose exec backend env | grep OLLAMA_URL
# Should output: OLLAMA_URL=http://ollama:11434
```

### Check Ollama Container
```bash
# Verify ollama container is running
docker-compose ps

# Output should show:
# 00-llm-ollama-engine    Up (healthy)
```

### Test Ollama API Directly
```bash
# From your host machine
curl http://localhost:11434/api/tags

# From inside backend container
docker-compose exec backend curl http://ollama:11434/api/tags
```

## If Still Not Working

### Check 1: Ollama Container Is Running
```bash
docker-compose logs ollama

# Should show model loading/serving messages
# NOT error messages
```

### Check 2: Network Connectivity
```bash
docker-compose exec backend ping ollama

# Should show:
# PING ollama (172.x.x.x) 56(84) bytes of data
# 64 bytes from ollama: icmp_seq=1 ttl=64 time=...
```

### Check 3: API Endpoint Responds
```bash
docker-compose exec backend curl -v http://ollama:11434/api/tags

# Should show:
# * Trying 172.x.x.x:11434...
# * Connected to ollama (172.x.x.x) port 11434 (#0)
# < HTTP/1.1 200 OK
```

### Check 4: Restart Everything
```bash
# Full restart with clean state
docker-compose down -v
docker-compose up -d

# Wait for health checks
docker-compose ps

# Should all show "Up (healthy)"
```

## Quick Checklist

- [ ] Files updated (config.py, audit_engine.py)
- [ ] Containers restarted (`docker-compose down && up -d`)
- [ ] Ollama container running and healthy
- [ ] Can curl ollama from host: `curl http://localhost:11434/api/tags`
- [ ] Run test audit
- [ ] Check backend logs for success

## Summary

**What changed**: Two files now point to the correct containerized Ollama URL
**What to do**: Restart Docker containers with `docker-compose restart`
**Expected result**: Audits now connect to Ollama and generate findings

After restart, audits should work normally and return findings instead of 500 errors.
