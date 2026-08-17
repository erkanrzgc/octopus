"""Rol-scoped subagent: route->SubAgent zinciri + scope-deny sonrasi self-correction."""
from agent.policy import LabPolicy
from agent.registry import ToolRegistry
from agent.subagent import SubAgent, run_task, SubAgentRun


class _RecExec:
    """Gercekten calisan araclari kaydeden sahte executor (scope garantisini test etmek icin)."""
    def __init__(self) -> None:
        self.ran: list[str] = []

    def run(self, tool: str, params: dict) -> str:
        self.ran.append(tool)
        return f"[mock {tool}]"


def test_run_task_routes_and_reports_role():
    run = run_task("komsu wifi WPA handshake yakala", lambda msgs: "cevap, arac yok")
    assert isinstance(run, SubAgentRun)
    assert run.role == "wireless"


def test_general_task_is_unscoped():
    run = run_task("bugun hava nasil", lambda msgs: "hava guzel")
    assert run.role == "general"
    assert SubAgent("general").registry.allowed is None


def test_scoped_subagent_self_corrects_after_scope_deny():
    # recon rolunde model ONCE yanlis (web=sqlmap) arac dener -> scope-deny -> SONRA dogru (nmap).
    # Garanti: executor rol-disi araci ASLA calistirmaz; rol-ici + kapsam-ici arac calisir.
    rec = _RecExec()
    reg = ToolRegistry.scoped("recon-scan", policy=LabPolicy(scope=["10.0.0.0/8"]), executor=rec)
    sub = SubAgent("recon-scan", registry=reg)
    calls = {"n": 0}

    def gen(messages):
        calls["n"] += 1
        if calls["n"] == 1:
            return '```arac\n{"arac":"sqlmap","parametreler":{"url":"http://10.0.0.1"}}\n```'
        if calls["n"] == 2:
            return '```arac\n{"arac":"nmap","parametreler":{"hedef":"10.0.0.1"}}\n```'
        return "tarama tamam."

    sub.run("portlari tara", gen, max_steps=5)
    assert "nmap" in rec.ran          # rol-ici + kapsam-ici -> executor CALISTIRDI
    assert "sqlmap" not in rec.ran    # rol-disi -> executor'a ulasmadan scope-deny
