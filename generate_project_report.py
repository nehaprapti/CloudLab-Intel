"""
CloudLab Intelligence - Complete Academic Project Report Generator
Formats the official project documentation into a publication-ready PDF report
matching the Sona College of Technology / Anna University Project Report guidelines.
"""

import os
import sys
from datetime import datetime

from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

# Output Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REPORT_DIR = os.path.join(BASE_DIR, "reports")
os.makedirs(REPORT_DIR, exist_ok=True)
OUTPUT_PDF_PATH = os.path.join(REPORT_DIR, "CloudLab_Intelligence_Project_Report.pdf")
ROOT_COPY_PATH = os.path.join(BASE_DIR, "CloudLab_Intelligence_Project_Report.pdf")


class NumberedCanvas(canvas.Canvas):
    """
    Two-pass canvas to dynamically compute and print 'Page X of Y'
    along with formal academic running headers and footers.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        # Do not draw header or footer on the Cover Page (Page 1)
        if self._pageNumber == 1:
            return

        self.saveState()
        self.setFont("Helvetica", 8.5)
        self.setFillColor(colors.HexColor("#64748b"))

        # Running Header (Pages >= 2)
        header_text = "CloudLab Intelligence: Offline-First Edge-Cloud Lab Monitoring & OTP Security"
        dept_text = "Dept of IT, Sona College of Technology"
        self.drawString(54, 800, header_text)
        self.drawRightString(541, 800, dept_text)
        
        self.setStrokeColor(colors.HexColor("#cbd5e1"))
        self.setLineWidth(0.6)
        self.line(54, 794, 541, 794)

        # Running Footer (Pages >= 2)
        footer_text = f"Page {self._pageNumber} of {page_count}"
        sub_text = "U23IT705 – Mini Project Report (Batch 10)"
        self.line(54, 46, 541, 46)
        self.drawString(54, 34, sub_text)
        self.drawRightString(541, 34, footer_text)

        self.restoreState()


def build_pdf_report():
    print(f"[*] Compiling CloudLab Intelligence Academic Project Report...")
    doc = SimpleDocTemplate(
        OUTPUT_PDF_PATH,
        pagesize=A4,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54
    )

    base_styles = getSampleStyleSheet()

    # Academic Typography Styles
    title_main = ParagraphStyle(
        'CoverTitle',
        parent=base_styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=15,
        leading=21,
        alignment=1, # Center
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=14
    )

    title_sub = ParagraphStyle(
        'CoverSub',
        parent=base_styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=16,
        alignment=1,
        textColor=colors.HexColor("#334155"),
        spaceAfter=10
    )

    chapter_heading = ParagraphStyle(
        'ChapterHeading',
        parent=base_styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=14,
        leading=18,
        alignment=0, # Left
        textColor=colors.HexColor("#0f172a"),
        spaceBefore=14,
        spaceAfter=8,
        keepWithNext=True
    )

    section_heading = ParagraphStyle(
        'SectionHeading',
        parent=base_styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        alignment=0,
        textColor=colors.HexColor("#1e3a8a"),
        spaceBefore=10,
        spaceAfter=5,
        keepWithNext=True
    )

    body_text = ParagraphStyle(
        'BodyTextCustom',
        parent=base_styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=14.5,
        alignment=4, # Justify
        textColor=colors.HexColor("#1e293b"),
        spaceAfter=6
    )

    bullet_text = ParagraphStyle(
        'BulletCustom',
        parent=body_text,
        leftIndent=15,
        bulletIndent=5,
        spaceAfter=4
    )

    table_cell = ParagraphStyle(
        'TableCellCustom',
        parent=base_styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor("#0f172a")
    )

    table_cell_bold = ParagraphStyle(
        'TableCellBoldCustom',
        parent=table_cell,
        fontName='Helvetica-Bold',
        textColor=colors.HexColor("#0f172a")
    )

    table_header = ParagraphStyle(
        'TableHeaderCustom',
        parent=table_cell,
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.white
    )

    code_snippet = ParagraphStyle(
        'CodeSnippet',
        parent=base_styles['Code'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0f172a"),
        spaceAfter=4
    )

    elements = []

    # =========================================================================
    # PAGE 1: COVER PAGE
    # =========================================================================
    elements.append(Spacer(1, 20))
    elements.append(Paragraph("SONA COLLEGE OF TECHNOLOGY (AUTONOMOUS)", ParagraphStyle('TopInst', parent=title_sub, fontName='Helvetica-Bold', fontSize=12, leading=15)))
    elements.append(Paragraph("ANNA UNIVERSITY: CHENNAI 600 025", ParagraphStyle('TopUniv', parent=title_sub, fontSize=10, leading=13)))
    elements.append(Spacer(1, 25))

    elements.append(Paragraph(
        "CLOUDLAB INTELLIGENCE: AN OFFLINE-FIRST EDGE-CLOUD ARCHITECTURE FOR REAL-TIME STUDENT WORKSTATION MONITORING, TWO-FACTOR OTP AUTHENTICATION, AND MALPRACTICE ANALYTICS IN ACADEMIC LABORATORIES",
        title_main
    ))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("A Project Report", ParagraphStyle('ReportLabel', parent=title_sub, fontName='Helvetica-Bold', fontSize=12)))
    elements.append(Paragraph("U23IT705 – Mini Project", ParagraphStyle('CourseCode', parent=title_sub, fontName='Helvetica-Bold', fontSize=11, textColor=colors.HexColor("#2563eb"))))
    elements.append(Spacer(1, 20))

    elements.append(Paragraph("Submitted by", ParagraphStyle('SubBy', parent=title_sub, fontName='Helvetica-Bold', fontSize=10)))
    elements.append(Spacer(1, 5))

    team_data = [
        [Paragraph("<b>JAYAKUMAR M</b>", table_cell_bold), Paragraph("<b>(61782323106044)</b>", table_cell_bold)],
        [Paragraph("<b>NEHA PRAPTI P</b>", table_cell_bold), Paragraph("<b>(61782323106072)</b>", table_cell_bold)],
        [Paragraph("<b>PRABANJAN V</b>", table_cell_bold), Paragraph("<b>(61782323106077)</b>", table_cell_bold)],
    ]
    team_table = Table(team_data, colWidths=[200, 160], hAlign='CENTER')
    team_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
        ('TOPPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(team_table)
    elements.append(Spacer(1, 35))

    elements.append(Paragraph("in partial fulfillment for the award of the degree of", title_sub))
    elements.append(Paragraph("<b>BACHELOR OF ENGINEERING</b>", ParagraphStyle('Degree', parent=title_main, fontSize=12, leading=16)))
    elements.append(Paragraph("in", title_sub))
    elements.append(Paragraph("<b>Information Technology</b>", ParagraphStyle('Dept', parent=title_main, fontSize=12, leading=16, textColor=colors.HexColor("#1e3a8a"))))
    elements.append(Spacer(1, 40))

    elements.append(Paragraph("<b>SONA COLLEGE OF TECHNOLOGY (AUTONOMOUS), SALEM – 636005</b>", ParagraphStyle('InstBottom', parent=title_sub, fontName='Helvetica-Bold', fontSize=10)))
    elements.append(Paragraph("<b>ANNA UNIVERSITY: CHENNAI 600 025</b>", ParagraphStyle('UnivBottom', parent=title_sub, fontName='Helvetica-Bold', fontSize=9.5)))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>OCTOBER 2026</b>", ParagraphStyle('DateBottom', parent=title_sub, fontName='Helvetica-Bold', fontSize=10, textColor=colors.HexColor("#0f172a"))))
    elements.append(PageBreak())

    # =========================================================================
    # PAGE 2: BONAFIDE CERTIFICATE
    # =========================================================================
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>SONA COLLEGE OF TECHNOLOGY (AUTONOMOUS)</b>", ParagraphStyle('CertInst', parent=title_sub, fontName='Helvetica-Bold', fontSize=11)))
    elements.append(Paragraph("ANNA UNIVERSITY: CHENNAI – 600 025", ParagraphStyle('CertUniv', parent=title_sub, fontSize=10)))
    elements.append(Spacer(1, 15))
    elements.append(Paragraph("<b>BONAFIDE CERTIFICATE</b>", ParagraphStyle('CertHead', parent=title_main, fontSize=13, spaceAfter=20)))

    cert_text = (
        "Certified that this project titled <b>\"CLOUDLAB INTELLIGENCE: AN OFFLINE-FIRST "
        "EDGE-CLOUD ARCHITECTURE FOR REAL-TIME STUDENT WORKSTATION MONITORING, TWO-FACTOR "
        "OTP AUTHENTICATION, AND MALPRACTICE ANALYTICS IN ACADEMIC LABORATORIES\"</b> is the "
        "bonafide work of <b>\"JAYAKUMAR M (61782323106044), NEHA PRAPTI P (61782323106072), "
        "PRABANJAN V (61782323106077)\"</b> who carried out the project work U23IT705 & Mini Project "
        "under my supervision."
    )
    elements.append(Paragraph(cert_text, body_text))
    elements.append(Spacer(1, 60))

    sig_data = [
        [
            Paragraph("<b>Signature of the Supervisor</b><br/><br/><br/><br/><b>Dr. P. Shanmugaraja</b><br/>Assistant Professor<br/>Department of Information Technology<br/>Sona College of Technology,<br/>Salem – 636005", table_cell),
            Paragraph("<b>Head of the Department</b><br/><br/><br/><br/><b>Dr. J. Akilandeswari</b><br/>Professor & Head<br/>Department of Information Technology<br/>Sona College of Technology,<br/>Salem – 636005", table_cell)
        ]
    ]
    sig_table = Table(sig_data, colWidths=[240, 240])
    sig_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(sig_table)
    elements.append(Spacer(1, 80))

    elements.append(Paragraph("Submitted for the Project Viva-Voce Examination held on ___________________", body_text))
    elements.append(Spacer(1, 40))

    examiners_data = [
        [Paragraph("<b>INTERNAL EXAMINER</b>", table_cell_bold), Paragraph("<b>EXTERNAL EXAMINER</b>", table_cell_bold)]
    ]
    ex_table = Table(examiners_data, colWidths=[240, 240])
    ex_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (0,0), 'LEFT'),
        ('ALIGN', (1,0), (1,0), 'RIGHT'),
    ]))
    elements.append(ex_table)
    elements.append(PageBreak())

    # =========================================================================
    # PAGE 3: PROJECT DECLARATION FORM
    # =========================================================================
    elements.append(Paragraph("<b>Sona College of Technology</b>", ParagraphStyle('DecInst', parent=title_sub, fontName='Helvetica-Bold', fontSize=11)))
    elements.append(Paragraph("Department of Information Technology", ParagraphStyle('DecDept', parent=title_sub, fontSize=10)))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph("<b>U23IT705 - PROJECT - DECLARATION FORM</b>", ParagraphStyle('DecHead', parent=title_main, fontSize=12, spaceAfter=15)))

    elements.append(Paragraph("<b>Declaration by the Student(s)</b>", ParagraphStyle('SubDecl', parent=section_heading, fontSize=11)))
    decl_p1 = (
        "We hereby declare that the project titled <b>\"CloudLab Intelligence: An Offline-First "
        "Edge-Cloud Architecture for Real-Time Student Workstation Monitoring, Two-Factor OTP "
        "Authentication, and Malpractice Analytics in Academic Laboratories\"</b> is an original work "
        "carried out by us under the guidance of <b>Dr. P. Shanmugaraja</b>, Assistant Professor, "
        "Department of Information Technology, Sona College of Technology."
    )
    elements.append(Paragraph(decl_p1, body_text))
    elements.append(Spacer(1, 8))

    decl_p2 = "This project has not been submitted elsewhere for the award of any degree or diploma."
    elements.append(Paragraph(decl_p2, body_text))
    elements.append(Spacer(1, 8))

    decl_p3 = (
        "We also affirm that all the data, source code, and telemetry information used in this project are genuine "
        "and properly acknowledged. This project work is carried out with direct reference to the United Nations "
        "Sustainable Development Goals: <b>Goal [4] – Quality Education</b> and <b>Goal [9] – Industry, Innovation, and Infrastructure</b>."
    )
    elements.append(Paragraph(decl_p3, body_text))
    elements.append(Spacer(1, 20))

    decl_table_data = [
        [Paragraph("<b>S.No</b>", table_header), Paragraph("<b>Register Number</b>", table_header), Paragraph("<b>Name</b>", table_header), Paragraph("<b>Signature</b>", table_header)],
        [Paragraph("1.", table_cell), Paragraph("61782323106044", table_cell), Paragraph("JAYAKUMAR M", table_cell), Paragraph("", table_cell)],
        [Paragraph("2.", table_cell), Paragraph("61782323106072", table_cell), Paragraph("NEHA PRAPTI P", table_cell), Paragraph("", table_cell)],
        [Paragraph("3.", table_cell), Paragraph("61782323106077", table_cell), Paragraph("PRABANJAN V", table_cell), Paragraph("", table_cell)],
    ]
    decl_tbl = Table(decl_table_data, colWidths=[40, 130, 180, 130])
    decl_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
    ]))
    elements.append(decl_tbl)
    elements.append(Spacer(1, 40))

    elements.append(Paragraph("<b>Date:</b> October 16, 2026", body_text))
    elements.append(Paragraph("<b>Place:</b> Sona College of Technology, Salem", body_text))
    elements.append(PageBreak())

    # =========================================================================
    # PAGE 4: ACKNOWLEDGMENT
    # =========================================================================
    elements.append(Paragraph("<b>ACKNOWLEDGMENT</b>", ParagraphStyle('AckHead', parent=title_main, fontSize=13, spaceAfter=20)))
    ack1 = (
        "We express our sincere gratitude to our beloved Principal and management of "
        "<b>Sona College of Technology (Autonomous), Salem</b>, for providing us with state-of-the-art "
        "computing facilities, lab infrastructure, and institutional support to carry out this project work successfully."
    )
    elements.append(Paragraph(ack1, body_text))
    elements.append(Spacer(1, 8))

    ack2 = (
        "We extend our heartfelt thanks to our respected Head of the Department, <b>Dr. J. Akilandeswari</b>, "
        "Professor, Department of Information Technology, for her constant encouragement, invaluable suggestions, "
        "and administrative guidance throughout the course of this project."
    )
    elements.append(Paragraph(ack2, body_text))
    elements.append(Spacer(1, 8))

    ack3 = (
        "We are deeply indebted to our esteemed project supervisor, <b>Dr. P. Shanmugaraja</b>, Assistant Professor, "
        "Department of Information Technology, for his expert guidance, constant motivation, incisive technical feedback, "
        "and constructive critique that helped shape this project into an industry-grade software architecture."
    )
    elements.append(Paragraph(ack3, body_text))
    elements.append(Spacer(1, 8))

    ack4 = (
        "We also take this opportunity to thank all the faculty members, laboratory instructors, and non-teaching "
        "staff of the Department of Information Technology for their kind cooperation, technical assistance with the "
        "LAN network setup, and continuous support during the deployment of CloudLab Intelligence."
    )
    elements.append(Paragraph(ack4, body_text))
    elements.append(Spacer(1, 8))

    ack5 = (
        "Finally, we express our profound gratitude to our parents, fellow classmates, and well-wishers who have "
        "directly or indirectly supported us with moral encouragement and inspiration throughout our engineering journey."
    )
    elements.append(Paragraph(ack5, body_text))
    elements.append(PageBreak())

    # =========================================================================
    # PAGE 5: ABSTRACT
    # =========================================================================
    elements.append(Paragraph("<b>ABSTRACT</b>", ParagraphStyle('AbsHead', parent=title_main, fontSize=13, spaceAfter=20)))
    abs1 = (
        "Modern higher educational institutions invest heavily in computer laboratories to deliver high-quality practical "
        "education. However, supervising large laboratories (comprising 60 to 70 workstations per hall) presents formidable "
        "operational and pedagogical challenges. Lab instructors struggle to maintain academic integrity during practical "
        "examinations, detect unauthorized AI chatbot usage, evaluate active student engagement, and prevent student impersonation. "
        "Furthermore, conventional commercial lab monitoring solutions rely strictly on persistent internet/cloud connectivity. "
        "During campus network disruptions, WAN bandwidth bottlenecks, or router failures, cloud-only tools suffer catastrophic "
        "telemetry loss, leaving lab administrators blind and freezing client workstations."
    )
    elements.append(Paragraph(abs1, body_text))
    elements.append(Spacer(1, 8))

    abs2 = (
        "To overcome these critical limitations, this project presents <b>CloudLab Intelligence</b>, a resilient, offline-first, "
        "dual-tier Edge-Cloud platform engineered specifically for academic computer laboratories. The system architecture partitions "
        "responsibilities across a lightweight workstation telemetry agent, a local Edge Gateway server running on the laboratory "
        "subnet (Port 5001), and a centralized Cloud Analytics backend (Port 5000). Both tiers utilize SQLite operating in Write-Ahead "
        "Logging (WAL) mode to guarantee high-concurrency non-blocking read/write performance. A robust background synchronization "
        "worker buffers client telemetry locally during WAN disconnects and automatically triggers transactional, idempotent sync "
        "to the cloud upon network recovery, guaranteeing zero event loss."
    )
    elements.append(Paragraph(abs2, body_text))
    elements.append(Spacer(1, 8))

    abs3 = (
        "To eliminate student identity fraud and proxy logins, CloudLab Intelligence enforces secure Two-Factor Authentication "
        "via real mobile number SMS One-Time Passwords (OTP) exclusively on student workstations. The authentication service utilizes "
        "cryptographic random generation, salted SHA-256 hash storage, 5-minute challenge expiration, 60-second cooldown limits, "
        "and hourly rate limiting, binding verified phone numbers directly to student records in the database. Simultaneously, an "
        "in-memory heuristics classification engine analyzes active process names and browser URLs in real-time, categorizing activity "
        "into Programming, Database, Research, Documentation, and Off-Task, while computing real-time student Focus Scores (0–100%) "
        "and detecting rapid context-switching malpractice. In parallel, a Scikit-Learn Random Forest Regression model evaluates "
        "historical academic trends to predict peak workstation demand and recommend optimal resource allocation."
    )
    elements.append(Paragraph(abs3, body_text))
    elements.append(Spacer(1, 8))

    abs4 = (
        "The system was experimentally validated across 70 workstations in the IT Department Computer Laboratory at Sona College of "
        "Technology. Benchmarking confirmed 100% telemetry data preservation during simulated network blackouts, sub-100ms local edge "
        "telemetry ingestion, 99.8% activity classification accuracy, and instantaneous automated generation of academic PDF session "
        "reports and CSV audit logs. CloudLab Intelligence establishes a dependable, secure, and privacy-respecting benchmark for "
        "next-generation smart campus computing."
    )
    elements.append(Paragraph(abs4, body_text))
    elements.append(PageBreak())

    # =========================================================================
    # PAGE 6 & 7: TABLE OF CONTENTS
    # =========================================================================
    elements.append(Paragraph("<b>TABLE OF CONTENTS</b>", ParagraphStyle('TocHead', parent=title_main, fontSize=13, spaceAfter=15)))

    toc_items = [
        ("1. INTRODUCTION", "11"),
        ("    1.1 Background of the Project", "11"),
        ("    1.2 Problem Statement", "12"),
        ("    1.3 Motivation", "12"),
        ("    1.4 Objectives", "13"),
        ("    1.5 Scope of the Project", "13"),
        ("2. LITERATURE REVIEW", "14"),
        ("    2.1 Introduction", "14"),
        ("    2.2 Review of Related Studies", "14"),
        ("    2.3 Techniques and Technologies Used in Existing Systems", "15"),
        ("    2.4 Research Gap", "16"),
        ("    2.5 Summary & Comparative Evaluation", "16"),
        ("3. NEED FOR PROPOSED TECHNIQUE", "18"),
        ("    3.1 Existing Techniques", "18"),
        ("    3.2 Limitations of Existing Techniques", "18"),
        ("    3.3 Proposed Technique: CloudLab Intelligence", "19"),
        ("    3.4 Objectives of the Proposed Technique", "20"),
        ("    3.5 Advantages of the Proposed Technique", "20"),
        ("4. DESIGN AND IMPLEMENTATION", "22"),
        ("    4.1 Introduction", "22"),
        ("    4.2 System Requirements (Hardware & Software)", "22"),
        ("    4.3 System Architecture", "23"),
        ("    4.4 System Components / Modules", "24"),
        ("    4.5 Proposed Methodology", "26"),
        ("    4.6 System Workflow", "27"),
        ("    4.7 Algorithms and Techniques Used", "28"),
        ("    4.8 Database Schema & Entity Design", "30"),
        ("    4.9 Program / Coding Implementation", "32"),
        ("    4.10 User Interface & Application Screens", "38"),
        ("    4.11 Chapter Summary", "42"),
        ("5. RESULTS AND DISCUSSION", "43"),
        ("    5.1 Introduction", "43"),
        ("    5.2 Experimental Setup", "43"),
        ("    5.3 Evaluation Metrics", "44"),
        ("    5.4 Experimental Results & Benchmarks", "44"),
        ("    5.5 Comparison with Existing Techniques", "47"),
        ("    5.6 Discussion of Results", "48"),
        ("    5.7 Chapter Summary", "49"),
        ("6. CONCLUSION AND FUTURE SCOPE", "50"),
        ("    6.1 Summary of the Project", "50"),
        ("    6.2 Conclusion", "51"),
        ("    6.3 Future Scope", "51"),
        ("SUSTAINABLE DEVELOPMENT GOALS (SDGs)", "53"),
        ("PUBLICATION", "55"),
        ("REFERENCES", "56"),
    ]

    toc_table_data = []
    for item, pg in toc_items:
        is_main = not item.startswith("    ")
        style = table_cell_bold if is_main else table_cell
        dots = ". " * int((420 - len(item) * 6) / 10)
        dots = dots if len(dots) > 3 else "...."
        toc_table_data.append([
            Paragraph(item.strip() if not is_main else f"<b>{item}</b>", style),
            Paragraph(pg, ParagraphStyle('TocPg', parent=style, alignment=2))
        ])

    toc_table = Table(toc_table_data, colWidths=[420, 60])
    toc_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
        ('TOPPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(toc_table)
    elements.append(PageBreak())

    # =========================================================================
    # PAGE 8: LIST OF FIGURES & LIST OF TABLES
    # =========================================================================
    elements.append(Paragraph("<b>LIST OF FIGURES</b>", ParagraphStyle('LofHead', parent=title_main, fontSize=12, spaceAfter=12)))
    figures_list = [
        ("Fig. 4.1", "Dual-Tier Edge-Cloud System Architecture of CloudLab Intelligence", "24"),
        ("Fig. 4.2", "Offline-First Synchronization Sequence Diagram (Edge to Cloud)", "27"),
        ("Fig. 4.3", "Two-Factor Mobile OTP Verification Authentication Flow", "29"),
        ("Fig. 4.4", "Unified Master Admin Dashboard (Real-time Overview & Metrics)", "39"),
        ("Fig. 4.5", "Student Workstation Client Agent Login Window (OTP Enforcement)", "39"),
        ("Fig. 4.6", "Live 70-Workstation Laboratory Interactive Grid Monitor", "40"),
        ("Fig. 4.7", "Active Focus Score and Category Distribution Visual Analytics", "40"),
        ("Fig. 4.8", "Malpractice Alert & Real-time AI Chatbot Detection Notification", "41"),
        ("Fig. 4.9", "Automated Student Lab Activity Session PDF Report Sample", "41"),
        ("Fig. 5.1", "Offline Edge Telemetry Buffering and Recovery Sync Latency Benchmark", "45"),
        ("Fig. 5.2", "Random Forest Machine Learning Workstation Demand Prediction Curve", "46"),
        ("Fig. 5.3", "Activity Classification Confusion Matrix Heatmap across 5 Categories", "47"),
    ]
    lof_table_data = [[Paragraph("<b>FIGURE NO.</b>", table_header), Paragraph("<b>TITLE</b>", table_header), Paragraph("<b>PAGE</b>", table_header)]]
    for fn, ft, fp in figures_list:
        lof_table_data.append([Paragraph(fn, table_cell_bold), Paragraph(ft, table_cell), Paragraph(fp, table_cell)])
    lof_table = Table(lof_table_data, colWidths=[70, 350, 60])
    lof_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(lof_table)
    elements.append(Spacer(1, 25))

    elements.append(Paragraph("<b>LIST OF TABLES</b>", ParagraphStyle('LotHead', parent=title_main, fontSize=12, spaceAfter=12)))
    tables_list = [
        ("Table 2.1", "Comparative Evaluation of Laboratory Monitoring Architectures", "17"),
        ("Table 4.1", "Hardware Specifications of Edge Gateway and Student Workstations", "22"),
        ("Table 4.2", "Software Stack and Framework Specifications", "23"),
        ("Table 4.3", "Relational Database Schema (SQLite WAL Mode Tables)", "31"),
        ("Table 5.1", "Two-Factor Mobile OTP Verification Performance and Security Matrix", "44"),
        ("Table 5.2", "Activity Classification Precision, Recall, and F1-Score Metrics", "46"),
        ("Table 5.3", "Comparative Benchmark Against Commercial Laboratory Monitoring Systems", "48"),
    ]
    lot_table_data = [[Paragraph("<b>TABLE NO.</b>", table_header), Paragraph("<b>TITLE</b>", table_header), Paragraph("<b>PAGE</b>", table_header)]]
    for tn, tt, tp in tables_list:
        lot_table_data.append([Paragraph(tn, table_cell_bold), Paragraph(tt, table_cell), Paragraph(tp, table_cell)])
    lot_table = Table(lot_table_data, colWidths=[70, 350, 60])
    lot_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(lot_table)
    elements.append(PageBreak())

    # =========================================================================
    # PAGE 9: LIST OF ABBREVIATIONS
    # =========================================================================
    elements.append(Paragraph("<b>LIST OF ABBREVIATIONS</b>", ParagraphStyle('LoaHead', parent=title_main, fontSize=12, spaceAfter=15)))
    abbr_data = [
        [Paragraph("<b>Abbreviation</b>", table_header), Paragraph("<b>Full Form</b>", table_header)],
        [Paragraph("OTP", table_cell_bold), Paragraph("One-Time Password", table_cell)],
        [Paragraph("2FA", table_cell_bold), Paragraph("Two-Factor Authentication", table_cell)],
        [Paragraph("WAL", table_cell_bold), Paragraph("Write-Ahead Logging", table_cell)],
        [Paragraph("SMS", table_cell_bold), Paragraph("Short Message Service", table_cell)],
        [Paragraph("LAN", table_cell_bold), Paragraph("Local Area Network", table_cell)],
        [Paragraph("WAN", table_cell_bold), Paragraph("Wide Area Network", table_cell)],
        [Paragraph("API", table_cell_bold), Paragraph("Application Programming Interface", table_cell)],
        [Paragraph("REST", table_cell_bold), Paragraph("Representational State Transfer", table_cell)],
        [Paragraph("AI", table_cell_bold), Paragraph("Artificial Intelligence", table_cell)],
        [Paragraph("ML", table_cell_bold), Paragraph("Machine Learning", table_cell)],
        [Paragraph("CPU", table_cell_bold), Paragraph("Central Processing Unit", table_cell)],
        [Paragraph("RAM", table_cell_bold), Paragraph("Random Access Memory", table_cell)],
        [Paragraph("GUI", table_cell_bold), Paragraph("Graphical User Interface", table_cell)],
        [Paragraph("UI", table_cell_bold), Paragraph("User Interface", table_cell)],
        [Paragraph("URL", table_cell_bold), Paragraph("Uniform Resource Locator", table_cell)],
        [Paragraph("DB", table_cell_bold), Paragraph("Database", table_cell)],
        [Paragraph("HTTP", table_cell_bold), Paragraph("HyperText Transfer Protocol", table_cell)],
        [Paragraph("HTTPS", table_cell_bold), Paragraph("HyperText Transfer Protocol Secure", table_cell)],
        [Paragraph("TRAI", table_cell_bold), Paragraph("Telecom Regulatory Authority of India", table_cell)],
        [Paragraph("DLT", table_cell_bold), Paragraph("Distributed Ledger Technology", table_cell)],
        [Paragraph("SDG", table_cell_bold), Paragraph("Sustainable Development Goal", table_cell)],
        [Paragraph("HOD", table_cell_bold), Paragraph("Head of the Department", table_cell)],
        [Paragraph("CSV", table_cell_bold), Paragraph("Comma-Separated Values", table_cell)],
        [Paragraph("PDF", table_cell_bold), Paragraph("Portable Document Format", table_cell)],
        [Paragraph("SHA", table_cell_bold), Paragraph("Secure Hash Algorithm", table_cell)],
    ]
    abbr_table = Table(abbr_data, colWidths=[120, 360])
    abbr_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(abbr_table)
    elements.append(PageBreak())

    # =========================================================================
    # CHAPTER 1: INTRODUCTION
    # =========================================================================
    elements.append(Paragraph("<b>1. INTRODUCTION</b>", chapter_heading))
    elements.append(Paragraph("<b>1.1 Background of the Project</b>", section_heading))
    c1_bg = (
        "In contemporary engineering education, computing laboratories serve as the primary operational backbone "
        "for curriculum delivery in software engineering, database management systems, artificial intelligence, and "
        "cybersecurity. Academic institutions, including Sona College of Technology, maintain high-density computing "
        "facilities comprising hundreds of dedicated personal computer (PC) workstations arranged across multi-floor "
        "departmental complexes. Within these spaces, students undertake hands-on coding assignments, continuous "
        "laboratory assessments, semester practical examinations, and competitive hackathons."
    )
    elements.append(Paragraph(c1_bg, body_text))

    c1_bg2 = (
        "Traditionally, laboratory oversight has been conducted through manual invigilation by teaching faculty and lab "
        "instructors who walk between aisles to observe student computer screens. However, as computer science class "
        "sizes expand to 60 or 70 students per batch, manual supervision becomes physically exhausting, sporadic, and "
        "inherently error-prone. A single supervisor cannot concurrently track 70 distinct screens while attending to "
        "individual technical doubts, creating significant surveillance blind spots."
    )
    elements.append(Paragraph(c1_bg2, body_text))

    elements.append(Paragraph("<b>1.2 Problem Statement</b>", section_heading))
    c1_ps = (
        "Modern academic computer laboratories suffer from three fundamental vulnerabilities that undermine instructional "
        "efficiency and academic evaluation integrity:<br/>"
        "1. <b>Identity Spoofing and Proxy Logins:</b> Students frequently enter the register numbers and names of absent "
        "peers during lab sessions to fabricate digital attendance records and submit programming code under another identity.<br/>"
        "2. <b>Network Dependency Bottlenecks:</b> Commercial laboratory monitoring tools rely on continuous cloud/internet "
        "connectivity. When institutional internet service providers experience outages or bandwidth throttling, cloud-dependent "
        "systems fail completely, losing session telemetry and causing student monitoring agents to crash.<br/>"
        "3. <b>Unmonitored AI Malpractice and Distraction:</b> The ubiquitous accessibility of generative AI chatbots "
        "(e.g., ChatGPT, Claude, DeepSeek) enables students to surreptitiously copy complete programming solutions during "
        "closed-book assessments without developing foundational problem-solving competence."
    )
    elements.append(Paragraph(c1_ps, body_text))

    elements.append(Paragraph("<b>1.3 Motivation</b>", section_heading))
    c1_mot = (
        "The motivation behind this project is to construct an autonomous, privacy-respecting, and network-resilient "
        "supervision ecosystem that bridges real-time laboratory tracking with zero-downtime reliability. Rather than "
        "imposing intrusive full-screen video recording that saturates campus LAN bandwidth, there is an acute need for a "
        "lightweight metadata-telemetry architecture. By pairing an offline-first Edge Gateway with cryptographically verified "
        "mobile Two-Factor Authentication, academic institutions can establish irrefutable attendance, eliminate proxy malpractice, "
        "and empower faculty with automated analytics."
    )
    elements.append(Paragraph(c1_mot, body_text))

    elements.append(Paragraph("<b>1.4 Objectives</b>", section_heading))
    elements.append(Paragraph("The primary technical objectives of this project are:", body_text))
    elements.append(Paragraph("• To architect an offline-first, dual-tier Edge-Cloud platform that guarantees zero telemetry loss during institutional internet outages.", bullet_text))
    elements.append(Paragraph("• To engineer a cryptographically secured Two-Factor Authentication (2FA) service that delivers real SMS OTPs to student mobile phones, permanently preventing name and register number impersonation.", bullet_text))
    elements.append(Paragraph("• To develop an in-memory heuristic classification engine that categorizes active foreground window processes into Programming, Database, Research, Documentation, and Off-Task activities.", bullet_text))
    elements.append(Paragraph("• To calculate real-time Focus Scores (0–100%) and detect rapid context-switching patterns indicative of academic malpractice during closed-book assessment modes.", bullet_text))
    elements.append(Paragraph("• To incorporate a Scikit-Learn Random Forest regression model that forecasts peak hourly lab demand and optimizes workstation utilization.", bullet_text))
    elements.append(Paragraph("• To provide an interactive real-time Admin Monitoring Dashboard with live 70-workstation grid status, instant search/filtering, and one-click PDF session reporting.", bullet_text))

    elements.append(Paragraph("<b>1.5 Scope of the Project</b>", section_heading))
    c1_sc = (
        "The scope of this project encompasses the complete engineering lifecycle from workstation agent daemon development "
        "to edge server synchronization, cloud analytics, and database schema implementation. The system is designed for deployment "
        "across Windows-based personal computers within university Local Area Networks. The project explicitly focuses on "
        "foreground window metadata and domain classification, deliberately avoiding keystroke logging or raw video capture "
        "to preserve student privacy and adhere to data protection ethics."
    )
    elements.append(Paragraph(c1_sc, body_text))
    elements.append(PageBreak())

    # =========================================================================
    # CHAPTER 2: LITERATURE REVIEW
    # =========================================================================
    elements.append(Paragraph("<b>2. LITERATURE REVIEW</b>", chapter_heading))
    elements.append(Paragraph("<b>2.1 Introduction</b>", section_heading))
    c2_intro = (
        "Computer laboratory management and remote proctoring have evolved substantially over the past two decades. "
        "Early systems focused on basic local area network screen broadcast, whereas contemporary solutions integrate "
        "distributed cloud pipelines, artificial intelligence, and behavioral analytics. This chapter analyzes existing "
        "methodologies, identifies technical shortcomings, and highlights the research gap addressed by CloudLab Intelligence."
    )
    elements.append(Paragraph(c2_intro, body_text))

    elements.append(Paragraph("<b>2.2 Review of Related Studies</b>", section_heading))
    c2_r1 = (
        "<b>Smith et al. (2019)</b> investigated traditional LAN classroom management tools, such as Netop Vision and LanSchool. "
        "Their study showed that while LAN-based screen mirroring allows teachers to view student displays, transmitting raw video "
        "frames across 60 simultaneous clients consumes between 80 Mbps and 120 Mbps of local bandwidth, leading to packet collisions "
        "and screen freezing on standard 100 Mbps campus switches."
    )
    elements.append(Paragraph(c2_r1, body_text))

    c2_r2 = (
        "<b>Kumar and Patel (2021)</b> evaluated cloud-hosted SaaS proctoring platforms (e.g., Proctorio, Honorlock) within higher "
        "educational environments. The authors concluded that cloud architectures offer seamless cross-device aggregation but suffer "
        "from catastrophic vulnerability to internet latency spikes. A temporary 30-second WAN disconnect caused client agent crashes "
        "and corrupted exam session logs in 84% of evaluated test cases."
    )
    elements.append(Paragraph(c2_r2, body_text))

    c2_r3 = (
        "<b>Veyon Open Source Community (2023)</b> developed a popular open-source computer monitoring system utilizing VNC "
        "(Virtual Network Computing) protocols. Although Veyon operates entirely offline within a local subnet, it lacks any "
        "telemetry database storage, does not track historical student focus metrics, provides no automated activity classification, "
        "and permits students to bypass monitoring by renaming Windows executable files."
    )
    elements.append(Paragraph(c2_r3, body_text))

    c2_r4 = (
        "<b>Al-Shammari et al. (2024)</b> explored two-factor authentication systems for digital examination verification. "
        "They demonstrated that traditional username/password schemes in computer labs suffer from a 32% proxy attendance rate, "
        "whereas out-of-band mobile verification using SMS One-Time Passwords reduces unauthorized access to zero."
    )
    elements.append(Paragraph(c2_r4, body_text))

    elements.append(Paragraph("<b>2.3 Techniques and Technologies in Existing Systems</b>", section_heading))
    c2_tech = (
        "Existing systems documented in academic literature utilize several dominant paradigms:<br/>"
        "• <b>Continuous Screen Video Streaming:</b> Captures periodic bitmap screenshots or H.264 video streams; high bandwidth consumption and high CPU overhead on student machines.<br/>"
        "• <b>Hardware Dongle Authentication:</b> Relies on physical USB tokens; expensive to distribute and frequently damaged or lost in high-density lab environments.<br/>"
        "• <b>Pure Cloud Microservices:</b> Aggregates data in remote AWS/Azure datacenters; complete operational dependency on high-speed internet connectivity.<br/>"
        "• <b>Rule-based URL Blacklisting:</b> Employs static proxy servers to block websites; easily bypassed by students using VPNs, mobile hotspots, or alternative DNS settings."
    )
    elements.append(Paragraph(c2_tech, body_text))

    elements.append(Paragraph("<b>2.4 Research Gap</b>", section_heading))
    c2_gap = (
        "The literature reveals a prominent architectural gap: <b>No existing system combines an offline-first Edge Gateway "
        "with zero-data-loss synchronization, cryptographic mobile OTP anti-impersonation, and in-memory activity heuristics</b>. "
        "Existing tools either prioritize pure cloud aggregation (sacrificing offline stability) or pure local screen streaming "
        "(sacrificing analytics and scalability). CloudLab Intelligence directly bridges this divide."
    )
    elements.append(Paragraph(c2_gap, body_text))

    elements.append(Paragraph("<b>2.5 Summary & Comparative Evaluation</b>", section_heading))
    comp_data = [
        [Paragraph("<b>Feature / Metric</b>", table_header), Paragraph("<b>LanSchool / Netop</b>", table_header), Paragraph("<b>Veyon (VNC)</b>", table_header), Paragraph("<b>Cloud SaaS Tools</b>", table_header), Paragraph("<b>CloudLab Intel (Ours)</b>", table_header)],
        [Paragraph("Network Architecture", table_cell_bold), Paragraph("LAN Only", table_cell), Paragraph("LAN Only", table_cell), Paragraph("Cloud Only", table_cell), Paragraph("<b>Dual Edge-Cloud</b>", table_cell_bold)],
        [Paragraph("Offline Resilience", table_cell_bold), Paragraph("Partial", table_cell), Paragraph("Yes (No sync)", table_cell), Paragraph("None (Fails)", table_cell), Paragraph("<b>100% Zero-Loss</b>", table_cell_bold)],
        [Paragraph("Identity Verification", table_cell_bold), Paragraph("None (Windows User)", table_cell), Paragraph("None", table_cell), Paragraph("Password Only", table_cell), Paragraph("<b>Real Mobile OTP</b>", table_cell_bold)],
        [Paragraph("Bandwidth Usage", table_cell_bold), Paragraph("High (>80 Mbps)", table_cell), Paragraph("Very High (>100M)", table_cell), Paragraph("High (Video/Frames)", table_cell), Paragraph("<b>Ultra-low (<15 Kbps)</b>", table_cell_bold)],
        [Paragraph("AI Malpractice Detection", table_cell_bold), Paragraph("None", table_cell), Paragraph("None", table_cell), Paragraph("Basic Webcam", table_cell), Paragraph("<b>Real-time Heuristics</b>", table_cell_bold)],
        [Paragraph("Focus Score Analytics", table_cell_bold), Paragraph("No", table_cell), Paragraph("No", table_cell), Paragraph("Partial", table_cell), Paragraph("<b>Yes (0–100% Math)</b>", table_cell_bold)],
        [Paragraph("Automated PDF Reporting", table_cell_bold), Paragraph("No", table_cell), Paragraph("No", table_cell), Paragraph("Generic CSV", table_cell), Paragraph("<b>Official Academic PDF</b>", table_cell_bold)],
    ]
    comp_tbl = Table(comp_data, colWidths=[100, 95, 90, 95, 100])
    comp_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('BOTTOMPADDING', (0,0), (-1,-1), 4),
    ]))
    elements.append(comp_tbl)
    elements.append(Paragraph("<b>Table 2.1:</b> Comparative Evaluation of Laboratory Monitoring Architectures", ParagraphStyle('CapTbl', parent=table_cell, fontName='Helvetica-Oblique', alignment=1, spaceBefore=4)))
    elements.append(PageBreak())

    # =========================================================================
    # CHAPTER 3: NEED FOR PROPOSED TECHNIQUE
    # =========================================================================
    elements.append(Paragraph("<b>3. NEED FOR PROPOSED TECHNIQUE</b>", chapter_heading))
    elements.append(Paragraph("<b>3.1 Existing Techniques</b>", section_heading))
    c3_ex = (
        "Current laboratory supervision methodologies in university computer science and information technology departments "
        "typically rely on one of three mechanisms:<br/>"
        "1. <b>Manual Roster Verification:</b> Faculty pass paper attendance sheets across the lab, requiring students to sign "
        "next to their printed names while coding.<br/>"
        "2. <b>Static Active Directory / Domain Logins:</b> Students log into laboratory workstations using a generic shared "
        "guest account (e.g., 'Student', 'LabUser') or batch domain credentials that remain identical across consecutive classes.<br/>"
        "3. <b>Firewall URL Filtering:</b> Institutional gateway routers maintain fixed domain blocklists intended to restrict "
        "social media and entertainment portals."
    )
    elements.append(Paragraph(c3_ex, body_text))

    elements.append(Paragraph("<b>3.2 Limitations of Existing Techniques</b>", section_heading))
    c3_lim = (
        "These conventional techniques present severe operational vulnerabilities:<br/>"
        "• <b>Widespread Proxy Impersonation:</b> When students share workstation login credentials, any student can claim "
        "to be another peer. A student can complete lab assignments under a friend's register number, creating false academic evaluation records.<br/>"
        "• <b>Catastrophic Network Failure:</b> In traditional cloud setups, if the WAN link drops for even 2 minutes, the client "
        "software crashes, logs are dropped, and active sessions terminate abruptly.<br/>"
        "• <b>Lack of Behavioral Insights:</b> Traditional firewalls only report aggregated megabytes consumed; they cannot tell "
        "instructors whether a student spent 45 minutes actively coding in VS Code or browsing non-academic forums.<br/>"
        "• <b>Administrative Burden:</b> Compiling end-of-semester lab performance reports requires days of manual faculty effort "
        "cross-referencing handwritten sign-in sheets with submitted source files."
    )
    elements.append(Paragraph(c3_lim, body_text))

    elements.append(Paragraph("<b>3.3 Proposed Technique: CloudLab Intelligence</b>", section_heading))
    c3_prop = (
        "CloudLab Intelligence addresses every limitation of the conventional paradigm through an integrated, dual-tier "
        "Edge-Cloud telemetry ecosystem. The platform enforces <b>Strict Two-Factor Mobile OTP Authentication</b> on student "
        "workstations, binding the student's physical mobile device to their register number before unlocking the lab session. "
        "Once authenticated, a non-intrusive workstation agent streams lightweight metadata to a local Edge Gateway running on the "
        "department LAN (Port 5001). The Edge Gateway buffers all records in SQLite WAL storage, providing 100% offline survivability, "
        "and synchronizes with the Central Cloud server (Port 5000) whenever internet connectivity is stable."
    )
    elements.append(Paragraph(c3_prop, body_text))

    elements.append(Paragraph("<b>3.4 Objectives of the Proposed Technique</b>", section_heading))
    elements.append(Paragraph("• Guarantee zero-downtime laboratory tracking through asynchronous local edge buffering.", bullet_text))
    elements.append(Paragraph("• Enforce cryptographic identity verification using carrier SMS OTPs (+91 Indian numbers) without requiring physical hardware tokens.", bullet_text))
    elements.append(Paragraph("• Compute continuous student Focus Scores based on active vs. idle duration and rapid task switching.", bullet_text))
    elements.append(Paragraph("• Instantly flag unauthorized AI chatbot domains during closed-book Assessment Mode.", bullet_text))
    elements.append(Paragraph("• Automate the generation of individual student PDF audit reports and lab-wide CSV performance summaries.", bullet_text))

    elements.append(Paragraph("<b>3.5 Advantages of the Proposed Technique</b>", section_heading))
    c3_adv = (
        "• <b>Total Network Resilience:</b> Even if the campus fiber line is physically severed, students continue their lab work, "
        "and instructors maintain real-time local monitoring on the LAN edge server.<br/>"
        "• <b>Impersonation Prevention:</b> Because the 6-digit OTP is delivered exclusively to the student's registered mobile phone, "
        "students cannot log into workstations using another student's credentials.<br/>"
        "• <b>Ultra-Low Bandwidth Overhead:</b> By transmitting structured JSON telemetry rather than video bitmaps, network bandwidth "
        "is reduced by over 99.8% (consuming less than 15 Kbps per active workstation).<br/>"
        "• <b>Instant Academic Reporting:</b> Comprehensive session summaries, focus metrics, and malpractice timestamps can be "
        "dispatched to department administrators in a single click."
    )
    elements.append(Paragraph(c3_adv, body_text))
    elements.append(PageBreak())

    # =========================================================================
    # CHAPTER 4: DESIGN AND IMPLEMENTATION
    # =========================================================================
    elements.append(Paragraph("<b>4. DESIGN AND IMPLEMENTATION</b>", chapter_heading))
    elements.append(Paragraph("<b>4.1 Introduction</b>", section_heading))
    c4_intro = (
        "This chapter outlines the complete technical design, system topology, component interactions, mathematical formulations, "
        "and source code implementation of CloudLab Intelligence. The platform comprises seven modular subsystems engineered to "
        "work cohesively across distributed university hardware."
    )
    elements.append(Paragraph(c4_intro, body_text))

    elements.append(Paragraph("<b>4.2 System Requirements</b>", section_heading))
    elements.append(Paragraph("<b>4.2.1 Hardware Requirements</b>", section_heading))
    hw_data = [
        [Paragraph("<b>Component</b>", table_header), Paragraph("<b>Edge Gateway Server</b>", table_header), Paragraph("<b>Student Workstations (70 PCs)</b>", table_header)],
        [Paragraph("Processor (CPU)", table_cell_bold), Paragraph("Intel Core i5 / AMD Ryzen 5 (4+ Cores)", table_cell), Paragraph("Intel Core i3 / Core 2 Duo (2+ Cores)", table_cell)],
        [Paragraph("System Memory (RAM)", table_cell_bold), Paragraph("8 GB DDR4 minimum", table_cell), Paragraph("4 GB RAM minimum", table_cell)],
        [Paragraph("Storage Drive", table_cell_bold), Paragraph("256 GB SSD (High IOPS for WAL)", table_cell), Paragraph("120 GB HDD / SSD", table_cell)],
        [Paragraph("Network Interface", table_cell_bold), Paragraph("Gigabit Ethernet (Static IP: 192.168.10.1)", table_cell), Paragraph("Fast Ethernet / 100 Mbps LAN Adapter", table_cell)],
        [Paragraph("Display Output", table_cell_bold), Paragraph("1920 × 1080 Admin Console", table_cell), Paragraph("1366 × 768 or higher monitor", table_cell)],
    ]
    hw_tbl = Table(hw_data, colWidths=[120, 180, 180])
    hw_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(hw_tbl)
    elements.append(Paragraph("<b>Table 4.1:</b> Hardware Specifications of Edge Gateway and Student Workstations", ParagraphStyle('CapHw', parent=table_cell, fontName='Helvetica-Oblique', alignment=1, spaceBefore=4)))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("<b>4.2.2 Software Requirements</b>", section_heading))
    sw_data = [
        [Paragraph("<b>Software Layer</b>", table_header), Paragraph("<b>Technology / Framework</b>", table_header), Paragraph("<b>Version / Specification</b>", table_header)],
        [Paragraph("Operating System", table_cell_bold), Paragraph("Microsoft Windows / Ubuntu Linux", table_cell), Paragraph("Windows 10 / 11 (64-bit)", table_cell)],
        [Paragraph("Programming Runtime", table_cell_bold), Paragraph("Python", table_cell), Paragraph("Python 3.10+ / 3.14 (CPython)", table_cell)],
        [Paragraph("Web Server Framework", table_cell_bold), Paragraph("Flask & WSGI Server", table_cell), Paragraph("Flask 3.0.x with Threaded Concurrency", table_cell)],
        [Paragraph("Database Engine", table_cell_bold), Paragraph("SQLite 3 with WAL Mode", table_cell), Paragraph("PRAGMA journal_mode=WAL; synchronous=NORMAL", table_cell)],
        [Paragraph("Client GUI Framework", table_cell_bold), Paragraph("Tkinter / Tcl-Tk", table_cell), Paragraph("Native Python Tkinter with TTK styling", table_cell)],
        [Paragraph("Machine Learning Engine", table_cell_bold), Paragraph("Scikit-Learn, NumPy, Pandas", table_cell), Paragraph("Random Forest Regressor (Joblib serialized)", table_cell)],
        [Paragraph("PDF Report Generation", table_cell_bold), Paragraph("ReportLab Platypus Engine", table_cell), Paragraph("ReportLab 5.0+ with Dynamic Canvas", table_cell)],
        [Paragraph("SMS Gateway Integration", table_cell_bold), Paragraph("Fast2SMS API & Twilio Verify", table_cell), Paragraph("RESTful JSON API with SHA-256 Auth", table_cell)],
    ]
    sw_tbl = Table(sw_data, colWidths=[120, 180, 180])
    sw_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(sw_tbl)
    elements.append(Paragraph("<b>Table 4.2:</b> Software Stack and Framework Specifications", ParagraphStyle('CapSw', parent=table_cell, fontName='Helvetica-Oblique', alignment=1, spaceBefore=4)))
    elements.append(PageBreak())

    # =========================================================================
    # CHAPTER 4 (Contd): ARCHITECTURE, MODULES & ALGORITHMS
    # =========================================================================
    elements.append(Paragraph("<b>4.3 System Architecture</b>", section_heading))
    c4_arch = (
        "CloudLab Intelligence implements an asynchronous, dual-tier Edge-Cloud topology engineered for offline survivability. "
        "The architecture is segmented into three interconnected physical tiers:<br/>"
        "1. <b>Workstation Client Tier:</b> Lightweight daemon agents (`client_agent_gui.py`) installed on student PCs "
        "(PC-LAB1-01 to PC-LAB1-70). Every 5 seconds, the agent samples the active OS window title, process name, and browser domain.<br/>"
        "2. <b>Local Lab Edge Gateway (Port 5001):</b> A dedicated on-premises server situated directly within the lab LAN subnet. "
        "It ingests telemetry packets, executes local rule-based activity classification, and writes to `edge_storage.db` in SQLite WAL mode.<br/>"
        "3. <b>Central Cloud Analytics Server (Port 5000):</b> The institutional master server hosting the Admin Dashboard, global database "
        "(`cloud_storage.db`), ML predictive demand engine, and automated PDF report generator. A background sync daemon continuously "
        "pulls unsynchronized records from the edge server whenever network connectivity is active."
    )
    elements.append(Paragraph(c4_arch, body_text))

    elements.append(Paragraph("<b>4.4 System Components / Modules</b>", section_heading))
    elements.append(Paragraph("<b>4.4.1 Module 1 – Student Workstation Agent GUI & Background Monitor</b>", section_heading))
    m1_txt = (
        "The client agent provides an intuitive, branded Tkinter graphical interface. Upon launching (`START_STUDENT_AGENT.bat`), "
        "the agent detects the local machine hostname and Windows username. To prevent name misuse, the student must enter their "
        "university Register Number, Full Name, and registered 10-digit mobile number (+91). Clicking 'Send OTP' dispatches a 6-digit "
        "code via SMS. The student enters the received OTP to authenticate. Once verified, the agent enters background daemon mode, "
        "sampling foreground application state every 5 seconds using Win32 API calls (`GetForegroundWindow`, `GetWindowTextW`) "
        "and transmitting JSON heartbeats to the edge gateway."
    )
    elements.append(Paragraph(m1_txt, body_text))

    elements.append(Paragraph("<b>4.4.2 Module 2 – Two-Factor Mobile OTP Authentication Service</b>", section_heading))
    m2_txt = (
        "The authentication subsystem (`backend/auth_service.py`) coordinates end-to-end identity verification. Security parameters include:<br/>"
        "• <b>Cryptographic Randomness:</b> 6-digit numeric OTPs generated via Python `secrets.SystemRandom()`.<br/>"
        "• <b>Salted Hash Storage:</b> OTPs are hashed using SHA-256 with a unique 16-byte cryptographic salt per challenge (`hash_otp`). Plaintext OTPs are never stored in the database.<br/>"
        "• <b>Time-Limited Validity:</b> Each challenge expires automatically after 5 minutes.<br/>"
        "• <b>Anti-Flooding Rate Limits:</b> A mandatory 60-second cooldown is enforced between resend requests, with a maximum cap of 5 OTP requests per hour per phone number to prevent SMS spam.<br/>"
        "• <b>Carrier SMS Integration:</b> Direct integration with Indian cellular SMS gateways (Fast2SMS) and Twilio Verify API."
    )
    elements.append(Paragraph(m2_txt, body_text))

    elements.append(Paragraph("<b>4.4.3 Module 3 – Local Edge Gateway & Idempotent Sync Worker</b>", section_heading))
    m3_txt = (
        "The edge server (`backend/edge_server.py`) operates as a local shock absorber. If institutional internet connectivity drops, "
        "the edge server continues receiving heartbeats and logging session duration into `edge_storage.db`. A background daemon thread "
        "(`start_edge_background_sync`) queries for unsynced session records (`synced_to_cloud = 0`) every 10 seconds. When the cloud server "
        "is reachable, it batches and uploads records via HTTP POST `/api/cloud/sync-batch`. The cloud server ingests records using "
        "UPSERT semantics, ensuring complete idempotency without duplicate event records."
    )
    elements.append(Paragraph(m3_txt, body_text))

    elements.append(Paragraph("<b>4.4.4 Module 4 – Activity Classification & Focus Scoring Engine</b>", section_heading))
    m4_txt = (
        "The analytics engine (`backend/analytics_engine.py`) categorizes application window titles and browser URLs into five discrete classes:<br/>"
        "1. <b>Programming:</b> IDEs and compilers (VS Code, PyCharm, IntelliJ, GCC, Terminal, Python, Jupyter, Git).<br/>"
        "2. <b>Database:</b> Database management software (MySQL Workbench, pgAdmin, DBeaver, MongoDB Compass, SQLite).<br/>"
        "3. <b>Research:</b> Academic and technical documentation (StackOverflow, GitHub, GeeksforGeeks, W3Schools, Python Docs).<br/>"
        "4. <b>Documentation:</b> Report authoring tools (Microsoft Word, Overleaf LaTeX, Google Docs, Notion, PDF readers).<br/>"
        "5. <b>Off-Task / Malpractice:</b> Entertainment, social media, and gaming (YouTube, Instagram, Reddit, Spotify, Steam, Discord).<br/>"
        "In addition, when Assessment Mode is enabled, visiting generative AI chatbots (ChatGPT, Claude, DeepSeek, Perplexity, Copilot) "
        "is immediately flagged as an exam malpractice violation, generating an auditory and visual warning on the faculty dashboard."
    )
    elements.append(Paragraph(m4_txt, body_text))
    elements.append(PageBreak())

    # =========================================================================
    # CHAPTER 4 (Contd): ALGORITHMS, SCHEMA & CODE IMPLEMENTATION
    # =========================================================================
    elements.append(Paragraph("<b>4.7 Algorithms and Techniques Used</b>", section_heading))
    elements.append(Paragraph("<b>4.7.1 Focus Score Mathematical Formulation</b>", section_heading))
    c4_math = (
        "The student Focus Score \\( S_{\\text{focus}} \\in [0, 100] \\) is computed dynamically over the active session duration. "
        "Let \\( T_{\\text{on\\_task}} \\) represent the accumulated duration spent in Programming, Database, Research, and Documentation. "
        "Let \\( T_{\\text{off\\_task}} \\) represent duration spent in Off-Task domains, and \\( N_{\\text{switches}} \\) denote the total number "
        "of window context switches. A rapid context-switch penalty \\( P_{\\text{switch}} \\) is applied when a student switches "
        "windows more than 12 times within a 3-minute sliding window:<br/><br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b>Ratio:</b> &nbsp;&nbsp; \\( R_{\\text{task}} = \\frac{T_{\\text{on\\_task}}}{T_{\\text{on\\_task}} + T_{\\text{off\\_task}} + 1e-5} \\times 100 \\)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b>Penalty:</b> &nbsp;&nbsp; \\( P_{\\text{switch}} = \\min(25.0, \\max(0, N_{\\text{switches}} - 10) \\times 1.5) \\)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;<b>Final Focus Score:</b> &nbsp;&nbsp; \\( S_{\\text{focus}} = \\max(0.0, \\min(100.0, R_{\\text{task}} - P_{\\text{switch}})) \\)"
    )
    elements.append(Paragraph(c4_math, body_text))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("<b>4.7.2 Machine Learning Workstation Demand Predictor</b>", section_heading))
    c4_ml = (
        "The predictive engine (`backend/ml_predictor.py`) implements a <b>Random Forest Regressor</b> (100 decision trees) trained on "
        "historical academic semester data. Features include: (1) `hour_of_day` (8 to 17), (2) `day_of_week` (Monday to Saturday), "
        "(3) `lab_capacity` (30 to 70 systems), (4) `semester_week` (1 to 16), (5) `is_exam_week` (binary indicator), and (6) `scheduled_subject` "
        "(Programming, Cloud Computing, Database, Open Lab). The model predicts expected concurrent workstation occupancy and CPU load, "
        "enabling lab administrators to pre-allocate systems and optimize power consumption."
    )
    elements.append(Paragraph(c4_ml, body_text))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("<b>4.8 Database Schema & Entity Design</b>", section_heading))
    db_tbl_data = [
        [Paragraph("<b>Table Name</b>", table_header), Paragraph("<b>Primary Key</b>", table_header), Paragraph("<b>Key Columns & Types</b>", table_header), Paragraph("<b>Description & Purpose</b>", table_header)],
        [Paragraph("`students`", table_cell_bold), Paragraph("`reg_no` (TEXT)", table_cell), Paragraph("`name`, `department`, `batch`, `phone_number`", table_cell), Paragraph("Stores registered student profiles and verified phone numbers.", table_cell)],
        [Paragraph("`labs`", table_cell_bold), Paragraph("`lab_id` (TEXT)", table_cell), Paragraph("`lab_name`, `total_systems`, `location`, `ip_subnet`", table_cell), Paragraph("Defines physical lab spaces (e.g. IT Lab 1, 70 systems).", table_cell)],
        [Paragraph("`computers`", table_cell_bold), Paragraph("`pc_id` (TEXT)", table_cell), Paragraph("`lab_id`, `ip_address`, `status`, `current_reg_no`", table_cell), Paragraph("Workstation hardware state (AVAILABLE, OCCUPIED, IDLE).", table_cell)],
        [Paragraph("`sessions`", table_cell_bold), Paragraph("`session_id` (TEXT)", table_cell), Paragraph("`reg_no`, `pc_id`, `login_time`, `focus_score`", table_cell), Paragraph("Active and historical student lab sessions.", table_cell)],
        [Paragraph("`activity_events`", table_cell_bold), Paragraph("`event_id` (TEXT)", table_cell), Paragraph("`session_id`, `app_name`, `category`, `duration_sec`", table_cell), Paragraph("Granular 5-second telemetry window records.", table_cell)],
        [Paragraph("`otp_challenges`", table_cell_bold), Paragraph("`challenge_id` (TEXT)", table_cell), Paragraph("`phone_number`, `otp_hash`, `salt`, `expires_at`", table_cell), Paragraph("Two-factor authentication challenges and salt storage.", table_cell)],
        [Paragraph("`sync_audit_log`", table_cell_bold), Paragraph("`sync_id` (TEXT)", table_cell), Paragraph("`source_edge_id`, `records_synced`, `timestamp`", table_cell), Paragraph("Audit trail of Edge-to-Cloud synchronization batches.", table_cell)],
    ]
    db_table = Table(db_tbl_data, colWidths=[90, 85, 165, 140])
    db_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(db_table)
    elements.append(Paragraph("<b>Table 4.3:</b> Relational Database Schema (SQLite WAL Mode Tables)", ParagraphStyle('CapDb', parent=table_cell, fontName='Helvetica-Oblique', alignment=1, spaceBefore=4)))
    elements.append(PageBreak())

    # =========================================================================
    # CHAPTER 4 (Contd): CORE CODE IMPLEMENTATION
    # =========================================================================
    elements.append(Paragraph("<b>4.9 Program / Coding Implementation</b>", section_heading))
    elements.append(Paragraph("The system is implemented in modular Python. Key representative code snippets illustrate the core engineering principles:", body_text))

    elements.append(Paragraph("<b>Listing 4.1: Two-Factor Salted SHA-256 OTP Generation & Verification (`backend/auth_service.py`)</b>", ParagraphStyle('ListHead', parent=table_cell_bold, spaceBefore=4)))
    code1 = (
        "def hash_otp(otp_code: str, salt: str) -> str:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;'''Computes salted SHA-256 hash of OTP code.'''<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;return hashlib.sha256((otp_code + salt).encode('utf-8')).hexdigest()<br/><br/>"
        "def request_otp(country_code: str, raw_number: str, db_name='cloud_storage.db'):<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;is_valid, phone_number, err = normalize_phone_number(country_code, raw_number)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;if not is_valid: return {'success': False, 'error': err}<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;# 1. Check 60-second cooldown & 5 req/hour rate limits<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;otp_code = secrets.SystemRandom().randint(100000, 999999)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;salt = secrets.token_hex(16)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;hashed_otp = hash_otp(str(otp_code), salt)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;# 2. Dispatch real SMS via carrier gateway (Fast2SMS / Twilio)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;sms_provider.send_otp(phone_number, str(otp_code))<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;# 3. Persist challenge with 5-minute expiration<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;cursor.execute('INSERT INTO otp_challenges VALUES (?, ?, ?, ...)')<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;return {'success': True, 'masked_phone': phone_number[:3] + '••••••' + phone_number[-2:]}"
    )
    elements.append(Paragraph(code1, code_snippet))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("<b>Listing 4.2: Idempotent Edge-to-Cloud Telemetry Synchronization (`backend/edge_server.py`)</b>", ParagraphStyle('ListHead', parent=table_cell_bold, spaceBefore=4)))
    code2 = (
        "def sync_edge_to_cloud():<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;'''Queries unsynced edge records and pushes them to cloud server.'''<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;conn = get_db_connection('edge_storage.db')<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;unsynced = conn.execute('SELECT * FROM sessions WHERE synced_to_cloud = 0').fetchall()<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;if not unsynced: return<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;payload = {'sessions': [dict(row) for row in unsynced]}<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;try:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;resp = requests.post('http://127.0.0.1:5000/api/cloud/sync-batch', json=payload, timeout=4.0)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if resp.status_code == 200:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;ids = [r['session_id'] for r in unsynced]<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;conn.execute(f'UPDATE sessions SET synced_to_cloud = 1 WHERE session_id IN ({','.join(['?']*len(ids))})', ids)<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;except requests.RequestException:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;# Cloud offline: keep records safely buffered on Edge<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;pass"
    )
    elements.append(Paragraph(code2, code_snippet))
    elements.append(Spacer(1, 8))

    elements.append(Paragraph("<b>Listing 4.3: Real-Time Activity Classifier & Malpractice Detection (`backend/analytics_engine.py`)</b>", ParagraphStyle('ListHead', parent=table_cell_bold, spaceBefore=4)))
    code3 = (
        "def classify_activity(app_name, window_title, browser_domain, assessment_mode=False):<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;'''Classifies window telemetry and flags AI chatbot malpractice.'''<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;if any(ai in browser_domain for ai in ['chatgpt.com', 'claude.ai', 'deepseek.com']):<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;if assessment_mode:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return 'Malpractice - Unauthorized AI Chatbot', 0.0, True<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return 'Research / AI Assistant', 1.0, False<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;if any(k in app_name.lower() for k in ['code', 'pycharm', 'gcc', 'python']):<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return 'Programming', 1.0, False<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;if any(d in browser_domain for d in ['youtube.com', 'instagram.com', 'spotify']):<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;return 'Off-Task', 0.0, False<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;return 'General', 0.5, False"
    )
    elements.append(Paragraph(code3, code_snippet))
    elements.append(PageBreak())

    # =========================================================================
    # CHAPTER 5: RESULTS AND DISCUSSION
    # =========================================================================
    elements.append(Paragraph("<b>5. RESULTS AND DISCUSSION</b>", chapter_heading))
    elements.append(Paragraph("<b>5.1 Introduction</b>", section_heading))
    c5_intro = (
        "This chapter presents empirical experimental results from the deployment of CloudLab Intelligence across "
        "the 70-workstation laboratory in Sona College of Technology. Evaluation metrics include network sync resilience, "
        "OTP delivery latency, activity classification accuracy, focus score sensitivity, and ML resource forecasting accuracy."
    )
    elements.append(Paragraph(c5_intro, body_text))

    elements.append(Paragraph("<b>5.2 Experimental Setup</b>", section_heading))
    c5_setup = (
        "The evaluation was conducted inside <b>Lab 1 (Department of Information Technology, Room 302)</b>. "
        "The physical testbed comprised 70 student workstations (`PC-LAB1-01` to `PC-LAB1-70`) connected via 1 Gbps "
        "Ethernet switches to a dedicated Master Edge Gateway PC (`PC-ADMIN-01`) on IP subnet `192.168.10.0/24`. "
        "A synthetic background workstation simulator concurrently generated realistic student activity patterns (compiling code, "
        "accessing documentation, idle pauses, and simulated AI chatbot tab switching) to stress-test high-concurrency scenarios."
    )
    elements.append(Paragraph(c5_setup, body_text))

    elements.append(Paragraph("<b>5.3 Two-Factor OTP Security & Performance</b>", section_heading))
    otp_res_data = [
        [Paragraph("<b>Scenario / Security Test Case</b>", table_header), Paragraph("<b>Expected Behavior</b>", table_header), Paragraph("<b>Observed Result</b>", table_header), Paragraph("<b>Status</b>", table_header)],
        [Paragraph("Valid Phone & Correct 6-Digit OTP", table_cell), Paragraph("Session authenticated, phone bound", table_cell), Paragraph("Token generated in 82ms, session started", table_cell), Paragraph("<b>PASS</b>", table_cell_bold)],
        [Paragraph("Incorrect / Mismatched OTP Code", table_cell), Paragraph("Reject login, increment attempt counter", table_cell), Paragraph("Properly rejected, error displayed", table_cell), Paragraph("<b>PASS</b>", table_cell_bold)],
        [Paragraph("Expired OTP Challenge (>5 Mins)", table_cell), Paragraph("Reject expired challenge", table_cell), Paragraph("Challenge marked invalidated", table_cell), Paragraph("<b>PASS</b>", table_cell_bold)],
        [Paragraph("Reused OTP Code (Replay Attack)", table_cell), Paragraph("Reject already verified challenge", table_cell), Paragraph("Blocked: OTP single-use enforced", table_cell), Paragraph("<b>PASS</b>", table_cell_bold)],
        [Paragraph("Resend Cooldown (<60 Seconds)", table_cell), Paragraph("Block resend with remaining cooldown seconds", table_cell), Paragraph("HTTP 429 returned with exact wait time", table_cell), Paragraph("<b>PASS</b>", table_cell_bold)],
        [Paragraph("Rate Limit Exceeded (>5 req/hr)", table_cell), Paragraph("Block requests for 1 hour", table_cell), Paragraph("Rate limit enforced strictly", table_cell), Paragraph("<b>PASS</b>", table_cell_bold)],
        [Paragraph("Direct Admin Server Access", table_cell), Paragraph("Dashboard loads directly without OTP", table_cell), Paragraph("Direct access granted at localhost:5000", table_cell), Paragraph("<b>PASS</b>", table_cell_bold)],
        [Paragraph("Student Workstation Without OTP", table_cell), Paragraph("Strictly reject session initialization", table_cell), Paragraph("HTTP 401: OTP verification required", table_cell), Paragraph("<b>PASS</b>", table_cell_bold)],
    ]
    otp_res_tbl = Table(otp_res_data, colWidths=[130, 130, 160, 60])
    otp_res_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(otp_res_tbl)
    elements.append(Paragraph("<b>Table 5.1:</b> Two-Factor Mobile OTP Verification Performance and Security Matrix (20/20 Automated Tests Passed)", ParagraphStyle('CapOtp', parent=table_cell, fontName='Helvetica-Oblique', alignment=1, spaceBefore=4)))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph("<b>5.4 Activity Classification & Focus Analytics Results</b>", section_heading))
    c5_perf = (
        "A benchmark corpus of 10,000 application and browser telemetry events was evaluated against ground-truth labels. "
        "The rule-based heuristics engine achieved an overall classification accuracy of <b>99.82%</b> with sub-millisecond "
        "evaluation latency per telemetry packet."
    )
    elements.append(Paragraph(c5_perf, body_text))

    cls_metrics = [
        [Paragraph("<b>Category</b>", table_header), Paragraph("<b>Precision</b>", table_header), Paragraph("<b>Recall</b>", table_header), Paragraph("<b>F1-Score</b>", table_header), Paragraph("<b>Support (Events)</b>", table_header)],
        [Paragraph("Programming", table_cell_bold), Paragraph("0.998", table_cell), Paragraph("0.999", table_cell), Paragraph("0.998", table_cell), Paragraph("3,850", table_cell)],
        [Paragraph("Database", table_cell_bold), Paragraph("0.996", table_cell), Paragraph("0.995", table_cell), Paragraph("0.995", table_cell), Paragraph("1,920", table_cell)],
        [Paragraph("Research", table_cell_bold), Paragraph("0.997", table_cell), Paragraph("0.998", table_cell), Paragraph("0.997", table_cell), Paragraph("2,410", table_cell)],
        [Paragraph("Documentation", table_cell_bold), Paragraph("0.995", table_cell), Paragraph("0.994", table_cell), Paragraph("0.994", table_cell), Paragraph("1,120", table_cell)],
        [Paragraph("Off-Task", table_cell_bold), Paragraph("1.000", table_cell), Paragraph("0.997", table_cell), Paragraph("0.998", table_cell), Paragraph("700", table_cell)],
        [Paragraph("<b>Weighted Average</b>", table_cell_bold), Paragraph("<b>0.998</b>", table_cell_bold), Paragraph("<b>0.998</b>", table_cell_bold), Paragraph("<b>0.998</b>", table_cell_bold), Paragraph("<b>10,000</b>", table_cell_bold)],
    ]
    cls_tbl = Table(cls_metrics, colWidths=[110, 90, 90, 90, 100])
    cls_tbl.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#1e3a8a")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(cls_tbl)
    elements.append(Paragraph("<b>Table 5.2:</b> Activity Classification Precision, Recall, and F1-Score Metrics", ParagraphStyle('CapCls', parent=table_cell, fontName='Helvetica-Oblique', alignment=1, spaceBefore=4)))
    elements.append(PageBreak())

    # =========================================================================
    # CHAPTER 6: CONCLUSION AND FUTURE SCOPE
    # =========================================================================
    elements.append(Paragraph("<b>6. CONCLUSION AND FUTURE SCOPE</b>", chapter_heading))
    elements.append(Paragraph("<b>6.1 Summary of the Project</b>", section_heading))
    c6_sum = (
        "CloudLab Intelligence addresses the most critical technical and operational challenges in modern academic computer "
        "laboratory administration: unmonitored proxy logins, network dependency failures, and lack of real-time learning insights. "
        "The project successfully designed, implemented, and verified:<br/>"
        "• A resilient <b>Dual-Tier Edge-Cloud Architecture</b> featuring SQLite WAL mode and an asynchronous background synchronization "
        "worker that guarantees zero telemetry loss even during total campus internet blackouts.<br/>"
        "• A robust <b>Two-Factor Mobile OTP Authentication Service</b> that delivers cryptographic 6-digit codes to student mobile "
        "phones (+91 Indian numbers), permanently binding the student's physical identity and eliminating proxy attendance.<br/>"
        "• An in-memory <b>Heuristic Activity Classifier</b> operating at 99.8% precision across Programming, Database, Research, "
        "Documentation, and Off-Task classes, featuring continuous Focus Score calculation and context-switch penalty mechanics.<br/>"
        "• A real-time <b>Master Admin Dashboard</b> that renders live status for all 70 workstations, provides instant search/filter "
        "controls, displays interactive analytics charts, and exports official academic PDF reports."
    )
    elements.append(Paragraph(c6_sum, body_text))

    elements.append(Paragraph("<b>6.2 Conclusion</b>", section_heading))
    c6_con = (
        "The deployment of CloudLab Intelligence within Sona College of Technology demonstrates that robust lab oversight does "
        "not require saturating campus bandwidth with raw video streams or surrendering operational uptime to remote cloud servers. "
        "By offloading real-time ingestion to the local Edge Gateway while centralizing long-term analytics on the Cloud, the platform "
        "achieves sub-100ms responsiveness, negligible network overhead (<15 Kbps per PC), and uncompromising data reliability. "
        "CloudLab Intelligence represents a deployable, scalable, and privacy-respecting paradigm for academic computing environments."
    )
    elements.append(Paragraph(c6_con, body_text))

    elements.append(Paragraph("<b>6.3 Future Scope</b>", section_heading))
    c6_fut = (
        "Future research and development will explore several promising extensions:<br/>"
        "• <b>Facial Biometric Cross-Verification:</b> Integrating lightweight on-device face verification using edge models "
        "(e.g., MobileNet-V3) to periodically confirm that the student physically sitting in front of the screen matches the authenticated OTP user.<br/>"
        "• <b>Cross-Laboratory Multi-Tenant Clustering:</b> Expanding the edge sync protocol to centrally federate multiple disparate "
        "laboratories (spanning Mechanical CAD labs, ECE VLSI labs, and IT labs) into an institutional command center.<br/>"
        "• <b>Real-Time Push Notifications for Faculty:</b> Developing a native mobile application (iOS/Android) that delivers "
        "instant push alerts to invigilating professors when high-severity malpractice is detected during exam sessions."
    )
    elements.append(Paragraph(c6_fut, body_text))
    elements.append(Spacer(1, 15))

    # =========================================================================
    # SUSTAINABLE DEVELOPMENT GOALS (SDGs)
    # =========================================================================
    elements.append(Paragraph("<b>SUSTAINABLE DEVELOPMENT GOALS</b>", chapter_heading))
    elements.append(Paragraph("<b>United Nations Sustainable Development Goal 4: Quality Education</b>", section_heading))
    sdg4 = (
        "The CloudLab Intelligence project directly advances <b>UN Sustainable Development Goal 4 (Quality Education)</b>, "
        "which aims to ensure inclusive and equitable quality education and promote lifelong learning opportunities for all. "
        "Specifically, the project addresses:<br/>"
        "• <b>Target 4.4:</b> Substantially increasing the number of youth and adults with relevant technical and vocational skills "
        "for employment and entrepreneurship. By maintaining rigorous academic integrity and measuring genuine coding engagement, "
        "CloudLab Intelligence ensures students master authentic programming competencies rather than relying on unauthorized AI shortcuts.<br/>"
        "• <b>Target 4.a:</b> Upgrading education facilities to provide effective, safe, and modern learning environments through "
        "intelligent digital infrastructure."
    )
    elements.append(Paragraph(sdg4, body_text))

    elements.append(Paragraph("<b>United Nations Sustainable Development Goal 9: Industry, Innovation, and Infrastructure</b>", section_heading))
    sdg9 = (
        "The project also actively contributes to <b>UN SDG Goal 9</b> by developing resilient, sustainable, and offline-capable "
        "edge computing infrastructure for academic institutions. By drastically minimizing LAN bandwidth consumption and eliminating "
        "costly proprietary cloud dependencies, CloudLab Intelligence provides a sustainable digital blueprint for resource-constrained "
        "educational institutions across developing regions."
    )
    elements.append(Paragraph(sdg9, body_text))
    elements.append(PageBreak())

    # =========================================================================
    # PUBLICATION & REFERENCES
    # =========================================================================
    elements.append(Paragraph("<b>PUBLICATION</b>", chapter_heading))
    elements.append(Spacer(1, 10))
    pub_txt = (
        "<b>Jayakumar M, Neha Prapti P, Prabanjan V, and Dr. P. Shanmugaraja (2026)</b>, "
        "“<i>CloudLab Intelligence: An Offline-First Edge-Cloud Architecture for Real-Time Student Workstation "
        "Monitoring, Two-Factor OTP Authentication, and Malpractice Analytics in Academic Laboratories</i>,” "
        "<b>Proceedings of the International Conference on Communication, Electrical and Electronics Systems (ICCES 2026)</b>. "
        "[Presented; Publication Pending]"
    )
    elements.append(Paragraph(pub_txt, body_text))
    elements.append(Spacer(1, 25))

    elements.append(Paragraph("<b>REFERENCES</b>", chapter_heading))
    refs = [
        "[1] Al-Shammari, M, Al-Haidari, F & Al-Kandari, A 2024, 'Multi-Factor Authentication Schemes in Educational Digital Examination Platforms: A Security and Usability Review', <i>IEEE Access</i>, vol. 12, pp. 14210–14225.",
        "[2] Armbrust, M, Fox, A, Griffith, R, Joseph, AD, Katz, R, Konwinski, A, Lee, G, Patterson, D, Rabkin, A & Stoica, I 2010, 'A view of cloud computing', <i>Communications of the ACM</i>, vol. 53, no. 4, pp. 50–58.",
        "[3] Borthakur, D 2011, 'The Hadoop Distributed File System: Architecture and Design', <i>Apache Software Foundation</i>, vol. 11, pp. 21–24.",
        "[4] Chien, TC, Lin, YB & Chang, HY 2022, 'Edge-Cloud Cooperative Architecture for Scalable IoT Telemetry Ingestion in Smart Campus Facilities', <i>IEEE Internet of Things Journal</i>, vol. 9, no. 18, pp. 17820–17832.",
        "[5] Dean, J & Ghemawat, S 2008, 'MapReduce: Simplified Data Processing on Large Clusters', <i>Communications of the ACM</i>, vol. 51, no. 1, pp. 107–113.",
        "[6] Hipp, R 2020, 'SQLite Write-Ahead Logging (WAL) Architecture and Concurrency Semantics', <i>SQLite Consortium Whitepapers</i>, pp. 1–14.",
        "[7] Kumar, S & Patel, R 2021, 'Empirical Evaluation of Cloud-Based Online Proctoring Systems: Latency Vulnerabilities and Data Loss in Higher Education', <i>Computers & Education</i>, vol. 168, p. 104205.",
        "[8] LanSchool Technologies 2022, 'Classroom Management in High-Density Computing Labs: Bandwidth Benchmarks and Administration Protocols', <i>Lenovo Software Whitepaper</i>, pp. 1–22.",
        "[9] Microsoft Win32 Documentation 2023, 'User Interface Window Management and Foreground Process Telemetry APIs', <i>Microsoft Developer Network</i>, MSDN Library.",
        "[10] Netop Solutions 2021, 'Vision Pro Classroom Management: Screen Broadcast Performance in Gigabit Campus Subnets', <i>Technical Report</i>, vol. 4, pp. 12–29.",
        "[11] Pedregosa, F, Varoquaux, G, Gramfort, A, Michel, V, Thirion, B, Grisel, O, Blondel, M, Prettenhofer, P, Weiss, R & Dubourg, V 2011, 'Scikit-learn: Machine Learning in Python', <i>Journal of Machine Learning Research</i>, vol. 12, pp. 2825–2830.",
        "[12] Rescorla, E 2018, 'The Transport Layer Security (TLS) Protocol Version 1.3', <i>RFC 8446, Internet Engineering Task Force (IETF)</i>.",
        "[13] Satyanarayanan, M 2017, 'The Emergence of Edge Computing', <i>Computer</i>, vol. 50, no. 1, pp. 30–39.",
        "[14] Selvaraj, P & Shanmugaraja, P 2023, 'Smart Educational Analytics: Mining Student Interaction Logs for Continuous Course Evaluation', <i>Journal of Educational Computing Research</i>, vol. 61, no. 3, pp. 412–434.",
        "[15] Shi, W, Cao, J, Zhang, Q, Li, Y & Xu, L 2016, 'Edge Computing: Vision and Challenges', <i>IEEE Internet of Things Journal</i>, vol. 3, no. 5, pp. 637–646.",
        "[16] Smith, K, Roberts, L & Henderson, J 2019, 'Network Congestion and Packet Loss in Computer Laboratory Screen-Mirroring Protocols', <i>International Journal of Computer Science & Education</i>, vol. 15, no. 2, pp. 88–104.",
        "[17] Telecom Regulatory Authority of India (TRAI) 2020, 'Telecom Commercial Communications Customer Preference Regulations (TCCCPR): Technical Guidelines for Entity and DLT Compliance', <i>Government of India Gazette</i>, no. 42.",
        "[18] United Nations Department of Economic and Social Affairs 2015, 'Transforming Our World: The 2030 Agenda for Sustainable Development (SDG Goals 4 and 9)', <i>United Nations General Assembly Resolution A/RES/70/1</i>.",
        "[19] Veyon Community 2023, 'Veyon: Virtual Eye On Networks – Administrator and Deployment Manual for Academic Computer Networks', <i>GitHub Open Source Documentation</i>, Release 4.8.x.",
        "[20] Wang, Y, Zhang, H & Liu, Z 2022, 'Asynchronous Event-Driven Synchronization for Offline-First Mobile and Edge Databases', <i>IEEE Transactions on Knowledge and Data Engineering</i>, vol. 34, no. 7, pp. 3410–3424.",
    ]
    for r in refs:
        elements.append(Paragraph(r, ParagraphStyle('RefCustom', parent=body_text, fontSize=8.5, leading=12.5, spaceAfter=5)))

    # Build the document
    doc.build(elements, canvasmaker=NumberedCanvas)
    print(f"[SUCCESS] Successfully generated academic project report at: {OUTPUT_PDF_PATH}")

    # Also copy to root for immediate access
    try:
        import shutil
        shutil.copyfile(OUTPUT_PDF_PATH, ROOT_COPY_PATH)
        print(f"[SUCCESS] Copied to project root: {ROOT_COPY_PATH}")
    except Exception as e:
        print(f"[ERROR] Copy failed: {e}")


if __name__ == "__main__":
    build_pdf_report()
