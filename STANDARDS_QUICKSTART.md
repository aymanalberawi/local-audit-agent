# Standards Management Quick Start Guide

## Access the Standards Management Page

1. **Open Browser**
   - Navigate to: `http://localhost:3000`

2. **Login**
   - Email: `admin@example.com`
   - Password: `password`

3. **Navigate to Standards**
   - Click "📚 Standards" in the left sidebar

## Using Standards Management

### View All Standards
- Standards list appears on the left side of the page
- Shows standard name, version, number of controls, and built-in status
- Current: 13 compliance frameworks available

### View Standard Details
1. Click any standard in the list
2. Right panel shows:
   - Full name and description
   - Version, region, and authority
   - Total control count
3. All controls listed with expandable details

### Expand Control Details
1. Click on any control row to expand
2. See full control information:
   - **Description**: What the control requires
   - **Data Sources**: Where to find evidence (e.g., user_profiles, audit_logs)
   - **Logic/Query**: How to verify compliance
3. Color-coded severity labels:
   - 🔴 CRITICAL (red)
   - 🟠 HIGH (orange)
   - 🟡 MEDIUM (yellow)
   - 🟢 LOW (green)

### Sync Standards with JSON Files

#### Export Database to JSON
- Button: "Export to JSON"
- Saves current database standard to `/standards/` directory
- Useful for: Backing up changes, sharing standards

#### Reload from JSON
- Button: "Reload from JSON"
- Updates database from JSON file
- Useful for: Undoing UI changes, reverting to original

### Use Standards in Audits

1. Go to **Audits** page
2. Create new audit
3. Select standard from dropdown (all 13 frameworks available)
4. Controls automatically loaded from database
5. Audit runs with database-backed standards

## API Usage (Advanced)

### List All Standards
```bash
curl http://localhost:8000/standards/
```

### Get Standard with Controls
```bash
curl http://localhost:8000/standards/1
curl http://localhost:8000/standards/by-name/ISO-27001
```

### Export to JSON
```bash
curl -X POST http://localhost:8000/standards/1/sync/to-json \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Reload from JSON
```bash
curl -X POST http://localhost:8000/standards/1/sync/from-json \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Available Standards (13 Frameworks)

| Framework | Region | Authority | Controls | Use Case |
|-----------|--------|-----------|----------|----------|
| **BAHRAIN-PDPL** | GCC | Bahrain PDPA | 6 | Personal data protection |
| **EU-GDPR** | EU | EDPB / DPAs | 18 | Data protection (EU) |
| **EU-NIS2** | EU | ENISA | 10 | Network security (EU) |
| **HIPAA** | US | HHS/OCR | 15 | Healthcare privacy |
| **ISO-27001** | GLOBAL | ISO/IEC | 20 | Information security |
| **KUWAIT-ISR** | GCC | CBK | 7 | Information security (Kuwait) |
| **NIST-CSF** | US | NIST | 20 | Cybersecurity framework |
| **PCI-DSS** | GLOBAL | PCI SSC | 19 | Payment card security |
| **QATAR-NISCF** | GCC | Qatar NIA | 8 | Information security (Qatar) |
| **SAMA-CSF** | GCC | SAMA | 15 | Cybersecurity framework (Saudi) |
| **SOC2** | US | AICPA | 18 | Service organization control |
| **UAE-NESA-IAS** | GCC | UAE IAS | 18 | Information assurance (UAE) |
| **UAE-PDPL** | GCC | UAE Data Office | 16 | Data protection (UAE) |

**Total**: 166 compliance controls

## Database Structure

Standards are organized in three main tables:

### audit_schemes
- Stores framework metadata
- Fields: name, version, region, authority, is_built_in
- Example: ISO-27001 v1.0

### audit_requirements
- Stores individual controls
- Fields: control_id, name, description, severity, data_sources, query_template
- Example: ISO-27001-A.5.1 - Access control policy

### standard_versions (optional)
- Tracks version history of frameworks
- Fields: version_number, source, created_at, created_by_user_id
- For future: version rollback, audit trails

## Troubleshooting

### Standards Not Appearing
1. Check backend logs: `docker logs audit_backend | grep Standards`
2. Verify database is running: `docker ps | grep audit_db`
3. Restart backend: `docker-compose restart backend`

### API Returns 404
1. Verify standard exists: `curl http://localhost:8000/standards/`
2. Check correct ID or name used
3. Ensure authentication token is valid

### Sync Fails
1. Check `/standards` directory exists
2. Verify file permissions
3. Check disk space available

### Frontend Shows No Controls
1. Refresh page: Ctrl+F5
2. Check browser console for errors
3. Verify backend API is responding

## Next Steps

1. **Create Audits**: Use standards in audit jobs
2. **Explore Frameworks**: Review different compliance standards
3. **Review Controls**: Understand each control's requirements
4. **Plan Audit**: Choose appropriate framework for your data
5. **Execute Audit**: Run compliance checks against controls

## Tips & Best Practices

✅ **Tip 1**: Use ISO-27001 for comprehensive information security audits  
✅ **Tip 2**: Use GDPR for data protection compliance  
✅ **Tip 3**: Use NIST-CSF for government/critical infrastructure  
✅ **Tip 4**: Use PCI-DSS for payment processing systems  
✅ **Tip 5**: Use HIPAA for healthcare data  
✅ **Tip 6**: Mix standards for comprehensive coverage  

## Documentation References

- **API Documentation**: See `/standards` endpoint details
- **Database Schema**: Check `backend/models/audit_scheme.py`
- **Service Logic**: Review `backend/services/standards_service.py`
- **Frontend Code**: Check `frontend/src/app/standards/page.tsx`

## Support

For issues or questions:
1. Check logs: `docker logs audit_backend`
2. Review test cases: `backend/tests/test_standards_integration.py`
3. Verify API responses with curl commands
4. Check database directly: psql commands

---

**Status**: ✅ Production Ready  
**Last Updated**: 2026-04-29  
**Version**: 1.0  
