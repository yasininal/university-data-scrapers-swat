import subprocess
import sys
import os
from pathlib import Path

def run_command(command, cwd=None):
    print(f"Running: {' '.join(command)} (cwd: {cwd})")
    try:
        subprocess.check_call(command, cwd=cwd)
    except subprocess.CalledProcessError as e:
        print(f"Error running command: {e}")
        return False
    return True

def main():
    root_dir = Path(__file__).resolve().parent
    requirements_file = root_dir / "requirements.txt"
    
    print("--- SWAT Project Setup ---")
    
    # 1. Install requirements
    if requirements_file.exists():
        print("Installing requirements...")
        run_command([sys.executable, "-m", "pip", "install", "-r", str(requirements_file)])
    else:
        print(f"Requirements file not found at {requirements_file}")

    # 2. Install Playwright browsers
    print("Installing Playwright browsers...")
    run_command([sys.executable, "-m", "playwright", "install", "chromium"])

    # 3. Initialize Grant Database
    grant_db_init = root_dir / "unified_control_dashboard" / "project" / "hibe" / "backend" / "init_db.py"
    if grant_db_init.exists():
        print("Initializing Grant database...")
        # Change directory to hibe/backend to run init_db.py correctly if needed
        # But actually init_db.py might be designed to run from root or its own dir.
        # Let's check init_db.py logic.
        cwd = grant_db_init.parent
        run_command([sys.executable, "init_db.py"], cwd=str(cwd))
    
    print("--- Setup Complete ---")

if __name__ == "__main__":
    main()
