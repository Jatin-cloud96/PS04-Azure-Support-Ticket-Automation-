"""
Script to launch the PS03 Invoice Processing Web Dashboard.
Ensures Azurite is running and opens http://localhost:8000 in your browser.
"""

import sys
import time
import webbrowser
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import uvicorn
from scripts.run_local_demo import ensure_azurite_running


def main():
    print("=" * 80)
    print("  PS03 INVOICE PROCESSING PIPELINE - INTERACTIVE WEB DASHBOARD")
    print("=" * 80)
    
    # 1. Ensure Azurite is active
    ensure_azurite_running()

    print("\n[Server] Starting FastAPI Web Server at http://127.0.0.1:8000 ...")
    print("[Server] Press Ctrl+C to stop the dashboard.\n")

    # Open browser after a slight delay
    def open_browser():
        time.sleep(1.5)
        webbrowser.open("http://127.0.0.1:8000")

    import threading
    threading.Thread(target=open_browser, daemon=True).start()

    uvicorn.run("src.ui.app:app", host="127.0.0.1", port=8000, log_level="info")


if __name__ == "__main__":
    main()
