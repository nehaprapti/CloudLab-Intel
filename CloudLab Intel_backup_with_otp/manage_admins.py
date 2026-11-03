"""
CloudLab Intelligence - Authorized Admin Security Vault Manager
Interactive CLI tool protected by Master Password: Admin@123
Allows viewing, adding, and managing authorized administrators in encrypted authorized_admins.json.
"""

import os
import sys
import getpass
import re

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.admin_vault import (
    load_admins_from_file, save_admins_to_file, decrypt_vault_payload,
    ADMINS_FILE, MASTER_ADMIN_PASSWORD
)


def get_password(prompt="Enter Master Admin Password: "):
    """
    Prompts for password displaying asterisks (*) in real time on Windows console.
    Handles backspace properly.
    """
    if not sys.stdin.isatty():
        return sys.stdin.readline().strip()

    print(prompt, end="", flush=True)
    password = []

    try:
        import msvcrt
        while True:
            ch = msvcrt.getwch()
            if ch in ('\r', '\n'):
                print()
                break
            elif ch == '\x08':  # Backspace
                if password:
                    password.pop()
                    sys.stdout.write('\b \b')
                    sys.stdout.flush()
            elif ch == '\x03':  # Ctrl+C
                print()
                sys.exit(0)
            elif ch in ('\x00', '\xe0'):  # Extended keys (Arrows, Home, etc.)
                msvcrt.getwch()  # Skip second byte
            else:
                password.append(ch)
                sys.stdout.write('*')
                sys.stdout.flush()
        return "".join(password)
    except Exception:
        try:
            return getpass.getpass("")
        except Exception:
            return input("").strip()


def clear_console():
    if sys.stdin.isatty():
        os.system("cls" if os.name == "nt" else "clear")


def pause(msg="\nPress Enter to continue..."):
    if sys.stdin.isatty():
        try:
            input(msg)
        except (EOFError, KeyboardInterrupt):
            pass


def print_banner():
    print("=" * 70)
    print("   CLOUDLAB INTELLIGENCE: MASTER ADMIN SECURITY VAULT")
    print("   SONA COLLEGE OF TECHNOLOGY - DEPARTMENT OF IT (BATCH 10)")
    print("   ENCRYPTION: PBKDF2-HMAC-SHA256 (256-BIT SECURE VAULT)")
    print("=" * 70)
    print()


def view_admins(admins):
    print("\n" + "-" * 70)
    print("   CURRENT AUTHORIZED ADMINISTRATORS (DECRYPTED VIEW)")
    print("-" * 70)
    if not admins:
        print("   [!] No authorized administrators registered in vault.")
    else:
        for idx, adm in enumerate(admins, 1):
            print(f"   [{idx}] Name:     {adm.get('name', 'N/A')}")
            print(f"       Admin ID: {adm.get('admin_id', 'N/A')}")
            print(f"       Email:    {adm.get('email', 'N/A')}")
            print("   " + "-" * 66)
    print()


def add_admin(admins, password):
    print("\n[*] ADD NEW AUTHORIZED ADMINISTRATOR")
    print("-" * 50)
    name = input("Enter Full Name: ").strip()
    if not name:
        print("[!] Error: Name cannot be blank.")
        return admins

    admin_id = input("Enter Admin ID (e.g. 23ITBE177 / ADMIN001): ").strip().upper()
    if not admin_id:
        print("[!] Error: Admin ID cannot be blank.")
        return admins

    email = input("Enter Authorized Email Address: ").strip().lower()
    if not email or not re.match(r"^[^@]+@[^@]+\.[^@]+$", email):
        print("[!] Error: Invalid email format.")
        return admins

    # Check duplicates
    for a in admins:
        if a.get("admin_id", "").upper() == admin_id:
            print(f"[!] Error: Admin ID '{admin_id}' is already registered.")
            return admins
        if a.get("email", "").lower() == email:
            print(f"[!] Error: Email '{email}' is already registered.")
            return admins

    new_admin = {"name": name, "admin_id": admin_id, "email": email}
    admins.append(new_admin)

    save_admins_to_file(admins, password)
    print(f"\n[+] SUCCESS: Administrator '{name}' ({admin_id}) added and vault re-encrypted!")
    return admins


def remove_admin(admins, password):
    if not admins:
        print("\n[!] No administrators to remove.")
        return admins

    view_admins(admins)
    choice = input("Enter index number of admin to remove (or 0 to cancel): ").strip()
    if not choice.isdigit():
        return admins
    idx = int(choice)
    if idx == 0 or idx > len(admins):
        print("[*] Operation cancelled.")
        return admins

    removed = admins.pop(idx - 1)
    save_admins_to_file(admins, password)
    print(f"\n[-] SUCCESS: Removed '{removed.get('name')}' ({removed.get('admin_id')}) from vault.")
    return admins


def main():
    clear_console()
    print_banner()

    print("[SECURITY] AUTHENTICATION REQUIRED")
    print("This vault protects authorized administrator credentials with AES-grade encryption.")
    print("The raw file 'authorized_admins.json' is stored in encrypted ciphertext.")
    print("-" * 70)

    entered_pass = get_password("Enter Master Admin Password: ")

    try:
        admins = load_admins_from_file(entered_pass)
        if entered_pass != MASTER_ADMIN_PASSWORD:
            raise ValueError("ACCESS DENIED: Incorrect Master Password!")
    except Exception as e:
        print("\n[ACCESS DENIED] Incorrect Master Password! Unauthorized access blocked.")
        pause("\nPress Enter to exit...")
        sys.exit(1)

    print("\n[ACCESS GRANTED] Master Password Verified. Authorized Session Active.\n")

    while True:
        print("=" * 50)
        print("   ADMIN SECURITY VAULT - CONTROL MENU")
        print("=" * 50)
        print("   [1] View Decrypted Authorized Admins")
        print("   [2] Add New Authorized Admin")
        print("   [3] Remove an Authorized Admin")
        print("   [4] Exit")
        print("=" * 50)
        try:
            choice = input("Select an option (1-4): ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if choice == "1":
            admins = load_admins_from_file(entered_pass)
            view_admins(admins)
        elif choice == "2":
            admins = add_admin(admins, entered_pass)
        elif choice == "3":
            admins = remove_admin(admins, entered_pass)
        elif choice == "4":
            print("\n[*] Exiting vault. Encrypted file is secured on disk.")
            break
        else:
            print("\n[!] Invalid choice. Please select 1, 2, 3, or 4.")
        
        pause("\nPress Enter to continue...")
        clear_console()
        print_banner()


if __name__ == "__main__":
    main()
