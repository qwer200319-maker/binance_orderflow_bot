from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict


class JsonLineStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, payload: Dict[str, Any]) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False) + "\n")


class JsonStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, payload: Dict[str, Any]) -> None:
        with self.path.open("w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, ensure_ascii=False)

    def load(self, default: Dict[str, Any] | None = None) -> Dict[str, Any]:
        if not self.path.exists():
            return default or {}
        with self.path.open("r", encoding="utf-8") as f:
            return json.load(f)
