"""
Cybersecurity Log Intelligence System - Entry Point
Run with:  python main.py
"""
import subprocess
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
        "--server.maxUploadSize=50",
    ]

    try:
        subprocess.run(cmd, cwd=str(root))
    except KeyboardInterrupt:
        print("\nShutting down.")
        sys.exit(0)


if __name__ == "__main__":
    main()
