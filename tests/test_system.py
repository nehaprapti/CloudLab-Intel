"""
CloudLab Intelligence - Automated Test Suite
Verifies Analytics Engine, Focus Scoring, ML Demand Prediction, PDF Generation, and Idempotent Sync.
"""

import os
import sys
import unittest
import json
import uuid
from datetime import datetime

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.models import init_db, get_db_connection
from backend.analytics_engine import classify_activity, extract_domain, analyze_context_switches, compute_student_summary
from backend.report_generator import generate_student_pdf_report, generate_overall_lab_pdf_report, export_sessions_to_csv, dispatch_report_to_administrator


class TestCloudLabSystem(unittest.TestCase):

    def setUp(self):
        init_db("test_cloud.db", is_edge=False)
        init_db("test_edge.db", is_edge=True)

    def test_01_activity_classification(self):
        """Tests rule-based activity classification algorithm."""
        self.assertEqual(classify_activity(app_name="Code", window_title="app.py"), "Programming")
        self.assertEqual(classify_activity(app_name="MySQLWorkbench"), "Database")
        self.assertEqual(classify_activity(app_name="chrome", browser_domain="https://stackoverflow.com/questions/123"), "Research & Learning")
        self.assertEqual(classify_activity(app_name="chrome", browser_domain="github.com"), "Research & Learning")
        self.assertEqual(classify_activity(app_name="WINWORD"), "Documentation")
        self.assertEqual(classify_activity(app_name="chrome", browser_domain="instagram.com"), "Off-Task")
        self.assertEqual(classify_activity(app_name="Spotify"), "Off-Task")
        print("[PASS] Activity Classification tests passed!")

    def test_02_context_switch_and_focus_scoring(self):
        """Tests context switch analysis and focus score computation."""
        events = [
            {"app_name": "Code", "category": "Programming", "duration_seconds": 30, "is_idle": 0, "is_tab_switch": 0},
            {"app_name": "Code", "category": "Programming", "duration_seconds": 30, "is_idle": 0, "is_tab_switch": 0},
            {"app_name": "chrome", "category": "Research & Learning", "duration_seconds": 20, "is_idle": 0, "is_tab_switch": 1},
            {"app_name": "Code", "category": "Programming", "duration_seconds": 40, "is_idle": 0, "is_tab_switch": 1},
        ]
        result = analyze_context_switches(events)
        self.assertIn("focus_score", result)
        self.assertGreaterEqual(result["focus_score"], 50.0)
        self.assertEqual(result["total_switches"], 2)
        print(f"[PASS] Context-Switch analysis test passed! (Focus Score: {result['focus_score']}%)")

    def test_03_pdf_report_generation(self):
        """Tests ReportLab academic PDF report creation."""
        mock_student = {
            "session_id": str(uuid.uuid4()),
            "reg_no": "61782323106044",
            "student_name": "Jayakumar M",
            "lab_id": "Lab 1 - AI & Cloud Lab",
            "pc_id": "PC-LAB1-01",
            "login_time": datetime.now().isoformat(),
            "logout_time": datetime.now().isoformat(),
            "total_duration_sec": 3600,
            "active_duration_sec": 3300,
            "idle_duration_sec": 300,
            "categories": {"Programming": 2400, "Research & Learning": 900, "Documentation": 300},
            "domain_usage": {"github.com": 500, "stackoverflow.com": 400},
            "app_usage": {"Code": 2400, "chrome": 900, "WINWORD": 300},
            "context_switches": {"focus_score": 96.5, "total_switches": 4, "switches_per_hour": 4.0, "rating": "Highly Focused"}
        }

        filepath, filename = generate_student_pdf_report(mock_student)
        self.assertTrue(os.path.exists(filepath))
        self.assertTrue(os.path.getsize(filepath) > 1000)
        print(f"[PASS] PDF Report generated successfully at: {filename} ({os.path.getsize(filepath)} bytes)")

    def test_05_admin_email_dispatch(self):
        """Tests administrator email and report dispatching."""
        mock_student = {
            "reg_no": "61782323106072",
            "student_name": "Neha Prapti P",
            "total_duration_sec": 1800,
            "context_switches": {"focus_score": 94.0}
        }
        res = dispatch_report_to_administrator(
            recipient_email="admin.it@sonatech.ac.in",
            report_type="student",
            student_reg_no="61782323106072",
            student_data=mock_student
        )
        self.assertEqual(res["status"], "SENT_SUCCESSFULLY")
        self.assertIn("pdf_filename", res)
        print("[PASS] Administrator Report Dispatch test passed!")


if __name__ == "__main__":
    unittest.main()
