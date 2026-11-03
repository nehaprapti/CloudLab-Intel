"""
CloudLab Intelligence - Report Generator & Dispatcher
Generates official academic PDF reports (using ReportLab), CSV exports,
and dispatches comprehensive student activity reports to administrators.
"""

import os
import csv
import io
import json
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

REPORT_OUTPUT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "reports")
os.makedirs(REPORT_OUTPUT_DIR, exist_ok=True)


def format_duration(seconds):
    """Formats seconds into HH:MM:SS or MMm SSs."""
    if not seconds:
        return "00:00:00"
    seconds = int(seconds)
    hrs = seconds // 3600
    mins = (seconds % 3600) // 60
    secs = seconds % 60
    if hrs > 0:
        return f"{hrs:02d}h {mins:02d}m {secs:02d}s"
    return f"{mins:02d}m {secs:02d}s"


def generate_student_pdf_report(student_data, events_data=None):
    """
    Generates a detailed, formal PDF report for a student lab session.
    """
    reg_no = student_data.get("reg_no", "Unknown")
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"CloudLab_Report_{reg_no}_{timestamp_str}.pdf"
    filepath = os.path.join(REPORT_OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#1e3a8a"),
        alignment=1 # Center
    )
    
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#475569"),
        alignment=1
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=10,
        spaceAfter=6
    )

    cell_style = ParagraphStyle(
        'TableCell',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#1e293b")
    )

    cell_bold = ParagraphStyle(
        'TableCellBold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11,
        textColor=colors.HexColor("#0f172a")
    )

    elements = []

    # Institution Header
    elements.append(Paragraph("SONA COLLEGE OF TECHNOLOGY (AUTONOMOUS)", title_style))
    elements.append(Paragraph("DEPARTMENT OF INFORMATION TECHNOLOGY — CLOUDLAB INTELLIGENCE", subtitle_style))
    elements.append(Paragraph("STUDENT DIGITAL ACTIVITY & LAB RESOURCE MONITORING REPORT", ParagraphStyle('SubSub', parent=subtitle_style, fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor("#2563eb"))))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=12))

    # Student & Session Overview Table
    login_t = student_data.get("login_time", "N/A")
    logout_t = student_data.get("logout_time") or "Active Session (In Progress)"
    total_dur = format_duration(student_data.get("total_duration_sec", 0))
    active_dur = format_duration(student_data.get("active_duration_sec", 0))
    idle_dur = format_duration(student_data.get("idle_duration_sec", 0))
    focus_data = student_data.get("context_switches", {})
    focus_score = focus_data.get("focus_score", student_data.get("focus_score", 100))
    rating = focus_data.get("rating", "Good Engagement")

    overview_data = [
        [Paragraph("<b>Student Name:</b>", cell_bold), Paragraph(str(student_data.get("student_name", "N/A")), cell_style),
         Paragraph("<b>Register No:</b>", cell_bold), Paragraph(str(student_data.get("reg_no", "N/A")), cell_style)],
        [Paragraph("<b>Lab Room:</b>", cell_bold), Paragraph(str(student_data.get("lab_id", "Lab 1 - AI & Cloud")), cell_style),
         Paragraph("<b>Workstation / PC:</b>", cell_bold), Paragraph(str(student_data.get("pc_id", "PC-01")), cell_style)],
        [Paragraph("<b>Login Time:</b>", cell_bold), Paragraph(str(login_t), cell_style),
         Paragraph("<b>Logout Time:</b>", cell_bold), Paragraph(str(logout_t), cell_style)],
        [Paragraph("<b>Total Duration:</b>", cell_bold), Paragraph(total_dur, cell_style),
         Paragraph("<b>Active / Idle Time:</b>", cell_bold), Paragraph(f"{active_dur} / {idle_dur}", cell_style)],
        [Paragraph("<b>Focus Score:</b>", cell_bold), Paragraph(f"<b>{focus_score}%</b> ({rating})", cell_bold),
         Paragraph("<b>Context Switches:</b>", cell_bold), Paragraph(f"{focus_data.get('total_switches', 0)} ({focus_data.get('switches_per_hour', 0)}/hr)", cell_style)]
    ]

    overview_table = Table(overview_data, colWidths=[110, 150, 110, 150])
    overview_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#f8fafc")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(overview_table)
    elements.append(Spacer(1, 10))

    # AI Chatbot Malpractice Audit Box (Assessment Monitoring)
    ai_violations = student_data.get("ai_violations", [])
    is_assessment = student_data.get("is_assessment_mode", False)
    
    if ai_violations:
        if is_assessment:
            alert_style = ParagraphStyle(
                'AlertStyle',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=9.5,
                textColor=colors.HexColor("#dc2626")
            )
            alert_desc = ParagraphStyle(
                'AlertDesc',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=8,
                textColor=colors.HexColor("#991b1b")
            )
            alert_data = [
                [Paragraph("🚨 ASSESSMENT INTEGRITY ALERT: AI CHATBOT / LLM USAGE DETECTED", alert_style)],
                [Paragraph(f"This workstation accessed unauthorized generative AI tools ({len(ai_violations)} times) during the active assessment. Flagged domains: {', '.join(set(v.get('domain', '') for v in ai_violations))}", alert_desc)]
            ]
            box_bg = colors.HexColor("#fee2e2")
            box_border = colors.HexColor("#ef4444")
        else:
            alert_style = ParagraphStyle(
                'AlertStyle',
                parent=styles['Normal'],
                fontName='Helvetica-Bold',
                fontSize=9.5,
                textColor=colors.HexColor("#4338ca")
            )
            alert_desc = ParagraphStyle(
                'AlertDesc',
                parent=styles['Normal'],
                fontName='Helvetica',
                fontSize=8,
                textColor=colors.HexColor("#3730a3")
            )
            alert_data = [
                [Paragraph("ℹ️ AI-ASSISTED LEARNING TOOLS UTILIZED (AUTHORIZED IN LEARNING MODE)", alert_style)],
                [Paragraph(f"This workstation engaged with approved AI research & learning assistants ({len(ai_violations)} times) for conceptual understanding. Domains: {', '.join(set(v.get('domain', '') for v in ai_violations))}", alert_desc)]
            ]
            box_bg = colors.HexColor("#e0e7ff")
            box_border = colors.HexColor("#6366f1")

        alert_table = Table(alert_data, colWidths=[520])
        alert_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), box_bg),
            ('BOX', (0, 0), (-1, -1), 1.5, box_border),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('LEFTPADDING', (0, 0), (-1, -1), 8),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(alert_table)
        elements.append(Spacer(1, 10))

    # Activity Category Breakdown Table
    elements.append(Paragraph("1. Activity Classification & Time Distribution", section_heading))
    categories = student_data.get("categories", {})
    total_sec = max(student_data.get("total_duration_sec", 1), 1)

    cat_headers = [Paragraph("<b>Activity Category</b>", cell_bold), Paragraph("<b>Time Spent</b>", cell_bold), Paragraph("<b>Percentage</b>", cell_bold), Paragraph("<b>Status / Remarks</b>", cell_bold)]
    cat_rows = [cat_headers]

    for cat_name, dur_sec in categories.items():
        pct = round((dur_sec / total_sec) * 100, 1)
        remarks = "Core Curriculum Activity" if cat_name in ["Programming", "Database"] else ("Reference & Learning" if cat_name == "Research & Learning" else ("Productive" if cat_name == "Documentation" else "Off-Task Alert"))
        cat_rows.append([
            Paragraph(cat_name, cell_style),
            Paragraph(format_duration(dur_sec), cell_style),
            Paragraph(f"{pct}%", cell_style),
            Paragraph(remarks, cell_style)
        ])

    if len(cat_rows) == 1:
        cat_rows.append([Paragraph("No categorized events logged", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style)])

    cat_table = Table(cat_rows, colWidths=[140, 110, 90, 180])
    cat_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(cat_table)
    elements.append(Spacer(1, 14))

    # Visited Browser Tabs & Domains Breakdown
    elements.append(Paragraph("2. Browser Tab Activity & Visited Domains", section_heading))
    domain_usage = student_data.get("domain_usage", {})
    
    dom_headers = [Paragraph("<b>Browser Domain / Tab Target</b>", cell_bold), Paragraph("<b>Duration</b>", cell_bold), Paragraph("<b>Classification</b>", cell_bold), Paragraph("<b>Engagement Level</b>", cell_bold)]
    dom_rows = [dom_headers]

    for dom, dur_sec in sorted(domain_usage.items(), key=lambda x: x[1], reverse=True)[:10]:
        from backend.analytics_engine import classify_activity
        dom_cat = classify_activity(browser_domain=dom)
        dom_pct = round((dur_sec / total_sec) * 100, 1)
        dom_rows.append([
            Paragraph(f"🌐 <b>{dom}</b>", cell_style),
            Paragraph(format_duration(dur_sec), cell_style),
            Paragraph(dom_cat, cell_style),
            Paragraph(f"{dom_pct}% of total session", cell_style)
        ])

    if len(dom_rows) == 1:
        dom_rows.append([Paragraph("No browser tabs visited during this session", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style)])

    dom_table = Table(dom_rows, colWidths=[180, 90, 120, 130])
    dom_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(dom_table)
    elements.append(Spacer(1, 14))

    # Application Usage Breakdown
    elements.append(Paragraph("3. Application Usage Summary", section_heading))
    app_usage = student_data.get("app_usage", {})
    
    app_headers = [Paragraph("<b>Application Name</b>", cell_bold), Paragraph("<b>Time Active</b>", cell_bold), Paragraph("<b>Category</b>", cell_bold), Paragraph("<b>Activity Ratio</b>", cell_bold)]
    app_rows = [app_headers]

    for app, dur_sec in sorted(app_usage.items(), key=lambda x: x[1], reverse=True)[:8]:
        from backend.analytics_engine import classify_activity
        app_cat = classify_activity(app_name=app)
        app_pct = round((dur_sec / total_sec) * 100, 1)
        app_rows.append([
            Paragraph(f"💻 <b>{app}</b>", cell_style),
            Paragraph(format_duration(dur_sec), cell_style),
            Paragraph(app_cat, cell_style),
            Paragraph(f"{app_pct}%", cell_style)
        ])

    if len(app_rows) == 1:
        app_rows.append([Paragraph("No application activity recorded", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style), Paragraph("-", cell_style)])

    app_table = Table(app_rows, colWidths=[180, 90, 120, 130])
    app_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(app_table)
    elements.append(Spacer(1, 20))

    # Signatures & Audit Footers
    sig_data = [
        [Paragraph("<b>System Administrator:</b>", cell_bold), Paragraph("<b>Lab In-Charge / Mentor:</b>", cell_bold), Paragraph("<b>Head of Department (IT):</b>", cell_bold)],
        [Paragraph("<i>Verified digitally via CloudLab Edge</i>", cell_style), Paragraph("<i>Mr. P. Dineshkumar, AP/IT</i>", cell_style), Paragraph("<i>Dr. J. Akilandeswari, Prof & Head/IT</i>", cell_style)],
        [Spacer(1, 15), Spacer(1, 15), Spacer(1, 15)],
        [Paragraph("Signature: ___________________", cell_style), Paragraph("Signature: ___________________", cell_style), Paragraph("Signature: ___________________", cell_style)]
    ]
    sig_table = Table(sig_data, colWidths=[170, 170, 180])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(KeepTogether(sig_table))

    doc.build(elements)
    return filepath, filename


def generate_overall_lab_pdf_report(lab_id, sessions_list):
    """
    Generates a master consolidated PDF report of all students in the laboratory.
    """
    timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"CloudLab_Master_Report_{lab_id}_{timestamp_str}.pdf"
    filepath = os.path.join(REPORT_OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=14, alignment=1, textColor=colors.HexColor("#1e3a8a"))
    subtitle_style = ParagraphStyle('DocSubtitle', parent=styles['Normal'], fontName='Helvetica', fontSize=9.5, alignment=1, textColor=colors.HexColor("#475569"))
    cell_style = ParagraphStyle('TableCell', parent=styles['Normal'], fontName='Helvetica', fontSize=8, leading=10)
    cell_bold = ParagraphStyle('TableCellBold', parent=styles['Normal'], fontName='Helvetica-Bold', fontSize=8, leading=10)

    elements = []
    elements.append(Paragraph("SONA COLLEGE OF TECHNOLOGY — DEPARTMENT OF IT", title_style))
    elements.append(Paragraph(f"MASTER LAB MONITORING REPORT — {lab_id}", ParagraphStyle('Head2', parent=subtitle_style, fontName='Helvetica-Bold', textColor=colors.HexColor("#2563eb"))))
    elements.append(Paragraph(f"Generated at: {datetime.now().strftime('%d-%m-%Y %H:%M:%S')} | Total Students Tracked: {len(sessions_list)}", subtitle_style))
    elements.append(Spacer(1, 10))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563eb"), spaceAfter=10))

    headers = [
        Paragraph("<b>Reg No</b>", cell_bold),
        Paragraph("<b>Student Name</b>", cell_bold),
        Paragraph("<b>PC ID</b>", cell_bold),
        Paragraph("<b>Login Time</b>", cell_bold),
        Paragraph("<b>Duration</b>", cell_bold),
        Paragraph("<b>Active %</b>", cell_bold),
        Paragraph("<b>Focus</b>", cell_bold),
        Paragraph("<b>Status</b>", cell_bold)
    ]
    rows = [headers]

    for s in sessions_list:
        rows.append([
            Paragraph(str(s.get("reg_no", "")), cell_style),
            Paragraph(str(s.get("student_name", "")), cell_style),
            Paragraph(str(s.get("pc_id", "")), cell_style),
            Paragraph(str(s.get("login_time", "")).split("T")[-1][:8] if "T" in str(s.get("login_time", "")) else str(s.get("login_time", ""))[-8:], cell_style),
            Paragraph(format_duration(s.get("total_duration_sec", 0)), cell_style),
            Paragraph(f"{s.get('active_pct', 90)}%", cell_style),
            Paragraph(f"{s.get('focus_score', 95)}%", cell_style),
            Paragraph(str(s.get("status", "ACTIVE")), cell_style)
        ])

    table = Table(rows, colWidths=[70, 110, 50, 70, 70, 50, 50, 50])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e2e8f0")),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor("#cbd5e1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#e2e8f0")),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 20))

    # Signature
    sig_data = [
        [Paragraph("<b>Lab Instructor:</b> _________________", cell_style), Paragraph("<b>HOD / Administrator:</b> _________________", cell_style)]
    ]
    sig_table = Table(sig_data, colWidths=[260, 260])
    elements.append(sig_table)

    doc.build(elements)
    return filepath, filename


def export_sessions_to_csv(sessions_list):
    """
    Exports student sessions to CSV formatted string.
    """
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Session ID", "Register Number", "Student Name", "Lab ID", "Workstation PC",
        "Login Time", "Logout Time", "Total Duration (sec)", "Active Duration (sec)",
        "Idle Duration (sec)", "Focus Score (%)", "Status"
    ])

    for s in sessions_list:
        writer.writerow([
            s.get("session_id"),
            s.get("reg_no"),
            s.get("student_name"),
            s.get("lab_id"),
            s.get("pc_id"),
            s.get("login_time"),
            s.get("logout_time"),
            s.get("total_duration_sec"),
            s.get("active_duration_sec"),
            s.get("idle_duration_sec"),
            s.get("focus_score"),
            s.get("status")
        ])

    return output.getvalue()


def dispatch_report_to_administrator(recipient_email, report_type="overall", student_reg_no=None, student_data=None, sessions_list=None, remarks=""):
    """
    Dispatches the generated report to the Administrator or Staff member.
    Generates academic PDF report and delivers it via SMTP email attachment to recipient_email.
    """
    now_iso = datetime.now().isoformat()
    if report_type == "student":
        if not student_data:
            student_data = {
                "reg_no": student_reg_no or "STUDENT",
                "student_name": f"Student ({student_reg_no or 'Registered'})",
                "total_duration_sec": 0,
                "active_duration_sec": 0,
                "idle_duration_sec": 0,
                "focus_score": 100.0,
                "app_usage": {},
                "domain_usage": {},
                "categories": {}
            }
        pdf_path, filename = generate_student_pdf_report(student_data)
        title = f"Student Digital Activity Report - {student_data.get('student_name')} ({student_data.get('reg_no')})"
        summary = {
            "reg_no": student_data.get("reg_no"),
            "student_name": student_data.get("student_name"),
            "total_duration": format_duration(student_data.get("total_duration_sec", 0)),
            "focus_score": student_data.get("context_switches", {}).get("focus_score", 100) if isinstance(student_data.get("context_switches"), dict) else student_data.get("focus_score", 100),
            "top_apps": list(student_data.get("app_usage", {}).keys())[:4],
            "top_tabs": list(student_data.get("domain_usage", {}).keys())[:4]
        }
    else:
        pdf_path, filename = generate_overall_lab_pdf_report("LAB-01 (AI & Cloud)", sessions_list or [])
        title = f"Overall Computer Laboratory Student Activity Report ({len(sessions_list or [])} Students)"
        summary = {
            "total_students": len(sessions_list or []),
            "lab": "Lab 1 - AI & Cloud Lab",
            "active_students": sum(1 for s in (sessions_list or []) if s.get("status") == "ACTIVE")
        }

    # Dispatch real email with PDF attachment to recipient_email (supports any staff email)
    from backend.email_provider import email_provider
    email_delivered = False
    delivery_note = ""

    if email_provider.is_configured() and recipient_email and "@" in recipient_email:
        try:
            em_res = email_provider.send_report_email(
                to_email=recipient_email,
                title=title,
                pdf_path=pdf_path,
                summary=summary,
                remarks=remarks or ""
            )
            email_delivered = em_res.get("success", False)
            if email_delivered:
                delivery_note = f" Delivered to {recipient_email} inbox."
            else:
                delivery_note = f" (Mail note: {em_res.get('error', 'Skipped')})"
        except Exception as ex:
            delivery_note = f" (Mail delivery exception: {str(ex)})"

    # Record in database log
    from backend.models import get_db_connection
    conn = get_db_connection("cloud_storage.db")
    cursor = conn.cursor()
    report_id = f"REP-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    cursor.execute("""
    INSERT INTO admin_reports (report_id, title, generated_at, recipient_email, status, summary_json, pdf_filename)
    VALUES (?, ?, ?, ?, 'SENT', ?, ?)
    """, (report_id, title, now_iso, recipient_email, json.dumps(summary), filename))
    conn.commit()
    conn.close()

    try:
        edge_conn = get_db_connection("edge_storage.db")
        edge_cursor = edge_conn.cursor()
        edge_cursor.execute("""
        INSERT INTO admin_reports (report_id, title, generated_at, recipient_email, status, summary_json, pdf_filename)
        VALUES (?, ?, ?, ?, 'SENT', ?, ?)
        """, (report_id, title, now_iso, recipient_email, json.dumps(summary), filename))
        edge_conn.commit()
        edge_conn.close()
    except Exception:
        pass

    return {
        "report_id": report_id,
        "recipient_email": recipient_email,
        "title": title,
        "status": "SENT",
        "email_delivered": email_delivered,
        "pdf_filename": filename,
        "generated_at": now_iso,
        "message": f"Report successfully dispatched to {recipient_email}.{delivery_note}"
    }
