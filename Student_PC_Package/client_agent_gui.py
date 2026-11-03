"""
CloudLab Intelligence - Native Student Workstation Client
Runs on student PCs, prompts for Register Number, Name & PC ID,
and monitors active application, browser tabs, visited websites & AI chatbot usage in real time.
"""

import os
import sys
import time
import json
import uuid
import socket
import getpass
import threading
import requests
import re
import tkinter as tk
from tkinter import messagebox, ttk
from datetime import datetime

# Windows Native API for active window capture
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

CONFIG_FILE = "agent_config.json"
DEFAULT_EDGE_URL = "http://127.0.0.1:5001"


def get_system_login_username():
    """Detects logged in Windows OS username or computer name."""
    try:
        u = os.environ.get("USERNAME") or getpass.getuser()
        if u and u.strip():
            return u.strip()
    except Exception:
        pass
    try:
        comp = os.environ.get("COMPUTERNAME") or socket.gethostname()
        if comp and comp.strip():
            return comp.strip()
    except Exception:
        pass
    return "PC-LAB1-01"


def get_hostname_and_ip():
    """Gets local PC hostname and IP."""
    try:
        hostname = socket.gethostname()
        ip = socket.gethostbyname(hostname)
        return hostname, ip
    except Exception:
        return "WORKSTATION-PC", "127.0.0.1"


def get_idle_duration_seconds():
    """Returns seconds of user keyboard/mouse inactivity."""
    class LASTINPUTINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("dwTime", wintypes.DWORD)]

    lii = LASTINPUTINFO()
    lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
    if user32.GetLastInputInfo(ctypes.byref(lii)):
        millis = kernel32.GetTickCount() - lii.dwTime
        return millis / 1000.0
    return 0.0


def get_active_window_metadata():
    """
    Captures active application name, window title, and browser domain/URL keyword
    using Windows User32 and Process API.
    """
    app_name = "Desktop"
    raw_title = "Desktop"
    browser_domain = ""

    hwnd = user32.GetForegroundWindow()
    if hwnd:
        length = user32.GetWindowTextLengthW(hwnd)
        if length > 0:
            buf = ctypes.create_unicode_buffer(length + 1)
            user32.GetWindowTextW(hwnd, buf, length + 1)
            raw_title = buf.value or "Desktop"

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        
        if pid.value:
            try:
                import psutil
                p = psutil.Process(pid.value)
                app_name = p.name().replace(".exe", "")
            except Exception:
                app_name = raw_title.split(" - ")[-1] if " - " in raw_title else "Application"

    window_title = raw_title
    lower_title = raw_title.lower()

    # Browser Detection & Domain Extraction
    browser_apps = ["chrome", "msedge", "firefox", "brave", "opera"]
    is_browser = any(b in app_name.lower() for b in browser_apps) or any(b in lower_title for b in ["google chrome", "microsoft edge", "firefox", "brave"])

    if is_browser:
        for suffix in [" - Google Chrome", " - Microsoft Edge", " - Mozilla Firefox", " - Brave", " - Opera"]:
            if window_title.endswith(suffix):
                window_title = window_title[:-len(suffix)].strip()
                break

        # AI Chatbot Detection
        if any(ai in lower_title for ai in ["chatgpt", "openai", "chat.openai"]):
            browser_domain = "chatgpt.com"
        elif any(ai in lower_title for ai in ["deepseek", "deepseek chat"]):
            browser_domain = "deepseek.com"
        elif any(ai in lower_title for ai in ["claude", "claude.ai", "anthropic"]):
            browser_domain = "claude.ai"
        elif any(ai in lower_title for ai in ["gemini", "bard", "gemini.google"]):
            browser_domain = "gemini.google.com"
        elif any(ai in lower_title for ai in ["perplexity", "perplexity.ai"]):
            browser_domain = "perplexity.ai"
        elif any(ai in lower_title for ai in ["copilot", "github copilot", "bing copilot"]):
            browser_domain = "copilot.microsoft.com"
        elif any(ai in lower_title for ai in ["blackbox", "blackbox.ai"]):
            browser_domain = "blackbox.ai"
        elif "github" in lower_title:
            browser_domain = "github.com"
        elif "stackoverflow" in lower_title:
            browser_domain = "stackoverflow.com"
        elif "geeksforgeeks" in lower_title:
            browser_domain = "geeksforgeeks.org"
        elif "w3schools" in lower_title:
            browser_domain = "w3schools.com"
        elif "leetcode" in lower_title:
            browser_domain = "leetcode.com"
        elif "hackerrank" in lower_title:
            browser_domain = "hackerrank.com"
        elif "youtube" in lower_title:
            browser_domain = "youtube.com"
        elif "google" in lower_title:
            browser_domain = "google.com"
        else:
            browser_domain = window_title.split(" - ")[-1] if " - " in window_title else "browser.tab"

    return app_name, window_title, browser_domain


class StudentAgentApp:
    def __init__(self, root):
        self.root = root
        self.root.title("CloudLab Intelligence • Student Workstation")
        w, h = 480, 680
        # Auto-center on monitor
        try:
            sw = self.root.winfo_screenwidth()
            sh = self.root.winfo_screenheight()
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2 - 25)
            self.root.geometry(f"{w}x{h}+{x}+{y}")
        except Exception:
            self.root.geometry(f"{w}x{h}")

        self.root.resizable(False, False)
        self.root.configure(bg="#f1f5f9")

        self.hostname, self.ip = get_hostname_and_ip()
        self.system_username = get_system_login_username()
        self.session_id = None
        self.reg_no = None
        self.student_name = None
        self.phone_number = None
        self.pc_id = self.system_username
        self.is_monitoring = False
        self.edge_url = self.load_edge_url()
        self.cooldown_remaining = 0
        self.cooldown_timer_id = None

        self.root.protocol("WM_DELETE_WINDOW", self.on_close_window)
        self.build_ui()

    def load_edge_url(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r") as f:
                    cfg = json.load(f)
                    return cfg.get("edge_url", DEFAULT_EDGE_URL)
            except Exception:
                pass
        return DEFAULT_EDGE_URL

    def save_edge_url(self, url):
        self.edge_url = url
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"edge_url": url}, f, indent=2)
        except Exception:
            pass

    def build_ui(self):
        # 1. Header with Deep Navy Gradient / Modern Banner
        header = tk.Frame(self.root, bg="#0f172a", pady=14, padx=20)
        header.pack(fill="x")

        # Top tag
        tk.Label(
            header,
            text="SONA COLLEGE OF TECHNOLOGY  •  DEPT OF IT",
            font=("Segoe UI", 8, "bold"),
            fg="#94a3b8",
            bg="#0f172a"
        ).pack()

        # Brand Title
        tk.Label(
            header,
            text="CloudLab Intelligence",
            font=("Segoe UI", 15, "bold"),
            fg="#ffffff",
            bg="#0f172a"
        ).pack(pady=(2, 4))

        # Security Badge Pill
        badge_frame = tk.Frame(header, bg="#064e3b", padx=10, pady=3, highlightbackground="#059669", highlightthickness=1)
        badge_frame.pack()
        tk.Label(
            badge_frame,
            text="🔐 Two-Factor Email OTP Workstation Security",
            font=("Segoe UI", 8, "bold"),
            fg="#34d399",
            bg="#064e3b"
        ).pack()

        # 2. Main Card Container (Floating Card Style)
        card_outer = tk.Frame(self.root, bg="#f1f5f9", padx=16, pady=12)
        card_outer.pack(fill="both", expand=True)

        body = tk.Frame(card_outer, bg="#ffffff", padx=20, pady=16, highlightbackground="#e2e8f0", highlightthickness=1)
        body.pack(fill="both", expand=True)

        # Helper for focus highlights and placeholders
        def style_entry(entry, placeholder_text):
            entry.insert(0, placeholder_text)
            entry.config(fg="#94a3b8", bg="#f8fafc", highlightbackground="#cbd5e1", highlightcolor="#2563eb", highlightthickness=1)

            def on_focus_in(event):
                if entry.get() == placeholder_text:
                    entry.delete(0, tk.END)
                    entry.config(fg="#0f172a", bg="#ffffff")
                entry.config(highlightbackground="#2563eb")

            def on_focus_out(event):
                if not entry.get().strip():
                    entry.insert(0, placeholder_text)
                    entry.config(fg="#94a3b8", bg="#f8fafc")
                entry.config(highlightbackground="#cbd5e1")

            entry.bind("<FocusIn>", on_focus_in)
            entry.bind("<FocusOut>", on_focus_out)

        # Helper for modern button hover effect
        def add_hover(btn, normal_bg, hover_bg):
            btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg) if str(btn["state"]) != "disabled" else None)
            btn.bind("<Leave>", lambda e: btn.config(bg=normal_bg) if str(btn["state"]) != "disabled" else None)

        # 1. Reg No
        tk.Label(body, text="🎓  Student Register Number:", font=("Segoe UI", 9, "bold"), fg="#1e293b", bg="#ffffff").pack(anchor="w", pady=(1, 2))
        self.entry_reg = tk.Entry(body, font=("Segoe UI", 9), relief="flat")
        self.entry_reg.pack(fill="x", ipady=4, pady=(0, 8))
        style_entry(self.entry_reg, "Enter your Register Number (e.g. 61782323106044)")

        # 2. Student Name
        tk.Label(body, text="👤  Student Full Name:", font=("Segoe UI", 9, "bold"), fg="#1e293b", bg="#ffffff").pack(anchor="w", pady=(1, 2))
        self.entry_name = tk.Entry(body, font=("Segoe UI", 9), relief="flat")
        self.entry_name.pack(fill="x", ipady=4, pady=(0, 8))
        style_entry(self.entry_name, "Enter your Full Name")

        # 3. Student Registered Email ID + Send OTP Row
        tk.Label(body, text="✉️  Registered Student Email ID (for OTP):", font=("Segoe UI", 9, "bold"), fg="#1e293b", bg="#ffffff").pack(anchor="w", pady=(1, 2))
        email_row = tk.Frame(body, bg="#ffffff")
        email_row.pack(fill="x", pady=(0, 4))

        self.entry_email = tk.Entry(email_row, font=("Segoe UI", 9), relief="flat")
        self.entry_email.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 8))
        style_entry(self.entry_email, "Enter your Email ID (e.g. name@gmail.com)")

        self.btn_send_otp = tk.Button(
            email_row,
            text="Send OTP",
            font=("Segoe UI", 9, "bold"),
            bg="#2563eb",
            fg="white",
            activebackground="#1d4ed8",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            padx=12,
            command=self.request_otp_action
        )
        self.btn_send_otp.pack(side="right", ipady=3)
        add_hover(self.btn_send_otp, "#2563eb", "#1d4ed8")

        # OTP Info / Feedback Box (Soft Blue Alert Pill)
        self.otp_info_frame = tk.Frame(body, bg="#eff6ff", padx=10, pady=5, highlightbackground="#bfdbfe", highlightthickness=1)
        self.otp_info_frame.pack(fill="x", pady=(0, 8))

        self.lbl_otp_info = tk.Label(
            self.otp_info_frame,
            text="📩 A 6-digit verification code will be sent to your Gmail inbox.",
            font=("Segoe UI", 8),
            fg="#1d4ed8",
            bg="#eff6ff",
            wraplength=380,
            justify="left"
        )
        self.lbl_otp_info.pack(anchor="w")

        # 4. 6-digit OTP Code Entry (Prominent Monospace Entry)
        tk.Label(body, text="🔑  Enter 6-Digit Email OTP Received:", font=("Segoe UI", 9, "bold"), fg="#1e293b", bg="#ffffff").pack(anchor="w", pady=(1, 2))
        self.entry_otp = tk.Entry(
            body,
            font=("Consolas", 12, "bold"),
            bg="#f8fafc",
            fg="#0f172a",
            insertbackground="#0f172a",
            relief="flat",
            justify="center",
            highlightbackground="#93c5fd",
            highlightcolor="#2563eb",
            highlightthickness=1
        )
        self.entry_otp.pack(fill="x", ipady=4, pady=(0, 8))
        style_entry(self.entry_otp, "Enter 6-digit OTP code")

        # 5. Workstation PC ID Selector
        tk.Label(body, text="🖥️  Assigned Workstation PC:", font=("Segoe UI", 9, "bold"), fg="#1e293b", bg="#ffffff").pack(anchor="w", pady=(1, 2))
        pc_options = [self.system_username]
        if self.hostname and self.hostname not in pc_options:
            pc_options.append(self.hostname)
        pc_options += ["PC-ADMIN-01"] + [f"PC-LAB1-{i:02d}" for i in range(1, 71)]
        seen = set()
        final_pc_options = [x for x in pc_options if not (x in seen or seen.add(x))]

        self.combo_pc = ttk.Combobox(body, values=final_pc_options, font=("Segoe UI", 9), state="normal")
        self.combo_pc.pack(fill="x", ipady=3, pady=(0, 8))
        self.combo_pc.set(self.system_username)

        # 6. Edge Server URL
        tk.Label(body, text="🌐  Master / Edge Server URL:", font=("Segoe UI", 8, "bold"), fg="#64748b", bg="#ffffff").pack(anchor="w", pady=(1, 1))
        self.entry_url = tk.Entry(body, font=("Segoe UI", 8), bg="#f8fafc", fg="#475569", insertbackground="#0f172a", relief="flat", highlightbackground="#e2e8f0", highlightthickness=1)
        self.entry_url.pack(fill="x", ipady=2, pady=(0, 12))
        self.entry_url.insert(0, self.edge_url)

        # 7. Action Button (Large Emerald Pill)
        self.btn_action = tk.Button(
            body,
            text="Verify OTP & Start Lab Session",
            font=("Segoe UI", 10, "bold"),
            bg="#10b981",
            fg="white",
            activebackground="#059669",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self.toggle_session
        )
        self.btn_action.pack(fill="x", ipady=7)
        add_hover(self.btn_action, "#10b981", "#059669")

        # 8. Footer Status Pill
        status_bar = tk.Frame(self.root, bg="#e2e8f0", pady=6, padx=12)
        status_bar.pack(fill="x", side="bottom")

        self.lbl_status = tk.Label(
            status_bar,
            text=f"🟢 Live Node • Host: {self.hostname} ({self.ip}) • Ready",
            font=("Segoe UI", 8, "bold"),
            fg="#334155",
            bg="#e2e8f0"
        )
        self.lbl_status.pack()

    def toggle_session(self):
        if not self.is_monitoring:
            self.start_session()
        else:
            self.stop_session()

    def normalize_url(self, raw_url):
        url = raw_url.strip()
        if not url:
            return DEFAULT_EDGE_URL
        # Clean duplicated prefixes if student pasted full url e.g. "http://http://..."
        while url.startswith("http://http://") or url.startswith("https://https://") or url.startswith("http://https://"):
            url = url[7:]
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{url}"
        host_part = url.replace("http://", "").replace("https://", "")
        if ":" not in host_part:
            url = f"{url.rstrip('/')}:5001"
        return url.rstrip("/")

    def request_otp_action(self):
        raw_email = self.entry_email.get().strip().lower()
        if not raw_email or raw_email.startswith("enter your") or "@" not in raw_email or "." not in raw_email:
            messagebox.showwarning("Email Required", "Please enter your valid Student Email ID (e.g. name@gmail.com) to receive your verification code.")
            self.entry_email.focus_set()
            return

        raw_url = self.entry_url.get().strip()
        self.edge_url = self.normalize_url(raw_url)
        self.save_edge_url(self.edge_url)

        reg = self.entry_reg.get().strip().upper()
        if reg.startswith("ENTER YOUR"):
            reg = ""
        name = self.entry_name.get().strip()
        if name.startswith("ENTER YOUR"):
            name = ""
        pc_id = self.combo_pc.get().strip() if hasattr(self, 'combo_pc') else "Lab Workstation"

        payload = {
            "country_code": "",
            "phone_number": raw_email,
            "email": raw_email,
            "reg_no": reg,
            "student_name": name,
            "pc_id": pc_id
        }

        self.btn_send_otp.config(state="disabled", text="Sending...")
        self.lbl_otp_info.config(text="Connecting to mail service and sending OTP to your inbox...", fg="#2563eb")
        self.root.update_idletasks()

        targets_to_try = [self.edge_url]
        if ":5001" in self.edge_url:
            targets_to_try.append(self.edge_url.replace(":5001", ":5000"))
        elif ":5000" in self.edge_url:
            targets_to_try.append(self.edge_url.replace(":5000", ":5001"))
        if "127.0.0.1" not in self.edge_url and "localhost" not in self.edge_url:
            targets_to_try.extend(["http://127.0.0.1:5001", "http://127.0.0.1:5000"])

        resp_data = None
        success_url = None

        for target in targets_to_try:
            try:
                # 20.0s timeout ensures Gmail SMTP TLS handshake (2-8s) completes without client timing out
                r = requests.post(f"{target}/api/edge/send-otp", json=payload, timeout=20.0)
                if r.status_code == 200:
                    try:
                        resp_data = r.json()
                        success_url = target
                        break
                    except Exception:
                        pass
                elif r.status_code in (400, 401, 403, 429):
                    try:
                        resp_data = r.json()
                    except Exception:
                        resp_data = {"error": "Server error processing OTP request."}
                    success_url = target
                    break
            except requests.exceptions.Timeout:
                resp_data = {"error": "Email delivery timed out. Please check server internet connection or retry."}
                break
            except requests.exceptions.ConnectionError:
                continue
            except Exception:
                continue

        if not resp_data:
            self.btn_send_otp.config(state="normal", text="Send OTP")
            self.lbl_otp_info.config(text="Failed to connect to Master/Edge Server. Check server URL.", fg="#ef4444")
            messagebox.showerror("Connection Failed", f"Could not reach server at {self.edge_url} to send OTP.\nPlease verify START_ADMIN_SERVER.bat is running.")
            return

        if resp_data.get("success"):
            self.edge_url = success_url
            self.entry_url.delete(0, tk.END)
            self.entry_url.insert(0, self.edge_url)
            self.save_edge_url(self.edge_url)

            masked = resp_data.get("masked_phone", raw_email)
            if hasattr(self, 'otp_info_frame'):
                self.otp_info_frame.config(bg="#ecfdf5", highlightbackground="#a7f3d0")
            self.lbl_otp_info.config(text=f"✅ OTP sent to {masked}. Check your Gmail inbox & enter code.", fg="#047857", bg="#ecfdf5")
            if self.entry_otp.get().startswith("Enter 6-digit"):
                self.entry_otp.delete(0, tk.END)
                self.entry_otp.config(fg="#0f172a")
            self.entry_otp.focus_set()

            cooldown = resp_data.get("cooldown_seconds", 60)
            self.start_cooldown_timer(cooldown)
        else:
            err_msg = resp_data.get("error", "Failed to dispatch OTP email.")
            if hasattr(self, 'otp_info_frame'):
                self.otp_info_frame.config(bg="#fef2f2", highlightbackground="#fecaca")
            self.lbl_otp_info.config(text=f"❌ {err_msg}", fg="#b91c1c", bg="#fef2f2")
            cooldown_rem = resp_data.get("cooldown_remaining", 0)
            if cooldown_rem > 0:
                self.start_cooldown_timer(cooldown_rem)
            else:
                self.btn_send_otp.config(state="normal", text="Send OTP")
            messagebox.showerror("OTP Request Failed", err_msg)

    def start_cooldown_timer(self, seconds):
        if self.cooldown_timer_id:
            try:
                self.root.after_cancel(self.cooldown_timer_id)
            except Exception:
                pass
        self.cooldown_remaining = seconds
        self._update_cooldown_tick()

    def _update_cooldown_tick(self):
        if self.cooldown_remaining > 0:
            self.btn_send_otp.config(state="disabled", text=f"Resend ({self.cooldown_remaining}s)")
            self.cooldown_remaining -= 1
            self.cooldown_timer_id = self.root.after(1000, self._update_cooldown_tick)
        else:
            self.btn_send_otp.config(state="normal", text="Resend OTP")
            self.cooldown_timer_id = None

    def start_session(self):
        reg = self.entry_reg.get().strip().upper()
        name = self.entry_name.get().strip()
        pc = self.combo_pc.get().strip() or self.system_username or "PC-LAB1-01"
        raw_url = self.entry_url.get().strip()
        raw_email = self.entry_email.get().strip().lower()
        otp_code = self.entry_otp.get().strip()

        if not reg or reg.startswith("ENTER YOUR") or not name or name.startswith("ENTER YOUR"):
            messagebox.showerror("Input Required", "Please enter your Register Number and Full Name to begin.")
            return

        if not raw_email or raw_email.startswith("enter your") or "@" not in raw_email or "." not in raw_email:
            messagebox.showerror("Email Required", "Please enter your registered Student Email ID (e.g. name@gmail.com).")
            self.entry_email.focus_set()
            return

        if not otp_code or otp_code.startswith("Enter 6-digit") or len(otp_code) != 6 or not otp_code.isdigit():
            messagebox.showerror("OTP Verification Required", "Please enter the 6-digit numeric OTP sent to your email.\n\nClick 'Send OTP' if you haven't received a code yet.")
            self.entry_otp.focus_set()
            return

        self.edge_url = self.normalize_url(raw_url)
        self.entry_url.delete(0, tk.END)
        self.entry_url.insert(0, self.edge_url)
        self.save_edge_url(self.edge_url)

        self.reg_no = reg
        self.student_name = name
        self.pc_id = pc
        self.session_id = str(uuid.uuid4())
        self.phone_number = raw_email

        payload = {
            "session_id": self.session_id,
            "reg_no": self.reg_no,
            "student_name": self.student_name,
            "lab_id": "LAB-01",
            "pc_id": self.pc_id,
            "phone_number": self.phone_number,
            "email": self.phone_number,
            "otp": otp_code,
            "login_time": datetime.now().isoformat()
        }

        # Auto-try edge URL with smart fallbacks (port 5001 -> port 5000 -> localhost)
        targets_to_try = [self.edge_url]
        if ":5001" in self.edge_url:
            targets_to_try.append(self.edge_url.replace(":5001", ":5000"))
        elif ":5000" in self.edge_url:
            targets_to_try.append(self.edge_url.replace(":5000", ":5001"))
        if "127.0.0.1" not in self.edge_url and "localhost" not in self.edge_url:
            targets_to_try.extend(["http://127.0.0.1:5001", "http://127.0.0.1:5000"])

        connected_url = None
        last_resp_data = None
        last_error = None

        for target in targets_to_try:
            try:
                resp = requests.post(f"{target}/api/edge/login", json=payload, timeout=8.0)
                if resp.status_code == 200:
                    try:
                        last_resp_data = resp.json()
                        if last_resp_data.get("success"):
                            connected_url = target
                            break
                    except Exception:
                        pass
                elif resp.status_code in (400, 401, 403):
                    try:
                        last_resp_data = resp.json()
                    except Exception:
                        last_resp_data = {"error": "Authentication failed."}
                    connected_url = target
                    break
            except requests.exceptions.ConnectionError:
                continue
            except Exception as ex:
                last_error = ex

        if connected_url and last_resp_data and last_resp_data.get("success"):
            self.edge_url = connected_url
            self.entry_url.delete(0, tk.END)
            self.entry_url.insert(0, self.edge_url)
            self.save_edge_url(self.edge_url)

            self.is_monitoring = True
            self.btn_action.config(text="End Session & Logout", bg="#ef4444", activebackground="#dc2626")
            parts = self.phone_number.split("@")
            masked = f"{parts[0][:2]}•••@{parts[1]}" if len(parts) == 2 and len(parts[0]) > 2 else self.phone_number
            self.lbl_status.config(text=f"🟢 Monitoring Active on {self.pc_id}! Authenticated ({masked})", fg="#34d399")
            self.entry_reg.config(state="disabled")
            self.entry_name.config(state="disabled")
            self.entry_email.config(state="disabled")
            self.btn_send_otp.config(state="disabled")
            self.entry_otp.config(state="disabled")
            self.combo_pc.config(state="disabled")

            # Minimize window to background so student can work
            self.root.iconify()

            # Start real-time background monitoring thread
            threading.Thread(target=self.monitoring_loop, daemon=True).start()
        elif last_resp_data and not last_resp_data.get("success"):
            err_msg = last_resp_data.get("error", "Email OTP verification failed.")
            messagebox.showerror(
                "Authentication Denied",
                f"Failed to authenticate session:\n\n{err_msg}\n\nPlease check your OTP and try again."
            )
        else:
            messagebox.showerror(
                "Connection Error",
                f"Could not reach Master Server at {self.edge_url}.\n\n"
                f"1. Make sure START_ADMIN_SERVER.bat is running on the Admin PC.\n"
                f"2. Check that the URL includes port :5001 or :5000."
            )

    def stop_session(self):
        if not self.session_id:
            return

        payload = {
            "session_id": self.session_id,
            "logout_time": datetime.now().isoformat()
        }

        try:
            for target in [self.edge_url, "http://127.0.0.1:5001", "http://127.0.0.1:5000"]:
                try:
                    r = requests.post(f"{target}/api/edge/logout", json=payload, timeout=4.0)
                    if r.status_code == 200:
                        break
                except Exception:
                    pass
        except Exception:
            pass

        self.is_monitoring = False
        self.btn_action.config(text="Verify OTP & Start Lab Session", bg="#10b981", activebackground="#059669")
        self.lbl_status.config(text="Session completed & PDF report saved.", fg="#60a5fa")
        self.entry_reg.config(state="normal")
        self.entry_name.config(state="normal")
        self.entry_email.config(state="normal")
        self.btn_send_otp.config(state="normal", text="Send OTP")
        self.entry_otp.config(state="normal")
        self.entry_otp.delete(0, tk.END)
        self.combo_pc.config(state="normal")
        if hasattr(self, 'otp_info_frame'):
            self.otp_info_frame.config(bg="#eff6ff", highlightbackground="#bfdbfe")
        self.lbl_otp_info.config(text="Session ended. Enter credentials and verify OTP for next student.", fg="#1d4ed8", bg="#eff6ff")
        self.lbl_status.config(text="Session completed & PDF report saved.", fg="#1e293b")
        messagebox.showinfo("Session Ended", f"Thank you {self.student_name}!\nYour lab activity & browser tab report has been securely saved to the Dispatch Center.")

    def on_close_window(self):
        """Handle student clicking 'X' on window - gracefully log out before exit."""
        if self.is_monitoring and self.session_id:
            try:
                payload = {
                    "session_id": self.session_id,
                    "logout_time": datetime.now().isoformat()
                }
                for target in [self.edge_url, "http://127.0.0.1:5001", "http://127.0.0.1:5000"]:
                    try:
                        requests.post(f"{target}/api/edge/logout", json=payload, timeout=1.5)
                        break
                    except Exception:
                        pass
            except Exception:
                pass
        self.root.destroy()

    def monitoring_loop(self):
        last_app = None
        last_dom = None
        last_title = None
        last_idle = False
        seconds_since_last_sync = 0

        while self.is_monitoring:
            try:
                time.sleep(1) # Fast local polling every 1 second
                seconds_since_last_sync += 1

                app, title, domain = get_active_window_metadata()
                idle_sec = get_idle_duration_seconds()
                is_idle = idle_sec >= 60.0 # Idle if no input >= 60s

                if is_idle:
                    app = f"Idle ({int(idle_sec)}s)"
                    title = f"No mouse/keyboard activity for {int(idle_sec)}s"

                # Check if a tab, window, application, or idle state switch occurred
                is_tab_switch = False
                state_changed = False

                if last_app is None:
                    # First run after login
                    state_changed = True
                elif is_idle != last_idle:
                    state_changed = True
                elif not is_idle and ((last_app != app) or (last_dom != domain) or (last_title != title)):
                    is_tab_switch = True
                    state_changed = True

                # ONLY SEND UPDATE IF:
                # 1. Student switched tabs/window/app (Instant event sync) OR
                # 2. Idle state toggled (Active <-> Idle) OR
                # 3. 10 seconds elapsed (Periodic duration keepalive)
                if state_changed or seconds_since_last_sync >= 10:
                    sync_duration = max(1, seconds_since_last_sync)
                    seconds_since_last_sync = 0

                    last_app = app
                    last_dom = domain
                    last_title = title
                    last_idle = is_idle

                    heartbeat = {
                        "event_id": str(uuid.uuid4()),
                        "session_id": self.session_id,
                        "reg_no": self.reg_no,
                        "lab_id": "LAB-01",
                        "pc_id": self.pc_id,
                        "app_name": app,
                        "window_title": title,
                        "browser_domain": domain,
                        "browser_tab_title": title,
                        "duration_seconds": sync_duration,
                        "is_idle": is_idle,
                        "is_tab_switch": is_tab_switch,
                        "timestamp": datetime.now().isoformat()
                    }

                    # Try sending heartbeat with auto-fallback
                    for target in [self.edge_url, "http://127.0.0.1:5001", "http://127.0.0.1:5000"]:
                        try:
                            r = requests.post(f"{target}/api/edge/heartbeat", json=heartbeat, timeout=2.0)
                            if r.status_code == 200:
                                break
                        except Exception:
                            pass

            except Exception as loop_ex:
                print(f"[Monitoring Loop Warning] {loop_ex}")


get_foreground_window_metadata = get_active_window_metadata


def main():
    root = tk.Tk()
    app = StudentAgentApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
