# 🐳 Fully Containerized Local Audit Agent - Complete Setup Guide

## Overview

The **Local Audit Agent** is now **100% containerized** with Docker. Every service runs in containers - no host dependencies required except Docker itself.

### Included Services:
- ✅ **Ollama** (11434) - Local LLM engine
- ✅ **PostgreSQL + pgvector** (5432) - Main database
- ✅ **Redis** (6379) - Message broker & cache
- ✅ **FastAPI Backend** (8000) - REST API
- ✅ **Celery Worker** - Background job processing
- ✅ **Celery Beat** - Scheduled task scheduler
- ✅ **Next.js Frontend** (3000) - Web UI
- ✅ **pgAdmin** (5050) - Database management UI
- ✅ **Oracle** (1521) - Optional test database

---

## Quick Start

### Prerequisites
```bash
# Install Docker and Docker Compose
# https://docs.docker.com/get-docker/
# Requires: Docker 20.10+ and Docker Compose 2.0+

docker --version
docker-compose --version
```

### 1. Start All Services (One Command)
```bash
cd /path/to/local-audit-agent

# Start all containers
docker-compose up -d

# Verify all containers are running
docker-compose ps
```

**Expected output:**
```
NAME                                    STATUS
00-llm-ollama-engine                    Up (healthy)
01-data-postgresql-primary              Up (healthy)
02-cache-redis-broker                   Up (healthy)
03-api-fastapi-server                   Up (healthy)
04-worker-celery-tasks                  Up
04b-scheduler-celery-beat               Up
05-ui-nextjs-react                      Up (healthy)
07-admin-pgadmin-ui                     Up
08-test-database-oracle                 Up
```

### 2. Access the Application

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | admin@example.com / password |
| **API Docs** | http://localhost:8000/docs | admin@example.com / password |
| **pgAdmin** | http://localhost:5050 | admin@local.dev / admin |
| **Ollama** | http://localhost:11434 | N/A |

### 3. Initialize Data (Automatic)
- Database schema created automatically
- Default admin user created: `admin@example.com` / `password`
- Audit standards imported from JSON files
- Initial LLM model: `llama2:latest`

---

## Service Details

### Ollama (LLM Engine)
```bash
# Pull additional models inside Ollama container
docker-compose exec ollama ollama pull llama2:latest
docker-compose exec ollama ollama pull neural-chat:latest
docker-compose exec ollama ollama pull qwen2.5-coder:7b

# List available models
docker-compose exec ollama ollama list

# Access Ollama API
curl http://localhost:11434/api/tags
```

### PostgreSQL Database
```bash
# Connect to database directly
docker-compose exec db psql -U admin -d audit_saas

# List tables
\dt

# Exit
\q
```

### Redis Cache
```bash
# Access Redis CLI
docker-compose exec redis redis-cli

# Check keys
KEYS *

# Check memory usage
INFO memory
```

### Backend API
```bash
# View logs
docker-compose logs backend

# Run migrations manually
docker-compose exec backend python -m alembic upgrade head

# Access bash
docker-compose exec backend bash
```

### Celery Worker
```bash
# View worker logs
docker-compose logs worker

# Access worker bash
docker-compose exec worker bash
```

### Celery Beat (Scheduler)
```bash
# View scheduler logs
docker-compose logs scheduler

# Check scheduled tasks
docker-compose exec scheduler celery -A worker.celery_app inspect scheduled
```

### Frontend (Next.js)
```bash
# View frontend logs
docker-compose logs frontend

# Rebuild frontend
docker-compose build frontend
docker-compose up -d frontend
```

### pgAdmin
```
URL: http://localhost:5050
Email: admin@local.dev
Password: admin

# Add PostgreSQL connection:
- Host: db
- Port: 5432
- Username: admin
- Password: password
- Database: audit_saas
```

---

## Common Tasks

### 1. Rebuild All Containers
```bash
# Rebuild and restart all services
docker-compose build
docker-compose up -d
```

### 2. View All Logs
```bash
# All logs
docker-compose logs -f

# Specific service
docker-compose logs -f backend
docker-compose logs -f worker
docker-compose logs -f frontend
```

### 3. Stop All Services
```bash
docker-compose down
```

### 4. Stop and Remove Data (Reset)
```bash
# ⚠️ WARNING: This deletes all audit data!
docker-compose down -v
```

### 5. Check Service Health
```bash
# All services
docker-compose ps

# Detailed health status
docker-compose ps --all

# Specific service health
docker-compose exec backend curl http://localhost:8000/health
docker-compose exec ollama curl http://localhost:11434/api/tags
```

### 6. Execute Commands in Containers
```bash
# Run command in backend
docker-compose exec backend python -c "print('Hello')"

# Run command in Ollama
docker-compose exec ollama ollama list

# Access interactive shell
docker-compose exec backend bash
docker-compose exec worker bash
docker-compose exec frontend sh
```

---

## Environment Variables

### Backend & Worker Services
Create `.env` file in project root:

```env
# Database
DATABASE_URL=postgresql://admin:password@db:5432/audit_saas

# Redis
REDIS_URL=redis://redis:6379/0

# Ollama LLM
OLLAMA_URL=http://ollama:11434
OLLAMA_MODEL=llama2:latest

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
```

**Note:** Environment variables are automatically set in docker-compose.yml. Only create `.env` if you need to override defaults.

---

## Network Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  audit-network (Docker Bridge)               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │
│  │ Ollama   │  │ Database │  │  Redis   │  │ Frontend │  │
│  │ :11434   │  │  :5432   │  │  :6379   │  │ :3000    │  │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │
│       ▲            ▲             ▲             ▲           │
│       │            │             │             │           │
│  ┌────────────────────────────────────────────────────┐   │
│  │         FastAPI Backend + Worker                    │   │
│  │  - Orchestrates all services                        │   │
│  │  - Communicates internally via service names       │   │
│  │  - Port 8000 exposed to host                       │   │
│  └────────────────────────────────────────────────────┘   │
│       ▲                                                     │
│       │                                                     │
│  ┌──────────────────────────────────┐                     │
│  │  pgAdmin UI  &  Optional Oracle  │                     │
│  └──────────────────────────────────┘                     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
         ▲
         │ (Network bridge - external access)
         │
    ┌────────────┐
    │  Host OS   │
    │ :3000 ──→ Frontend
    │ :8000 ──→ Backend
    │ :5050 ──→ pgAdmin
    │ :11434 ──→ Ollama
    └────────────┘
```

---

## Volumes (Persistent Storage)

All data persists across container restarts:

| Volume | Purpose | Path |
|--------|---------|------|
| `pgdata` | PostgreSQL data | `/var/lib/postgresql/data` |
| `redis-data` | Redis persistent storage | `/data` |
| `ollama-data` | Ollama models & data | `/root/.ollama` |
| `backend-uploads` | User uploaded files | `/app/uploads` |
| `pgadmin-data` | pgAdmin configuration | `/var/lib/pgadmin` |
| `oracle-data` | Oracle test database | `/opt/oracle/oradata` |

---

## Scaling Up (Production Deployment)

### Deploy to Production Server

**Option 1: Direct Docker Compose**
```bash
# On production server
git clone https://github.com/your-org/local-audit-agent.git
cd local-audit-agent

# Change to production environment variables
# Edit .env with production database, Ollama URLs, etc.

# Start services
docker-compose -f docker-compose.prod.yml up -d
```

**Option 2: Kubernetes (K8s)**
```bash
# Generate Kubernetes manifests from docker-compose
docker-compose convert > kubernetes-manifest.yaml

# Deploy to K8s cluster
kubectl apply -f kubernetes-manifest.yaml
```

**Option 3: AWS/Azure/GCP**
- Use managed database services (RDS, Cloud SQL)
- Use containerized orchestration (ECS, AKS, Cloud Run)
- Reference internal DNS names in docker-compose

---

## Troubleshooting

### Service Won't Start
```bash
# Check logs
docker-compose logs -f [service_name]

# Verify health status
docker-compose ps

# Restart service
docker-compose restart [service_name]
```

### Database Connection Error
```bash
# Check PostgreSQL is running
docker-compose exec db pg_isready

# Check database exists
docker-compose exec db psql -U admin -l
```

### Ollama Not Responding
```bash
# Check Ollama health
docker-compose exec ollama ollama serve

# Check Ollama logs
docker-compose logs ollama

# Restart Ollama
docker-compose restart ollama
```

### Frontend Can't Connect to Backend
```bash
# Check network connectivity
docker-compose exec frontend curl -v http://backend:8000/health

# Verify DNS resolution
docker-compose exec frontend nslookup backend
```

### Redis Connection Error
```bash
# Check Redis health
docker-compose exec redis redis-cli ping

# View Redis logs
docker-compose logs redis
```

---

## Stopping & Cleanup

### Graceful Stop
```bash
# Stop all containers (preserves data)
docker-compose down
```

### Full Reset (Delete All Data)
```bash
# ⚠️ WARNING: Deletes ALL audit data permanently!
docker-compose down -v

# Also remove images (rebuild needed next time)
docker-compose down -v --rmi all
```

### Remove Unused Resources
```bash
# Remove stopped containers
docker container prune

# Remove unused volumes
docker volume prune

# Remove unused networks
docker network prune

# Full cleanup (safe)
docker system prune
```

---

## Performance Tuning

### Increase Worker Concurrency
Edit `docker-compose.yml`, worker service:
```yaml
command: celery -A worker.celery_app worker --loglevel=info -Q main-queue,scheduler-queue,celery --concurrency=4
```

### Database Connection Pool
Edit backend environment:
```env
DATABASE_POOL_SIZE=20
DATABASE_POOL_RECYCLE=3600
```

### Redis Memory Limit
Edit redis service in docker-compose.yml:
```yaml
command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
```

---

## Security Considerations

### Before Production Deployment:

1. **Change Default Passwords**
   ```bash
   # Update in docker-compose.yml or .env
   POSTGRES_PASSWORD=<secure_password>
   PGADMIN_DEFAULT_PASSWORD=<secure_password>
   ORACLE_PWD=<secure_password>
   ```

2. **Update Default Admin User**
   ```bash
   # After first login, change password via UI or SQL
   UPDATE users SET hashed_password = '<new_hash>' WHERE email = 'admin@example.com';
   ```

3. **Use Environment-Specific Configs**
   ```bash
   # Create docker-compose.prod.yml with production settings
   # Don't commit passwords to git
   ```

4. **Enable SSL/TLS**
   - Use nginx/traefik reverse proxy
   - Install SSL certificates (Let's Encrypt)
   - Enforce HTTPS

5. **Restrict Network Access**
   ```bash
   # Remove port exposures for internal services
   # Keep only frontend (3000) and backend (8000) exposed
   ```

6. **Use Private Registry**
   ```bash
   # Push custom images to private Docker registry
   # Instead of building from git
   ```

---

## Monitoring & Logging

### View Real-time Logs
```bash
# All services
docker-compose logs -f

# Follow specific service
docker-compose logs -f backend
docker-compose logs -f worker
docker-compose logs -f frontend
```

### Disk Usage
```bash
# Show disk usage per container
docker system df

# Show volume sizes
docker system df -v
```

### Resource Usage
```bash
# Monitor CPU, memory, I/O
docker stats

# Or use docker-compose plugin
docker stats --services
```

---

## Getting Help

- **Docker Compose Docs:** https://docs.docker.com/compose/
- **Docker Troubleshooting:** https://docs.docker.com/config/containers/logging/
- **Ollama Setup:** https://ollama.ai
- **PostgreSQL Docs:** https://www.postgresql.org/docs/
- **Project Issues:** Check GitHub issues

---

## Summary

✅ All services containerized  
✅ Single command startup: `docker-compose up -d`  
✅ All data persists across restarts  
✅ Services communicate internally  
✅ Healthy status checks  
✅ Easy scaling and deployment  
✅ Production-ready configuration  

**You now have a fully containerized, production-ready audit application!** 🚀
