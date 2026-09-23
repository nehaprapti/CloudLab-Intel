"""
CloudLab Intelligence - Clean Lab Initialization & Seed Script
Configured for Sona College IT Computer Lab with 70 Workstations (PC-LAB1-01 to PC-LAB1-70)
and registers the 3 Sona College Project Team Members (Batch 10).
"""

import os
import uuid
from datetime import datetime, timedelta
from backend.models import get_db_connection, init_db

# 3 Project Team Members from Mini Project Proposal
STUDENTS = [
    {"reg_no": "61782323106044", "name": "Jayakumar M", "dept": "Information Technology", "batch": "Batch 10 (2026-27)", "section": "IV Year / IT-A"},
    {"reg_no": "61782323106072", "name": "Neha Prapti P", "dept": "Information Technology", "batch": "Batch 10 (2026-27)", "section": "IV Year / IT-A"},
    {"reg_no": "61782323106077", "name": "Prabanjan V", "dept": "Information Technology", "batch": "Batch 10 (2026-27)", "section": "IV Year / IT-A"},
]

TOTAL_LAB_SYSTEMS = 70


def seed_database(db_name="cloud_storage.db", is_edge=False):
    init_db(db_name, is_edge=is_edge)
    conn = get_db_connection(db_name)
    cursor = conn.cursor()

    # Clear existing data for fresh seed
    cursor.execute("DELETE FROM activity_events")
    cursor.execute("DELETE FROM sessions")
    cursor.execute("DELETE FROM computers")
    cursor.execute("DELETE FROM students")
    cursor.execute("DELETE FROM labs")

    # 1. Lab 1 (Sona College IT Computer Laboratory - Capacity 70 Systems)
    cursor.execute("""
    INSERT INTO labs (lab_id, lab_name, total_systems, location, ip_subnet)
    VALUES ('LAB-01', 'Lab 1 - IT Department Computer Laboratory', 70, 'IT Block - 3rd Floor (Room 302)', '192.168.10.0/24')
    """)

    # 2. Admin Master PC and 70 Student Workstations (All initialized as AVAILABLE)
    cursor.execute("""
    INSERT INTO computers (pc_id, lab_id, ip_address, status)
    VALUES ('PC-ADMIN-01', 'LAB-01', '192.168.10.1', 'AVAILABLE')
    """)

    for i in range(1, TOTAL_LAB_SYSTEMS + 1):
        pc_id = f"PC-LAB1-{i:02d}"
        ip = f"192.168.10.{100 + i}"
        cursor.execute("""
        INSERT INTO computers (pc_id, lab_id, ip_address, status)
        VALUES (?, 'LAB-01', ?, 'AVAILABLE')
        """, (pc_id, ip))

    # 3. Register the 3 Project Team Members
    now = datetime.now()
    for s in STUDENTS:
        cursor.execute("""
        INSERT INTO students (reg_no, name, department, batch, year_section, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (s["reg_no"], s["name"], s["dept"], s["batch"], s["section"], (now - timedelta(days=5)).isoformat()))

    conn.commit()
    conn.close()
    print(f"[{db_name}] Initialized 70 Workstations (PC-LAB1-01 to PC-LAB1-70) in AVAILABLE state for live student logins.")


def seed_all():
    seed_database("cloud_storage.db", is_edge=False)
    seed_database("edge_storage.db", is_edge=True)


if __name__ == "__main__":
    seed_all()
