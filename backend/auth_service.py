"""
CloudLab Intelligence - Secure Authentication & OTP Service
Handles Mobile OTP generation, verification, salted hashing, rate limiting,
cooldown periods, session lifecycle management, and role-based user access.
"""

import os
import re
import uuid
import secrets
import hashlib
from datetime import datetime, timezone, timedelta
from backend.models import get_db_connection
from backend.sms_provider import sms_provider
from backend.email_provider import email_provider

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Load .env file if present without external dependencies
def load_dotenv():
    env_path = os.path.join(BASE_DIR, ".env")
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
                    if key not in os.environ:
                        os.environ[key] = val
        except Exception:
            pass

load_dotenv()

# Security & OTP Configuration
OTP_EXPIRY_MINUTES = int(os.environ.get("OTP_EXPIRY_MINUTES", "5"))
OTP_COOLDOWN_SECONDS = int(os.environ.get("OTP_COOLDOWN_SECONDS", "60"))
OTP_MAX_ATTEMPTS = int(os.environ.get("OTP_MAX_ATTEMPTS", "3"))
OTP_MAX_REQUESTS_PER_HOUR = int(os.environ.get("OTP_MAX_REQUESTS_PER_HOUR", "5"))


def normalize_phone_number(country_code: str, raw_number: str):
    """
    Validates and normalizes phone number to E.164 format.
    Default country is India (+91).
    Returns (is_valid, normalized_phone, error_message).
    """
    if not raw_number:
        return False, "", "Mobile number is required."

    cleaned_cc = re.sub(r"[^\d+]", "", country_code or "+91")
    if not cleaned_cc.startswith("+"):
        cleaned_cc = "+" + cleaned_cc

    # Clean digits only from mobile number
    digits = re.sub(r"\D", "", raw_number)
    # Strip leading zero if present
    if digits.startswith("0"):
        digits = digits[1:]

    # Validation rules for India (+91)
    if cleaned_cc == "+91":
        # If user included 91 prefix in the input box, strip it
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        if len(digits) != 10:
            return False, "", "Indian mobile number must be exactly 10 digits."
        if digits[0] not in "6789":
            return False, "", "Indian mobile number must start with 6, 7, 8, or 9."
        normalized = f"+91{digits}"
        return True, normalized, ""

    # General E.164 validation
    if len(digits) < 7 or len(digits) > 15:
        return False, "", "Mobile number must be between 7 and 15 digits."

    normalized = f"{cleaned_cc}{digits}"
    if not re.match(r"^\+[1-9]\d{7,14}$", normalized):
        return False, "", "Invalid mobile number format."

    return True, normalized, ""


def normalize_identifier(identifier: str, country_code: str = "+91"):
    """
    Validates and normalizes either a student Email ID or Mobile Number.
    Returns (is_valid, normalized_identifier, is_email, error_message).
    """
    cleaned = (identifier or "").strip()
    if not cleaned:
        return False, "", False, "Student Email ID or Mobile Number is required."

    if "@" in cleaned:
        cleaned_email = cleaned.lower()
        if re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$", cleaned_email):
            return True, cleaned_email, True, ""
        return False, "", True, "Invalid email address format (e.g., student@gmail.com)."

    # Otherwise validate as mobile phone number
    is_valid, phone, err = normalize_phone_number(country_code, cleaned)
    return is_valid, phone, False, err


def hash_otp(otp: str, salt: str) -> str:
    """Computes SHA-256 hash of salt + OTP."""
    return hashlib.sha256((salt + otp).encode("utf-8")).hexdigest()


def generate_cryptographic_otp() -> str:
    """Generates a secure 6-digit random OTP."""
    # Using cryptographically secure system random
    return f"{secrets.SystemRandom().randint(100000, 999999)}"


def request_otp(country_code: str, raw_number: str, db_name="cloud_storage.db", test_override_otp=None, student_name="Student", pc_id="Workstation"):
    """
    Handles Step 1 & Step 2 of the authentication flow:
    - Normalizes & validates student Email ID or Mobile Number
    - Enforces resend cooldown & hourly rate limits
    - Invalidates existing unverified challenges
    - Generates secure random 6-digit OTP
    - Dispatches OTP via real Email (free) or SMS provider
    - Stores salted OTP hash with 5-minute expiry
    """
    is_valid, identifier, is_email, err = normalize_identifier(raw_number, country_code)
    if not is_valid:
        return {"success": False, "error": err}

    conn = get_db_connection(db_name)
    cursor = conn.cursor()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # 1. Check Resend Cooldown (e.g. 60 seconds)
    cursor.execute("""
    SELECT created_at FROM otp_challenges
    WHERE phone_number = ? AND is_invalidated = 0
    ORDER BY created_at DESC LIMIT 1
    """, (identifier,))
    last_row = cursor.fetchone()
    if last_row:
        try:
            last_ts = datetime.fromisoformat(last_row["created_at"])
            if last_ts.tzinfo is None:
                last_ts = last_ts.replace(tzinfo=timezone.utc)
            elapsed = (now - last_ts).total_seconds()
            if elapsed < OTP_COOLDOWN_SECONDS:
                remaining = int(OTP_COOLDOWN_SECONDS - elapsed)
                conn.close()
                return {
                    "success": False,
                    "error": f"Please wait {remaining} seconds before requesting a new OTP.",
                    "cooldown_remaining": remaining
                }
        except Exception:
            pass

    # 2. Hourly Rate Limiting (e.g. max 5 OTP requests per hour)
    one_hour_ago = (now - timedelta(hours=1)).isoformat()
    cursor.execute("""
    SELECT COUNT(*) as cnt FROM otp_challenges
    WHERE phone_number = ? AND created_at >= ?
    """, (identifier, one_hour_ago))
    cnt_row = cursor.fetchone()
    if cnt_row and cnt_row["cnt"] >= OTP_MAX_REQUESTS_PER_HOUR:
        conn.close()
        return {
            "success": False,
            "error": "Too many OTP requests. Please try again after 1 hour."
        }

    # 3. Invalidate previous active challenges for this identifier
    cursor.execute("""
    UPDATE otp_challenges
    SET is_invalidated = 1
    WHERE phone_number = ? AND is_verified = 0
    """, (identifier,))

    # 4. Generate secure OTP
    otp_code = test_override_otp if test_override_otp else generate_cryptographic_otp()
    salt = secrets.token_hex(16)
    hashed_otp = hash_otp(otp_code, salt)
    challenge_id = str(uuid.uuid4())
    expires_at = (now + timedelta(minutes=OTP_EXPIRY_MINUTES)).isoformat()
    
    # Print to Admin Terminal for live lab visibility and demo testing
    channel_name = "Email" if is_email else "Mobile"
    print(f"\n[*] [STUDENT OTP DISPATCH] {channel_name}: {identifier} | 6-Digit OTP: {otp_code} (Valid for 5 mins)\n")

    # 5. Dispatch OTP via Email or SMS Provider
    if not test_override_otp:
        if is_email:
            email_res = email_provider.send_otp_email(
                to_email=identifier,
                otp_code=otp_code,
                student_name=student_name or "Student",
                pc_id=pc_id or "Lab Workstation"
            )
            if not email_res.get("success"):
                conn.close()
                return {
                    "success": False,
                    "error": email_res.get("error", "Failed to deliver OTP email. Please verify server email configuration.")
                }
        else:
            sms_result = sms_provider.send_otp(identifier, otp_code)
            if not sms_result.get("success"):
                conn.close()
                return {
                    "success": False,
                    "error": sms_result.get("error", "Failed to deliver SMS. Please try again later.")
                }

    # 6. Save challenge into database
    cursor.execute("""
    INSERT INTO otp_challenges (challenge_id, phone_number, otp_hash, salt, expires_at, created_at, attempts, is_verified, is_invalidated)
    VALUES (?, ?, ?, ?, ?, ?, 0, 0, 0)
    """, (challenge_id, identifier, hashed_otp, salt, expires_at, now_iso))

    conn.commit()
    conn.close()

    # Format identifier for friendly display
    if is_email:
        parts = identifier.split("@")
        u, d = parts[0], parts[1]
        masked = f"{u[:2]}•••••@{d}" if len(u) > 2 else f"{u}•••••@{d}"
        msg = f"OTP sent to {masked}."
    else:
        masked = f"{identifier[:3]} {identifier[3:5]}••••••{identifier[-2:]}" if len(identifier) >= 10 else identifier
        msg = f"OTP sent via SMS to {masked}."

    return {
        "success": True,
        "message": msg,
        "phone_number": identifier,
        "masked_phone": masked,
        "is_email": is_email,
        "cooldown_seconds": OTP_COOLDOWN_SECONDS,
        "expires_in_minutes": OTP_EXPIRY_MINUTES
    }


def verify_otp(phone_number: str, submitted_otp: str, user_name=None, reg_no=None, db_name="cloud_storage.db"):
    """
    Handles Step 3 & Step 4 of the authentication flow:
    - Validates submitted OTP
    - Enforces attempt limits and expiration
    - Prevents replay/reuse
    - Links or registers user in users table
    - Generates secure HttpOnly session token
    """
    phone_number = (phone_number or "").strip()
    submitted_otp = (submitted_otp or "").strip()

    if not phone_number or not submitted_otp:
        return {"success": False, "error": "Email/Phone number and OTP are required."}

    # Normalize identifier (lowercases email, normalizes phone format)
    if "@" in phone_number:
        phone_number = phone_number.lower()
    else:
        is_valid, norm_identifier, _, _ = normalize_identifier(phone_number)
        if is_valid:
            phone_number = norm_identifier

    if not re.match(r"^\d{6}$", submitted_otp):
        return {"success": False, "error": "Invalid OTP. Please enter a 6-digit numeric code."}

    conn = get_db_connection(db_name)
    cursor = conn.cursor()
    now = datetime.now(timezone.utc)
    now_iso = now.isoformat()

    # Find the latest active challenge for this phone number
    cursor.execute("""
    SELECT * FROM otp_challenges
    WHERE phone_number = ? AND is_invalidated = 0 AND is_verified = 0
    ORDER BY created_at DESC LIMIT 1
    """, (phone_number,))
    challenge = cursor.fetchone()

    if not challenge:
        # Check if already verified or expired
        cursor.execute("""
        SELECT * FROM otp_challenges
        WHERE phone_number = ? ORDER BY created_at DESC LIMIT 1
        """, (phone_number,))
        past = cursor.fetchone()
        conn.close()
        if past and past["is_verified"] == 1:
            return {"success": False, "error": "OTP has already been used. Please request a new OTP."}
        return {"success": False, "error": "No active OTP request found. Please request a new OTP."}

    challenge_id = challenge["challenge_id"]
    attempts = challenge["attempts"] or 0
    salt = challenge["salt"]
    expected_hash = challenge["otp_hash"]

    # 1. Check expiration (5 minutes)
    try:
        exp_ts = datetime.fromisoformat(challenge["expires_at"])
        if exp_ts.tzinfo is None:
            exp_ts = exp_ts.replace(tzinfo=timezone.utc)
        if now > exp_ts:
            cursor.execute("UPDATE otp_challenges SET is_invalidated = 1 WHERE challenge_id = ?", (challenge_id,))
            conn.commit()
            conn.close()
            return {"success": False, "error": "OTP expired. Please request a new OTP."}
    except Exception:
        pass

    # 2. Check maximum verification attempts (e.g. 3 attempts)
    if attempts >= OTP_MAX_ATTEMPTS:
        cursor.execute("UPDATE otp_challenges SET is_invalidated = 1 WHERE challenge_id = ?", (challenge_id,))
        conn.commit()
        conn.close()
        return {
            "success": False,
            "error": "Too many incorrect attempts. This OTP has been invalidated. Please request a new OTP."
        }

    # 3. Verify OTP
    otp_is_valid = False

    # Check Twilio Verify API if configured
    if sms_provider.is_twilio_verify():
        twilio_res = sms_provider.verify_otp_provider(phone_number, submitted_otp)
        if twilio_res.get("checked"):
            otp_is_valid = twilio_res.get("success", False)

    # Fallback / standard verification: check salted SHA-256 hash
    if not otp_is_valid:
        computed_hash = hash_otp(submitted_otp, salt)
        if computed_hash == expected_hash:
            otp_is_valid = True

    if not otp_is_valid:
        new_attempts = attempts + 1
        is_now_invalid = 1 if new_attempts >= OTP_MAX_ATTEMPTS else 0
        cursor.execute("""
        UPDATE otp_challenges
        SET attempts = ?, is_invalidated = ?
        WHERE challenge_id = ?
        """, (new_attempts, is_now_invalid, challenge_id))
        conn.commit()
        conn.close()

        if is_now_invalid:
            return {
                "success": False,
                "error": "Too many incorrect attempts. This OTP has been invalidated. Please request a new OTP."
            }
        return {"success": False, "error": "Invalid OTP. Please try again."}

    # 4. OTP is VALID! Mark challenge as verified and invalidated (single-use)
    cursor.execute("""
    UPDATE otp_challenges
    SET is_verified = 1, is_invalidated = 1
    WHERE challenge_id = ?
    """, (challenge_id,))

    # 5. User Registration & Role System Integration
    cursor.execute("SELECT * FROM users WHERE phone_number = ?", (phone_number,))
    existing_user = cursor.fetchone()

    if existing_user:
        user_id = existing_user["user_id"]
        user_role = existing_user["role"] # Preserve admin, faculty, or student role!
        user_display_name = existing_user["name"]
        assigned_reg_no = existing_user["reg_no"]

        # Update last login
        cursor.execute("""
        UPDATE users SET last_login = ? WHERE user_id = ?
        """, (now_iso, user_id))
    else:
        # Check if phone number matches a student record
        matched_student = None
        if reg_no:
            cursor.execute("SELECT * FROM students WHERE reg_no = ?", (reg_no.strip().upper(),))
            matched_student = cursor.fetchone()

        user_id = str(uuid.uuid4())
        # NEVER grant admin privileges to newly authenticated users automatically
        user_role = "student"
        user_display_name = (user_name or "").strip() or (matched_student["name"] if matched_student else f"Student {phone_number[-4:]}")
        assigned_reg_no = (reg_no or "").strip().upper() if reg_no else (matched_student["reg_no"] if matched_student else None)

        cursor.execute("""
        INSERT INTO users (user_id, phone_number, name, role, reg_no, department, created_at, last_login, is_active)
        VALUES (?, ?, ?, ?, ?, 'Information Technology', ?, ?, 1)
        """, (user_id, phone_number, user_display_name, user_role, assigned_reg_no, now_iso, now_iso))

        # If student record exists, update phone_number
        if assigned_reg_no:
            try:
                cursor.execute("UPDATE students SET phone_number = ? WHERE reg_no = ?", (phone_number, assigned_reg_no))
            except Exception:
                pass

    # 6. Establish Secure Authenticated Session
    session_token = secrets.token_urlsafe(32)
    session_expires_at = (now + timedelta(days=1)).isoformat()

    cursor.execute("""
    INSERT INTO auth_sessions (session_token, user_id, phone_number, role, created_at, expires_at, is_active)
    VALUES (?, ?, ?, ?, ?, ?, 1)
    """, (session_token, user_id, phone_number, user_role, now_iso, session_expires_at))

    conn.commit()
    conn.close()

    return {
        "success": True,
        "message": "Authentication successful.",
        "session_token": session_token,
        "user": {
            "user_id": user_id,
            "phone_number": phone_number,
            "name": user_display_name,
            "role": user_role,
            "reg_no": assigned_reg_no
        }
    }


def validate_session(session_token: str, db_name="cloud_storage.db"):
    """
    Validates server session token and returns active user if valid.
    """
    if not session_token:
        return None

    conn = get_db_connection(db_name)
    cursor = conn.cursor()
    now_iso = datetime.now(timezone.utc).isoformat()

    cursor.execute("""
    SELECT s.session_token, s.user_id, s.phone_number, s.role, s.expires_at,
           u.name, u.reg_no, u.department
    FROM auth_sessions s
    JOIN users u ON s.user_id = u.user_id
    WHERE s.session_token = ? AND s.is_active = 1 AND s.expires_at > ? AND u.is_active = 1
    """, (session_token, now_iso))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        "session_token": row["session_token"],
        "user_id": row["user_id"],
        "phone_number": row["phone_number"],
        "role": row["role"],
        "name": row["name"],
        "reg_no": row["reg_no"],
        "department": row["department"]
    }


def invalidate_session(session_token: str, db_name="cloud_storage.db"):
    """
    Invalidates active session token on logout.
    """
    if not session_token:
        return True

    conn = get_db_connection(db_name)
    cursor = conn.cursor()
    cursor.execute("UPDATE auth_sessions SET is_active = 0 WHERE session_token = ?", (session_token,))
    conn.commit()
    conn.close()
    return True
