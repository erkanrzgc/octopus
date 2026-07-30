from agent.registry import ToolRegistry
from agent.policy import LabPolicy
from agent.executor import MockExecutor
from agent.audit import AuditLog
from agent.skills import SkillLibrary, Skill
from eval.skill_correction_eval import evaluate, Case, has_only_known_flags


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
