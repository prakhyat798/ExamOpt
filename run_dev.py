"""
ExamOpt — Root Development Runner
Starts the FastAPI Backend and optionally the Vite Frontend development server.
"""

import sys
import subprocess
import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BACKEND_DIR = ROOT_DIR / "backend"
FRONTEND_DIR = ROOT_DIR / "frontend"
VENV_PYTHON = BACKEND_DIR / ".venv" / "Scripts" / "python.exe"

if not VENV_PYTHON.exists():
    VENV_PYTHON = Path(sys.executable)


def main():
    print("=" * 65)
    print(" ExamOpt: Intelligent Examination Timetable Optimization System")
    print(" GLA University Context — CSED Block AB-XI")
    print("=" * 65)
    print(f"[+] Root Directory: {ROOT_DIR}")
    print(f"[+] Backend Directory: {BACKEND_DIR}")
    print(f"[+] Python Executable: {VENV_PYTHON}")

    # Check if database exists, if not generate it
    db_file = BACKEND_DIR / "examopt.db"
    if not db_file.exists():
        print("[!] Local database not found. Generating synthetic seeds...")
        subprocess.run([str(VENV_PYTHON), str(BACKEND_DIR / "seed_generator.py")], check=True)

    print("\n[+] Launching FastAPI Unified Application on http://localhost:8000 ...")
    print("    - Web & Mobile PWA App: http://localhost:8000/")
    print("    - Interactive API Docs: http://localhost:8000/docs")
    print("    - Health Check:         http://localhost:8000/health\n")

    env = os.environ.copy()
    env["PYTHONPATH"] = str(BACKEND_DIR)

    try:
        subprocess.run(
            [str(VENV_PYTHON), "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"],
            cwd=str(BACKEND_DIR),
            env=env
        )
    except KeyboardInterrupt:
        print("\n[+] ExamOpt server stopped gracefully.")


if __name__ == "__main__":
    main()
