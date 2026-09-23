import sqlite3
import os
import json
import uuid
from datetime import datetime, timezone

def get_db_path(db_name="cloud_storage.db"):
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
    os.makedirs(data_dir, exist_ok=True)
    return os.path.join(data_dir, db_name)

def get_db_connection(db_name="cloud_storage.db"):
    db_path = get_db_path(db_name)
    conn = sqlite3.connect(db_path, timeout=60.0, check_same_thread=False, isolation_level=None)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA busy_timeout=60000")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn

def init_db(db_name="cloud_storage.db", is_edge=False):
    conn = get_db_connection(db_name)
    cursor = conn.cursor()

    # Common Student Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        reg_no TEXT PRIMARY KEY,
        name TEXT NOT NULL,
        department TEXT DEFAULT 'Information Technology',
        batch TEXT DEFAULT 'Batch 10 (2026-27)',
        year_section TEXT DEFAULT 'IV Year / IT-A',
        created_at TEXT NOT NULL
    )
    """)

    # Labs Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS labs (
        lab_id TEXT PRIMARY KEY,
        lab_name TEXT NOT NULL,
        total_systems INTEGER DEFAULT 30,
        location TEXT DEFAULT 'IT Block - 3rd Floor',
        ip_subnet TEXT DEFAULT '192.168.10.0/24'
    )
    """)

    # Computers Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS computers (
        pc_id TEXT PRIMARY KEY,
        lab_id TEXT NOT NULL,
        ip_address TEXT,
        status TEXT DEFAULT 'AVAILABLE', -- AVAILABLE, OCCUPIED, IDLE, OFFLINE
        current_session_id TEXT,
        current_reg_no TEXT,
        current_app TEXT,
        current_tab TEXT,
        last_heartbeat TEXT,
        FOREIGN KEY (lab_id) REFERENCES labs(lab_id)
    )
    """)

    # Sessions Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sessions (
        session_id TEXT PRIMARY KEY,
        reg_no TEXT NOT NULL,
        student_name TEXT NOT NULL,
        lab_id TEXT NOT NULL,
        pc_id TEXT NOT NULL,
        login_time TEXT NOT NULL,
        logout_time TEXT,
        total_duration_sec INTEGER DEFAULT 0,
        active_duration_sec INTEGER DEFAULT 0,
        idle_duration_sec INTEGER DEFAULT 0,
        focus_score REAL DEFAULT 100.0,
        tab_switches_count INTEGER DEFAULT 0,
        status TEXT DEFAULT 'ACTIVE', -- ACTIVE, COMPLETED
        synced_to_cloud INTEGER DEFAULT 0,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (reg_no) REFERENCES students(reg_no)
    )
    """)

    # Activity Events Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_events (
        event_id TEXT PRIMARY KEY,
        session_id TEXT NOT NULL,
        reg_no TEXT NOT NULL,
        lab_id TEXT NOT NULL,
        pc_id TEXT NOT NULL,
        app_name TEXT NOT NULL,
        window_title TEXT,
        browser_domain TEXT,
        browser_tab_title TEXT,
        category TEXT DEFAULT 'General', -- Programming, Database, Research, Documentation, Off-Task
        duration_seconds INTEGER DEFAULT 5,
        is_idle INTEGER DEFAULT 0,
        is_tab_switch INTEGER DEFAULT 0,
        timestamp TEXT NOT NULL,
        synced_to_cloud INTEGER DEFAULT 0,
        FOREIGN KEY (session_id) REFERENCES sessions(session_id)
    )
    """)

    # Indices for high-speed reporting
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_session ON activity_events(session_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_reg_no ON activity_events(reg_no)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_events_timestamp ON activity_events(timestamp)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_reg_no ON sessions(reg_no)")

    if is_edge:
        # Edge Offline Sync Queue
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS sync_queue (
            queue_id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_id TEXT UNIQUE NOT NULL,
            event_type TEXT NOT NULL, -- 'session_start', 'event', 'session_end'
            payload_json TEXT NOT NULL,
            status TEXT DEFAULT 'PENDING', -- PENDING, SYNCED, FAILED
            attempts INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            synced_at TEXT
        )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_queue_status ON sync_queue(status)")

    # Sync Audit Log (Idempotency and sync history)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sync_log (
        sync_id TEXT PRIMARY KEY,
        source_node TEXT NOT NULL,
        batch_size INTEGER NOT NULL,
        status TEXT NOT NULL,
        idempotency_hash TEXT UNIQUE NOT NULL,
        synced_at TEXT NOT NULL,
        details TEXT
    )
    """)

    # Admin Reports History
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS admin_reports (
        report_id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        generated_at TEXT NOT NULL,
        recipient_email TEXT NOT NULL,
        status TEXT DEFAULT 'SENT', -- SENT, PENDING, FAILED
        summary_json TEXT,
        pdf_filename TEXT
    )
    """)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db("cloud_storage.db", is_edge=False)
    init_db("edge_storage.db", is_edge=True)
    print("Database tables initialized for Cloud and Edge!")
