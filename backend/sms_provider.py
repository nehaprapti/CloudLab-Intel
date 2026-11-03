"""
CloudLab Intelligence - Secure SMS OTP Provider Service
Supports real SMS delivery through:
1. Twilio Verify API (Recommended Global & India OTP Service)
2. Twilio Programmable SMS API
3. Fast2SMS API (Direct Indian SMS Gateway for +91 numbers)

Never exposes secrets or logs OTP values.
"""

import os
import re
import json
import urllib.parse
import requests

# Load environment helper
def load_dotenv():
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_path):
        try:
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    key, val = line.split("=", 1)
                    key = key.strip()
                    val = val.strip().strip("'\"")
                    os.environ[key] = val
        except Exception:
            pass

def get_env_var(key, default=None):
    if key not in os.environ:
        load_dotenv()
    return os.environ.get(key, default)

class SMSProvider:
    """
    Unified SMS delivery provider compatible with Twilio, Fast2SMS, and custom gateways.
    """
    def __init__(self):
        self.provider_type = self._detect_provider()

    def _detect_provider(self):
        explicit = get_env_var("SMS_PROVIDER", "").strip().lower()
        if explicit in ("twilio", "fast2sms", "custom"):
            return explicit
        
        # Auto-detect from credentials
        if get_env_var("TWILIO_ACCOUNT_SID") and get_env_var("TWILIO_AUTH_TOKEN"):
            return "twilio"
        if get_env_var("FAST2SMS_API_KEY"):
            return "fast2sms"
        
        return "none"

    def is_configured(self):
        """
        Returns True only if valid, non-placeholder credentials are provided.
        """
        prov = self._detect_provider()
        if prov == "twilio":
            sid = get_env_var("TWILIO_ACCOUNT_SID", "").strip()
            token = get_env_var("TWILIO_AUTH_TOKEN", "").strip()
            if sid and token and "placeholder" not in sid.lower() and "placeholder" not in token.lower() and not sid.startswith("AC_your_"):
                return True
        elif prov == "fast2sms":
            key = get_env_var("FAST2SMS_API_KEY", "").strip()
            if key and "placeholder" not in key.lower() and not key.startswith("your_") and "*" not in key:
                return True
        return False

    def send_otp(self, phone_number: str, otp_code: str) -> dict:
        """
        Sends the OTP to the specified phone number via the configured provider.
        Does NOT log the OTP value to protect user security.
        """
        if not self.is_configured():
            return {
                "success": False,
                "error": "SMS provider is not configured. Please set SMS provider credentials in the .env file (e.g., Twilio or Fast2SMS)."
            }

        prov = self._detect_provider()

        if prov == "twilio":
            return self._send_twilio(phone_number, otp_code)
        elif prov == "fast2sms":
            return self._send_fast2sms(phone_number, otp_code)
        else:
            return {
                "success": False,
                "error": f"Unsupported or unconfigured SMS provider: '{prov}'."
            }

    def _send_twilio(self, phone_number: str, otp_code: str) -> dict:
        """
        Delivers OTP using Twilio Verify API (if TWILIO_VERIFY_SERVICE_SID is set)
        or Twilio Programmable SMS API.
        """
        account_sid = get_env_var("TWILIO_ACCOUNT_SID", "").strip()
        auth_token = get_env_var("TWILIO_AUTH_TOKEN", "").strip()
        verify_service_sid = get_env_var("TWILIO_VERIFY_SERVICE_SID", "").strip()
        from_number = get_env_var("TWILIO_PHONE_NUMBER", "").strip()

        # 1. Use Twilio Verify API if Service SID is provided
        if verify_service_sid and verify_service_sid.startswith("VA"):
            try:
                url = f"https://verify.twilio.com/v2/Services/{verify_service_sid}/Verifications"
                payload = {
                    "To": phone_number,
                    "Channel": "sms"
                }
                resp = requests.post(url, data=payload, auth=(account_sid, auth_token), timeout=10.0)
                if resp.status_code in (200, 201):
                    return {"success": True, "provider": "twilio_verify"}
                else:
                    err_msg = "Twilio Verify delivery failed"
                    try:
                        err_json = resp.json()
                        err_msg = err_json.get("message", err_msg)
                    except Exception:
                        pass
                    return {"success": False, "error": f"Twilio Verify Error: {err_msg}"}
            except Exception as e:
                return {"success": False, "error": f"Twilio Verify network failure: {str(e)}"}

    def is_twilio_verify(self) -> bool:
        prov = self._detect_provider()
        verify_service_sid = get_env_var("TWILIO_VERIFY_SERVICE_SID", "").strip()
        return prov == "twilio" and verify_service_sid.startswith("VA")

    def verify_otp_provider(self, phone_number: str, submitted_otp: str) -> dict:
        """
        Validates OTP code directly with Twilio Verify API when configured.
        """
        if not self.is_twilio_verify():
            return {"checked": False, "success": False}

        account_sid = get_env_var("TWILIO_ACCOUNT_SID", "").strip()
        auth_token = get_env_var("TWILIO_AUTH_TOKEN", "").strip()
        verify_service_sid = get_env_var("TWILIO_VERIFY_SERVICE_SID", "").strip()

        try:
            url = f"https://verify.twilio.com/v2/Services/{verify_service_sid}/VerificationCheck"
            payload = {
                "To": phone_number,
                "Code": submitted_otp
            }
            resp = requests.post(url, data=payload, auth=(account_sid, auth_token), timeout=10.0)
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "approved" or data.get("valid") is True:
                    return {"checked": True, "success": True}
                else:
                    return {"checked": True, "success": False, "error": "Invalid OTP code entered."}
            else:
                err_msg = "Twilio verification failed"
                try:
                    err_msg = resp.json().get("message", err_msg)
                except Exception:
                    pass
                return {"checked": True, "success": False, "error": err_msg}
        except Exception as e:
            return {"checked": True, "success": False, "error": f"Twilio Verify check failure: {str(e)}"}

        # 2. Use Twilio Programmable SMS API
        if not from_number:
            return {
                "success": False,
                "error": "Twilio configuration incomplete: Please specify TWILIO_PHONE_NUMBER or TWILIO_VERIFY_SERVICE_SID."
            }

        sms_body = f"Your CloudLab Intelligence verification code is: {otp_code}. Valid for 5 minutes. Do not share this OTP."
        try:
            url = f"https://api.twilio.com/2010-04-01/Accounts/{account_sid}/Messages.json"
            payload = {
                "From": from_number,
                "To": phone_number,
                "Body": sms_body
            }
            resp = requests.post(url, data=payload, auth=(account_sid, auth_token), timeout=10.0)
            if resp.status_code in (200, 201):
                return {"success": True, "provider": "twilio_sms"}
            else:
                err_msg = "Twilio SMS delivery failed"
                try:
                    err_json = resp.json()
                    err_msg = err_json.get("message", err_msg)
                except Exception:
                    pass
                return {"success": False, "error": f"Twilio SMS Error: {err_msg}"}
        except Exception as e:
            return {"success": False, "error": f"Twilio SMS network failure: {str(e)}"}

    def _send_fast2sms(self, phone_number: str, otp_code: str) -> dict:
        """
        Delivers OTP via Fast2SMS DLT/OTP gateway for Indian (+91) phone numbers.
        Tries OTP route first, and if restricted, tries Quick SMS (q) route.
        """
        api_key = get_env_var("FAST2SMS_API_KEY", "").strip()
        # Fast2SMS expects 10-digit Indian phone number
        cleaned_phone = phone_number.replace("+91", "").replace("-", "").replace(" ", "").strip()
        if len(cleaned_phone) != 10:
            return {
                "success": False,
                "error": "Fast2SMS requires a valid 10-digit Indian mobile number."
            }

        url = "https://www.fast2sms.com/dev/bulkV2"
        headers = {
            "authorization": api_key,
            "Content-Type": "application/json"
        }

        # 1. Try OTP route first
        try:
            payload_otp = {
                "variables_values": otp_code,
                "route": "otp",
                "numbers": cleaned_phone
            }
            resp = requests.post(url, json=payload_otp, headers=headers, timeout=10.0)
            data = resp.json()
            if data.get("return") is True:
                return {"success": True, "provider": "fast2sms_otp"}
        except Exception:
            pass

        # 2. Try Quick SMS (q) route as secondary attempt
        try:
            payload_quick = {
                "message": f"Your CloudLab Intelligence verification code is: {otp_code}. Valid for 5 mins.",
                "language": "english",
                "route": "q",
                "numbers": cleaned_phone
            }
            resp = requests.post(url, json=payload_quick, headers=headers, timeout=10.0)
            data = resp.json()
            if data.get("return") is True:
                return {"success": True, "provider": "fast2sms_quick"}
            else:
                err_msg = data.get("message", "Fast2SMS delivery rejected")
                status_code = data.get("status_code")
                if status_code in (996, 999) or "100 inr" in str(err_msg).lower() or "website verification" in str(err_msg).lower():
                    return {
                        "success": False,
                        "error": "Fast2SMS requires a 1-time ₹100 wallet recharge or Website Verification on fast2sms.com to deliver real SMS to mobile numbers."
                    }
                return {"success": False, "error": f"Fast2SMS Error: {err_msg}"}
        except Exception as e:
            return {"success": False, "error": f"Fast2SMS network failure: {str(e)}"}


# Global SMS provider singleton
sms_provider = SMSProvider()
