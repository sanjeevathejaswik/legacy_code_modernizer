import os
import json
from typing import Any

import config


def ensure_output_dirs() -> None:
    for sub in ("", "modules", "docs", "audit", "converted", "tests", "hitl", "build", "observability"):
        os.makedirs(os.path.join(config.OUTPUT_DIR, sub), exist_ok=True)


def save_json(data: Any, relative_path: str) -> str:
    path = os.path.join(config.OUTPUT_DIR, relative_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    return path


def save_text(content: str, relative_path: str) -> str:
    path = os.path.join(config.OUTPUT_DIR, relative_path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


def load_json(relative_path: str) -> Any:
    path = os.path.join(config.OUTPUT_DIR, relative_path)
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_source_code(file_path: str) -> str:
    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()
