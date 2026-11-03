"""
CloudLab Intelligence - Cryptographic Admin Vault Service
Provides zero-dependency AES-grade 256-bit encryption (PBKDF2-HMAC-SHA256)
to protect authorized_admins.json with Master Password: Admin@123
"""

import os
import json
import hashlib
import hmac
import secrets

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ADMINS_FILE = os.path.join(BASE_DIR, "authorized_admins.json")
MASTER_ADMIN_PASSWORD = os.environ.get("MASTER_ADMIN_PASSWORD", "Admin@123")


def derive_keys(password: str, salt: bytes):
    """Derives 64 bytes (32 for encryption, 32 for authentication tag) via PBKDF2."""
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations=100000, dklen=64)


def encrypt_vault_payload(data_list: list, password: str = MASTER_ADMIN_PASSWORD) -> dict:
    """Encrypts a list of admin records into a protected vault dictionary."""
    plaintext = json.dumps(data_list, indent=2)
    salt = secrets.token_bytes(16)
    iv = secrets.token_bytes(16)
    keys = derive_keys(password, salt)
    enc_key = keys[:32]
    mac_key = keys[32:]

    data_bytes = plaintext.encode("utf-8")
    keystream = bytearray()
    counter = 0
    while len(keystream) < len(data_bytes):
        h = hmac.new(enc_key, iv + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        keystream.extend(h)
        counter += 1

    ciphertext = bytes([b ^ k for b, k in zip(data_bytes, keystream[:len(data_bytes)])])
    mac = hmac.new(mac_key, salt + iv + ciphertext, hashlib.sha256).hexdigest()

    return {
        "_security_notice": "PROTECTED VAULT: THIS FILE IS ENCRYPTED. USE MANAGE_ADMINS.bat (Password: Admin@123) TO VIEW OR EDIT.",
        "algorithm": "PBKDF2-HMAC-SHA256-CTR",
        "iterations": 100000,
        "salt": salt.hex(),
        "iv": iv.hex(),
        "ciphertext": ciphertext.hex(),
        "mac": mac
    }


def decrypt_vault_payload(vault_dict: dict, password: str = MASTER_ADMIN_PASSWORD) -> list:
    """Decrypts a vault dictionary into a list of admin records. Raises ValueError on wrong password."""
    try:
        salt = bytes.fromhex(vault_dict["salt"])
        iv = bytes.fromhex(vault_dict["iv"])
        ciphertext = bytes.fromhex(vault_dict["ciphertext"])
        expected_mac = vault_dict["mac"]
    except KeyError:
        raise ValueError("Invalid vault format.")

    keys = derive_keys(password, salt)
    enc_key = keys[:32]
    mac_key = keys[32:]

    actual_mac = hmac.new(mac_key, salt + iv + ciphertext, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(actual_mac, expected_mac):
        raise ValueError("ACCESS DENIED: Incorrect Master Password!")

    keystream = bytearray()
    counter = 0
    while len(keystream) < len(ciphertext):
        h = hmac.new(enc_key, iv + counter.to_bytes(4, "big"), hashlib.sha256).digest()
        keystream.extend(h)
        counter += 1

    plaintext = bytes([b ^ k for b, k in zip(ciphertext, keystream[:len(ciphertext)])])
    return json.loads(plaintext.decode("utf-8"))


def load_admins_from_file(password: str = MASTER_ADMIN_PASSWORD) -> list:
    """Reads authorized_admins.json, automatically decrypting if encrypted."""
    if not os.path.exists(ADMINS_FILE):
        return []
    try:
        with open(ADMINS_FILE, "r", encoding="utf-8") as f:
            raw = json.load(f)
            if isinstance(raw, list):
                # Plaintext format fallback
                return raw
            elif isinstance(raw, dict) and "ciphertext" in raw:
                # Encrypted vault format
                return decrypt_vault_payload(raw, password)
    except Exception:
        pass
    return []


def save_admins_to_file(admins_list: list, password: str = MASTER_ADMIN_PASSWORD) -> bool:
    """Encrypts and writes authorized admin records into authorized_admins.json."""
    vault = encrypt_vault_payload(admins_list, password)
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(vault, f, indent=2)
    return True
