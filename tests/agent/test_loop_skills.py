from agent.loop import run_tool_loop
from agent.messages import Message
from agent.registry import ToolRegistry
from agent.policy import LabPolicy
from agent.executor import MockExecutor
from agent.audit import AuditLog
from agent.skills import SkillLibrary, Skill


def _reg(tmp_path):
    return ToolRegistry(LabPolicy(scope=["10.10.10.0/24"]), MockExecutor(), AuditLog(tmp_path / "a.jsonl"))


def _lib_with_nmap():
    return SkillLibrary(tools={
        "nmap": Skill(name="nmap", description="port tarayici",
                      body="Kanonik: -sV -Pn. Tuzak: -sS root ister.",
                      kind="tool", tool="nmap", path="mem")
    })


def test_new_tool_triggers_injection_then_executes(tmp_path):
    # 1. tur: eksik/ham nmap cagrisi -> harness skill enjekte eder, regenerate
    # 2. tur: model duzeltilmis cagriyi verir -> execute
    # 3. tur: duz cevap
    replies = iter([
        '```arac\n{"arac":"nmap","parametreler":{"hedef":"10.10.10.5"}}\n```',
        '```arac\n{"arac":"nmap","parametreler":{"hedef":"10.10.10.5","secenekler":"-sV -Pn"}}\n```',
        "Tarama bitti.",
    ])
    seen = {}
    def generate(msgs):
        # ikinci uretimden once skill enjekte edilmis olmali (user turu)
        seen["last_user_has_skill"] = any(
            m.role == "user" and "ARAÇ KILAVUZU" in m.content for m in msgs)
        return next(replies)
    res = run_tool_loop([Message("user", "tara")], generate, _reg(tmp_path),
                        skills=_lib_with_nmap())
    # araç 1 kez calisti (duzeltilmis cagri), enjeksiyon 1 kez oldu
    assert len(res.calls) == 1
    assert res.calls[0].params.get("secenekler") == "-sV -Pn"
    assert "bitti" in res.final
    # enjeksiyon mesaji transcript'te var
    # (seen: 2. uretim sirasinda skill zaten eklenmisti)


def test_injection_is_user_role_and_once_per_tool(tmp_path):
    # ayni araci iki tur ust uste cagirsa bile enjeksiyon 1 kez
    replies = iter([
        '```arac\n{"arac":"nmap","parametreler":{"hedef":"10.10.10.5"}}\n```',
        '```arac\n{"arac":"nmap","parametreler":{"hedef":"10.10.10.5","secenekler":"-sV"}}\n```',
        '```arac\n{"arac":"nmap","parametreler":{"hedef":"10.10.10.6","secenekler":"-sV"}}\n```',
        "bitti",
    ])
    captured = {"msgs": None}
    def generate(msgs):
        captured["msgs"] = list(msgs)
        return next(replies)
    res = run_tool_loop([Message("user", "tara")], generate, _reg(tmp_path),
                        skills=_lib_with_nmap(), max_steps=10)
    injections = [m for m in captured["msgs"] if m.role == "user" and "ARAÇ KILAVUZU" in m.content]
    assert len(injections) == 1                 # cache: bir kez
    assert len(res.calls) == 2                  # iki gercek nmap turu calisti


def test_fallback_runs_original_when_model_drops_call_after_injection(tmp_path):
    # v81 davranisi: model GECERLI cagriyi verir; skill enjekte edilince cagriyi YENIDEN
    # yazmaz, duzyaziya duser -> ertelenen orijinal cagri KAYBOLMAMALI (FALLBACK calistirir).
    # Mekanizma monoton: skill ACIK, OFF'tan kotu OLAMAZ.
    replies = iter([
        '```arac\n{"arac":"nmap","parametreler":{"hedef":"10.10.10.5","secenekler":"-sV -Pn"}}\n```',
        "Tamam, kilavuzu okudum; komut zaten dogru.",   # arac YOK -> re-emit basarisiz
    ])
    res = run_tool_loop([Message("user", "tara")], lambda m: next(replies), _reg(tmp_path),
                        skills=_lib_with_nmap())
    assert len(res.calls) == 1                                   # orijinal cagri fallback ile calisti
    assert res.calls[0].params.get("secenekler") == "-sV -Pn"


def test_fallback_not_triggered_when_correction_succeeds(tmp_path):
    # Model duzeltilmis cagriyi YENIDEN uretirse fallback DEVREYE GIRMEZ, cift-calisma OLMAZ:
    # yalniz duzeltilmis cagri calisir (orijinal ham cagri degil).
    replies = iter([
        '```arac\n{"arac":"nmap","parametreler":{"hedef":"10.10.10.5"}}\n```',           # ham
        '```arac\n{"arac":"nmap","parametreler":{"hedef":"10.10.10.5","secenekler":"-sV -Pn"}}\n```',
        "bitti",
    ])
    res = run_tool_loop([Message("user", "tara")], lambda m: next(replies), _reg(tmp_path),
                        skills=_lib_with_nmap())
    assert len(res.calls) == 1                                   # cift degil, tek
    assert res.calls[0].params.get("secenekler") == "-sV -Pn"   # duzeltilmis olan


def test_no_skill_for_tool_executes_normally(tmp_path):
    # skill kutuphanesi bos -> davranis eskisi gibi (enjeksiyon yok)
    replies = iter([
        '```arac\n{"arac":"nmap","parametreler":{"hedef":"10.10.10.5","secenekler":"-sV"}}\n```',
        "bitti",
    ])
    res = run_tool_loop([Message("user", "tara")], lambda m: next(replies), _reg(tmp_path),
                        skills=SkillLibrary())
    assert len(res.calls) == 1 and "bitti" in res.final
