"""Sohbet mesaji: rol + icerik. Roller: system|user|assistant|tool."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}

    @classmethod
    def from_dict(cls, d: dict[str, str]) -> "Message":
        return cls(role=str(d["role"]), content=str(d["content"]))
