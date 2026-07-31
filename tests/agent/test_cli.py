import sys

import agent.cli as cli
from agent.cli import run_demo


def test_demo_runs_end_to_end():
    transcript = run_demo(scope=["10.10.10.0/24"])
    assert "nmap" in transcript
    assert "ARAÇ ÇIKTISI" in transcript or "10.10.10.5" in transcript
    assert transcript.strip().endswith("(demo bitti)")


def test_main_routes_gguf(monkeypatch, capsys):
    called: dict = {}

    def _fake(scope, model="octopus-v7"):
        called["args"] = (scope, model)
        return "GGUF_DEMO_OUT"

    monkeypatch.setattr(cli, "run_gguf_demo", _fake)
    monkeypatch.setattr(sys, "argv", ["prog", "--gguf"])
    cli.main()
    out = capsys.readouterr().out
    assert "GGUF_DEMO_OUT" in out
    assert called["args"][1] == "octopus-v7"


def test_docker_container_ip_rejects_injection(monkeypatch):
    """Enjeksiyon kapisi: gecersiz/kotucul container adi hic komut kurmadan None doner."""
    import subprocess
    called: dict = {}

    def _boom(*a, **k):
        called["ran"] = True
        raise AssertionError("subprocess kotucul adla CAGRILMAMALI")

    monkeypatch.setattr(subprocess, "run", _boom)
    assert cli._docker_container_ip("octopus-target; rm -rf /") is None
    assert cli._docker_container_ip("$(whoami)") is None
    assert cli._docker_container_ip("a b") is None
    assert "ran" not in called                            # subprocess'e hic gidilmedi


def test_gguf_demo_activates_skills_by_default(monkeypatch):
    """Canlı beyin yolu skill katmanini VARSAYILAN olarak yukler (dormant DEGIL)."""
    import agent.backends.gguf_model as gm
    from agent.loop import ToolLoopResult
    from agent.skills import SkillLibrary
    captured: dict = {}

    monkeypatch.setattr(gm, "GgufModel", lambda **k: (lambda msgs: "cevap"))

    def _fake_loop(msgs, gen, registry, *, max_steps=10, skills=None):
        captured["skills"] = skills
        return ToolLoopResult(final="ok", steps=1, calls=[])

    monkeypatch.setattr(cli, "run_tool_loop", _fake_loop)
    cli.run_gguf_demo(scope=["10.10.10.0/24"])
    assert isinstance(captured["skills"], SkillLibrary)
    assert captured["skills"].tools                        # 13 arac-skill yuklendi


def test_gguf_demo_skills_can_be_disabled(monkeypatch):
    """Testler/hiz icin skills=None ile acikca kapatilabilir (geriye-uyum)."""
    import agent.backends.gguf_model as gm
    from agent.loop import ToolLoopResult
    captured: dict = {}

    monkeypatch.setattr(gm, "GgufModel", lambda **k: (lambda msgs: "cevap"))

    def _fake_loop(msgs, gen, registry, *, max_steps=10, skills=None):
        captured["skills"] = skills
        return ToolLoopResult(final="ok", steps=1, calls=[])

    monkeypatch.setattr(cli, "run_tool_loop", _fake_loop)
    cli.run_gguf_demo(scope=["10.10.10.0/24"], skills=None)
    assert captured["skills"] is None


def test_main_routes_gguf_docker_combo(monkeypatch, capsys):
    """--gguf --docker birlikte -> gercek beyin + gercek docker eli uctan uca."""
    called: dict = {}

    def _fake(scope, model="octopus-v7", target="octopus-target"):
        called["args"] = (scope, model, target)
        return "GGUF_DOCKER_OUT"

    monkeypatch.setattr(cli, "run_gguf_docker_demo", _fake)
    monkeypatch.setattr(sys, "argv", ["prog", "--gguf", "--docker"])
    cli.main()
    out = capsys.readouterr().out
    assert "GGUF_DOCKER_OUT" in out
    assert called["args"][1] == "octopus-v7"
