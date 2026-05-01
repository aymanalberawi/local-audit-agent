# 🔍 Local Audit Agent - Containerized Compliance Audit SaaS

A full-stack compliance audit platform with **AI-powered findings**, professional **PDF report generation**, and **complete Docker containerization**. No external APIs required — everything runs locally.

## 🌟 Features

### 🤖 Intelligent Audit Engine
- **Two-phase agentic system**: LLM-powered discovery + evaluation
- **Vector-based caching**: Uses pgvector for intelligent schema discovery
- **Real-time progress tracking**: Live audit logs with LLM transparency
- **Retry/Resume capability**: Automatically handle and recover from failures
- **Multi-standard support**: GDPR, ISO 27001, SOC 2, HIPAA, and more

### 📄 Professional Report Generation
- **One-click PDF export** with complete audit analysis
- **Executive summary** with compliance scores (0-100%)
- **Detailed findings** with severity classification
- **Evidence data** from the audit
- **AI-generated remediation steps** for each control violation

### 🐳 Full Containerization
- **Zero host dependencies** — only Docker required
- **Service orchestration** via Docker Compose
- **Health checks** and automatic restart policies
- **Named volumes** for persistent data
- **Internal container networking** — no localhost issues

### 🔐 Enterprise-Ready
- **Role-based access control (RBAC)**: Admin, Auditor, Analyst roles
- **Multi-tenancy**: Company-based data isolation
- **Secure authentication**: JWT tokens with bcrypt password hashing
- **Comprehensive audit logging**: Track all actions and decisions
- **Error tracking**: Detailed error categorization and logging

## 🏗️ Architecture

```
┌─────────────────────────────────────────┐
│      Docker Network (audit-network)     │
├─────────────────────────────────────────┤
│                                         │
│  ┌──────────────┐  ┌──────────────┐   │
│  │  Ollama      │  │  PostgreSQL  │   │
│  │  (LLM)       │  │  + pgvector  │   │
│  │ :11434       │  │  :5432       │   │
│  └──────────────┘  └──────────────┘   │
│         ↑                ↑             │
│         └────┬───────────┘             │
│              │                         │
│  ┌───────────────────────────────┐    │
│  │   FastAPI Backend :8000       │    │
│  │   - Audit Engine              │    │
│  │   - Report Generator          │    │
│  │   - API Endpoints             │    │
│  └───────────────────────────────┘    │
│         ↓           ↓        ↓        │
│  ┌──────────┐ ┌──────────┐ ┌──────┐  │
│  │ Celery   │ │  Redis   │ │Next. │  │
│  │ Worker   │ │ :6379    │ │js    │  │
│  │          │ │          │ │:3000 │  │
│  └──────────┘ └──────────┘ └──────┘  │
│                                       │
└─────────────────────────────────────────┘
         ↑ (Exposed Ports)
    3000, 8000, 5050, 11434
```

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose 2.0+
- Git

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/local-audit-agent.git
cd local-audit-agent

# Start all services
docker-compose up -d

# Wait for health checks
docker-compose ps
# All services should show "Up (healthy)"
```

### Access the Application

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | http://localhost:3000 | admin@example.com / password |
| **API Docs** | http://localhost:8000/docs | Same as frontend |
| **pgAdmin** | http://localhost:5050 | admin@local.dev / admin |
| **Ollama API** | http://localhost:11434 | N/A |

## 📊 Usage

### 1. Create an Audit
```
Audits Tab → Create New Audit
Select: Connection + Standard (e.g., Mock Database + GDPR_UAE)
Click: Start Audit
```

### 2. Monitor Progress
- Real-time progress bar shows execution stages
- Live audit logs show every decision and LLM interaction
- See exactly what the AI is doing

### 3. Review Findings
- View all violations grouped by severity
- See evidence data that triggered each finding
- Understand the issue and remediation steps

### 4. Download Report
- **One-click PDF export** with professional formatting
- Compliance score calculation
- Complete audit trail and recommendations
- Ready for auditors and compliance teams

## 🛠️ Tech Stack

| Component | Technology |
|-----------|------------|
| **Backend API** | FastAPI, SQLAlchemy |
| **Frontend** | Next.js, React, TypeScript |
| **Database** | PostgreSQL with pgvector |
| **Cache** | Redis |
| **LLM** | Ollama (local inference) |
| **Task Queue** | Celery + Redis |
| **Scheduler** | Celery Beat |
| **Reports** | ReportLab (PDF generation) |
| **Containerization** | Docker & Docker Compose |

## 📁 Project Structure

```
local-audit-agent/
├── backend/
│   ├── main.py                 # FastAPI app entry point
│   ├── worker.py               # Celery task definitions
│   ├── init_db.py              # Database initialization
│   ├── requirements.txt         # Python dependencies
│   ├── Dockerfile              # Backend container config
│   ├── core/                   # Core modules (auth, config, database)
│   ├── models/                 # SQLAlchemy ORM models
│   ├── routers/                # API route handlers
│   ├── services/               # Business logic
│   │   ├── audit_engine.py     # Main audit logic
│   │   ├── report_generator.py # PDF report generation
│   │   └── connectors/         # Data source connectors
│   └── alembic/                # Database migrations
│
├── frontend/
│   ├── src/
│   │   ├── app/                # Next.js app directory
│   │   ├── components/         # React components
│   │   └── lib/                # Utilities and API helpers
│   ├── package.json            # Node dependencies
│   ├── Dockerfile              # Frontend container config
│   └── tsconfig.json           # TypeScript config
│
├── docker-compose.yml          # Service orchestration
├── docker-compose.prod.yml     # Production overrides
├── .env.example                # Environment template
├── start.sh                     # Quick start script
├── stop.sh                      # Quick stop script
│
└── docs/
    ├── DOCKER_SETUP.md         # Docker deployment guide
    ├── PDF_REPORT_FEATURE.md   # Report feature documentation
    ├── QUICK_START_PDF_EXPORT.md
    └── ... (other guides)
```

## 🔑 Key Features Explained

### AI-Powered Audit Discovery
The system uses LLM intelligence to:
1. Analyze your data schema
2. Identify relevant tables for compliance controls
3. Cache discoveries using vector embeddings (pgvector)
4. Evaluate each data row against control requirements
5. Generate findings with severity classification

### Live Audit Logging
Watch in real-time as the audit executes:
- See the LLM prompts being sent
- View the AI responses and reasoning
- Monitor data discovery and evaluation progress
- Understand exactly what triggered each finding

### Professional PDF Reports
Export audit results with:
- Executive summary and compliance score
- Detailed findings with evidence
- Specific remediation steps
- Complete audit trail
- Professional formatting suitable for auditors

## 🔐 Security Features

- ✅ Role-based access control (Admin, Auditor, Analyst)
- ✅ Multi-tenancy with company data isolation
- ✅ JWT authentication with token expiration
- ✅ Password hashing with bcrypt
- ✅ Comprehensive audit logging
- ✅ Error categorization and tracking
- ✅ Retry/resume on transient failures

## 📊 Performance

| Metric | Value |
|--------|-------|
| Audit Duration | 1-2.5 minutes (depending on data size) |
| LLM Calls per Audit | 30-50 calls |
| PDF Generation | < 3 seconds |
| Typical PDF Size | 200-600 KB |
| Container Startup | 30-40 seconds |

## 🐛 Debugging & Monitoring

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs backend -f
docker-compose logs worker -f
docker-compose logs frontend -f
```

### Check Health
```bash
docker-compose ps
# All services should show "Up (healthy)"
```

### Access Database
```bash
docker-compose exec db psql -U admin -d audit_saas
```

### Debug Audit Job
```bash
curl http://localhost:8000/audit/jobs/{job_id}/debug \
  -H "Authorization: Bearer TOKEN" | jq
```

## 📖 Documentation

Comprehensive guides are included:
- **DOCKER_SETUP.md** - Complete Docker deployment guide
- **PDF_REPORT_FEATURE.md** - PDF export feature details
- **QUICK_START_PDF_EXPORT.md** - Quick reference
- **FINDINGS_DEBUG_GUIDE.md** - Debugging findings issues
- **TEST_AUDIT_FLOW.md** - End-to-end testing guide
- **HOW_TO_USE_PDF_EXPORT.md** - User walkthrough

## 🚀 Deployment

### Docker Compose (Development)
```bash
docker-compose up -d
```

### Production Deployment
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

See `DOCKER_SETUP.md` for detailed production deployment instructions.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙋 Support

For issues, questions, or suggestions:
- Check the documentation in the `docs/` directory
- Review the troubleshooting guides
- Open an issue on GitHub

## 🎯 Roadmap

- [ ] Custom company branding in PDF reports
- [ ] Email report distribution
- [ ] Report scheduling and automation
- [ ] Multi-language support
- [ ] Advanced filtering and search
- [ ] Compliance score trends over time
- [ ] Kubernetes deployment support
- [ ] API rate limiting and quotas

## 🙌 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Frontend with [Next.js](https://nextjs.org/) and [React](https://react.dev/)
- LLM inference via [Ollama](https://ollama.ai/)
- Database: [PostgreSQL](https://www.postgresql.org/) with [pgvector](https://github.com/pgvector/pgvector)
- Reports: [ReportLab](https://www.reportlab.com/)

---

**Made with ❤️ for compliance teams who deserve better tools**
