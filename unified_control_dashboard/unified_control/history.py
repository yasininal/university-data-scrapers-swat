import json
from pathlib import Path
from typing import List, Dict

from .models import RunResult


def load_history(history_file: Path) -> List[Dict]:
    if not history_file.exists():
        return []
    try:
        return json.loads(history_file.read_text(encoding="utf-8"))
    except Exception:
        return []


def append_history(history_file: Path, result: RunResult, max_items: int = 200) -> None:
    history_file.parent.mkdir(parents=True, exist_ok=True)
    items = load_history(history_file)
    items.insert(0, result.to_dict())
    items = items[:max_items]
    history_file.write_text(json.dumps(items, ensure_ascii=False, indent=2), encoding="utf-8")
