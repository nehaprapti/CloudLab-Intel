"""
CloudLab Intelligence - Master Orchestration Launcher
Initializes databases, seeds data, trains ML models, and starts both
Edge Server (Port 5001) and Cloud Analytics Server (Port 5000).
Sona College of Technology - Department of Information Technology (Batch 10)
"""

import os
import sys
import time
import threading
import webbrowser

# Add current directory to path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from backend.models import init_db
from backend.seed_data import seed_all
from backend.edge_server import app as edge_app, start_edge_background_sync
from backend.cloud_server import app as cloud_app


def run_edge():
    """Runs the Local Lab Edge Server on Port 5001."""
    start_edge_background_sync()
    edge_app.run(host="0.0.0.0", port=5001, debug=False, use_reloader=False, threaded=True)


def run_cloud():
    """Runs the Central Cloud Analytics Server on Port 5000."""
    cloud_app.run(host="0.0.0.0", port=5000, debug=False, use_reloader=False, threaded=True)


def main():
    print("=" * 70)
    print("   CLOUDLAB INTELLIGENCE: OFFLINE-FIRST EDGE-CLOUD PLATFORM")
    print("   SONA COLLEGE OF TECHNOLOGY - DEPT OF IT - BATCH 10 (2026-27)")
    print("=" * 70)

    # 1. Initialize databases
    print("\n[*] Initializing Edge and Cloud SQLite Databases...")
    init_db("cloud_storage.db", is_edge=False)
    init_db("edge_storage.db", is_edge=True)

    # 2. Seed initial data
    print("[*] Seeding laboratory workstations and student records...")
    seed_all()

    # 3. Start Edge Server in background daemon thread
    print("[*] Starting Local Lab Edge Server on http://127.0.0.1:5001...")
    edge_thread = threading.Thread(target=run_edge, daemon=True)
    edge_thread.start()

    # Wait 1 sec for edge to boot
    time.sleep(1)

    print("[*] Starting Central Cloud Analytics Backend on http://127.0.0.1:5000...")
    print("\n" + "=" * 70)
    print("   SYSTEM RUNNING AND READY FOR MONITORING & REPORTING")
    print("   - Admin Web Dashboard:       http://127.0.0.1:5000")
    print("   - Edge Node REST API:        http://127.0.0.1:5001")
    print("   - Live Lab Workstation Grid: http://127.0.0.1:5000")
    print("   - Student Portal:            http://127.0.0.1:5000 (Tab 6)")
    print("=" * 70 + "\n")

    # Optionally open browser
    try:
        webbrowser.open("http://127.0.0.1:5000")
    except Exception:
        pass

    # Run Cloud Server in main thread
    run_cloud()


if __name__ == "__main__":
    main()
