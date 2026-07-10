"""Domaine gore yonlendiren executor: asistan araclari -> AssistantExecutor;
diger (guvenlik) araclari -> secili guvenlik executor'i (Mock/Real/Docker).
Executor Protocol'unu uygular; asla firlatmaz."""
from __future__ import annotations

from agent.catalog import get_spec
from agent.executor import Executor


class CompositeExecutor:
    def __init__(self, security: Executor, assistant: Executor) -> None:
        self.security = security
        self.assistant = assistant

    def run(self, tool: str, params: dict) -> str:
        spec = get_spec(tool)
        if spec is None:
            return f"HATA: bilinmeyen arac '{tool}'"
        if spec.domain == "asistan":
            return self.assistant.run(tool, params)
        return self.security.run(tool, params)
