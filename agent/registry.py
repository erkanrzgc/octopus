"""Katalog + policy + executor + audit'i baglar. invoke(): yetki kontrol -> calistir -> logla.
Asla exception firlatmaz; hatayi metin olarak modele geri dondurur (dongu olmesin)."""
from __future__ import annotations
from dataclasses import dataclass
from agent.audit import AuditLog
from agent.catalog import CATALOG, get_spec
from agent.executor import Executor, MockExecutor
from agent.policy import LabPolicy
from agent.toolcall import ToolCall


@dataclass
class ToolRegistry:
    policy: LabPolicy
    executor: Executor
    audit: AuditLog

    @classmethod
    def default(cls) -> "ToolRegistry":
        return cls(LabPolicy.default(), MockExecutor(), AuditLog.default())

    def tool_names(self) -> list[str]:
        return list(CATALOG)

    def invoke(self, call: ToolCall) -> str:
        self.audit.write("tool.start", f"{call.name} {call.params}")
        spec = get_spec(call.name)
        if spec is None:
            msg = f"HATA: bilinmeyen arac '{call.name}'"
            self.audit.write("tool.error", msg)
            return msg
        decision = self.policy.decide(spec, call.params)
        if not decision.allowed:
            kind = "tool.policy.approval" if decision.requires_approval else "tool.policy.deny"
            self.audit.write(kind, decision.reason)
            prefix = "ONAY GEREKLI" if decision.requires_approval else "REDDEDILDI"
            return f"{prefix}: {decision.reason}"
        try:
            out = self.executor.run(call.name, call.params)
        except Exception as exc:  # noqa: BLE001 - modele bildir, cokme
            out = f"HATA: {type(exc).__name__}: {exc}"
        self.audit.write("tool.done", f"{call.name} -> {out[:80]}")
        return out
