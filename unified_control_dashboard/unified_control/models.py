from dataclasses import dataclass, asdict, field
from datetime import datetime
from pathlib import Path
from typing import List


@dataclass
class ScraperJob:
    id: str
    name: str
    category: str
    description: str
    command: List[str]
    cwd: Path
    expected_outputs: List[str]
    dependencies: List[str] = field(default_factory=list)


@dataclass
class RunResult:
    job_id: str
    job_name: str
    success: bool
    exit_code: int
    started_at: str
    finished_at: str
    duration_seconds: float
    stdout: str
    stderr: str

    def to_dict(self) -> dict:
        return asdict(self)

    @staticmethod
    def now_iso() -> str:
        return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
