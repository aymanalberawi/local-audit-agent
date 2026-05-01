"""
PDF Report Generator for Audit Results
Generates professional audit reports with findings, evidence, and remediation steps.
"""

import json
import logging
from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional, Any

from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak, Image
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT, TA_JUSTIFY

logger = logging.getLogger(__name__)


class AuditReportGenerator:
    """Generate professional PDF audit reports."""

    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
        self.page_width, self.page_height = letter
        self.margin = 0.5 * inch

    def _create_custom_styles(self):
        """Create custom paragraph styles for the report."""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#0066cc'),
            spaceAfter=12,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='CustomHeading2',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#0066cc'),
            spaceAfter=6,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='CustomHeading3',
            parent=self.styles['Heading3'],
            fontSize=12,
            textColor=colors.HexColor('#333333'),
            spaceAfter=4,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='BodyCustom',
            parent=self.styles['BodyText'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=6
        ))

        self.styles.add(ParagraphStyle(
            name='CriticalLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.white,
            backColor=colors.HexColor('#ff0000'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='HighLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.white,
            backColor=colors.HexColor('#ff6600'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='MediumLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.white,
            backColor=colors.HexColor('#ffaa00'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='LowLabel',
            parent=self.styles['Normal'],
            fontSize=9,
            textColor=colors.white,
            backColor=colors.HexColor('#00cc00'),
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

    def generate_report(self,
                       job_id: int,
                       job_data: Dict[str, Any],
                       findings: List[Dict[str, Any]],
                       audit_logs: List[Dict[str, Any]],
                       company_name: str,
                       connection_name: str) -> bytes:
        """
        Generate a complete audit report PDF.

        Args:
            job_id: Audit job ID
            job_data: Job metadata (status, standard_name, created_at, etc.)
            findings: List of findings from the audit
            audit_logs: List of audit logs (for evidence)
            company_name: Company that owns the audit
            connection_name: Name of the audited data source

        Returns:
            PDF bytes ready to write to file
        """
        # Create PDF in memory
        pdf_buffer = BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer,
            pagesize=letter,
            rightMargin=self.margin,
            leftMargin=self.margin,
            topMargin=self.margin,
            bottomMargin=self.margin,
            title=f"Audit Report - {job_data.get('standard_name', 'Unknown')}",
        )

        # Build report content
        content = []
        content.extend(self._build_cover_page(job_id, job_data, company_name, connection_name))
        content.append(PageBreak())
        content.extend(self._build_executive_summary(findings, job_data))
        content.append(PageBreak())
        content.extend(self._build_findings_section(findings))

        if audit_logs:
            content.append(PageBreak())
            content.extend(self._build_evidence_section(audit_logs))

        # Build PDF
        doc.build(content)
        pdf_data = pdf_buffer.getvalue()
        pdf_buffer.close()

        logger.info(f"Generated PDF report for audit job {job_id} ({len(pdf_data)} bytes)")
        return pdf_data

    def _build_cover_page(self, job_id: int, job_data: Dict, company_name: str, connection_name: str) -> List:
        """Build the cover page."""
        content = []

        content.append(Spacer(1, 1.5 * inch))

        # Title
        content.append(Paragraph("COMPLIANCE AUDIT REPORT", self.styles['CustomTitle']))
        content.append(Spacer(1, 0.3 * inch))

        # Standard
        standard_name = job_data.get('standard_name', 'Unknown Standard')
        content.append(Paragraph(f"<b>{standard_name}</b>", self.styles['CustomHeading2']))
        content.append(Spacer(1, 0.5 * inch))

        # Metadata table
        metadata = [
            ['Report ID:', f"AUD-{job_id:06d}"],
            ['Generated:', datetime.now().strftime('%B %d, %Y at %I:%M %p')],
            ['Company:', company_name],
            ['Data Source:', connection_name],
            ['Audit Date:', job_data.get('created_at', 'N/A')],
            ['Status:', job_data.get('status', 'Unknown').upper()],
        ]

        metadata_table = Table(metadata, colWidths=[1.5*inch, 3.5*inch])
        metadata_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#f0f0f0')),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.grey),
        ]))

        content.append(metadata_table)
        content.append(Spacer(1, 0.8 * inch))
        content.append(Paragraph(
            "<i>This report contains confidential information about the audit findings and remediation recommendations. "
            "It should be handled and distributed according to your organization's confidentiality policies.</i>",
            self.styles['BodyCustom']
        ))

        return content

    def _build_executive_summary(self, findings: List[Dict], job_data: Dict) -> List:
        """Build the executive summary section."""
        content = []

        content.append(Paragraph("Executive Summary", self.styles['CustomHeading2']))
        content.append(Spacer(1, 0.2 * inch))

        # Calculate statistics
        total_findings = len(findings)
        critical_count = len([f for f in findings if f.get('severity') == 'CRITICAL'])
        high_count = len([f for f in findings if f.get('severity') == 'HIGH'])
        medium_count = len([f for f in findings if f.get('severity') == 'MEDIUM'])
        low_count = len([f for f in findings if f.get('severity') == 'LOW'])

        # Calculate compliance score
        compliance_score = 100 - min(100, (critical_count * 25 + high_count * 10 + medium_count * 5 + low_count * 2) / (total_findings or 1))
        compliance_score = max(0, compliance_score)

        # Summary text
        summary_text = (
            f"This audit evaluated {job_data.get('connection_name', 'the data source')} against the "
            f"{job_data.get('standard_name', 'compliance standard')} requirements. "
            f"The assessment identified <b>{total_findings} control violations</b> across the evaluated systems."
        )
        content.append(Paragraph(summary_text, self.styles['BodyCustom']))
        content.append(Spacer(1, 0.2 * inch))

        # Statistics table
        stats_data = [
            ['Metric', 'Count', 'Percentage'],
            ['CRITICAL Findings', str(critical_count), f"{(critical_count/max(total_findings,1)*100):.1f}%"],
            ['HIGH Findings', str(high_count), f"{(high_count/max(total_findings,1)*100):.1f}%"],
            ['MEDIUM Findings', str(medium_count), f"{(medium_count/max(total_findings,1)*100):.1f}%"],
            ['LOW Findings', str(low_count), f"{(low_count/max(total_findings,1)*100):.1f}%"],
            ['Total Findings', str(total_findings), '100%'],
        ]

        stats_table = Table(stats_data, colWidths=[2*inch, 1.2*inch, 1.2*inch])
        stats_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066cc')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 10),
            ('FONTNAME', (0, 1), (0, -1), 'Helvetica-Bold'),
        ]))

        content.append(stats_table)
        content.append(Spacer(1, 0.3 * inch))

        # Compliance score
        content.append(Paragraph("Compliance Score", self.styles['CustomHeading3']))
        content.append(Spacer(1, 0.1 * inch))
        score_color = '#00cc00' if compliance_score >= 80 else '#ffaa00' if compliance_score >= 60 else '#ff0000'
        content.append(Paragraph(
            f"<font color='{score_color}' size=16><b>{compliance_score:.1f}%</b></font>",
            self.styles['BodyCustom']
        ))
        content.append(Spacer(1, 0.2 * inch))

        # Key findings
        content.append(Paragraph("Key Findings", self.styles['CustomHeading3']))
        content.append(Spacer(1, 0.1 * inch))

        if critical_count > 0:
            content.append(Paragraph(
                f"🔴 <b>{critical_count} CRITICAL finding(s)</b> require immediate remediation to prevent security or compliance breaches.",
                self.styles['BodyCustom']
            ))

        if high_count > 0:
            content.append(Paragraph(
                f"🟠 <b>{high_count} HIGH finding(s)</b> should be remediated soon to reduce risk exposure.",
                self.styles['BodyCustom']
            ))

        return content

    def _build_findings_section(self, findings: List[Dict]) -> List:
        """Build the detailed findings section."""
        content = []

        content.append(Paragraph("Detailed Findings", self.styles['CustomHeading2']))
        content.append(Spacer(1, 0.2 * inch))

        if not findings:
            content.append(Paragraph(
                "No findings - All controls passed! ✅",
                self.styles['BodyCustom']
            ))
            return content

        # Group findings by severity
        severity_order = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW']
        for severity in severity_order:
            severity_findings = [f for f in findings if f.get('severity') == severity]
            if not severity_findings:
                continue

            # Severity section header
            content.append(Paragraph(f"{severity} Severity Findings ({len(severity_findings)})",
                                    self.styles['CustomHeading3']))
            content.append(Spacer(1, 0.15 * inch))

            # Each finding
            for idx, finding in enumerate(severity_findings, 1):
                content.extend(self._build_finding_detail(finding, severity, idx))
                content.append(Spacer(1, 0.2 * inch))

        return content

    def _build_finding_detail(self, finding: Dict, severity: str, index: int) -> List:
        """Build a single finding detail."""
        content = []

        # Finding header with severity badge
        control_id = finding.get('control_id', 'Unknown')
        issue = finding.get('issue_description', 'No description')

        # Create finding box
        finding_header = Table([
            [
                Paragraph(f"<b>Finding {index}: {control_id}</b>", self.styles['CustomHeading3']),
                Paragraph(severity, self.styles[f'{severity}Label']) if severity in ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW'] else ''
            ]
        ], colWidths=[4.5*inch, 1*inch])

        finding_header.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#f9f9f9')),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (1, 0), 'CENTER'),
            ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
            ('GRID', (0, 0), (-1, 0), 1, colors.HexColor('#cccccc')),
        ]))

        content.append(finding_header)
        content.append(Spacer(1, 0.1 * inch))

        # Issue description
        content.append(Paragraph("<b>Issue:</b>", self.styles['CustomHeading3']))
        content.append(Paragraph(issue, self.styles['BodyCustom']))
        content.append(Spacer(1, 0.1 * inch))

        # Evidence
        raw_data = finding.get('raw_data', {})
        if raw_data:
            content.append(Paragraph("<b>Evidence:</b>", self.styles['CustomHeading3']))
            if isinstance(raw_data, dict):
                evidence_items = []
                for key, value in list(raw_data.items())[:10]:  # Limit to 10 items
                    evidence_items.append(f"• <b>{key}:</b> {str(value)[:80]}")
                content.append(Paragraph("<br/>".join(evidence_items), self.styles['BodyCustom']))
            else:
                content.append(Paragraph(str(raw_data)[:500], self.styles['BodyCustom']))
            content.append(Spacer(1, 0.1 * inch))

        # Remediation
        remediation = self._get_remediation_steps(finding.get('control_id', ''), severity)
        content.append(Paragraph("<b>Remediation Steps:</b>", self.styles['CustomHeading3']))
        for step in remediation:
            content.append(Paragraph(f"• {step}", self.styles['BodyCustom']))

        return content

    def _get_remediation_steps(self, control_id: str, severity: str) -> List[str]:
        """Get remediation steps for a finding."""
        # Map control IDs to remediation steps
        remediation_map = {
            'ACC-01': [
                'Implement role-based access control (RBAC) with principle of least privilege',
                'Audit all admin accounts and remove unnecessary privileges',
                'Establish regular access reviews (quarterly or semi-annually)',
                'Configure audit logging for all privileged user actions',
                'Implement multi-factor authentication (MFA) for admin accounts',
            ],
            'ACC-02': [
                'Review and update access control policies',
                'Implement automated access provisioning and de-provisioning',
                'Conduct user access reviews across all systems',
                'Document access control requirements',
                'Train staff on access control procedures',
            ],
            'AUTH-01': [
                'Implement strong password policies (minimum 12 characters, complexity rules)',
                'Enable multi-factor authentication (MFA) for all user accounts',
                'Implement secure password storage with proper hashing algorithms',
                'Configure account lockout after failed login attempts',
                'Regular security awareness training on authentication',
            ],
            'DLP-01': [
                'Implement data classification and labeling',
                'Configure Data Loss Prevention (DLP) tools',
                'Restrict data transfers to authorized destinations',
                'Monitor and log all data access and transfers',
                'Establish data handling policies and procedures',
            ],
            'SEC-01': [
                'Conduct comprehensive security assessment',
                'Implement missing security controls',
                'Update security policies and procedures',
                'Deploy intrusion detection/prevention systems',
                'Regular security testing and vulnerability scanning',
            ],
            'ENC-01': [
                'Implement encryption for data at rest (AES-256 or stronger)',
                'Implement encryption for data in transit (TLS 1.2 or higher)',
                'Establish key management procedures',
                'Regular encryption audits and reviews',
                'Educate staff on encryption requirements',
            ],
        }

        # Get specific remediation or use generic
        if control_id in remediation_map:
            return remediation_map[control_id]
        else:
            # Generic remediation based on severity
            if severity == 'CRITICAL':
                return [
                    'Address this finding immediately as it poses significant compliance or security risk',
                    'Develop a detailed remediation plan with specific timelines',
                    'Assign responsibility to appropriate teams',
                    'Implement temporary controls while permanent solution is being developed',
                    'Document and track remediation progress',
                ]
            elif severity == 'HIGH':
                return [
                    'Develop a remediation plan to address this finding within 30 days',
                    'Assign clear responsibility for remediation',
                    'Monitor progress and update status regularly',
                    'Test remediation to ensure effectiveness',
                    'Document completed remediation',
                ]
            else:
                return [
                    'Include in the next quarterly review and remediation cycle',
                    'Evaluate cost-benefit of remediation',
                    'Plan implementation with other low-priority items',
                    'Document any risk acceptance decisions',
                ]

    def _build_evidence_section(self, audit_logs: List[Dict]) -> List:
        """Build the evidence and audit log section."""
        content = []

        content.append(Paragraph("Audit Evidence and Logs", self.styles['CustomHeading2']))
        content.append(Spacer(1, 0.2 * inch))

        if not audit_logs:
            content.append(Paragraph("No audit logs available.", self.styles['BodyCustom']))
            return content

        content.append(Paragraph(
            f"The following table shows the detailed audit execution logs and evidence collected during the assessment:",
            self.styles['BodyCustom']
        ))
        content.append(Spacer(1, 0.15 * inch))

        # Build logs table (limit to last 30 logs)
        log_data = [['Timestamp', 'Type', 'Control', 'Message']]
        for log in audit_logs[-30:]:
            timestamp = log.get('timestamp', 'N/A')
            if isinstance(timestamp, datetime):
                timestamp = timestamp.strftime('%Y-%m-%d %H:%M:%S')

            log_type = log.get('log_type', 'system')
            control_id = log.get('control_id', '-')
            message = log.get('message', '')[:60]  # Truncate long messages

            log_data.append([timestamp, log_type, control_id, message])

        logs_table = Table(log_data, colWidths=[1.2*inch, 0.8*inch, 0.8*inch, 2.2*inch])
        logs_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0066cc')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('TOPPADDING', (0, 0), (-1, 0), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f9f9f9')]),
        ]))

        content.append(logs_table)
        return content
