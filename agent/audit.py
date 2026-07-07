"""Denetim gunlugu: her arac cagrisi jsonl'e (event, detail, zaman)."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path


@dataclass
class AuditLog:
    path: Path

    @classmethod
    def default(cls) -> "AuditLog":
        return cls(Path("lab") / "logs" / "audit.jsonl")

    def write(self, event: str, detail: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        rec = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, "detail": detail}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
