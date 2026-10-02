"""
JagatData — Single entry point.

Run this from the JagatData folder:
    python main.py

This starts BOTH:
  - FastAPI backend  →  http://127.0.0.1:8000   (+ Swagger at /docs)
  - Streamlit dashboard →  http://127.0.0.1:8501

Press Ctrl+C to stop everything.
"""
import os
import sys
import subprocess
import threading
import time
import webbrowser

# ── Make sure we're running from the right folder ─────────────────────────────
HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)
if HERE not in sys.path:
    sys.path.insert(0, HERE)

def print_banner():
    print()
    print("=" * 65)
    print("  🏛️  JagatData — Connecting Government Systems")
    print("       Simplifying Public Services  |  SIH 2026")
    print("=" * 65)
    print()


def main():
    print_banner()

    # ── 1. Start Streamlit dashboard in a background subprocess ───────────────────
    DASHBOARD = os.path.join(HERE, "streamlit_app", "app.py")

    streamlit_proc = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", DASHBOARD,
         "--server.port", "8501",
         "--server.headless", "true",
         "--browser.gatherUsageStats", "false"],
        cwd=HERE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    # ── 2. Open browser after backend is up ───────────────────────────────────────
    def open_browser():
        time.sleep(4)           # wait for both services to be ready
        print("  ✅ Backend   →  http://127.0.0.1:8000")
        print("  ✅ Dashboard →  http://127.0.0.1:8501  (opening in browser...)")
        print("  ✅ API Docs  →  http://127.0.0.1:8000/docs")
        print()
        print("  Demo login:  admin / admin123")
        print()
        print("  Press Ctrl+C to stop everything.")
        print()
        webbrowser.open("http://127.0.0.1:8501")

    threading.Thread(target=open_browser, daemon=True).start()

    # ── 3. Run FastAPI/Uvicorn in the main thread (Ctrl+C stops it) ───────────────
    try:
        import uvicorn
        from backend.main import app
        uvicorn.run(app, host="127.0.0.1", port=8000, reload=False)
    except KeyboardInterrupt:
        pass
    finally:
        print("\n  Shutting down JagatData...")
        streamlit_proc.terminate()
        try:
            streamlit_proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            streamlit_proc.kill()
        print("  Goodbye! 👋\n")


if __name__ == "__main__":
    main()
