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
