import subprocess
import time
from datetime import datetime

from .models import ScraperJob, RunResult


def run_job(job: ScraperJob, timeout_seconds: int) -> RunResult:
    started = datetime.utcnow()
    t0 = time.time()

    try:
        completed = subprocess.run(
            job.command,
            cwd=str(job.cwd),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
        success = completed.returncode == 0
        stdout = completed.stdout or ""
        stderr = completed.stderr or ""
        exit_code = completed.returncode
    except subprocess.TimeoutExpired as exc:
        success = False
        stdout = (exc.stdout.decode("utf-8", errors="ignore") if isinstance(exc.stdout, bytes) else (exc.stdout or ""))
        stderr = (exc.stderr.decode("utf-8", errors="ignore") if isinstance(exc.stderr, bytes) else (exc.stderr or ""))
        stderr = (stderr + "\n\nProcess timed out.").strip()
        exit_code = 124
    except Exception as exc:
        success = False
        stdout = ""
        stderr = f"Unexpected runner error: {exc}"
        exit_code = 1

    finished = datetime.utcnow()
    return RunResult(
        job_id=job.id,
        job_name=job.name,
        success=success,
        exit_code=exit_code,
        started_at=started.replace(microsecond=0).isoformat() + "Z",
        finished_at=finished.replace(microsecond=0).isoformat() + "Z",
        duration_seconds=round(time.time() - t0, 2),
        stdout=stdout[-12000:],
        stderr=stderr[-12000:],
    )
