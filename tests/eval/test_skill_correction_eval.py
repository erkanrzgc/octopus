from agent.registry import ToolRegistry
from agent.policy import LabPolicy
from agent.executor import MockExecutor
from agent.audit import AuditLog
from agent.skills import SkillLibrary, Skill
from eval.skill_correction_eval import (
    evaluate, Case, has_only_known_flags, FABRICATION_CASES, _report)


def _reg(tmp_path):
    return ToolRegistry(LabPolicy(scope=["10.10.10.0/24"]), MockExecutor(), AuditLog(tmp_path / "a.jsonl"))


def _lib():
    return SkillLibrary(tools={
        "nmap": Skill(name="nmap", description="port", body="gecerli flag: -sV -Pn -p-",
                      kind="tool", tool="nmap", path="mem")})


def test_has_only_known_flags_detects_fabricated():
    assert has_only_known_flags("nmap", "-sV -Pn") is True
    assert has_only_known_flags("nmap", "--turbo-mode") is False   # uydurma


def test_skills_on_fixes_fabricated_flag(tmp_path):
    # Ayni model: skill KAPALIYKEN uydurma flag; skill ACIKKEN duzeltir.
    def make_gen():
        # skill enjekte edilirse (user'da 'gecerli flag' gorurse) duzelt, yoksa uydur
        state = {"n": 0}
        def gen(msgs):
            state["n"] += 1
            saw_skill = any(m.role == "user" and "gecerli flag" in m.content for m in msgs)
            if state["n"] == 1 and not saw_skill:
                return '```arac\n{"arac":"nmap","parametreler":{"hedef":"10.10.10.5","secenekler":"--turbo-mode"}}\n```'
            if saw_skill:
                return '```arac\n{"arac":"nmap","parametreler":{"hedef":"10.10.10.5","secenekler":"-sV"}}\n```'
            return "bitti"
        return gen

    cases = [Case(prompt="10.10.10.5 tara", tool="nmap")]
    off = evaluate(make_gen, cases, _reg(tmp_path), skills=None)
    on = evaluate(make_gen, cases, _reg(tmp_path), skills=_lib())
    assert off.valid_flags_after == 0      # skill yok -> uydurma flag kaldi
    assert on.valid_flags_after == 1       # skill var -> duzeldi
    # per-case detay dogru dolduruluyor: OFF cagirdi ama gecersiz, ON gecerli
    assert off.outcomes[0].called is True and off.outcomes[0].valid is False
    assert on.outcomes[0].valid is True and on.outcomes[0].secenekler == "-sV"


# Her fabrication case'in KANONIK (dogru) cevabi. Eval GECERLILIGI: bu cevaplar allow-list
# icinde OLMALI, yoksa dogru cevap yanlislikla 'uydurma' sayilir ve ON'un duzeltmesi olculemez.
_CANONICAL_ANSWERS = {
    "nmap": "-p 21,22,80 -sV -O -Pn",
    "gobuster": "dir -x php,txt -t 50",
    "sqlmap": "--dbs --batch --level=5 --risk=3",
    "hydra": "-l admin -P rockyou.txt -t 4 ssh",
    "ffuf": "-fc 404 -t 40",
    "nikto": "-ssl -o out.html -Format htm",
}


def test_fabrication_cases_have_allowlisted_canonical_answers():
    # Her case'in dogru cevabi has_only_known_flags'ten GECMELI (allow-list superkume).
    for case in FABRICATION_CASES:
        canonical = _CANONICAL_ANSWERS[case.tool]
        assert has_only_known_flags(case.tool, canonical) is True, \
            f"{case.tool} kanonik cevabi allow-list disinda: {canonical}"


def test_fabrication_cases_cover_distinct_tools():
    tools = [c.tool for c in FABRICATION_CASES]
    assert len(tools) == len(set(tools)) >= 6   # her arac bir kez, en az 6 farkli arac


def test_report_flags_skill_correction():
    # Sahte OFF/ON sonucuyla _report ciktisini dogrula: duzeltilen case isaretlenir.
    from eval.skill_correction_eval import EvalResult, CaseOutcome
    off = EvalResult(total=1, valid_flags_before=0, valid_flags_after=0, outcomes=[
        CaseOutcome(prompt="p", tool="nmap", secenekler="--turbo", called=True, valid=False)])
    on = EvalResult(total=1, valid_flags_before=1, valid_flags_after=1, outcomes=[
        CaseOutcome(prompt="p", tool="nmap", secenekler="-sV", called=True, valid=True)])
    out = _report("octopus-test", off, on)
    assert "SKILL DUZELTTI" in out
    assert "NET (ON - OFF): +1" in out
