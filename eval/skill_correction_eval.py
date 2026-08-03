"""Skill katmani etkisini olc: FINAL calisan arac cagrisi UYDURMA flag iceriyor mu?
skill KAPALI vs ACIK. Gercek model (GgufModel) veya scripted 'generate' ile calisir.
proxy metrik: 'gecerli-flag' orani = uydurma-flag'in tersi."""
from __future__ import annotations

from dataclasses import dataclass, field

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
class CaseOutcome:
    """Tek case sonucu (per-case rapor icin): hangi arac, FINAL secenekler, gecerli mi, cagrildi mi."""
    prompt: str
    tool: str
    secenekler: str          # FINAL calisan cagrinin secenekler'i ("" = arac hic cagrilmadi)
    called: bool             # model bu araci hic cagirdi mi
    valid: bool              # FINAL cagride uydurma-flag YOK (cagrilmadiysa False)


@dataclass
class EvalResult:
    total: int
    valid_flags_before: int   # (ayrilmis: ilk cagri) — bu surumde final ile ayni cerceve
    valid_flags_after: int    # FINAL calisan cagrida uydurma-flag yok
    outcomes: list[CaseOutcome] = field(default_factory=list)  # per-case detay (geriye-uyumlu)


def _last_call_for(tool: str, calls) -> object | None:
    for c in reversed(calls):
        if c.name == tool:
            return c
    return None


def evaluate(generate_factory, cases: list[Case], registry: ToolRegistry,
             skills: SkillLibrary | None) -> EvalResult:
    """generate_factory: her case icin taze bir generate callable dondurur (durum sizmasin)."""
    valid_after = 0
    outcomes: list[CaseOutcome] = []
    for case in cases:
        gen = generate_factory()
        msgs = [Message("user", case.prompt)]
        res = run_tool_loop(msgs, gen, registry, skills=skills)
        call = _last_call_for(case.tool, res.calls)
        secenekler = str(call.params.get("secenekler", "")) if call is not None else ""
        valid = call is not None and has_only_known_flags(case.tool, secenekler)
        if valid:
            valid_after += 1
        outcomes.append(CaseOutcome(prompt=case.prompt, tool=case.tool, secenekler=secenekler,
                                    called=call is not None, valid=valid))
    return EvalResult(total=len(cases), valid_flags_before=valid_after,
                      valid_flags_after=valid_after, outcomes=outcomes)


# Uydurma-TETIKLEYEN case'ler: niyet Turkce yazilir (flag EL VERILMEZ) ki model dogal olarak
# bir flag uydursun; her case'in KANONIK cevabi _KNOWN_FLAGS icinde (yoksa dogru cevap yanlislikla
# 'uydurma' sayilir). Boylece OFF'ta model uydurabilir -> ON'da tool-skill md kanonigi ogretip
# duzeltir. Eski (nmap -sV / gobuster dir / sqlmap sqli) case'ler v0.8.1'de zaten gecerliydi
# (OFF 3/3) -> duzeltilecek uydurma yok -> skill faydasi OLCULEMIYORDU; bunlar headroom yaratir.
FABRICATION_CASES: list[Case] = [
    # kanonik: -p 21,22,80 -sV -O -Pn   (tuzak: --osscan-guess / --no-ping / --version)
    Case("10.10.10.5 hedefinde 21, 22 ve 80 portlarini servis versiyonu ve isletim sistemi "
         "tahminiyle, ama hedefe ping atmadan tara", "nmap"),
    # kanonik: dir -u <url> -w <wl> -x php,txt -t 50   (tuzak: --extensions / --threads)
    Case("http://10.10.10.5/ altinda php ve txt uzantili dosyalari 50 is parcaciyla (thread) ara",
         "gobuster"),
    # kanonik: -u <url> --dbs --batch --level=5 --risk=3   (tuzak: --databases / --yes)
    Case("http://10.10.10.5/?id=1 uzerinde veritabani isimlerini cikar, sorulari otomatik onayla, "
         "seviye 5 ve risk 3 ile calis", "sqlmap"),
    # kanonik: -l admin -P rockyou.txt -t 4 ssh   (tuzak: --login / --passwords)
    Case("10.10.10.5 ssh servisine admin kullanicisi ve rockyou.txt listesiyle 4 paralel "
         "kaba-kuvvet dene", "hydra"),
    # kanonik: -w <wl> -u http://.../FUZZ -fc 404 -t 40   (tuzak: --filter-code / --threads)
    Case("http://10.10.10.5/FUZZ dizinlerini tararken 404 durum kodunu gizle ve 40 thread kullan",
         "ffuf"),
    # kanonik: -h <host> -ssl -o out.html -Format htm   (tuzak: --ssl / --output)
    Case("10.10.10.5 hedefini SSL uzerinden tara, ciktiyi out.html dosyasina htm formatinda kaydet",
         "nikto"),
]


def _report(model: str, off: EvalResult, on: EvalResult) -> str:
    """OFF-vs-ON'u per-case yan yana yaz: hangi case'de skill uydurmayi duzeltti gorunur."""
    lines = [f"model={model}  temp=0  cases={off.total}",
             f"gecerli-flag (skill OFF): {off.valid_flags_after}/{off.total}",
             f"gecerli-flag (skill ON):  {on.valid_flags_after}/{on.total}",
             f"NET (ON - OFF): {on.valid_flags_after - off.valid_flags_after:+d}",
             "",
             "per-case (arac: OFF -> ON  |  secenekler):"]
    for o_off, o_on in zip(off.outcomes, on.outcomes):
        mark_off = "OK " if o_off.valid else ("--" if o_off.called else "??")  # ?? = arac cagrilmadi
        mark_on = "OK " if o_on.valid else ("--" if o_on.called else "??")
        delta = " <== SKILL DUZELTTI" if (o_on.valid and not o_off.valid) else (
                " <== SKILL BOZDU" if (o_off.valid and not o_on.valid) else "")
        lines.append(f"  {o_off.tool:9s} {mark_off}-> {mark_on}{delta}")
        lines.append(f"    OFF secenekler: {o_off.secenekler or '(cagrilmadi)'}")
        lines.append(f"    ON  secenekler: {o_on.secenekler or '(cagrilmadi)'}")
    return "\n".join(lines)


def run_against_ollama(model: str = "octopus-v9", scope: list[str] | None = None,
                       cases: list[Case] | None = None) -> str:
    """GERCEK model ile skill OFF vs ON karsilastirmasi (temp=0, deterministik). Ollama+GGUF gerektirir.
    cases=None -> FABRICATION_CASES (uydurma-tetikleyen). Kullanim: uv run python -m eval.skill_correction_eval."""
    from agent.audit import AuditLog
    from agent.executor import MockExecutor
    from agent.policy import LabPolicy
    from agent.backends.gguf_model import GgufModel

    scope = scope or ["10.10.10.0/24"]
    cases = cases or FABRICATION_CASES

    def reg():
        return ToolRegistry(LabPolicy(scope=scope), MockExecutor(), AuditLog.default())

    lib = SkillLibrary.load()

    def factory():
        return GgufModel(model=model, temperature=0.0)  # deterministik: gurultu degil sinyal

    off = evaluate(factory, cases, reg(), skills=None)
    on = evaluate(factory, cases, reg(), skills=lib)
    return _report(model, off, on)


if __name__ == "__main__":
    print(run_against_ollama())
