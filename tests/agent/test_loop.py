from agent.loop import run_tool_loop, ToolLoopResult
from agent.messages import Message
from agent.registry import ToolRegistry
from agent.policy import LabPolicy
from agent.executor import MockExecutor
from agent.audit import AuditLog


def _reg(tmp_path):
    return ToolRegistry(LabPolicy(scope=["10.10.10.0/24"]), MockExecutor(), AuditLog(tmp_path / "a.jsonl"))


def test_single_tool_then_final(tmp_path):
    # scripted model: 1. tur arac cagirir, 2. tur duz cevap
    scripted = iter([
        '```arac\n{"arac":"nmap","parametreler":{"hedef":"10.10.10.5","secenekler":"-sV"}}\n```',
        "Tarama bitti: 3 acik port var.",
    ])
    def generate(msgs): return next(scripted)
    res = run_tool_loop([Message("user", "tara")], generate, _reg(tmp_path))
    assert isinstance(res, ToolLoopResult)
    assert res.steps == 2 and "3 acik port" in res.final
    assert len(res.calls) == 1


def test_plain_answer_no_tools(tmp_path):
    res = run_tool_loop([Message("user", "selam")], lambda m: "Merhaba, ben Octópus.", _reg(tmp_path))
    assert res.steps == 1 and "Octópus" in res.final and res.calls == []


def test_max_steps_guard(tmp_path):
    # her turda arac cagiran sonsuz model -> max_steps'te durur
    call = '```arac\n{"arac":"nmap","parametreler":{"hedef":"10.10.10.5"}}\n```'
    res = run_tool_loop([Message("user", "x")], lambda m: call, _reg(tmp_path), max_steps=3)
    assert res.steps == 3
