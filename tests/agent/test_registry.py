from agent.registry import ToolRegistry
from agent.policy import LabPolicy
from agent.executor import MockExecutor
from agent.audit import AuditLog
from agent.toolcall import ToolCall


def _reg(tmp_path, scope=None, allow_high=False):
    return ToolRegistry(
        policy=LabPolicy(scope=scope or ["10.10.10.0/24"], allow_high=allow_high),
        executor=MockExecutor(),
        audit=AuditLog(tmp_path / "a.jsonl"),
    )


def test_invoke_in_scope_runs(tmp_path):
    out = _reg(tmp_path).invoke(ToolCall("nmap", {"hedef": "10.10.10.5", "secenekler": "-sV"}))
    assert "10.10.10.5" in out


def test_invoke_out_of_scope_returns_policy_reason(tmp_path):
    out = _reg(tmp_path).invoke(ToolCall("nmap", {"hedef": "8.8.8.8"}))
    assert "kapsam" in out.lower()


def test_invoke_unknown_tool(tmp_path):
    out = _reg(tmp_path).invoke(ToolCall("yok_boyle", {}))
    assert "bilinmeyen" in out.lower()


def test_high_risk_blocked_without_approval(tmp_path):
    out = _reg(tmp_path).invoke(ToolCall("msfvenom", {"secenekler": "-p x"}))
    assert "onay" in out.lower()
