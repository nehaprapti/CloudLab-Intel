"""
CloudLab Intelligence - Edge Layer Server
Local Lab Edge Server (Port 5001) managing local database, offline queue,
and idempotent synchronization to Central Cloud API.
"""

import os
import json
import time
import uuid
import hashlib
import threading
import requests
from datetime import datetime, timezone
from flask import Flask, request, jsonify
from backend.models import get_db_connection, init_db
from backend.analytics_engine import classify_activity, analyze_context_switches, compute_student_summary
from backend.report_generator import generate_student_pdf_report, dispatch_report_to_administrator
from backend.auth_service import request_otp, verify_otp, normalize_phone_number

app = Flask(__name__)

# Edge state
EDGE_STATE = {
    "node_id": "EDGE-LAB1-NODE-01",
    "lab_id": "LAB-01",
    "is_online": True, # Can be toggled to simulate network outage
    "cloud_api_url": "http://127.0.0.1:5000/api/cloud/sync",
    "last_sync_time": None,
    "last_sync_status": "IDLE",
    "sync_interval_sec": 5
}

def generate_idempotency_key(event_ids):
    """Generates an idempotent hash for a batch of event IDs."""
    raw = ":".join(sorted(event_ids))
    return hashlib.sha256(raw.encode()).hexdigest()


# ------------------- Edge API Endpoints ------------------- #

@app.route("/api/edge/status", methods=["GET"])
def edge_status():
    """Returns local edge server health, offline queue statistics, and network state."""
    conn = get_db_connection("edge_storage.db")
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) as pending_count FROM sync_queue WHERE status = 'PENDING'")
    pending_count = cursor.fetchone()["pending_count"]
    
    cursor.execute("SELECT COUNT(*) as synced_count FROM sync_queue WHERE status = 'SYNCED'")
    synced_count = cursor.fetchone()["synced_count"]

    cursor.execute("SELECT COUNT(*) as active_sessions FROM sessions WHERE status = 'ACTIVE'")
    active_sessions = cursor.fetchone()["active_sessions"]

    cursor.execute("SELECT COUNT(*) as total_events FROM activity_events")
    total_events = cursor.fetchone()["total_events"]
    conn.close()

    return jsonify({
        "status": "ONLINE" if EDGE_STATE["is_online"] else "OFFLINE_MODE",
        "node_id": EDGE_STATE["node_id"],
        "lab_id": EDGE_STATE["lab_id"],
        "is_online": EDGE_STATE["is_online"],
        "pending_queue_count": pending_count,
        "synced_queue_count": synced_count,
        "active_sessions_count": active_sessions,
        "total_events_logged": total_events,
        "last_sync_time": EDGE_STATE["last_sync_time"],
        "last_sync_status": EDGE_STATE["last_sync_status"],
        "cloud_endpoint": EDGE_STATE["cloud_api_url"]
    })


@app.route("/api/edge/toggle-network", methods=["POST"])
def toggle_network():
    """Simulates internet disruption / restoration at the lab edge."""
    data = request.get_json() or {}
    if "is_online" in data:
        EDGE_STATE["is_online"] = bool(data["is_online"])
    else:
        EDGE_STATE["is_online"] = not EDGE_STATE["is_online"]

    status_str = "ONLINE (Connected to Cloud)" if EDGE_STATE["is_online"] else "OFFLINE (Queuing locally)"
    
    if EDGE_STATE["is_online"]:
        # Trigger immediate sync worker
        threading.Thread(target=process_sync_queue, daemon=True).start()

    return jsonify({
        "success": True,
        "is_online": EDGE_STATE["is_online"],
        "message": f"Edge network status switched to {status_str}"
    })


@app.route("/api/edge/send-otp", methods=["POST"])
def edge_send_otp():
    """
    Generates and dispatches Mobile OTP for student workstation authentication.
    Prevents student name and register number misuse.
    """
    data = request.get_json(silent=True) or {}
    country_code = data.get("country_code", "+91")
    raw_number = data.get("phone_number", "") or data.get("email", "")
    student_name = data.get("student_name", "Student")
    pc_id = data.get("pc_id", "Lab Workstation")

    # Request OTP using edge_storage.db
    result = request_otp(country_code, raw_number, db_name="edge_storage.db", student_name=student_name, pc_id=pc_id)
    if result.get("success"):
        # Mirror the exact same challenge into cloud_storage.db (prevents duplicate email & mismatch)
        try:
            e_conn = get_db_connection("edge_storage.db")
            e_cur = e_conn.cursor()
            e_cur.execute("SELECT * FROM otp_challenges WHERE phone_number = ? ORDER BY created_at DESC LIMIT 1", (result["phone_number"],))
            ch_row = e_cur.fetchone()
            e_conn.close()
            if ch_row:
                c_conn = get_db_connection("cloud_storage.db")
                c_cur = c_conn.cursor()
                c_cur.execute("UPDATE otp_challenges SET is_invalidated = 1 WHERE phone_number = ?", (ch_row["phone_number"],))
                c_cur.execute("""
                INSERT OR REPLACE INTO otp_challenges (challenge_id, phone_number, otp_hash, salt, expires_at, created_at, attempts, is_verified, is_invalidated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (ch_row["challenge_id"], ch_row["phone_number"], ch_row["otp_hash"], ch_row["salt"], ch_row["expires_at"], ch_row["created_at"], ch_row["attempts"], ch_row["is_verified"], ch_row["is_invalidated"]))
                c_conn.commit()
                c_conn.close()
        except Exception:
            pass
    status_code = 200 if result.get("success") else 400
    return jsonify(result), status_code


@app.route("/api/edge/login", methods=["POST"])
def edge_student_login():
    """
    Authenticates student at lab computer and creates a secure session locally.
    Enforces Email OTP verification to prevent impersonation or name misuse.
    """
    data = request.get_json() or {}
    reg_no = data.get("reg_no", "").strip().upper()
    student_name = data.get("student_name", "").strip() or f"Student-{reg_no}"
    lab_id = data.get("lab_id", "LAB-01")
    pc_id = data.get("pc_id", "PC-LAB1-01")
    phone_number = (data.get("phone_number", "") or data.get("email", "")).strip()
    otp_code = data.get("otp", "").strip()
    is_simulation = data.get("is_simulation", False)
    login_time = data.get("login_time") or datetime.now().isoformat()
    session_id = data.get("session_id") or str(uuid.uuid4())

    if not reg_no:
        return jsonify({"error": "Register Number is required"}), 400

    # Enforce Email OTP verification for student workstations (preventing name misuse)
    if not is_simulation:
        if not phone_number or not otp_code:
            return jsonify({
                "success": False,
                "error": "Email / Mobile OTP verification is required to start student session and prevent name misuse."
            }), 400

        # Verify submitted OTP
        ver = verify_otp(phone_number, otp_code, user_name=student_name, reg_no=reg_no, db_name="edge_storage.db")
        if not ver.get("success"):
            ver = verify_otp(phone_number, otp_code, user_name=student_name, reg_no=reg_no, db_name="cloud_storage.db")

        if not ver.get("success"):
            return jsonify({
                "success": False,
                "error": ver.get("error", "Invalid OTP. Email verification failed.")
            }), 401

    conn = get_db_connection("edge_storage.db")
    cursor = conn.cursor()

    # Ensure student record exists with verified mobile number
    cursor.execute("""
    INSERT INTO students (reg_no, name, department, created_at, phone_number)
    VALUES (?, ?, 'Information Technology', ?, ?)
    ON CONFLICT(reg_no) DO UPDATE SET
        name = excluded.name,
        phone_number = COALESCE(excluded.phone_number, students.phone_number)
    """, (reg_no, student_name, login_time, phone_number))

    # Close any existing active session on this PC
    cursor.execute("""
    UPDATE sessions SET status = 'COMPLETED', logout_time = ?, updated_at = ?
    WHERE pc_id = ? AND status = 'ACTIVE'
    """, (login_time, login_time, pc_id))

    # Create new session with verified phone number
    cursor.execute("""
    INSERT INTO sessions (session_id, reg_no, student_name, lab_id, pc_id, login_time, status, updated_at, phone_number)
    VALUES (?, ?, ?, ?, ?, ?, 'ACTIVE', ?, ?)
    """, (session_id, reg_no, student_name, lab_id, pc_id, login_time, login_time, phone_number))

    # Update computer status
    cursor.execute("""
    INSERT INTO computers (pc_id, lab_id, status, current_session_id, current_reg_no, last_heartbeat)
    VALUES (?, ?, 'OCCUPIED', ?, ?, ?)
    ON CONFLICT(pc_id) DO UPDATE SET
        status = 'OCCUPIED',
        current_session_id = excluded.current_session_id,
        current_reg_no = excluded.current_reg_no,
        last_heartbeat = excluded.last_heartbeat
    """, (pc_id, lab_id, session_id, reg_no, login_time))

    # Queue event for cloud sync
    queue_payload = {
        "type": "SESSION_START",
        "session_id": session_id,
        "reg_no": reg_no,
        "student_name": student_name,
        "phone_number": phone_number,
        "lab_id": lab_id,
        "pc_id": pc_id,
        "login_time": login_time
    }
    cursor.execute("""
    INSERT INTO sync_queue (event_id, event_type, payload_json, status, created_at)
    VALUES (?, 'SESSION_START', ?, 'PENDING', ?)
    """, (f"sess-start-{session_id}", json.dumps(queue_payload), login_time))

    conn.commit()
    conn.close()

    # If online, try syncing
    if EDGE_STATE["is_online"]:
        threading.Thread(target=process_sync_queue, daemon=True).start()

    return jsonify({
        "success": True,
        "session_id": session_id,
        "reg_no": reg_no,
        "student_name": student_name,
        "phone_number": phone_number,
        "lab_id": lab_id,
        "pc_id": pc_id,
        "login_time": login_time,
        "message": f"Identity verified via OTP for {student_name} ({reg_no}). Session initialized on {pc_id}."
    })


@app.route("/api/edge/heartbeat", methods=["POST"])
def edge_heartbeat():
    """
    Receives monitoring agent heartbeat: active application, browser domain/tab, idle state.
    Classifies activity and records event into local edge DB and sync queue.
    """
    data = request.get_json() or {}
    session_id = data.get("session_id")
    reg_no = data.get("reg_no", "")
    lab_id = data.get("lab_id", "LAB-01")
    pc_id = data.get("pc_id", "PC-LAB1-01")
    app_name = data.get("app_name", "Unknown")
    window_title = data.get("window_title", "")
    browser_domain = data.get("browser_domain", "")
    browser_tab_title = data.get("browser_tab_title", "")
    duration_sec = int(data.get("duration_seconds", 5))
    is_idle = 1 if data.get("is_idle", False) else 0
    is_tab_switch = 1 if data.get("is_tab_switch", False) else 0
    timestamp = data.get("timestamp") or datetime.now().isoformat()
    event_id = data.get("event_id") or str(uuid.uuid4())

    # Automatic Rule-Based Classification
    category = classify_activity(app_name, window_title, browser_domain)

    conn = get_db_connection("edge_storage.db")
    cursor = conn.cursor()

    # 1. Insert activity event locally
    cursor.execute("""
    INSERT OR IGNORE INTO activity_events 
    (event_id, session_id, reg_no, lab_id, pc_id, app_name, window_title, browser_domain, browser_tab_title, category, duration_seconds, is_idle, is_tab_switch, timestamp)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (event_id, session_id, reg_no, lab_id, pc_id, app_name, window_title, browser_domain, browser_tab_title, category, duration_sec, is_idle, is_tab_switch, timestamp))

    # 2. Update session duration and dynamic metrics
    cursor.execute("SELECT total_duration_sec, active_duration_sec, idle_duration_sec, tab_switches_count FROM sessions WHERE session_id = ?", (session_id,))
    cur_sess = cursor.fetchone()
    
    new_tot = (cur_sess["total_duration_sec"] if cur_sess else 0) + duration_sec
    new_act = (cur_sess["active_duration_sec"] if cur_sess else 0) + (0 if is_idle else duration_sec)
    new_idle = (cur_sess["idle_duration_sec"] if cur_sess else 0) + (duration_sec if is_idle else 0)
    new_switches = (cur_sess["tab_switches_count"] if cur_sess else 0) + (1 if is_tab_switch else 0)

    # Dynamic Focus Score Calculation:
    # 1. Idle Penalty: deduct points based on idle percentage (60s+ of inactivity)
    idle_pct = (new_idle / max(1, new_tot)) * 100.0
    idle_penalty = idle_pct * 0.8
    # 2. Tab Switch Penalty: if student switches tabs frequently, deduct points
    switch_penalty = max(0, new_switches - 2) * 2.0
    
    live_focus_score = max(10.0, min(100.0, round(100.0 - idle_penalty - switch_penalty, 1)))

    cursor.execute("""
    UPDATE sessions SET
        total_duration_sec = ?,
        active_duration_sec = ?,
        idle_duration_sec = ?,
        tab_switches_count = ?,
        focus_score = ?,
        updated_at = ?
    WHERE session_id = ?
    """, (new_tot, new_act, new_idle, new_switches, live_focus_score, timestamp, session_id))

    # 3. Update computer status
    pc_status = "IDLE" if is_idle else "OCCUPIED"
    cursor.execute("""
    UPDATE computers SET
        status = ?,
        current_app = ?,
        current_tab = ?,
        last_heartbeat = ?
    WHERE pc_id = ?
    """, (pc_status, app_name, browser_domain or window_title, timestamp, pc_id))

    # 4. Add to sync queue
    event_payload = {
        "type": "ACTIVITY_EVENT",
        "event_id": event_id,
        "session_id": session_id,
        "reg_no": reg_no,
        "lab_id": lab_id,
        "pc_id": pc_id,
        "app_name": app_name,
        "window_title": window_title,
        "browser_domain": browser_domain,
        "browser_tab_title": browser_tab_title,
        "category": category,
        "duration_seconds": duration_sec,
        "is_idle": is_idle,
        "is_tab_switch": is_tab_switch,
        "timestamp": timestamp
    }
    cursor.execute("""
    INSERT OR IGNORE INTO sync_queue (event_id, event_type, payload_json, status, created_at)
    VALUES (?, 'ACTIVITY_EVENT', ?, 'PENDING', ?)
    """, (event_id, json.dumps(event_payload), timestamp))

    conn.commit()
    conn.close()

    if EDGE_STATE["is_online"]:
        threading.Thread(target=process_sync_queue, daemon=True).start()

    return jsonify({
        "success": True,
        "event_id": event_id,
        "category": category,
        "recorded_at_edge": True,
        "offline_queued": not EDGE_STATE["is_online"]
    })


@app.route("/api/edge/logout", methods=["POST"])
def edge_logout():
    """Ends student session, calculates final metrics, and queues logout sync payload."""
    data = request.get_json() or {}
    session_id = data.get("session_id")
    logout_time = data.get("logout_time") or datetime.now().isoformat()

    conn = get_db_connection("edge_storage.db")
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,))
    session = cursor.fetchone()
    if not session:
        conn.close()
        return jsonify({"error": "Session not found"}), 404

    # Fetch all events for session to compute focus score
    cursor.execute("SELECT * FROM activity_events WHERE session_id = ?", (session_id,))
    events = [dict(row) for row in cursor.fetchall()]
    switch_stats = analyze_context_switches(events)

    cursor.execute("""
    UPDATE sessions SET
        status = 'COMPLETED',
        logout_time = ?,
        focus_score = ?,
        updated_at = ?
    WHERE session_id = ?
    """, (logout_time, switch_stats["focus_score"], logout_time, session_id))

    # Mark computer as COMPLETED for 60-second summary display before reset
    cursor.execute("""
    UPDATE computers SET
        status = 'COMPLETED',
        current_app = 'Session Ended (Report Dispatched)',
        current_tab = '',
        last_heartbeat = ?
    WHERE pc_id = ?
    """, (logout_time, session["pc_id"]))

    # Queue session completion event
    logout_payload = {
        "type": "SESSION_END",
        "session_id": session_id,
        "logout_time": logout_time,
        "focus_score": switch_stats["focus_score"],
        "total_duration_sec": session["total_duration_sec"],
        "active_duration_sec": session["active_duration_sec"],
        "idle_duration_sec": session["idle_duration_sec"]
    }
    cursor.execute("""
    INSERT INTO sync_queue (event_id, event_type, payload_json, status, created_at)
    VALUES (?, 'SESSION_END', ?, 'PENDING', ?)
    """, (f"sess-end-{session_id}", json.dumps(logout_payload), logout_time))

    conn.commit()
    conn.close()

    # Automatically generate academic PDF report and store in admin_reports
    try:
        sess_dict = dict(session)
        sess_dict["logout_time"] = logout_time
        sess_dict["focus_score"] = switch_stats["focus_score"]
        summary = compute_student_summary(sess_dict, events)
        dispatch_report_to_administrator(
            recipient_email="admin.it@sonatech.ac.in",
            report_type="student",
            student_reg_no=session["reg_no"],
            student_data=summary,
            sessions_list=None
        )
    except Exception as e:
        print(f"[Edge Logout] Auto PDF generation error: {e}")

    if EDGE_STATE["is_online"]:
        threading.Thread(target=process_sync_queue, daemon=True).start()

    return jsonify({
        "success": True,
        "session_id": session_id,
        "logout_time": logout_time,
        "focus_score": switch_stats["focus_score"],
        "message": f"Session completed successfully for {session['reg_no']}."
    })


@app.route("/api/edge/sync-now", methods=["POST"])
def manual_sync():
    """Triggers immediate synchronization attempt to Cloud API."""
    result = process_sync_queue()
    return jsonify(result)


# ------------------- Idempotent Synchronization Worker ------------------- #

def process_sync_queue(batch_size=50):
    """
    Offline-First Idempotent Synchronization Engine:
    Pulls pending events from local queue, bundles them with an idempotency hash,
    and sends to Cloud API. Prevents duplicates upon re-connection.
    """
    if not EDGE_STATE["is_online"]:
        EDGE_STATE["last_sync_status"] = "OFFLINE (Queuing)"
        return {"success": False, "message": "Edge is currently offline. Events remain safely buffered in local queue."}

    conn = get_db_connection("edge_storage.db")
    cursor = conn.cursor()

    cursor.execute("""
    SELECT queue_id, event_id, event_type, payload_json
    FROM sync_queue
    WHERE status = 'PENDING'
    ORDER BY queue_id ASC
    LIMIT ?
    """, (batch_size,))
    
    pending_items = cursor.fetchall()
    if not pending_items:
        EDGE_STATE["last_sync_status"] = "IDLE (All synchronized)"
        conn.close()
        return {"success": True, "synced_count": 0, "message": "No pending events to sync."}

    event_ids = [item["event_id"] for item in pending_items]
    idempotency_key = generate_idempotency_key(event_ids)
    batch_records = [json.loads(item["payload_json"]) for item in pending_items]

    payload = {
        "edge_node_id": EDGE_STATE["node_id"],
        "lab_id": EDGE_STATE["lab_id"],
        "batch_id": str(uuid.uuid4()),
        "idempotency_key": idempotency_key,
        "timestamp": datetime.now().isoformat(),
        "records": batch_records
    }

    try:
        EDGE_STATE["last_sync_status"] = f"SYNCING ({len(pending_items)} items)..."
        response = requests.post(EDGE_STATE["cloud_api_url"], json=payload, timeout=8.0)
        
        if response.status_code == 200:
            resp_data = response.json()
            queue_ids = [item["queue_id"] for item in pending_items]
            now_iso = datetime.now().isoformat()
            
            cursor.execute(f"""
            UPDATE sync_queue
            SET status = 'SYNCED', synced_at = ?
            WHERE queue_id IN ({','.join(['?']*len(queue_ids))})
            """, [now_iso] + queue_ids)

            conn.commit()
            EDGE_STATE["last_sync_time"] = now_iso
            EDGE_STATE["last_sync_status"] = f"SYNCED ({len(pending_items)} records)"
            conn.close()
            return {
                "success": True,
                "synced_count": len(pending_items),
                "idempotency_key": idempotency_key,
                "cloud_response": resp_data
            }
        else:
            EDGE_STATE["last_sync_status"] = f"CLOUD_ERROR ({response.status_code})"
            conn.close()
            return {"success": False, "message": f"Cloud returned status {response.status_code}"}

    except Exception as ex:
        EDGE_STATE["last_sync_status"] = f"DISCONNECTED: {str(ex)[:40]}"
        conn.close()
        return {"success": False, "message": f"Could not reach cloud API: {str(ex)}"}


def start_edge_background_sync():
    """Periodic daemon thread to sync edge queue whenever online."""
    def run_sync_loop():
        while True:
            time.sleep(EDGE_STATE["sync_interval_sec"])
            if EDGE_STATE["is_online"]:
                try:
                    process_sync_queue()
                except Exception:
                    pass
    
    t = threading.Thread(target=run_sync_loop, daemon=True)
    t.start()


if __name__ == "__main__":
    init_db("edge_storage.db", is_edge=True)
    start_edge_background_sync()
    print("Edge server starting on http://127.0.0.1:5001")
    app.run(host="0.0.0.0", port=5001, debug=False)
