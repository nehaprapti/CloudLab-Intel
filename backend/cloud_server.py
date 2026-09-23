"""
CloudLab Intelligence - Central Cloud Backend & Analytics API
Runs on Port 5000, serving the Admin Dashboard, Idempotent Data Ingestion,
Deep Analytics Engine, ML Optimization, and Report Generation & Dispatching.
"""

import os
import json
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, send_file, send_from_directory, Response

from backend.models import get_db_connection, init_db
from backend.analytics_engine import classify_activity, analyze_context_switches, compute_student_summary
from backend.report_generator import (
    generate_student_pdf_report, generate_overall_lab_pdf_report,
    export_sessions_to_csv, dispatch_report_to_administrator, REPORT_OUTPUT_DIR
)

# Setup Flask application
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
app = Flask(__name__, static_folder=STATIC_DIR, static_url_path="")

# Central settings
GLOBAL_SETTINGS = {
    "assessment_mode": False, # False: Learning Mode (AI Allowed), True: Assessment Mode (AI Malpractice Detected)
    "assessment_mode_enabled_at": None # Timestamp when assessment mode was toggled ON
}

# Mirror Edge API endpoints on Cloud Server (Port 5000) for dual-port accessibility
from backend.edge_server import edge_student_login, edge_heartbeat, edge_logout, edge_status
app.add_url_rule("/api/edge/login", "cloud_edge_login", edge_student_login, methods=["POST"])
app.add_url_rule("/api/edge/heartbeat", "cloud_edge_heartbeat", edge_heartbeat, methods=["POST"])
app.add_url_rule("/api/edge/logout", "cloud_edge_logout", edge_logout, methods=["POST"])
app.add_url_rule("/api/edge/status", "cloud_edge_status", edge_status, methods=["GET"])


# ------------------- Web UI Routes & Settings ------------------- #

@app.route("/")
def index():
    """Serves the Unified CloudLab Intelligence Admin & Student Dashboard."""
    return send_from_directory(STATIC_DIR, "index.html")

@app.route("/api/admin/settings", methods=["GET"])
def get_admin_settings():
    """Returns central system settings."""
    return jsonify(GLOBAL_SETTINGS)

@app.route("/api/admin/toggle-assessment", methods=["POST", "GET"])
def toggle_assessment_mode():
    """Toggles Assessment Mode on/off."""
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        if "assessment_mode" in data:
            new_mode = bool(data["assessment_mode"])
        else:
            new_mode = not GLOBAL_SETTINGS.get("assessment_mode", False)

        GLOBAL_SETTINGS["assessment_mode"] = new_mode
        if new_mode:
            GLOBAL_SETTINGS["assessment_mode_enabled_at"] = datetime.now().isoformat()
        else:
            GLOBAL_SETTINGS["assessment_mode_enabled_at"] = None

    return jsonify({
        "success": True,
        "assessment_mode": GLOBAL_SETTINGS.get("assessment_mode", False),
        "assessment_mode_enabled_at": GLOBAL_SETTINGS.get("assessment_mode_enabled_at"),
        "message": f"Assessment mode is now {'ACTIVATED' if GLOBAL_SETTINGS.get('assessment_mode', False) else 'DEACTIVATED'}."
    })


# ------------------- Idempotent Cloud Data Ingestion ------------------- #

@app.route("/api/cloud/sync", methods=["POST"])
def cloud_sync_ingest():
    """
    Idempotent Cloud Ingestion Endpoint:
    Receives batch from edge node. Validates idempotency key to prevent duplicate insertion.
    """
    data = request.get_json() or {}
    batch_id = data.get("batch_id") or str(uuid.uuid4())
    edge_node_id = data.get("edge_node_id", "UNKNOWN-EDGE")
    idempotency_key = data.get("idempotency_key", "")
    records = data.get("records", [])
    now_iso = datetime.now().isoformat()

    conn = get_db_connection("cloud_storage.db")
    cursor = conn.cursor()

    # Check if this batch has already been processed (Idempotent Receiver Pattern)
    cursor.execute("SELECT * FROM sync_log WHERE idempotency_hash = ?", (idempotency_key,))
    existing_sync = cursor.fetchone()
    if existing_sync:
        conn.close()
        return jsonify({
            "status": "ALREADY_PROCESSED",
            "message": "Batch already processed by cloud receiver. Idempotency enforced.",
            "batch_id": batch_id,
            "synced_records": len(records)
        }), 200

    inserted_events = 0
    updated_sessions = 0

    for rec in records:
        rec_type = rec.get("type")

        if rec_type == "SESSION_START":
            session_id = rec.get("session_id")
            reg_no = rec.get("reg_no")
            student_name = rec.get("student_name")
            lab_id = rec.get("lab_id", "LAB-01")
            pc_id = rec.get("pc_id")
            login_time = rec.get("login_time")

            cursor.execute("""
            INSERT OR IGNORE INTO students (reg_no, name, department, created_at)
            VALUES (?, ?, 'Information Technology', ?)
            """, (reg_no, student_name, login_time))

            cursor.execute("""
            INSERT INTO sessions (session_id, reg_no, student_name, lab_id, pc_id, login_time, status, synced_to_cloud, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', 1, ?)
            ON CONFLICT(session_id) DO UPDATE SET updated_at = excluded.updated_at
            """, (session_id, reg_no, student_name, lab_id, pc_id, login_time, now_iso))

            cursor.execute("""
            INSERT INTO computers (pc_id, lab_id, status, current_session_id, current_reg_no, last_heartbeat)
            VALUES (?, ?, 'OCCUPIED', ?, ?, ?)
            ON CONFLICT(pc_id) DO UPDATE SET
                status = 'OCCUPIED',
                current_session_id = excluded.current_session_id,
                current_reg_no = excluded.current_reg_no,
                last_heartbeat = excluded.last_heartbeat
            """, (pc_id, lab_id, session_id, reg_no, login_time))

            updated_sessions += 1

        elif rec_type == "ACTIVITY_EVENT":
            event_id = rec.get("event_id") or str(uuid.uuid4())
            session_id = rec.get("session_id")
            reg_no = rec.get("reg_no")
            lab_id = rec.get("lab_id", "LAB-01")
            pc_id = rec.get("pc_id")
            app_name = rec.get("app_name")
            window_title = rec.get("window_title", "")
            browser_domain = rec.get("browser_domain", "")
            browser_tab_title = rec.get("browser_tab_title", "")
            category = rec.get("category") or classify_activity(app_name, window_title, browser_domain)
            duration_sec = int(rec.get("duration_seconds", 5))
            is_idle = int(rec.get("is_idle", 0))
            is_tab_switch = int(rec.get("is_tab_switch", 0))
            timestamp = rec.get("timestamp")

            cursor.execute("""
            INSERT OR IGNORE INTO activity_events
            (event_id, session_id, reg_no, lab_id, pc_id, app_name, window_title, browser_domain, browser_tab_title, category, duration_seconds, is_idle, is_tab_switch, timestamp, synced_to_cloud)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (event_id, session_id, reg_no, lab_id, pc_id, app_name, window_title, browser_domain, browser_tab_title, category, duration_sec, is_idle, is_tab_switch, timestamp))

            cursor.execute("""
            UPDATE sessions SET
                total_duration_sec = total_duration_sec + ?,
                active_duration_sec = active_duration_sec + ?,
                idle_duration_sec = idle_duration_sec + ?,
                tab_switches_count = tab_switches_count + ?,
                updated_at = ?
            WHERE session_id = ?
            """, (
                duration_sec,
                0 if is_idle else duration_sec,
                duration_sec if is_idle else 0,
                is_tab_switch,
                timestamp,
                session_id
            ))

            pc_status = "IDLE" if is_idle else "OCCUPIED"
            cursor.execute("""
            UPDATE computers SET
                status = ?,
                current_app = ?,
                current_tab = ?,
                last_heartbeat = ?
            WHERE pc_id = ?
            """, (pc_status, app_name, browser_domain or window_title, timestamp, pc_id))

            inserted_events += 1

        elif rec_type == "SESSION_END":
            session_id = rec.get("session_id")
            logout_time = rec.get("logout_time")
            focus_score = rec.get("focus_score", 100)

            cursor.execute("""
            UPDATE sessions SET
                status = 'COMPLETED',
                logout_time = ?,
                focus_score = ?,
                updated_at = ?
            WHERE session_id = ?
            """, (logout_time, focus_score, now_iso, session_id))

            # Mark computer as COMPLETED for 60s summary display before reset
            cursor.execute("""
            UPDATE computers SET
                status = 'COMPLETED',
                current_app = 'Session Ended (Report Dispatched)',
                current_tab = '',
                last_heartbeat = ?
            WHERE current_session_id = ?
            """, (logout_time, session_id))

            # Automatically generate academic PDF report and add to dispatch table
            try:
                cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
                sess_row = cursor.fetchone()
                if sess_row:
                    sess_dict = dict(sess_row)
                    cursor.execute("SELECT * FROM activity_events WHERE session_id = ? ORDER BY timestamp ASC", (session_id,))
                    evs = [dict(r) for r in cursor.fetchall()]
                    is_assessment = GLOBAL_SETTINGS.get("assessment_mode", False)
                    summary = compute_student_summary(sess_dict, evs, is_assessment_mode=is_assessment)
                    pdf_path, pdf_filename = generate_student_pdf_report(summary, evs)
                    dispatch_report_to_administrator(
                        recipient_email="admin.it@sonatech.ac.in",
                        report_type="student",
                        student_reg_no=sess_dict.get("reg_no"),
                        student_data=summary,
                        sessions_list=None
                    )
            except Exception as e:
                print(f"[Cloud Sync] Auto-PDF report generation error: {e}")

            updated_sessions += 1

    # Record sync batch in audit log
    cursor.execute("""
    INSERT INTO sync_log (sync_id, source_node, batch_size, status, idempotency_hash, synced_at, details)
    VALUES (?, ?, ?, 'SUCCESS', ?, ?, ?)
    """, (batch_id, edge_node_id, len(records), idempotency_key, now_iso, f"Events: {inserted_events}, Sessions: {updated_sessions}"))

    conn.commit()
    conn.close()

    return jsonify({
        "status": "SUCCESS",
        "batch_id": batch_id,
        "synced_records": len(records),
        "events_inserted": inserted_events,
        "sessions_updated": updated_sessions,
        "timestamp": now_iso
    })


# ------------------- Administrator Analytics & Monitoring APIs ------------------- #

@app.route("/api/admin/overview", methods=["GET"])
def admin_overview():
    """Returns top-level KPIs for the laboratory."""
    conn = get_db_connection("cloud_storage.db")
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total FROM computers")
    total_computers = cursor.fetchone()["total"] or 30

    cursor.execute("SELECT COUNT(*) as occupied FROM computers WHERE status IN ('OCCUPIED', 'IDLE')")
    occupied_computers = cursor.fetchone()["occupied"]

    cursor.execute("SELECT COUNT(*) as active FROM sessions WHERE status = 'ACTIVE'")
    active_sessions = cursor.fetchone()["active"]

    cursor.execute("SELECT COUNT(*) as total_students FROM students")
    total_students = cursor.fetchone()["total_students"]

    cursor.execute("SELECT AVG(focus_score) as avg_focus FROM sessions WHERE total_duration_sec > 0")
    avg_focus_row = cursor.fetchone()
    avg_focus = round(avg_focus_row["avg_focus"] or 92.5, 1)

    cursor.execute("SELECT SUM(total_duration_sec) as total_sec FROM sessions")
    total_sec = cursor.fetchone()["total_sec"] or 0

    cursor.execute("SELECT COUNT(*) as syncs FROM sync_log")
    total_syncs = cursor.fetchone()["syncs"]

    # Category distribution across entire lab
    cursor.execute("""
    SELECT category, SUM(duration_seconds) as cat_duration
    FROM activity_events
    GROUP BY category
    """)
    category_rows = cursor.fetchall()
    cat_distribution = {row["category"]: row["cat_duration"] for row in category_rows}

    conn.close()

    return jsonify({
        "total_computers": total_computers,
        "occupied_computers": occupied_computers,
        "available_computers": max(0, total_computers - occupied_computers),
        "utilization_pct": round((occupied_computers / max(total_computers, 1)) * 100, 1),
        "active_students": active_sessions,
        "total_registered_students": total_students,
        "avg_focus_score": avg_focus,
        "total_monitored_hours": round(total_sec / 3600.0, 2),
        "total_synced_batches": total_syncs,
        "category_distribution": cat_distribution
    })


@app.route("/api/admin/live-lab", methods=["GET"])
def admin_live_lab():
    """Returns real-time state of all lab workstations for the visual grid."""
    db_to_use = "edge_storage.db" if os.path.exists(os.path.join(BASE_DIR, "data", "edge_storage.db")) else "cloud_storage.db"
    conn = get_db_connection(db_to_use)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT c.pc_id, c.lab_id, c.status as pc_status, c.current_app, c.current_tab, c.last_heartbeat,
           s.session_id, s.reg_no, s.student_name, s.login_time, s.logout_time, s.total_duration_sec,
           s.active_duration_sec, s.idle_duration_sec, s.focus_score, s.tab_switches_count
    FROM computers c
    LEFT JOIN sessions s ON c.current_session_id = s.session_id
    ORDER BY c.pc_id ASC
    """)
    
    pcs = []
    now = datetime.now()
    db_changed = False

    for row in cursor.fetchall():
        status = row["pc_status"] or "AVAILABLE"
        reset_in_sec = 0
        pc_id = row["pc_id"]
        session_id = row["session_id"]
        
        # 1. AUTO-LOGOUT DETECTOR: If OCCUPIED/IDLE and no heartbeat for > 20s, student closed app or disconnected
        if status in ("OCCUPIED", "IDLE"):
            hb_ts = row["last_heartbeat"] or row["login_time"]
            if hb_ts:
                try:
                    cleaned_ts = str(hb_ts).replace("Z", "").replace(" ", "T").split(".")[0]
                    ts = datetime.fromisoformat(cleaned_ts)
                    hb_elapsed = (now - ts).total_seconds()
                    if hb_elapsed >= 20: # No heartbeat for 20s -> Consider student logged out / agent closed
                        now_str = now.isoformat()
                        if session_id:
                            cursor.execute("""
                            UPDATE sessions SET status = 'COMPLETED', logout_time = ?, updated_at = ? WHERE session_id = ?
                            """, (now_str, now_str, session_id))
                        cursor.execute("""
                        UPDATE computers SET status = 'COMPLETED', current_app = 'Agent Closed / Disconnected', current_tab = '', last_heartbeat = ? WHERE pc_id = ?
                        """, (now_str, pc_id))
                        status = "COMPLETED"
                        db_changed = True
                except Exception:
                    pass

        # 2. 60-SECOND CLEANUP: If COMPLETED, remove after 60s
        if status == "COMPLETED":
            logout_ts = row["last_heartbeat"] or row["logout_time"]
            if logout_ts:
                try:
                    cleaned_ts = str(logout_ts).replace("Z", "").replace(" ", "T").split(".")[0]
                    ts = datetime.fromisoformat(cleaned_ts)
                    elapsed = (now - ts).total_seconds()
                    if elapsed >= 60 or elapsed < 0:
                        cursor.execute("""
                        UPDATE computers SET
                            status = 'AVAILABLE',
                            current_session_id = NULL,
                            current_reg_no = NULL,
                            current_app = 'Idle / No Active App',
                            current_tab = ''
                        WHERE pc_id = ?
                        """, (pc_id,))
                        status = "AVAILABLE"
                        db_changed = True
                    else:
                        reset_in_sec = max(1, int(60 - elapsed))
                except Exception:
                    cursor.execute("""
                    UPDATE computers SET
                        status = 'AVAILABLE',
                        current_session_id = NULL,
                        current_reg_no = NULL,
                        current_app = 'Idle / No Active App',
                        current_tab = ''
                    WHERE pc_id = ?
                    """, (pc_id,))
                    status = "AVAILABLE"
                    db_changed = True
            else:
                cursor.execute("""
                UPDATE computers SET
                    status = 'AVAILABLE',
                    current_session_id = NULL,
                    current_reg_no = NULL,
                    current_app = 'Idle / No Active App',
                    current_tab = ''
                WHERE pc_id = ?
                """, (pc_id,))
                status = "AVAILABLE"
                db_changed = True

        # Dynamic Workstation Mode: Only include workstations with active session or within 60s completed countdown
        if status in ("OCCUPIED", "IDLE", "COMPLETED"):
            assessment_switches = 0
            is_ai_in_assessment = False

            # Count tab switches and AI usage strictly AFTER Assessment Mode was enabled
            if GLOBAL_SETTINGS.get("assessment_mode") and GLOBAL_SETTINGS.get("assessment_mode_enabled_at") and session_id:
                try:
                    cursor.execute("""
                    SELECT COUNT(*) as cnt FROM activity_events
                    WHERE session_id = ? AND is_tab_switch = 1 AND timestamp >= ?
                    """, (session_id, GLOBAL_SETTINGS["assessment_mode_enabled_at"]))
                    r_sw = cursor.fetchone()
                    assessment_switches = r_sw["cnt"] if r_sw else 0

                    cursor.execute("""
                    SELECT COUNT(*) as cnt FROM activity_events
                    WHERE session_id = ? AND category = 'AI Assistance' AND timestamp >= ?
                    """, (session_id, GLOBAL_SETTINGS["assessment_mode_enabled_at"]))
                    r_ai = cursor.fetchone()
                    if r_ai and r_ai["cnt"] > 0:
                        is_ai_in_assessment = True
                except Exception:
                    pass

            pcs.append({
                "pc_id": row["pc_id"],
                "lab_id": row["lab_id"],
                "status": status,
                "reset_in_sec": reset_in_sec,
                "current_app": row["current_app"] or "Idle / No Active App",
                "current_tab": row["current_tab"] or "",
                "last_heartbeat": row["last_heartbeat"],
                "session_id": row["session_id"],
                "reg_no": row["reg_no"],
                "student_name": row["student_name"],
                "login_time": row["login_time"],
                "total_duration_sec": row["total_duration_sec"] or 0,
                "focus_score": row["focus_score"] or 100.0,
                "tab_switches": row["tab_switches_count"] or 0,
                "assessment_tab_switches": assessment_switches,
                "is_ai_in_assessment": is_ai_in_assessment
            })

    if db_changed:
        conn.commit()
    conn.close()
    return jsonify({
        "lab_id": "LAB-01",
        "computers": pcs,
        "assessment_mode": GLOBAL_SETTINGS["assessment_mode"],
        "assessment_mode_enabled_at": GLOBAL_SETTINGS.get("assessment_mode_enabled_at")
    })


@app.route("/api/admin/students", methods=["GET"])
def admin_students_list():
    """Returns complete list of students and their overall lab sessions."""
    conn = get_db_connection("cloud_storage.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT s.session_id, s.reg_no, s.student_name, s.lab_id, s.pc_id,
           s.login_time, s.logout_time, s.total_duration_sec, s.active_duration_sec,
           s.idle_duration_sec, s.focus_score, s.tab_switches_count, s.status,
           st.department, st.batch, st.year_section
    FROM sessions s
    LEFT JOIN students st ON s.reg_no = st.reg_no
    ORDER BY s.login_time DESC
    """)

    sessions = []
    for row in cursor.fetchall():
        tot = row["total_duration_sec"] or 0
        act = row["active_duration_sec"] or 0
        sessions.append({
            "session_id": row["session_id"],
            "reg_no": row["reg_no"],
            "student_name": row["student_name"],
            "department": row["department"] or "Information Technology",
            "batch": row["batch"] or "Batch 10 (2026-27)",
            "year_section": row["year_section"] or "IV Year / IT-A",
            "lab_id": row["lab_id"],
            "pc_id": row["pc_id"],
            "login_time": row["login_time"],
            "logout_time": row["logout_time"],
            "total_duration_sec": tot,
            "active_duration_sec": act,
            "idle_duration_sec": row["idle_duration_sec"] or 0,
            "active_pct": round((act / max(tot, 1)) * 100, 1),
            "focus_score": row["focus_score"] or 100.0,
            "tab_switches_count": row["tab_switches_count"] or 0,
            "status": row["status"]
        })

    conn.close()
    return jsonify({"sessions": sessions})


@app.route("/api/admin/student/<reg_no>/report", methods=["GET"])
def admin_student_detailed_report(reg_no):
    """
    Returns full granular report for a specific student:
    - Login / Logout timestamps
    - App usage breakdown
    - Browser tabs / domains visited with durations
    - Category distribution
    - Context switches and Focus score
    """
    db_to_use = "edge_storage.db" if os.path.exists(os.path.join(BASE_DIR, "data", "edge_storage.db")) else "cloud_storage.db"
    conn = get_db_connection(db_to_use)
    cursor = conn.cursor()

    cursor.execute("""
    SELECT * FROM sessions
    WHERE reg_no = ?
    ORDER BY login_time DESC
    LIMIT 1
    """, (reg_no,))
    session = cursor.fetchone()

    if not session:
        conn.close()
        # Fallback to cloud_storage.db if not found in edge
        conn = get_db_connection("cloud_storage.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE reg_no = ? ORDER BY login_time DESC LIMIT 1", (reg_no,))
        session = cursor.fetchone()
        if not session:
            conn.close()
            return jsonify({"error": f"No sessions found for student register number {reg_no}"}), 404

    session_dict = dict(session)
    session_id = session_dict["session_id"]

    # Fetch all activity events for this session
    cursor.execute("""
    SELECT * FROM activity_events
    WHERE session_id = ?
    ORDER BY timestamp ASC
    """, (session_id,))
    events = [dict(r) for r in cursor.fetchall()]

    conn.close()

    is_assessment = GLOBAL_SETTINGS.get("assessment_mode", False)
    summary = compute_student_summary(session_dict, events, is_assessment_mode=is_assessment)
    summary["events_count"] = len(events)
    # Reverse events to give newest first for the live timeline
    summary["recent_events"] = list(reversed(events))[:25]

    return jsonify(summary)


# ------------------- Report Export & Email Dispatch APIs ------------------- #

@app.route("/api/admin/export-pdf/<reg_no>", methods=["GET"])
def export_student_pdf(reg_no):
    """Generates and downloads student session PDF report."""
    conn = get_db_connection("cloud_storage.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions WHERE reg_no = ? ORDER BY login_time DESC LIMIT 1", (reg_no,))
    session = cursor.fetchone()
    if not session:
        conn.close()
        return jsonify({"error": "Student session not found"}), 404

    session_dict = dict(session)
    cursor.execute("SELECT * FROM activity_events WHERE session_id = ?", (session_dict["session_id"],))
    events = [dict(r) for r in cursor.fetchall()]
    conn.close()

    summary = compute_student_summary(session_dict, events)
    filepath, filename = generate_student_pdf_report(summary, events)

    return send_file(filepath, as_attachment=True, download_name=filename, mimetype="application/pdf")


@app.route("/api/admin/export-lab-pdf", methods=["GET"])
def export_master_lab_pdf():
    """Generates and downloads master lab PDF report."""
    conn = get_db_connection("cloud_storage.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY login_time DESC")
    sessions = [dict(r) for r in cursor.fetchall()]
    conn.close()

    filepath, filename = generate_overall_lab_pdf_report("Lab 1 - AI & Cloud Computing", sessions)
    return send_file(filepath, as_attachment=True, download_name=filename, mimetype="application/pdf")


@app.route("/api/admin/export-csv", methods=["GET"])
def export_csv():
    """Exports all sessions into CSV format."""
    conn = get_db_connection("cloud_storage.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM sessions ORDER BY login_time DESC")
    sessions = [dict(r) for r in cursor.fetchall()]
    conn.close()

    csv_data = export_sessions_to_csv(sessions)
    return Response(
        csv_data,
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=CloudLab_Sessions_Report.csv"}
    )


@app.route("/api/admin/send-report", methods=["POST"])
def send_admin_report():
    """
    Dispatches report to Administrator email address.
    """
    data = request.get_json() or {}
    recipient_email = data.get("email", "admin.it@sonatech.ac.in").strip()
    report_type = data.get("report_type", "overall") # "overall" or "student"
    reg_no = data.get("reg_no")

    student_data = None
    sessions_list = None

    db_to_use = "edge_storage.db" if os.path.exists(os.path.join(BASE_DIR, "data", "edge_storage.db")) else "cloud_storage.db"
    conn = get_db_connection(db_to_use)
    cursor = conn.cursor()

    if report_type == "student" and reg_no:
        cursor.execute("SELECT * FROM sessions WHERE reg_no = ? ORDER BY login_time DESC LIMIT 1", (reg_no,))
        sess = cursor.fetchone()
        if not sess:
            conn.close()
            conn = get_db_connection("cloud_storage.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions WHERE reg_no = ? ORDER BY login_time DESC LIMIT 1", (reg_no,))
            sess = cursor.fetchone()

        if sess:
            sess_dict = dict(sess)
            cursor.execute("SELECT * FROM activity_events WHERE session_id = ?", (sess_dict["session_id"],))
            events = [dict(r) for r in cursor.fetchall()]
            is_assessment = GLOBAL_SETTINGS.get("assessment_mode", False)
            student_data = compute_student_summary(sess_dict, events, is_assessment_mode=is_assessment)
    else:
        cursor.execute("SELECT * FROM sessions ORDER BY login_time DESC")
        sessions_list = [dict(r) for r in cursor.fetchall()]
        if not sessions_list:
            conn.close()
            conn = get_db_connection("cloud_storage.db")
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM sessions ORDER BY login_time DESC")
            sessions_list = [dict(r) for r in cursor.fetchall()]

    conn.close()

    dispatch_result = dispatch_report_to_administrator(
        recipient_email=recipient_email,
        report_type=report_type,
        student_reg_no=reg_no,
        student_data=student_data,
        sessions_list=sessions_list
    )

    return jsonify(dispatch_result)


@app.route("/api/admin/dispatched-reports", methods=["GET"])
def get_dispatched_reports():
    """Returns history of reports dispatched to the administrator."""
    conn = get_db_connection("cloud_storage.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin_reports ORDER BY generated_at DESC LIMIT 20")
    reports = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return jsonify({"dispatched_reports": reports})


@app.route("/api/admin/download-pdf/<filename>", methods=["GET"])
def download_saved_pdf(filename):
    """Serves a previously generated PDF report."""
    filepath = os.path.join(REPORT_OUTPUT_DIR, filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True, download_name=filename, mimetype="application/pdf")
    return jsonify({"error": "File not found"}), 404


@app.route("/api/admin/delete-report/<report_id>", methods=["DELETE", "POST"])
def delete_dispatched_report(report_id):
    """Deletes a dispatched report record and its associated PDF file."""
    conn = get_db_connection("cloud_storage.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM admin_reports WHERE report_id = ?", (report_id,))
    report = cursor.fetchone()

    if report:
        report_dict = dict(report)
        pdf_path = report_dict.get("pdf_path")
        if pdf_path and os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
            except Exception:
                pass
        
        cursor.execute("DELETE FROM admin_reports WHERE report_id = ?", (report_id,))
        conn.commit()

    conn.close()

    # Also remove from edge storage if exists
    try:
        edge_conn = get_db_connection("edge_storage.db")
        edge_cursor = edge_conn.cursor()
        edge_cursor.execute("DELETE FROM admin_reports WHERE report_id = ?", (report_id,))
        edge_conn.commit()
        edge_conn.close()
    except Exception:
        pass

    return jsonify({"success": True, "message": f"Report {report_id} deleted successfully."})


# ------------------- Direct Agent Ingestion (Port 5000 / 5001 Unified) ------------------- #

@app.route("/api/edge/login", methods=["POST"])
def direct_student_login():
    """Allows student agent to login directly to Cloud or Edge."""
    from backend.edge_server import edge_student_login
    return edge_student_login()


@app.route("/api/edge/heartbeat", methods=["POST"])
def direct_student_heartbeat():
    """Allows student agent to send heartbeats directly to Cloud or Edge."""
    from backend.edge_server import edge_heartbeat
    return edge_heartbeat()


@app.route("/api/edge/logout", methods=["POST"])
def direct_student_logout():
    """Allows student agent to logout directly to Cloud or Edge."""
    from backend.edge_server import edge_student_logout
    return edge_student_logout()


@app.route("/api/edge/status", methods=["GET"])
def direct_edge_status():
    """Returns edge sync status."""
    from backend.edge_server import get_edge_status
    return get_edge_status()


# ------------------- Seed Endpoint ------------------- #

@app.route("/api/admin/seed", methods=["POST"])
def seed_database_endpoint():
    """Seeds initial demonstration data."""
    from backend.seed_data import seed_all
    seed_all()
    return jsonify({"success": True, "message": "Demo lab data populated successfully!"})


if __name__ == "__main__":
    init_db("cloud_storage.db", is_edge=False)
    print("Central Cloud API starting on http://127.0.0.1:5000")
    app.run(host="0.0.0.0", port=5000, debug=False)
