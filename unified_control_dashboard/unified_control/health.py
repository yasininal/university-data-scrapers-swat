import importlib
import socket
from pathlib import Path
from typing import Dict, List


def port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        return s.connect_ex((host, port)) == 0


def check_modules(modules: List[str]) -> Dict[str, bool]:
    result: Dict[str, bool] = {}
    for mod in modules:
        try:
            importlib.import_module(mod)
            result[mod] = True
        except Exception:
            result[mod] = False
    return result


def check_paths(base: Path, required_paths: List[str]) -> Dict[str, bool]:
    return {p: (base / p).exists() for p in required_paths}
