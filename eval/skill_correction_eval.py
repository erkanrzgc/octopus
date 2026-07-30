"""Skill katmani etkisini olc: FINAL calisan arac cagrisi UYDURMA flag iceriyor mu?
skill KAPALI vs ACIK. Gercek model (GgufModel) veya scripted 'generate' ile calisir.
proxy metrik: 'gecerli-flag' orani = uydurma-flag'in tersi."""
from __future__ import annotations

from dataclasses import dataclass

from agent.loop import run_tool_loop
from agent.messages import Message
from agent.registry import ToolRegistry
from agent.skills import SkillLibrary

# Pilot araclar icin kucuk kanonik flag allow-list'i (uydurma tespiti icin; tam liste degil).
_KNOWN_FLAGS: dict[str, set[str]] = {
    "nmap": {"-sV", "-sC", "-A", "-O", "-Pn", "-p-", "-p", "-T4", "-sS", "-sT", "-sU",
             "--top-ports", "-oN", "-oX", "--script"},
    "masscan": {"-p", "--rate", "-oL", "-oJ", "-oX", "--banners"},
    "gobuster": {"dir", "dns", "vhost", "-u", "-w", "-x", "-t", "-d", "-s", "-b"},
    "ffuf": {"-w", "-u", "-X", "-d", "-mc", "-fc", "-fs", "-t", "-H"},
    "sqlmap": {"--batch", "--level", "--risk", "-r", "-p", "-u", "--dbs", "--tables",
               "--columns", "--dump", "--current-user", "--is-dba", "--os-shell"},
    "nikto": {"-h", "-ssl", "-p", "-Tuning", "-o", "-Format", "-useproxy"},
    "nuclei": {"-u", "-l", "-t", "-tags", "-severity", "-rl", "-o", "-update-templates"},
    "metasploit": {"use", "set", "run", "exploit", "search", "show", "check",
                   "sessions", "background", "RHOSTS", "LHOST", "PAYLOAD", "SESSION"},
    "netexec": {"smb", "winrm", "ldap", "mssql", "ssh", "-u", "-p", "-H", "--local-auth",
                "--shares", "--sam", "--lsa", "-x", "--continue-on-success"},
    "hydra": {"-l", "-L", "-p", "-P", "-t", "-f", "-o", "-s",
              "ssh", "ftp", "rdp", "http-post-form", "http-get-form"},
    "trufflehog": {"git", "github", "s3", "filesystem", "docker",
                   "--results", "--json", "--fail", "--only-verified", "--org", "--image"},
    "magika": {"-r", "--json", "--mime-type", "-s"},
    "ghunt": {"email", "gaia", "drive", "geolocate", "spiderdal", "login", "--json"},
}


def known_flags(tool: str) -> set[str]:
    return _KNOWN_FLAGS.get(tool, set())


def has_only_known_flags(tool: str, secenekler: str) -> bool:
    """secenekler icindeki her '-' ile baslayan token bilinen flag mi? Bilinen yoksa True (skorlama)."""
    allow = known_flags(tool)
    if not allow:
        return True
    tokens = [t for t in (secenekler or "").split() if t.startswith("-")]
    return all(t.split("=", 1)[0] in allow for t in tokens)


@dataclass(frozen=True)
class Case:
    prompt: str
    tool: str


@dataclass
class EvalResult:
    total: int
    valid_flags_before: int   # (ayrilmis: ilk cagri) — bu surumde final ile ayni cerceve
    valid_flags_after: int    # FINAL calisan cagrida uydurma-flag yok


def _last_call_for(tool: str, calls) -> object | None:
    for c in reversed(calls):
        if c.name == tool:
            return c
    return None


def evaluate(generate_factory, cases: list[Case], registry: ToolRegistry,
             skills: SkillLibrary | None) -> EvalResult:
    """generate_factory: her case icin taze bir generate callable dondurur (durum sizmasin)."""
    valid_after = 0
    for case in cases:
        gen = generate_factory()
        msgs = [Message("user", case.prompt)]
        res = run_tool_loop(msgs, gen, registry, skills=skills)
        call = _last_call_for(case.tool, res.calls)
        if call is not None and has_only_known_flags(case.tool, str(call.params.get("secenekler", ""))):
            valid_after += 1
    return EvalResult(total=len(cases), valid_flags_before=valid_after, valid_flags_after=valid_after)


def run_against_ollama(model: str = "octopus-v9", scope: list[str] | None = None) -> str:
    """GERCEK model ile skill OFF vs ON karsilastirmasi. Ollama+GGUF gerektirir.
    Kullanim: uv run python -m eval.skill_correction_eval  (v9 GGUF indirilince)."""
    from agent.audit import AuditLog
    from agent.executor import MockExecutor
    from agent.policy import LabPolicy
    from agent.backends.gguf_model import GgufModel

    scope = scope or ["10.10.10.0/24"]
    cases = [
        Case("10.10.10.5 yetkili lab hedefini nmap ile tara", "nmap"),
        Case("http://10.10.10.5/ dizinlerini gobuster ile bul", "gobuster"),
        Case("http://10.10.10.5/?id=1 icin sqlmap ile sqli dene", "sqlmap"),
    ]

    def reg():
        return ToolRegistry(LabPolicy(scope=scope), MockExecutor(), AuditLog.default())

    lib = SkillLibrary.load()

    def factory():
        return GgufModel(model=model)

    off = evaluate(factory, cases, reg(), skills=None)
    on = evaluate(factory, cases, reg(), skills=lib)
    return (f"model={model}  cases={off.total}\n"
            f"gecerli-flag (skill OFF): {off.valid_flags_after}/{off.total}\n"
            f"gecerli-flag (skill ON):  {on.valid_flags_after}/{on.total}")


if __name__ == "__main__":
    print(run_against_ollama())
