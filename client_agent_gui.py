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
        self.root.title("CloudLab Intelligence - Student Workstation Login")
        self.root.geometry("440x480")
        self.root.resizable(False, False)
        self.root.configure(bg="#0f172a")

        self.hostname, self.ip = get_hostname_and_ip()
        self.system_username = get_system_login_username()
        self.session_id = None
        self.reg_no = None
        self.student_name = None
        self.pc_id = self.system_username
        self.is_monitoring = False
        self.edge_url = self.load_edge_url()

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
        # Header
        header_frame = tk.Frame(self.root, bg="#1e293b", pady=12)
        header_frame.pack(fill="x")

        tk.Label(
            header_frame,
            text="CloudLab Intelligence",
            font=("Helvetica", 14, "bold"),
            fg="#60a5fa",
            bg="#1e293b"
        ).pack()

        tk.Label(
            header_frame,
            text="Sona College of Technology • Dept of IT",
            font=("Helvetica", 9),
            fg="#94a3b8",
            bg="#1e293b"
        ).pack()

        # Body Form
        body = tk.Frame(self.root, bg="#0f172a", padx=25, pady=12)
        body.pack(fill="both", expand=True)

        # Placeholder helper function
        def setup_placeholder(entry, placeholder_text):
            entry.insert(0, placeholder_text)
            entry.config(fg="#94a3b8")

            def on_focus_in(event):
                if entry.get() == placeholder_text:
                    entry.delete(0, tk.END)
                    entry.config(fg="#ffffff")

            def on_focus_out(event):
                if not entry.get().strip():
                    entry.insert(0, placeholder_text)
                    entry.config(fg="#94a3b8")

            entry.bind("<FocusIn>", on_focus_in)
            entry.bind("<FocusOut>", on_focus_out)

        # Reg No
        tk.Label(body, text="Register Number:", font=("Helvetica", 9, "bold"), fg="#e2e8f0", bg="#0f172a").pack(anchor="w", pady=(2, 2))
        self.entry_reg = tk.Entry(body, font=("Helvetica", 10), bg="#1e293b", fg="#ffffff", insertbackground="white", relief="flat", highlightthickness=1, highlightcolor="#3b82f6")
        self.entry_reg.pack(fill="x", ipady=3, pady=(0, 8))
        setup_placeholder(self.entry_reg, "Enter your Register Number (e.g. 61782323106044)")

        # Name
        tk.Label(body, text="Student Name:", font=("Helvetica", 9, "bold"), fg="#e2e8f0", bg="#0f172a").pack(anchor="w", pady=(2, 2))
        self.entry_name = tk.Entry(body, font=("Helvetica", 10), bg="#1e293b", fg="#ffffff", insertbackground="white", relief="flat", highlightthickness=1, highlightcolor="#3b82f6")
        self.entry_name.pack(fill="x", ipady=3, pady=(0, 8))
        setup_placeholder(self.entry_name, "Enter your Full Name")

        # Workstation PC ID Selector (Auto-filled with Windows Login Username)
        tk.Label(body, text="Assigned Workstation PC / Login User:", font=("Helvetica", 9, "bold"), fg="#e2e8f0", bg="#0f172a").pack(anchor="w", pady=(2, 2))
        pc_options = [self.system_username]
        if self.hostname and self.hostname not in pc_options:
            pc_options.append(self.hostname)
        pc_options += ["PC-ADMIN-01"] + [f"PC-LAB1-{i:02d}" for i in range(1, 71)]
        
        seen = set()
        final_pc_options = [x for x in pc_options if not (x in seen or seen.add(x))]

        self.combo_pc = ttk.Combobox(body, values=final_pc_options, font=("Helvetica", 10), state="normal")
        self.combo_pc.pack(fill="x", ipady=3, pady=(0, 8))
        self.combo_pc.set(self.system_username)

        # Edge Server URL
        tk.Label(body, text="Master / Edge Server URL:", font=("Helvetica", 8), fg="#94a3b8", bg="#0f172a").pack(anchor="w", pady=(2, 1))
        self.entry_url = tk.Entry(body, font=("Helvetica", 9), bg="#1e293b", fg="#94a3b8", insertbackground="white", relief="flat")
        self.entry_url.pack(fill="x", ipady=2, pady=(0, 12))
        self.entry_url.insert(0, self.edge_url)

        # Action Button
        self.btn_action = tk.Button(
            body,
            text="Start Lab Session",
            font=("Helvetica", 11, "bold"),
            bg="#10b981",
            fg="white",
            activebackground="#059669",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self.toggle_session
        )
        self.btn_action.pack(fill="x", ipady=6)

        # Status Label
        self.lbl_status = tk.Label(
            body,
            text=f"Host: {self.hostname} ({self.ip}) • Ready",
            font=("Helvetica", 8),
            fg="#64748b",
            bg="#0f172a"
        )
        self.lbl_status.pack(pady=8)

    def toggle_session(self):
        if not self.is_monitoring:
            self.start_session()
        else:
            self.stop_session()

    def normalize_url(self, raw_url):
        url = raw_url.strip()
        if not url:
            return DEFAULT_EDGE_URL
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{url}"
        host_part = url.replace("http://", "").replace("https://", "")
        if ":" not in host_part:
            url = f"{url.rstrip('/')}:5001"
        return url.rstrip("/")

    def start_session(self):
        reg = self.entry_reg.get().strip().upper()
        name = self.entry_name.get().strip()
        pc = self.combo_pc.get().strip() or self.system_username or "PC-LAB1-01"
        raw_url = self.entry_url.get().strip()

        if not reg or reg.startswith("ENTER YOUR") or not name or name.startswith("ENTER YOUR"):
            messagebox.showerror("Input Required", "Please enter your Register Number and Full Name to begin.")
            return

        self.edge_url = self.normalize_url(raw_url)
        self.entry_url.delete(0, tk.END)
        self.entry_url.insert(0, self.edge_url)
        self.save_edge_url(self.edge_url)

        self.reg_no = reg
        self.student_name = name
        self.pc_id = pc
        self.session_id = str(uuid.uuid4())

        payload = {
            "session_id": self.session_id,
            "reg_no": self.reg_no,
            "student_name": self.student_name,
            "lab_id": "LAB-01",
            "pc_id": self.pc_id,
            "login_time": datetime.now().isoformat()
        }

        # Auto-try edge URL with smart fallbacks (port 5001 -> port 5000 -> localhost)
        targets_to_try = [self.edge_url]
        if ":5001" in self.edge_url:
            targets_to_try.append(self.edge_url.replace(":5001", ":5000"))
        if "127.0.0.1" not in self.edge_url and "localhost" not in self.edge_url:
            targets_to_try.extend(["http://127.0.0.1:5001", "http://127.0.0.1:5000"])

        connected_url = None
        last_error = None

        for target in targets_to_try:
            try:
                resp = requests.post(f"{target}/api/edge/login", json=payload, timeout=2.5)
                if resp.status_code == 200:
                    connected_url = target
                    break
            except Exception as ex:
                last_error = ex

        if connected_url:
            self.edge_url = connected_url
            self.entry_url.delete(0, tk.END)
            self.entry_url.insert(0, self.edge_url)
            self.save_edge_url(self.edge_url)

            self.is_monitoring = True
            self.btn_action.config(text="End Session & Logout", bg="#ef4444", activebackground="#dc2626")
            self.lbl_status.config(text=f"🟢 Monitoring Active on {self.pc_id}!", fg="#34d399")
            self.entry_reg.config(state="disabled")
            self.entry_name.config(state="disabled")
            self.combo_pc.config(state="disabled")

            # Minimize window to background so student can work
            self.root.iconify()

            # Start real-time background monitoring thread
            threading.Thread(target=self.monitoring_loop, daemon=True).start()
        else:
            messagebox.showerror(
                "Connection Error",
                f"Could not reach Master Server at {self.edge_url}.\n\n"
                f"1. Make sure START_ADMIN_SERVER.bat is running on the Admin PC.\n"
                f"2. Check that the URL includes port :5001 (e.g. http://127.0.0.1:5001 or http://<Admin-IP>:5001)."
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
        self.btn_action.config(text="Start Lab Session", bg="#10b981", activebackground="#059669")
        self.lbl_status.config(text="Session completed & PDF report saved.", fg="#60a5fa")
        self.entry_reg.config(state="normal")
        self.entry_name.config(state="normal")
        self.combo_pc.config(state="normal")
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
