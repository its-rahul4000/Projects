"""
Cybersecurity Log Intelligence System - Entry Point
Run with:  python main.py
"""
# Launches the Streamlit CLI with a fixed argv and shell=False; no user input.
import subprocess  # nosec B404
import sys
import os
from pathlib import Path


def main():
    root = Path(__file__).resolve().parent
    app_file = root / "app.py"

    if not app_file.exists():
        print(f"ERROR: app.py not found at {app_file}", file=sys.stderr)
        sys.exit(1)

    print("=" * 60)
    print("  Cybersecurity Log Intelligence System")
    print("  Starting on http://localhost:8501")
    print("=" * 60)

    cmd = [
        sys.executable, "-m", "streamlit", "run",
        str(app_file),
        "--server.port=8501",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        "--server.maxUploadSize=5000",
    ]

    try:
        # Fixed argv built from sys.executable; shell=False; no user input.
        subprocess.run(cmd, cwd=str(root))  # nosec
    except KeyboardInterrupt:
        print("\nShutting down.")
        sys.exit(0)


if __name__ == "__main__":
    main()
