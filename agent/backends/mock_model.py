"""Scripted model backend: onceden verilen yanitlari sirayla dondurur (test + demo).
Gercek model (GGUF/HF) Faz 2'de ayni __call__(messages)->str arayuzune takilir."""
from __future__ import annotations
from agent.messages import Message

_DEFAULT = "Ben Octópus. Baska bir sey ekleyemiyorum (mock)."


class ScriptedModel:
    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self._i = 0

    def __call__(self, messages: list[Message]) -> str:
        if self._i < len(self._replies):
            r = self._replies[self._i]
            self._i += 1
            return r
        return _DEFAULT
