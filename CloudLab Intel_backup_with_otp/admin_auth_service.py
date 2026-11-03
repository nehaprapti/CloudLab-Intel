"""
CloudLab Intelligence - Admin Authentication & OTP Verification Service
Specifically handles authorized administrator identity verification,
cryptographic OTP generation, secure email delivery, rate limiting, and session security.
"""

import os
import json
import uuid
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from backend.email_provider import email_provider, get_env_var
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMINS_FILE = os.path.join(BASE_DIR, "authorized_admins.json")

from backend.admin_vault import load_admins_from_file, save_admins_to_file

# Security Configuration
ADMIN_OTP_EXPIRY_MINUTES = 5
ADMIN_OTP_COOLDOWN_SECONDS = 60
ADMIN_OTP_MAX_ATTEMPTS = 3

# In-memory stores for security state
_admin_challenges = {}   # challenge_id -> challenge record
_admin_cooldowns = {}    # (admin_id, email) -> datetime of last request
_active_admin_sessions = {} # session_token -> admin session info


def load_authorized_admins():
    """
    Reads authorized admin records from authorized_admins.json.
    Automatically decrypts AES-grade vault with Master Admin Password (Admin@123).
    Supports multiple admin entries with name, admin_id, and email.
    """
    return load_admins_from_file()


def verify_admin_details(name: str, admin_id: str, email: str):
    """
    Compares entered Name, Admin ID, and Email Address against authorized_admins.json.
    All three values must match the SAME admin record.
    Returns matched record dict or None.
    """
    name_clean = (name or "").strip().lower()
    admin_id_clean = (admin_id or "").strip().upper()
    email_clean = (email or "").strip().lower()

    if not name_clean or not admin_id_clean or not email_clean:
        return None

    admins = load_authorized_admins()
    for rec in admins:
        rec_name = str(rec.get("name", "")).strip().lower()
        rec_id = str(rec.get("admin_id", "")).strip().upper()
        rec_email = str(rec.get("email", "")).strip().lower()

        if rec_name == name_clean and rec_id == admin_id_clean and rec_email == email_clean:
            return {
                "name": rec.get("name", "").strip(),
                "admin_id": rec.get("admin_id", "").strip(),
                "email": rec.get("email", "").strip()
            }
    return None


def send_admin_otp_email(to_email: str, otp_code: str, admin_name: str, admin_id: str) -> dict:
    """
    Delivers a branded, high-priority verification email with the 6-digit OTP code to the authorized admin email.
    """
    sender_email = get_env_var("SMTP_EMAIL", "").strip()
    sender_password = get_env_var("SMTP_PASSWORD", "").strip().replace(" ", "")

    if not email_provider.is_configured():
        return {
            "success": False,
            "error": "SMTP email service is not configured in .env file. Please check SMTP_EMAIL and SMTP_PASSWORD."
        }

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"CloudLab Intelligence: Admin Login OTP is {otp_code}"
        msg["From"] = f"CloudLab Intelligence Admin Security <{sender_email}>"
        msg["To"] = to_email
        msg["X-Priority"] = "1"

        plain_text = (
            f"Hello {admin_name},\n\n"
            f"Your CloudLab Intelligence Admin Dashboard login verification code is: {otp_code}\n\n"
            f"Admin ID: {admin_id}\n"
            f"Valid for 5 minutes. Do not share this OTP with anyone.\n\n"
            f"Department of Information Technology • Sona College of Technology"
        )

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #0f172a; margin: 0; padding: 24px; }}
            .container {{ max-width: 520px; margin: 0 auto; background: #ffffff; border-radius: 16px; overflow: hidden; box-shadow: 0 10px 25px -5px rgba(0,0,0,0.3); border: 1px solid #e2e8f0; }}
            .header {{ background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 50%, #2563eb 100%); color: white; padding: 28px 24px; text-align: center; }}
            .header h1 {{ margin: 0; font-size: 20px; font-weight: 800; letter-spacing: 0.5px; }}
            .header p {{ margin: 6px 0 0; font-size: 12px; opacity: 0.9; color: #93c5fd; }}
            .badge {{ display: inline-block; margin-top: 10px; background: rgba(16, 185, 129, 0.2); border: 1px solid #10b981; color: #a7f3d0; font-size: 11px; font-weight: 700; padding: 3px 10px; border-radius: 20px; }}
            .content {{ padding: 32px 28px; color: #1e293b; text-align: center; }}
            .greeting {{ font-size: 16px; font-weight: 700; margin-bottom: 8px; color: #0f172a; }}
            .subtitle {{ font-size: 13px; color: #64748b; line-height: 1.5; margin-bottom: 20px; }}
            .info-card {{ background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 10px; padding: 12px 18px; margin: 16px 0; text-align: left; font-size: 12px; color: #334155; }}
            .otp-box {{ background: #eff6ff; border: 2px dashed #2563eb; border-radius: 14px; padding: 20px; margin: 24px 0; display: inline-block; width: 85%; }}
            .otp-label {{ font-size: 11px; text-transform: uppercase; letter-spacing: 1.5px; color: #2563eb; font-weight: 800; margin-bottom: 8px; }}
            .otp-code {{ font-size: 36px; font-weight: 900; letter-spacing: 10px; color: #1e3a8a; font-family: 'Consolas', 'Courier New', monospace; }}
            .expiry {{ font-size: 12px; color: #dc2626; font-weight: 700; margin-top: 10px; }}
            .footer {{ background: #f8fafc; border-top: 1px solid #e2e8f0; padding: 18px; text-align: center; font-size: 11px; color: #64748b; line-height: 1.5; }}
          </style>
        </head>
        <body>
          <div class="container">
            <div class="header">
              <h1>CloudLab Intelligence</h1>
              <p>Sona College of Technology • Department of IT</p>
              <div class="badge">🔐 START_ADMIN_SERVER Secure Login</div>
            </div>
            <div class="content">
              <div class="greeting">Hello, {admin_name}</div>
              <div class="subtitle">A request to access the Master Administration Console has been initiated. Use the 6-digit verification code below to complete your login.</div>
              
              <div class="info-card">
                <div><b>Authorized Admin ID:</b> {admin_id}</div>
                <div><b>Target Service:</b> START_ADMIN_SERVER (Port 5000)</div>
              </div>

              <div class="otp-box">
                <div class="otp-label">One-Time Login Password</div>
                <div class="otp-code">{otp_code}</div>
                <div class="expiry">⏱️ Expires in 5 minutes • Single-use only</div>
              </div>

              <p style="font-size: 12px; color: #94a3b8; margin: 0;">If you did not initiate this login request, please safeguard your credentials.</p>
            </div>
            <div class="footer">
              Department of Information Technology • Batch 10 (2026-27)<br/>
              CloudLab Intelligence Academic Workstation & Governance Platform
            </div>
          </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(plain_text, "plain"))
        msg.attach(MIMEText(html_content, "html"))

        server = smtplib.SMTP(email_provider.smtp_server, email_provider.smtp_port, timeout=15.0)
        server.ehlo()
        server.starttls()
        server.ehlo()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, [to_email], msg.as_string())
        server.quit()

        return {"success": True, "message": f"OTP successfully delivered to {to_email}."}
    except Exception as e:
        return {"success": False, "error": f"Email delivery error: {str(e)}"}


def request_admin_otp(name: str, admin_id: str, email: str, test_override_otp=None) -> dict:
    """
    Verifies admin credentials, enforces cooldown, generates secure 6-digit OTP,
    hashes it with salt, dispatches via email, and returns challenge ID.
    If details do not match, strictly returns 'INVALID ADMIN DETAILS'.
    """
    admin = verify_admin_details(name, admin_id, email)
    if not admin:
        return {
            "success": False,
            "error": "INVALID ADMIN DETAILS"
        }

    cooldown_key = (admin["admin_id"].upper(), admin["email"].lower())
    now = datetime.now(timezone.utc)

    # 1. Enforce Resend Cooldown
    if cooldown_key in _admin_cooldowns and not test_override_otp:
        elapsed = (now - _admin_cooldowns[cooldown_key]).total_seconds()
        if elapsed < ADMIN_OTP_COOLDOWN_SECONDS:
            remaining = int(ADMIN_OTP_COOLDOWN_SECONDS - elapsed)
            return {
                "success": False,
                "error": f"Please wait {remaining} seconds before requesting a new OTP.",
                "cooldown_remaining": remaining
            }

    # 2. Invalidate previous active challenges for this admin
    to_delete = [
        cid for cid, ch in _admin_challenges.items()
        if ch["admin_id"].upper() == admin["admin_id"].upper()
    ]
    for cid in to_delete:
        _admin_challenges.pop(cid, None)

    # 3. Generate Cryptographically Secure 6-digit OTP
    otp_code = test_override_otp if test_override_otp else f"{secrets.randbelow(900000) + 100000}"
    salt = secrets.token_hex(16)
    otp_hash = hashlib.sha256(f"{otp_code}:{salt}".encode()).hexdigest()
    challenge_id = str(uuid.uuid4())
    expires_at = now + timedelta(minutes=ADMIN_OTP_EXPIRY_MINUTES)

    # 4. Dispatch OTP via Email (skipped only in automated tests where test_override_otp is provided)
    if not test_override_otp:
        dispatch_result = send_admin_otp_email(
            to_email=admin["email"],
            otp_code=otp_code,
            admin_name=admin["name"],
            admin_id=admin["admin_id"]
        )
        if not dispatch_result.get("success"):
            return {
                "success": False,
                "error": dispatch_result.get("error", "Failed to deliver OTP to admin email.")
            }

    # Update cooldown & store challenge (Plaintext OTP is NEVER stored)
    _admin_cooldowns[cooldown_key] = now
    _admin_challenges[challenge_id] = {
        "admin_id": admin["admin_id"],
        "name": admin["name"],
        "email": admin["email"],
        "salt": salt,
        "otp_hash": otp_hash,
        "expires_at": expires_at,
        "attempts": 0
    }

    # Mask email for safe UI display (e.g. ka•••••@gmail.com)
    parts = admin["email"].split("@")
    u, d = parts[0], parts[1]
    masked = f"{u[:2]}•••••@{d}" if len(u) > 2 else f"{u}•••••@{d}"

    return {
        "success": True,
        "message": f"Verification OTP sent to {masked}.",
        "challenge_id": challenge_id,
        "masked_email": masked,
        "cooldown_seconds": ADMIN_OTP_COOLDOWN_SECONDS
    }


def verify_admin_otp(challenge_id: str, entered_otp: str) -> dict:
    """
    Verifies entered 6-digit OTP against salted hash.
    Enforces expiry (5 min) and attempt limits (3 attempts).
    If incorrect, strictly returns 'INVALID OTP. PLEASE TRY AGAIN.'
    """
    if not challenge_id or not entered_otp:
        return {
            "success": False,
            "error": "INVALID OTP. PLEASE TRY AGAIN."
        }

    challenge = _admin_challenges.get(challenge_id)
    if not challenge:
        return {
            "success": False,
            "error": "INVALID OTP. PLEASE TRY AGAIN."
        }

    now = datetime.now(timezone.utc)

    # 1. Check expiration
    if now > challenge["expires_at"]:
        _admin_challenges.pop(challenge_id, None)
        return {
            "success": False,
            "error": "OTP has expired. Please request a new OTP."
        }

    # 2. Check maximum attempts
    if challenge["attempts"] >= ADMIN_OTP_MAX_ATTEMPTS:
        _admin_challenges.pop(challenge_id, None)
        return {
            "success": False,
            "error": "Maximum incorrect attempts exceeded. Please request a new OTP."
        }

    entered_cleaned = str(entered_otp).strip()
    calculated_hash = hashlib.sha256(f"{entered_cleaned}:{challenge['salt']}".encode()).hexdigest()

    challenge["attempts"] += 1

    # 3. Check hash match
    if calculated_hash != challenge["otp_hash"]:
        if challenge["attempts"] >= ADMIN_OTP_MAX_ATTEMPTS:
            _admin_challenges.pop(challenge_id, None)
            return {
                "success": False,
                "error": "Maximum incorrect attempts exceeded. Please request a new OTP."
            }
        return {
            "success": False,
            "error": "INVALID OTP. PLEASE TRY AGAIN."
        }

    # Successful verification - remove challenge to prevent replay
    admin_info = {
        "admin_id": challenge["admin_id"],
        "name": challenge["name"],
        "email": challenge["email"],
        "role": "admin"
    }
    _admin_challenges.pop(challenge_id, None)

    # Issue secure session token (valid for 8 hours)
    session_token = secrets.token_urlsafe(32)
    session_expires = now + timedelta(hours=8)
    _active_admin_sessions[session_token] = {
        "admin_id": admin_info["admin_id"],
        "name": admin_info["name"],
        "email": admin_info["email"],
        "role": "admin",
        "created_at": now.isoformat(),
        "expires_at": session_expires
    }

    return {
        "success": True,
        "message": "Admin authenticated successfully.",
        "session_token": session_token,
        "admin": admin_info
    }


def validate_admin_session(session_token: str):
    """
    Validates an active admin session token. Returns admin record if valid, else None.
    """
    if not session_token:
        return None

    sess = _active_admin_sessions.get(session_token)
    if not sess:
        return None

    now = datetime.now(timezone.utc)
    if now > sess["expires_at"]:
        _active_admin_sessions.pop(session_token, None)
        return None

    return {
        "admin_id": sess["admin_id"],
        "name": sess["name"],
        "email": sess["email"],
        "role": sess["role"]
    }


def logout_admin_session(session_token: str):
    """
    Invalidates active admin session on logout.
    """
    if session_token:
        _active_admin_sessions.pop(session_token, None)
    return True
