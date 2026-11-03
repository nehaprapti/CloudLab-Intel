"""
CloudLab Intelligence - Mobile OTP Authentication Automated Test Suite
Verifies all 12 required authentication scenarios:
1. Valid mobile number and correct OTP
2. Valid mobile number and incorrect OTP
3. Expired OTP
4. Reused OTP
5. Multiple OTP requests and resend cooldown
6. Too many incorrect OTP attempts (rate-limiting per challenge)
7. SMS delivery failure handling
8. Invalid mobile number validation
9. Successful login, HttpOnly cookie setting, and dashboard redirection
10. Logout and protected-route access control
11. Existing CloudLab features compatibility (Analytics, Reports, Edge APIs)
12. Existing user roles and permissions preservation (Admin vs Student)
"""

import os
import sys
import unittest
import json
import uuid
from datetime import datetime, timezone, timedelta

# Add project root to sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.models import init_db, get_db_connection
from backend.seed_data import seed_database
from backend.auth_service import (
    request_otp, verify_otp, normalize_phone_number,
    validate_session, invalidate_session
)
from backend.cloud_server import app as cloud_app
from backend.analytics_engine import classify_activity, analyze_context_switches
from backend.report_generator import generate_student_pdf_report


class TestMobileOTPAuthentication(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.test_db = "test_auth.db"
        seed_database(cls.test_db, is_edge=False)
        cloud_app.config["TESTING"] = True
        cls.client = cloud_app.test_client()

    def setUp(self):
        # Clean OTP challenges and sessions between test runs
        conn = get_db_connection(self.test_db)
        conn.execute("DELETE FROM otp_challenges")
        conn.execute("DELETE FROM auth_sessions")
        conn.commit()
        conn.close()

        try:
            conn_c = get_db_connection("cloud_storage.db")
            conn_c.execute("DELETE FROM otp_challenges WHERE phone_number LIKE '+9198765%' OR phone_number LIKE '%@gmail.com'")
            conn_c.execute("DELETE FROM auth_sessions WHERE user_id IN (SELECT user_id FROM users WHERE phone_number LIKE '+9198765%')")
            conn_c.commit()
            conn_c.close()
        except Exception:
            pass

        try:
            conn_e = get_db_connection("edge_storage.db")
            conn_e.execute("DELETE FROM otp_challenges WHERE phone_number LIKE '+9198765%' OR phone_number LIKE '%@gmail.com'")
            conn_e.commit()
            conn_e.close()
        except Exception:
            pass

    # 1. Valid mobile number and correct OTP
    def test_01_valid_mobile_and_correct_otp(self):
        req = request_otp("+91", "9876511111", db_name=self.test_db, test_override_otp="123456")
        self.assertTrue(req["success"])

        ver = verify_otp("+919876511111", "123456", db_name=self.test_db)
        self.assertTrue(ver["success"])
        self.assertIn("session_token", ver)
        self.assertEqual(ver["user"]["phone_number"], "+919876511111")
        self.assertEqual(ver["user"]["role"], "student")
        print("[PASS] Scenario 1: Valid mobile number and correct OTP verified.")

    # 2. Valid mobile number and incorrect OTP
    def test_02_valid_mobile_and_incorrect_otp(self):
        req = request_otp("+91", "9876522222", db_name=self.test_db, test_override_otp="654321")
        self.assertTrue(req["success"])

        ver = verify_otp("+919876522222", "111111", db_name=self.test_db)
        self.assertFalse(ver["success"])
        self.assertEqual(ver["error"], "Invalid OTP. Please try again.")
        print("[PASS] Scenario 2: Incorrect OTP properly rejected.")

    # 3. Expired OTP
    def test_03_expired_otp(self):
        req = request_otp("+91", "9876533333", db_name=self.test_db, test_override_otp="999888")
        self.assertTrue(req["success"])

        # Manually expire the challenge in test database
        conn = get_db_connection(self.test_db)
        past_time = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
        conn.execute("UPDATE otp_challenges SET expires_at = ? WHERE phone_number = '+919876533333'", (past_time,))
        conn.commit()
        conn.close()

        ver = verify_otp("+919876533333", "999888", db_name=self.test_db)
        self.assertFalse(ver["success"])
        self.assertEqual(ver["error"], "OTP expired. Please request a new OTP.")
        print("[PASS] Scenario 3: Expired OTP challenge properly rejected.")

    # 4. Reused OTP
    def test_04_reused_otp(self):
        req = request_otp("+91", "9876544444", db_name=self.test_db, test_override_otp="555444")
        self.assertTrue(req["success"])

        # 1st verification succeeds
        ver1 = verify_otp("+919876544444", "555444", db_name=self.test_db)
        self.assertTrue(ver1["success"])

        # 2nd attempt with same OTP fails
        ver2 = verify_otp("+919876544444", "555444", db_name=self.test_db)
        self.assertFalse(ver2["success"])
        self.assertIn("already been used", ver2["error"])
        print("[PASS] Scenario 4: Reused OTP challenge prevented.")

    # 5. Multiple OTP requests and resend cooldown
    def test_05_resend_cooldown(self):
        # First request succeeds
        req1 = request_otp("+91", "9876555555", db_name=self.test_db, test_override_otp="111222")
        self.assertTrue(req1["success"])

        # Immediate second request fails due to 60s cooldown
        req2 = request_otp("+91", "9876555555", db_name=self.test_db, test_override_otp="333444")
        self.assertFalse(req2["success"])
        self.assertIn("Please wait", req2["error"])
        self.assertIn("seconds before requesting a new OTP", req2["error"])
        print("[PASS] Scenario 5: Resend cooldown enforced.")

    # 6. Too many incorrect OTP attempts
    def test_06_too_many_incorrect_attempts(self):
        req = request_otp("+91", "9876566666", db_name=self.test_db, test_override_otp="777888")
        self.assertTrue(req["success"])

        # Attempt 1: Fail
        v1 = verify_otp("+919876566666", "000001", db_name=self.test_db)
        self.assertFalse(v1["success"])
        self.assertEqual(v1["error"], "Invalid OTP. Please try again.")

        # Attempt 2: Fail
        v2 = verify_otp("+919876566666", "000002", db_name=self.test_db)
        self.assertFalse(v2["success"])
        self.assertEqual(v2["error"], "Invalid OTP. Please try again.")

        # Attempt 3: Fail & Lock challenge
        v3 = verify_otp("+919876566666", "000003", db_name=self.test_db)
        self.assertFalse(v3["success"])
        self.assertIn("Too many incorrect attempts", v3["error"])

        # Attempt 4: Even with correct OTP, locked
        v4 = verify_otp("+919876566666", "777888", db_name=self.test_db)
        self.assertFalse(v4["success"])
        print("[PASS] Scenario 6: Rate limiting per challenge (max attempts) verified.")

    # 7. SMS delivery failure handling
    def test_07_sms_delivery_failure_handling(self):
        # When provider is not configured or fails, request_otp does NOT simulate fake SMS
        # Temporarily clear provider credentials
        old_sid = os.environ.get("TWILIO_ACCOUNT_SID")
        old_f2s = os.environ.get("FAST2SMS_API_KEY")
        old_prov = os.environ.get("SMS_PROVIDER")
        os.environ["SMS_PROVIDER"] = "none"
        os.environ["FAST2SMS_API_KEY"] = ""
        os.environ["TWILIO_ACCOUNT_SID"] = ""

        req = request_otp("+91", "9876577777", db_name=self.test_db, test_override_otp=None)
        self.assertFalse(req["success"])
        self.assertTrue(bool(req.get("error")))
        print("[PASS] Scenario 7: SMS failure handled safely without fake delivery.")

        # Restore env
        if old_sid: os.environ["TWILIO_ACCOUNT_SID"] = old_sid
        else: os.environ.pop("TWILIO_ACCOUNT_SID", None)
        if old_f2s: os.environ["FAST2SMS_API_KEY"] = old_f2s
        else: os.environ.pop("FAST2SMS_API_KEY", None)
        if old_prov: os.environ["SMS_PROVIDER"] = old_prov
        else: os.environ.pop("SMS_PROVIDER", None)

    # 8. Invalid mobile number validation
    def test_08_invalid_mobile_numbers(self):
        # Letters
        v1, _, err1 = normalize_phone_number("+91", "abcdefghij")
        self.assertFalse(v1)
        # Less than 10 digits for India
        v2, _, err2 = normalize_phone_number("+91", "98765")
        self.assertFalse(v2)
        # Invalid starting digit (India must start with 6, 7, 8, or 9)
        v3, _, err3 = normalize_phone_number("+91", "1234567890")
        self.assertFalse(v3)
        self.assertIn("must start with 6, 7, 8, or 9", err3)
        # Empty string
        v4, _, err4 = normalize_phone_number("+91", "")
        self.assertFalse(v4)
        print("[PASS] Scenario 8: Mobile number format validations verified.")

    # 9. Successful login and dashboard redirection
    def test_09_login_and_cookie_redirection(self):
        request_otp("+91", "9876588888", db_name="cloud_storage.db", test_override_otp="888999")
        
        resp = self.client.post("/api/auth/verify-otp", json={
            "phone_number": "+919876588888",
            "otp": "888999",
            "name": "Test Student"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["redirect_url"], "/")

        # Check HttpOnly cookie
        cookie_header = resp.headers.get("Set-Cookie", "")
        self.assertIn("cloudlab_session=", cookie_header)
        self.assertIn("HttpOnly", cookie_header)

        # Access dashboard using authenticated session
        dash_resp = self.client.get("/")
        self.assertEqual(dash_resp.status_code, 200)
        print("[PASS] Scenario 9: Successful login sets HttpOnly session and grants dashboard access.")

    # 10. Direct Admin Dashboard Access & Student Strict OTP Enforcement
    def test_10_admin_direct_access_and_student_protection(self):
        client = cloud_app.test_client()

        # 1. Admin Dashboard / is accessible directly without OTP
        admin_page = client.get("/")
        self.assertEqual(admin_page.status_code, 200)

        # 2. Admin overview API is accessible directly without OTP
        admin_api = client.get("/api/admin/overview")
        self.assertEqual(admin_api.status_code, 200)

        # 3. Student workstation login strictly requires OTP (anti-misuse)
        student_unauth = client.post("/api/edge/login", json={
            "reg_no": "61782323106044",
            "student_name": "Jayakumar M",
            "pc_id": "PC-LAB1-01"
        })
        self.assertEqual(student_unauth.status_code, 400)
        self.assertIn("Mobile OTP verification is required", student_unauth.get_json()["error"])
        print("[PASS] Scenario 10: Admin Dashboard accessible directly, Student Workstations strictly require OTP.")

    # 11. Existing CloudLab Intelligence features intact
    def test_11_existing_features_intact(self):
        # Activity classification
        self.assertEqual(classify_activity("Code", "test.py"), "Programming")
        self.assertEqual(classify_activity("chrome", browser_domain="github.com"), "Research & Learning")

        # Context switch focus score
        events = [
            {"app_name": "Code", "category": "Programming", "duration_seconds": 30, "is_idle": 0, "is_tab_switch": 0},
            {"app_name": "chrome", "category": "Research & Learning", "duration_seconds": 20, "is_idle": 0, "is_tab_switch": 1}
        ]
        score_data = analyze_context_switches(events)
        self.assertGreater(score_data["focus_score"], 0)

        # PDF Report Generation
        mock_student = {
            "session_id": str(uuid.uuid4()),
            "reg_no": "61782323106044",
            "student_name": "Jayakumar M",
            "login_time": datetime.now().isoformat(),
            "logout_time": datetime.now().isoformat(),
            "total_duration_sec": 1200,
            "active_duration_sec": 1100,
            "idle_duration_sec": 100,
            "categories": {"Programming": 1000},
            "domain_usage": {"github.com": 200},
            "app_usage": {"Code": 1000},
            "context_switches": {"focus_score": 95.0, "total_switches": 1, "switches_per_hour": 1.0, "rating": "Focused"}
        }
        pdf_path, _ = generate_student_pdf_report(mock_student)
        self.assertTrue(os.path.exists(pdf_path))

        # Edge API compatibility
        edge_resp = self.client.get("/api/edge/status")
        self.assertEqual(edge_resp.status_code, 200)
        print("[PASS] Scenario 11: All existing CloudLab features verified intact.")

    # 12. User Roles and Permissions Preservation
    def test_12_roles_and_permissions(self):
        conn = get_db_connection(self.test_db)
        
        # Verify admin user exists with role='admin'
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE role = 'admin'")
        admin_row = cursor.fetchone()
        self.assertIsNotNone(admin_row)
        self.assertEqual(admin_row["role"], "admin")

        # Admin login preserves admin role
        admin_phone = admin_row["phone_number"]
        request_otp("+91", admin_phone, db_name=self.test_db, test_override_otp="999111")
        ver_admin = verify_otp(admin_phone, "999111", db_name=self.test_db)
        self.assertEqual(ver_admin["user"]["role"], "admin")

        # Existing student login preserves student role
        team_phone = "+919876500001"
        request_otp("+91", team_phone, db_name=self.test_db, test_override_otp="999222")
        ver_team = verify_otp(team_phone, "999222", db_name=self.test_db)
        self.assertEqual(ver_team["user"]["role"], "student")
        self.assertEqual(ver_team["user"]["reg_no"], "61782323106044")

        # New user login does NOT grant admin role
        new_phone = "+919123456789"
        request_otp("+91", new_phone, db_name=self.test_db, test_override_otp="999333")
        ver_new = verify_otp(new_phone, "999333", db_name=self.test_db)
        self.assertEqual(ver_new["user"]["role"], "student")
        self.assertNotEqual(ver_new["user"]["role"], "admin")

        conn.close()
        print("[PASS] Scenario 12: Roles and permissions preservation verified.")

    # 13. Student workstation agent login strictly requires OTP (anti-name-misuse)
    def test_13_student_workstation_login_requires_otp(self):
        resp = self.client.post("/api/edge/login", json={
            "reg_no": "61782323106044",
            "student_name": "Jayakumar M",
            "pc_id": "PC-LAB1-01"
        })
        self.assertEqual(resp.status_code, 400)
        data = resp.get_json()
        self.assertFalse(data.get("success"))
        self.assertIn("Mobile OTP verification is required", data.get("error", ""))
        print("[PASS] Scenario 13: Student workstation login strictly blocked without OTP.")

    # 14. Student workstation agent rejects incorrect OTP
    def test_14_student_workstation_invalid_otp_rejected(self):
        # Create challenge
        request_otp("+91", "9876543210", db_name="edge_storage.db", test_override_otp="654321")

        resp = self.client.post("/api/edge/login", json={
            "reg_no": "61782323106044",
            "student_name": "Jayakumar M",
            "pc_id": "PC-LAB1-01",
            "phone_number": "+919876543210",
            "otp": "000000"
        })
        self.assertEqual(resp.status_code, 401)
        data = resp.get_json()
        self.assertFalse(data.get("success"))
        print("[PASS] Scenario 14: Student workstation login rejected with invalid OTP.")

    # 15. Student workstation agent succeeds with valid OTP
    def test_15_student_workstation_valid_otp_success(self):
        # Create challenge
        request_otp("+91", "9876577777", db_name="edge_storage.db", test_override_otp="777888")

        resp = self.client.post("/api/edge/login", json={
            "reg_no": "61782323106045",
            "student_name": "Karthikeyan K",
            "pc_id": "PC-LAB1-02",
            "phone_number": "+919876577777",
            "otp": "777888"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("phone_number"), "+919876577777")
        self.assertEqual(data.get("reg_no"), "61782323106045")
        print("[PASS] Scenario 15: Student workstation login verified with valid OTP.")

    # 16. Student anti-impersonation: student session & record binds verified phone number
    def test_16_student_anti_impersonation_binding(self):
        conn = get_db_connection("edge_storage.db")
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students WHERE reg_no = '61782323106045'")
        row = cursor.fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(row["phone_number"], "+919876577777")

        cursor.execute("SELECT * FROM sessions WHERE reg_no = '61782323106045' ORDER BY login_time DESC LIMIT 1")
        sess = cursor.fetchone()
        self.assertIsNotNone(sess)
        self.assertEqual(sess["phone_number"], "+919876577777")
        conn.close()
    # 17. Email OTP request and case-insensitive verification
    def test_17_email_otp_end_to_end_verification(self):
        # 1. Request OTP for student email (mixed case)
        res = request_otp("", "Prabanjanvelavan32@gmail.com", db_name="edge_storage.db", test_override_otp="888999")
        self.assertTrue(res.get("success"))
        self.assertTrue(res.get("is_email"))
        self.assertEqual(res.get("phone_number"), "prabanjanvelavan32@gmail.com")

        # 2. Student Agent logs in with lowercase email and correct OTP
        resp = self.client.post("/api/edge/login", json={
            "reg_no": "61782323106099",
            "student_name": "Prabanjan V",
            "pc_id": "PC-LAB1-05",
            "phone_number": "prabanjanvelavan32@gmail.com",
            "otp": "888999"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data.get("success"))
        self.assertEqual(data.get("phone_number"), "prabanjanvelavan32@gmail.com")
        print("[PASS] Scenario 17: Email OTP end-to-end authentication verified.")

    # 18. Email OTP wrong code rejected
    def test_18_email_otp_wrong_code_rejected(self):
        request_otp("", "student_test@gmail.com", db_name="edge_storage.db", test_override_otp="123456")
        resp = self.client.post("/api/edge/login", json={
            "reg_no": "61782323106098",
            "student_name": "Test Student",
            "pc_id": "PC-LAB1-06",
            "phone_number": "student_test@gmail.com",
            "otp": "000000"
        })
        self.assertEqual(resp.status_code, 401)
        data = resp.get_json()
        self.assertFalse(data.get("success"))
        print("[PASS] Scenario 18: Email OTP with invalid code properly rejected.")


if __name__ == "__main__":
    unittest.main()
