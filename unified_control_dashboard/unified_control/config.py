from pathlib import Path
import sys

DASHBOARD_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = DASHBOARD_ROOT / "project"
DATA_DIR = DASHBOARD_ROOT / "data"
HISTORY_FILE = DATA_DIR / "run_history.json"

VENV_LOCAL = DASHBOARD_ROOT / ".venv" / "bin" / "python"
VENV_PARENT = DASHBOARD_ROOT.parent / ".venv" / "bin" / "python"
if VENV_LOCAL.exists():
	PYTHON_EXECUTABLE = str(VENV_LOCAL)
elif VENV_PARENT.exists():
	PYTHON_EXECUTABLE = str(VENV_PARENT)
else:
	PYTHON_EXECUTABLE = str(Path(sys.executable))

RUN_TIMEOUT_SECONDS = 3600
HISTORY_LIMIT = 200
