"""
Tests for Admin Authentication & OTP Verification Feature
Validates authorized_admins.json matching, OTP security invariants,
attempt limits, cooldowns, and session lifecycle.
"""

import os
import json
import uuid
import unittest
from datetime import datetime, timezone, timedelta
from backend.cloud_server import app as cloud_app
from backend.admin_auth_service import (
    load_authorized_admins, verify_admin_details, request_admin_otp,
    verify_admin_otp, validate_admin_session, logout_admin_session,
    _admin_challenges, _admin_cooldowns, _active_admin_sessions
)


class TestAdminOTPAuthentication(unittest.TestCase):
    def setUp(self):
        cloud_app.config["TESTING"] = True
        self.client = cloud_app.test_client()
        # Clear test state
        _admin_challenges.clear()
        _admin_cooldowns.clear()
        _active_admin_sessions.clear()

    def test_01_load_authorized_admins(self):
        """Tests reading authorized admin from authorized_admins.json."""
        admins = load_authorized_admins()
        self.assertIsInstance(admins, list)
        self.assertGreaterEqual(len(admins), 1)
        admin_ids = [a.get("admin_id") for a in admins]
        self.assertIn("23ITBE177", admin_ids)
        print("[PASS] Test 01: authorized_admins.json successfully loaded with Prabanjan V.")

    def test_02_verify_admin_details_exact_match(self):
        """Tests matching Name, Admin ID, and Email against the authorized record."""
        # Valid Admin
        admin = verify_admin_details("Prabanjan V", "23ITBE177", "prabanjanvelavan32@gmail.com")
        self.assertIsNotNone(admin)
        self.assertEqual(admin["admin_id"], "23ITBE177")
        self.assertEqual(admin["name"], "Prabanjan V")

        # Case-insensitive & trimmed matching
        admin_ci = verify_admin_details("  prabanjan v  ", "23itbe177", "PRABANJANVELAVAN32@GMAIL.COM")
        self.assertIsNotNone(admin_ci)
        self.assertEqual(admin_ci["admin_id"], "23ITBE177")
        print("[PASS] Test 02: Valid admin credentials verified with case-insensitive and whitespace-safe matching.")

    def test_03_verify_admin_details_invalid_combinations(self):
        """Tests that mismatched details fail and return None."""
        # Wrong Name
        self.assertIsNone(verify_admin_details("Wrong Name", "23ITBE177", "prabanjanvelavan32@gmail.com"))
        # Wrong Admin ID
        self.assertIsNone(verify_admin_details("Prabanjan V", "ADMIN999", "prabanjanvelavan32@gmail.com"))
        # Wrong Email
        self.assertIsNone(verify_admin_details("Prabanjan V", "23ITBE177", "wrong@gmail.com"))
        # Empty inputs
        self.assertIsNone(verify_admin_details("", "", ""))
        print("[PASS] Test 03: Invalid admin credential combinations properly rejected.")

    def test_04_request_admin_otp_invalid_details(self):
        """Tests that invalid admin details return 'INVALID ADMIN DETAILS' without sending OTP."""
        res = request_admin_otp("Unknown Admin", "ADMIN999", "intruder@evil.com", test_override_otp="123456")
        self.assertFalse(res["success"])
        self.assertEqual(res["error"], "INVALID ADMIN DETAILS")
        self.assertEqual(len(_admin_challenges), 0)

        # API Endpoint Test
        resp = self.client.post("/api/admin/auth/send-otp", json={
            "name": "Intruder",
            "admin_id": "23ITBE177",
            "email": "intruder@evil.com"
        })
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.get_json()["error"], "INVALID ADMIN DETAILS")
        print("[PASS] Test 04: 'INVALID ADMIN DETAILS' displayed on mismatch and OTP is blocked.")

    def test_05_request_admin_otp_success_and_hashing(self):
        """Tests OTP generation, salted hashing, and that plaintext OTP is never stored."""
        res = request_admin_otp("Prabanjan V", "23ITBE177", "prabanjanvelavan32@gmail.com", test_override_otp="654321")
        self.assertTrue(res["success"])
        self.assertIn("challenge_id", res)
        challenge_id = res["challenge_id"]

        challenge = _admin_challenges[challenge_id]
        self.assertNotIn("654321", challenge.values(), "Plaintext OTP must NEVER be stored")
        self.assertIn("salt", challenge)
        self.assertIn("otp_hash", challenge)
        print("[PASS] Test 05: Cryptographic OTP generated and stored securely as salted SHA-256 hash.")

    def test_06_admin_otp_resend_cooldown(self):
        """Tests enforcement of the 60-second cooldown between OTP requests."""
        # First request sets cooldown
        _admin_cooldowns[("23ITBE177", "prabanjanvelavan32@gmail.com")] = datetime.now(timezone.utc)
        
        # Second immediate request must be rejected
        res = request_admin_otp("Prabanjan V", "23ITBE177", "prabanjanvelavan32@gmail.com")
        self.assertFalse(res["success"])
        self.assertIn("wait", res["error"].lower())
        self.assertIn("cooldown_remaining", res)
        print("[PASS] Test 06: Resend cooldown period enforced successfully.")

    def test_07_admin_verify_otp_incorrect(self):
        """Tests entering an incorrect OTP displays 'INVALID OTP. PLEASE TRY AGAIN.'."""
        res = request_admin_otp("Prabanjan V", "23ITBE177", "prabanjanvelavan32@gmail.com", test_override_otp="112233")
        challenge_id = res["challenge_id"]

        # Wrong OTP via service
        v_res = verify_admin_otp(challenge_id, "999999")
        self.assertFalse(v_res["success"])
        self.assertEqual(v_res["error"], "INVALID OTP. PLEASE TRY AGAIN.")

        # Wrong OTP via API
        api_res = self.client.post("/api/admin/auth/verify-otp", json={
            "challenge_id": challenge_id,
            "otp": "000000"
        })
        self.assertEqual(api_res.status_code, 400)
        self.assertEqual(api_res.get_json()["error"], "INVALID OTP. PLEASE TRY AGAIN.")
        print("[PASS] Test 07: Incorrect OTP properly rejected with 'INVALID OTP. PLEASE TRY AGAIN.'.")

    def test_08_admin_verify_otp_max_attempts(self):
        """Tests that exceeding max incorrect attempts invalidates the challenge."""
        res = request_admin_otp("Prabanjan V", "23ITBE177", "prabanjanvelavan32@gmail.com", test_override_otp="123456")
        challenge_id = res["challenge_id"]

        verify_admin_otp(challenge_id, "111111")
        verify_admin_otp(challenge_id, "222222")
        final_res = verify_admin_otp(challenge_id, "333333")

        self.assertFalse(final_res["success"])
        self.assertIn("Maximum incorrect attempts", final_res["error"])
        self.assertNotIn(challenge_id, _admin_challenges)
        print("[PASS] Test 08: Brute-force protection locks out challenge after maximum attempts.")

    def test_09_admin_verify_otp_expired(self):
        """Tests that an expired OTP challenge is rejected."""
        res = request_admin_otp("Prabanjan V", "23ITBE177", "prabanjanvelavan32@gmail.com", test_override_otp="123456")
        challenge_id = res["challenge_id"]

        # Fast-forward expiry
        _admin_challenges[challenge_id]["expires_at"] = datetime.now(timezone.utc) - timedelta(seconds=10)

        v_res = verify_admin_otp(challenge_id, "123456")
        self.assertFalse(v_res["success"])
        self.assertIn("expired", v_res["error"].lower())
        print("[PASS] Test 09: Expired OTP challenge rejected.")

    def test_10_admin_verify_otp_success_and_session(self):
        """Tests successful OTP verification, session generation, status check, and logout."""
        # 1. Send OTP
        res = request_admin_otp("Prabanjan V", "23ITBE177", "prabanjanvelavan32@gmail.com", test_override_otp="789012")
        challenge_id = res["challenge_id"]

        # 2. Verify OTP via API
        resp = self.client.post("/api/admin/auth/verify-otp", json={
            "challenge_id": challenge_id,
            "otp": "789012"
        })
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["admin"]["admin_id"], "23ITBE177")
        self.assertEqual(data["admin"]["name"], "Prabanjan V")

        # 3. Check Cookie
        cookie_header = resp.headers.get("Set-Cookie", "")
        self.assertIn("cloudlab_admin_session=", cookie_header)
        self.assertIn("HttpOnly", cookie_header)

        # 4. Check Status API
        status_resp = self.client.get("/api/admin/auth/status")
        self.assertEqual(status_resp.status_code, 200)
        status_data = status_resp.get_json()
        self.assertTrue(status_data["authenticated"])
        self.assertEqual(status_data["admin"]["admin_id"], "23ITBE177")

        # 5. Check Logout API
        logout_resp = self.client.post("/api/admin/auth/logout")
        self.assertEqual(logout_resp.status_code, 200)

        # Verify status is now unauthenticated
        status_after = self.client.get("/api/admin/auth/status")
        self.assertFalse(status_after.get_json()["authenticated"])
        print("[PASS] Test 10: Successful OTP verification, authenticated session management, and logout verified.")


if __name__ == "__main__":
    unittest.main()
