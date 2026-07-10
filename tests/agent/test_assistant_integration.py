from agent.audit import AuditLog
from agent.backends.assistant_executor import AssistantExecutor
from agent.composite_executor import CompositeExecutor
from agent.executor import MockExecutor
from agent.policy import LabPolicy
from agent.registry import ToolRegistry
from agent.toolcall import ToolCall


def _registry(tmp_path):
    pol = LabPolicy(scope=["10.0.0.0/24"], workspace_root=str(tmp_path), allow_high=False)
    execu = CompositeExecutor(security=MockExecutor(), assistant=AssistantExecutor(str(tmp_path)))
    return ToolRegistry(pol, execu, AuditLog.default())


def test_write_file_end_to_end(tmp_path):
    reg = _registry(tmp_path)
    out = reg.invoke(ToolCall(name="write_file", params={"yol": "a.txt", "icerik": "veri"}))
    assert "yazildi" in out
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "veri"


def test_traversal_denied_never_writes(tmp_path):
    reg = _registry(tmp_path)
    out = reg.invoke(ToolCall(name="write_file", params={"yol": "../evil.txt", "icerik": "x"}))
    assert "REDDEDILDI" in out
    assert not (tmp_path.parent / "evil.txt").exists()   # diske hic dokunmadi


def test_run_cmd_needs_approval(tmp_path):
    reg = _registry(tmp_path)
    out = reg.invoke(ToolCall(name="run_cmd", params={"komut": "ls -la"}))
    assert "ONAY GEREKLI" in out
