from agent.registry import ToolRegistry
from agent.policy import LabPolicy
from agent.executor import MockExecutor
from agent.audit import AuditLog
from agent.catalog import extension_augmented_system_prompt, EXTENSION_TOOL_NAMES
from eval.extension_discovery_eval import (
    DiscoveryCase, evaluate_discovery, DISCOVERY_CASES, _report, DiscoveryResult, DiscoveryOutcome)


def _reg(tmp_path):
    return ToolRegistry(LabPolicy(scope=["10.10.10.0/24"]), MockExecutor(), AuditLog(tmp_path / "a.jsonl"))


def test_augmented_prompt_appends_manifest_without_altering_base():
    base = "TABAN SISTEM PROMPT"
    aug = extension_augmented_system_prompt(base)
    assert aug.startswith(base)        # taban birebir korunur (basa degil sona eklenir)
    assert aug != base
    for tool in ("trufflehog", "magika", "ghunt"):
        assert tool in aug             # 3 eklenti tanitilir
    assert "nmap" not in aug           # 117 egitilmis arac DOKULMEZ


def test_evaluate_discovery_counts_only_emission(tmp_path):
    # OFF model araci bilmez (duzyazi), ON model manifest sayesinde emit eder -> kesif kazanci.
    case = [DiscoveryCase("depoyu sizmis sir icin tara", "trufflehog")]

    def off_factory():
        return lambda msgs: "Bunun icin egitilmis bir aracim yok; elle incelemen gerekir."

    def on_factory():
        replies = iter(['```arac\n{"arac":"trufflehog","parametreler":{"hedef":"repo"}}\n```', "bitti"])
        return lambda msgs: next(replies)

    res = evaluate_discovery(off_factory, on_factory, case, lambda: _reg(tmp_path))
    assert res.called_off == 0 and res.called_on == 1
    assert res.outcomes[0].off_called is False and res.outcomes[0].on_called is True


def test_discovery_cases_target_real_extension_tools():
    # Her case'in beklenen araci gercekten bir EXTENSION aracidir (egitilmemis) -> olcum gecerli.
    for case in DISCOVERY_CASES:
        assert case.tool in EXTENSION_TOOL_NAMES
    assert len(DISCOVERY_CASES) == len(EXTENSION_TOOL_NAMES) == 3


def test_report_marks_discovery_gain():
    res = DiscoveryResult(total=1, called_off=0, called_on=1, outcomes=[
        DiscoveryOutcome(prompt="p", tool="trufflehog", off_called=False, on_called=True)])
    out = _report("octopus-test", res)
    assert "KESIF KAZANCI (ON - OFF): +1" in out
    assert "<== KESIF KAZANCI" in out
