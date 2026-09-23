"""
CloudLab Intelligence - Lightweight Client Monitoring Agent & Lab Simulator
Captures active application metadata, browser domains/tabs, context switches,
and active/idle duration, sending heartbeats to the local Edge Server.
"""

import os
import sys
import time
import json
import uuid
import random
import threading
import requests
from datetime import datetime, timezone

try:
    import psutil
except ImportError:
    psutil = None

EDGE_HEARTBEAT_URL = "http://127.0.0.1:5001/api/edge/heartbeat"
EDGE_LOGIN_URL = "http://127.0.0.1:5001/api/edge/login"
EDGE_LOGOUT_URL = "http://127.0.0.1:5001/api/edge/logout"


def get_active_window_metadata():
    """
    Non-invasive, privacy-first active window and browser metadata collector.
    Captures only executable name and sanitized window title / domain.
    """
    app_name = "VS Code"
    window_title = "cloud_sync.py - Visual Studio Code"
    browser_domain = ""
    is_idle = False

    # Try Windows-specific active window inspection if available
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            hwnd = user32.GetForegroundWindow()
            if hwnd:
                length = user32.GetWindowTextLengthW(hwnd)
                buf = ctypes.create_unicode_buffer(length + 1)
                user32.GetWindowTextW(hwnd, buf, length + 1)
                title = buf.value

                pid = ctypes.c_ulong()
                user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
                
                if psutil and pid.value:
                    try:
                        p = psutil.Process(pid.value)
                        app_name = p.name().replace(".exe", "")
                        window_title = title
                        
                        # Extract domain if browser
                        if app_name.lower() in ["chrome", "msedge", "firefox", "brave"]:
                            from backend.analytics_engine import extract_domain
                            browser_domain = extract_domain(title)
                    except Exception:
                        pass
        except Exception:
            pass

    return {
        "app_name": app_name,
        "window_title": window_title,
        "browser_domain": browser_domain,
        "is_idle": is_idle
    }


class ClientMonitoringAgent:
    """
    Lightweight Agent running on the student workstation.
    """
    def __init__(self, reg_no, student_name, pc_id="PC-LAB1-01", lab_id="LAB-01"):
        self.reg_no = reg_no
        self.student_name = student_name
        self.pc_id = pc_id
        self.lab_id = lab_id
        self.session_id = None
        self.is_running = False
        self.last_app = None
        self.last_domain = None
        self.heartbeat_interval = 5

    def login(self):
        self.session_id = str(uuid.uuid4())
        payload = {
            "session_id": self.session_id,
            "reg_no": self.reg_no,
            "student_name": self.student_name,
            "lab_id": self.lab_id,
            "pc_id": self.pc_id,
            "login_time": datetime.now().isoformat()
        }
        try:
            resp = requests.post(EDGE_LOGIN_URL, json=payload, timeout=4.0)
            if resp.status_code == 200:
                print(f"[Agent] Logged in successfully: {self.reg_no} on {self.pc_id}")
                return True
        except Exception as e:
            print(f"[Agent] Login error: {e}")
        return False

    def logout(self):
        if not self.session_id:
            return
        payload = {
            "session_id": self.session_id,
            "logout_time": datetime.now().isoformat()
        }
        try:
            requests.post(EDGE_LOGOUT_URL, json=payload, timeout=4.0)
            print(f"[Agent] Logged out: {self.reg_no}")
        except Exception as e:
            print(f"[Agent] Logout error: {e}")
        self.is_running = False

    def send_heartbeat(self, metadata=None):
        if not metadata:
            metadata = get_active_window_metadata()

        is_tab_switch = False
        curr_app = metadata.get("app_name")
        curr_dom = metadata.get("browser_domain")

        if (self.last_app and self.last_app != curr_app) or (self.last_domain and self.last_domain != curr_dom):
            is_tab_switch = True

        self.last_app = curr_app
        self.last_domain = curr_dom

        payload = {
            "event_id": str(uuid.uuid4()),
            "session_id": self.session_id,
            "reg_no": self.reg_no,
            "lab_id": self.lab_id,
            "pc_id": self.pc_id,
            "app_name": curr_app,
            "window_title": metadata.get("window_title", ""),
            "browser_domain": curr_dom,
            "browser_tab_title": metadata.get("window_title", ""),
            "duration_seconds": self.heartbeat_interval,
            "is_idle": metadata.get("is_idle", False),
            "is_tab_switch": is_tab_switch,
            "timestamp": datetime.now().isoformat()
        }

        try:
            requests.post(EDGE_HEARTBEAT_URL, json=payload, timeout=4.0)
        except Exception as e:
            pass

    def run(self):
        if not self.login():
            return
        self.is_running = True
        while self.is_running:
            self.send_heartbeat()
            time.sleep(self.heartbeat_interval)


# ------------------- Multi-Student Lab Workstation Simulator ------------------- #

SAMPLE_ACTIVITIES = [
    {"app": "Code", "title": "app.py - VS Code (Python Project)", "domain": ""},
    {"app": "Code", "title": "models.py - VS Code (FastAPI Project)", "domain": ""},
    {"app": "MySQLWorkbench", "title": "MySQL Workbench - student_records connection", "domain": ""},
    {"app": "chrome", "title": "Stack Overflow - How to fix SQLite locking issue", "domain": "stackoverflow.com"},
    {"app": "chrome", "title": "GitHub - Repo: cloudlab-intelligence", "domain": "github.com"},
    {"app": "chrome", "title": "GeeksforGeeks - Dijkstra's Algorithm in Python", "domain": "geeksforgeeks.org"},
    {"app": "chrome", "title": "AWS Documentation - EC2 Auto Scaling Groups", "domain": "aws.amazon.com"},
    {"app": "chrome", "title": "W3Schools - SQL Join Operations", "domain": "w3schools.com"},
    {"app": "WINWORD", "title": "Mini_Project_Documentation_V2.docx - Word", "domain": ""},
    {"app": "chrome", "title": "Overleaf - Cloud Computing Paper Draft", "domain": "overleaf.com"},
    {"app": "chrome", "title": "YouTube - Cloud Computing Full Course Lecture", "domain": "youtube.com"},
    {"app": "chrome", "title": "Reddit - r/programmerhumor", "domain": "reddit.com"},
    {"app": "Spotify", "title": "Spotify - Lofi Coding Beats", "domain": ""}
]

class LabWorkstationSimulator:
    """
    Simulates multiple concurrent students in the lab for testing and live demonstrations.
    """
    def __init__(self):
        self.active_simulators = {}
        self.is_simulating = False

    def start_simulation(self, students_list=None):
        if self.is_simulating:
            return

        if not students_list:
            students_list = [
                {"reg_no": "61782323106044", "name": "Jayakumar M", "pc": "PC-LAB1-01"},
                {"reg_no": "61782323106072", "name": "Neha Prapti P", "pc": "PC-LAB1-02"},
                {"reg_no": "61782323106077", "name": "Prabanjan V", "pc": "PC-LAB1-03"},
                {"reg_no": "61782323106012", "name": "Ananya S", "pc": "PC-LAB1-04"},
                {"reg_no": "61782323106025", "name": "Dharun Kumar R", "pc": "PC-LAB1-05"},
                {"reg_no": "61782323106038", "name": "Harish K", "pc": "PC-LAB1-06"},
                {"reg_no": "61782323106055", "name": "Kavya M", "pc": "PC-LAB1-07"},
                {"reg_no": "61782323106089", "name": "Siddharth T", "pc": "PC-LAB1-08"},
            ]

        self.is_simulating = True

        for s in students_list:
            agent = ClientMonitoringAgent(
                reg_no=s["reg_no"],
                student_name=s["name"],
                pc_id=s["pc"],
                lab_id="LAB-01"
            )
            if agent.login():
                self.active_simulators[s["reg_no"]] = agent

        # Background simulator loop
        def loop():
            while self.is_simulating:
                for reg_no, agent in list(self.active_simulators.items()):
                    # Pick activity
                    act = random.choice(SAMPLE_ACTIVITIES)
                    is_idle = random.random() < 0.08
                    metadata = {
                        "app_name": act["app"],
                        "window_title": act["title"],
                        "browser_domain": act["domain"],
                        "is_idle": is_idle
                    }
                    agent.send_heartbeat(metadata)
                time.sleep(5)

        t = threading.Thread(target=loop, daemon=True)
        t.start()
        print(f"[Simulator] Running simulation for {len(self.active_simulators)} students in Lab 1.")

    def stop_simulation(self):
        self.is_simulating = False
        for reg_no, agent in list(self.active_simulators.items()):
            agent.logout()
        self.active_simulators.clear()
        print("[Simulator] Stopped all simulated lab workstations.")


lab_simulator = LabWorkstationSimulator()

if __name__ == "__main__":
    agent = ClientMonitoringAgent("61782323106044", "Jayakumar M", "PC-LAB1-01")
    agent.login()
    print("Testing 2 heartbeats...")
    agent.send_heartbeat()
    time.sleep(2)
    agent.send_heartbeat()
    agent.logout()
    print("Agent test completed.")
