# Role-Scoped Subagent Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an in-harness, deterministic-router role-scoped subagent backend so each task runs against only its slice of the 130-tool catalog, to improve tool-selection (measured 62–79%) with no retrain.

**Architecture:** `route(gorev)->role` (code) → `SubAgent(role)` builds a role-scoped `ToolRegistry` (allowlist = the domain's tools + `asistan`) → runs the UNCHANGED `run_tool_loop`. Out-of-role calls are rejected with a menu; the loop self-corrects via tool-result feedback. Role ≡ catalog `domain` (single source of truth). Default scoping = **B (allowlist-only, on-distribution prompt)**.

**Tech Stack:** Python 3, `uv`, `pytest`. Reuses `agent/catalog.py`, `agent/registry.py`, `agent/loop.py`, `agent/policy.py`, `agent/backends/*`. No new deps.

## Global Constraints
- **Branch:** work on `feat/b2-assistant-sft-data` only. **Never touch `main`.**
- **Commits:** this repo commits ONLY on the user's explicit go-ahead (standing rule). Each task's "Stage & checkpoint" step means: stage the changes and report; do NOT `git commit` unprompted, and never `git add -A`/`git add .` (stage exact paths).
- **Packaging:** `uv run pytest ...`, `uv run python ...`. Tests are offline (mock model/executor) for Tasks 1–4; Task 5 needs a served model.
- **Roles = catalog `domain`** — never hardcode tool lists; derive from `agent.catalog.CATALOG`.
- **`asistan` is cross-cutting** (in every role) and **not** a routable role. `general` = full catalog (router fallback) = today's behavior exactly.
- **Do NOT modify** `agent/loop.py`, `agent/policy.py`, `agent/executor.py`, `agent/catalog*.py`.
- ASCII file paths; Turkish only in strings/comments where the codebase already does so.

## File Structure
- Create `agent/roles.py` — role→tool membership, derived from CATALOG.
- Create `agent/router.py` — deterministic `route(gorev)->role`.
- Modify `agent/registry.py` — add `allowed` field, `scoped()` classmethod, scope-deny in `invoke()`.
- Create `agent/subagent.py` — `SubAgent`, `run_task`.
- Create tests: `tests/agent/test_roles.py`, `test_router.py`, `test_registry_scoped.py`, `test_subagent.py`.
- Task 5: create `eval/run_subagent_eval.py` — flat vs scoped-B selection comparison.

---

### Task 1: `agent/roles.py` — role membership

**Files:**
- Create: `agent/roles.py`
- Test: `tests/agent/test_roles.py`

**Interfaces:**
- Consumes: `agent.catalog.CATALOG` (`dict[str, ToolSpec]`, `ToolSpec.domain: str`).
- Produces: `ROLES: tuple[str,...]`, `ASISTAN: str`, `GENERAL: str`, `role_tools(role: str) -> frozenset[str]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_roles.py
from agent.catalog import CATALOG
from agent.roles import ROLES, ASISTAN, GENERAL, role_tools
import pytest

def test_asistan_not_routable():
    assert ASISTAN == "asistan"
    assert ASISTAN not in ROLES

def test_general_returns_full_catalog():
    assert role_tools(GENERAL) == frozenset(CATALOG)

def test_asistan_tools_in_every_role():
    asistan = {n for n, s in CATALOG.items() if s.domain == "asistan"}
    for r in ROLES:
        assert asistan <= role_tools(r), f"asistan not in {r}"

def test_role_slice_is_domain_plus_asistan():
    web = {n for n, s in CATALOG.items() if s.domain == "web"}
    asistan = {n for n, s in CATALOG.items() if s.domain == "asistan"}
    assert role_tools("web") == frozenset(web | asistan)

def test_union_of_roles_covers_catalog():
    union = set()
    for r in ROLES:
        union |= role_tools(r)
    assert union == set(CATALOG)  # every non-asistan domain is a role; asistan rides along

def test_unknown_role_raises():
    with pytest.raises(ValueError):
        role_tools("nope")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_roles.py -q`
Expected: FAIL (`ModuleNotFoundError: agent.roles`).

- [ ] **Step 3: Write minimal implementation**

```python
# agent/roles.py
"""Rol = katalog domain'i (TEK KAYNAK: CATALOG.domain). asistan araclari cross-cutting
(her role dahil), routable rol DEGIL. general = tum katalog (router fallback = bugunku davranis)."""
from __future__ import annotations
from agent.catalog import CATALOG

ASISTAN = "asistan"
GENERAL = "general"
# routable roller = asistan HARIC tum domain'ler, sirali (deterministik)
ROLES: tuple[str, ...] = tuple(sorted({s.domain for s in CATALOG.values()} - {ASISTAN}))
_ASISTAN_TOOLS = frozenset(n for n, s in CATALOG.items() if s.domain == ASISTAN)


def role_tools(role: str) -> frozenset[str]:
    """role icin izinli arac adlari. general -> tum katalog; domain -> o dilim + asistan.
    Bilinmeyen role -> ValueError (router yalniz gecerli rol veya general dondurur)."""
    if role == GENERAL:
        return frozenset(CATALOG)
    if role not in ROLES:
        raise ValueError(f"bilinmeyen rol: {role!r}")
    return frozenset(n for n, s in CATALOG.items() if s.domain == role) | _ASISTAN_TOOLS
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agent/test_roles.py -q`
Expected: PASS (6 tests).

- [ ] **Step 5: Stage & checkpoint** (stage `agent/roles.py tests/agent/test_roles.py`; report; commit only on user go-ahead).

---

### Task 2: `agent/router.py` — deterministic task→role

**Files:**
- Create: `agent/router.py`
- Test: `tests/agent/test_router.py`

**Interfaces:**
- Consumes: `agent.roles.GENERAL`.
- Produces: `route(gorev: str) -> str` (a role in `ROLES`, or `GENERAL`).

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_router.py
from agent.router import route

def test_wireless():
    assert route("komsu wifi agini test et, WPA handshake yakala") == "wireless"

def test_password():
    assert route("bu hash listesini hashcat ile kir") == "password"

def test_web():
    assert route("hedef sitede SQL injection dene, sqlmap kullan") == "web"

def test_exploit_ad():
    assert route("SMB paylasimina netexec ile baglan, lateral hareket") == "exploit-ad"

def test_recon():
    assert route("10.0.0.0/24 aginda canli hostlari ve portlari tara (nmap)") == "recon-scan"

def test_blue_server():
    assert route("sunucuda fail2ban ve firewall ile sertlestirme yap") == "blue-server"

def test_empty_and_unknown_go_general():
    assert route("") == "general"
    assert route("bugun hava nasil") == "general"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_router.py -q`
Expected: FAIL (`ModuleNotFoundError: agent.router`).

- [ ] **Step 3: Write minimal implementation**

```python
# agent/router.py
"""Deterministik gorev->rol yonlendirici (KOD, model degil). Turkce anahtar + arac-adi ipuclari.
Ilk eslesen rol kazanir (oncelik = tuple sirasi); eslesme yoksa GENERAL (bugunku tam-katalog)."""
from __future__ import annotations
from agent.roles import GENERAL

# (rol, anahtar-kelimeler). SIRA = oncelik: daha ozgul roller once.
_ROUTES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("wireless", ("wifi", "kablosuz", "wpa", "wpa2", "handshake", "aircrack", "deauth", "reaver")),
    ("password", ("parola kir", "sifre kir", "hash", "hashcat", "hydra", "john", "brute")),
    ("exploit-ad", ("active directory", "kerberos", "smb", "mimikatz", "ntlm", "lateral",
                    "impacket", "netexec", "metasploit", "meterpreter", "payload", "reverse shell")),
    ("web", ("sql injection", "sqlmap", "xss", "web uygulama", "http", "url", "dizin tara",
             "wordpress", "burp", "gobuster", "ffuf", "nikto")),
    ("traffic-mitm", ("sniff", "mitm", "ortadaki adam", "pcap", "trafik yakala", "wireshark",
                      "tcpdump", "arp spoof", "responder")),
    ("osint", ("osint", "whois", "dns kaydi", "subdomain", "email topla", "shodan",
               "theharvester", "amass", "sherlock")),
    ("recon-scan", ("port tara", "port taramasi", "nmap", "canli host", "ag kesf", "masscan", "rustscan")),
    ("privesc", ("yetki yuksel", "privesc", "linpeas", "winpeas", "root ol")),
    ("forensic-re", ("adli", "forensic", "bellek dump", "memory dump", "tersine muhendis",
                     "malware analiz", "ghidra", "volatility", "radare2")),
    ("blue-server", ("firewall", "fail2ban", "ids", "ips", "sertlestir", "hardening",
                     "rootkit", "suricata", "sunucu guvenlik", "log analiz", "iptables")),
    ("cloud", ("kubernetes", "k8s", "docker imaj", "terraform", "iac tara", "trivy", "prowler")),
    ("mobile-social", ("apk", "android uygulama", "mobil uygulama", "phishing", "oltalama",
                       "gophish", "setoolkit")),
    ("secrets", ("secret tara", "sizinti tara", "api key sizint", "trufflehog", "gizli anahtar")),
)


def route(gorev: str) -> str:
    low = (gorev or "").lower()
    for role, keys in _ROUTES:
        if any(k in low for k in keys):
            return role
    return GENERAL
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agent/test_router.py -q`
Expected: PASS (7 tests). If a keyword misfires, adjust the `_ROUTES` table (not the test's intent).

- [ ] **Step 5: Stage & checkpoint** (`agent/router.py tests/agent/test_router.py`).

---

### Task 3: `agent/registry.py` — role-scoped enforcement

**Files:**
- Modify: `agent/registry.py`
- Test: `tests/agent/test_registry_scoped.py`

**Interfaces:**
- Consumes: `agent.roles.role_tools`, `agent.toolcall.ToolCall`, existing `LabPolicy/MockExecutor/AuditLog`.
- Produces: `ToolRegistry.allowed: frozenset[str] | None`; `ToolRegistry.scoped(role, *, policy=None, executor=None, audit=None)`; scope-deny behavior in `invoke()`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_registry_scoped.py
from agent.registry import ToolRegistry
from agent.roles import role_tools
from agent.toolcall import ToolCall

def test_default_is_unscoped():
    assert ToolRegistry.default().allowed is None

def test_scoped_tool_names_match_role():
    reg = ToolRegistry.scoped("recon-scan")
    assert set(reg.tool_names()) == set(role_tools("recon-scan"))

def test_scoped_rejects_out_of_role():
    reg = ToolRegistry.scoped("recon-scan")           # sqlmap is 'web', not recon
    out = reg.invoke(ToolCall("sqlmap", {"url": "http://x"}))
    assert "BU ROL İÇİN DEĞİL" in out
    assert "sqlmap" in out

def test_scoped_allows_in_role_tool():
    reg = ToolRegistry.scoped("recon-scan")
    out = reg.invoke(ToolCall("nmap", {"hedef": "10.0.0.1"}))
    assert "BU ROL İÇİN DEĞİL" not in out          # reaches policy/executor

def test_scoped_allows_asistan_tool():
    reg = ToolRegistry.scoped("recon-scan")            # read_file is 'asistan' (cross-cutting)
    out = reg.invoke(ToolCall("read_file", {"yol": "lab/x.txt"}))
    assert "BU ROL İÇİN DEĞİL" not in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_registry_scoped.py -q`
Expected: FAIL (`scoped` / `allowed` not defined).

- [ ] **Step 3: Write minimal implementation** — edit `agent/registry.py`:

Add `allowed` to the dataclass and a `scoped` classmethod; add the scope pre-check as the first thing in `invoke()` (after the start-audit, before `get_spec`). Keep everything else identical.

```python
# add field to @dataclass ToolRegistry:
    allowed: frozenset[str] | None = None   # None = scope YOK (tam katalog)

# add classmethod (next to default()):
    @classmethod
    def scoped(cls, role: str, *, policy=None, executor=None, audit=None) -> "ToolRegistry":
        from agent.roles import role_tools
        return cls(policy or LabPolicy.default(), executor or MockExecutor(),
                   audit or AuditLog.default(), allowed=role_tools(role))

# tool_names():
    def tool_names(self) -> list[str]:
        return sorted(self.allowed) if self.allowed is not None else list(CATALOG)

# in invoke(), immediately after self.audit.write("tool.start", ...):
        if self.allowed is not None and call.name not in self.allowed:
            msg = (f"BU ROL İÇİN DEĞİL: '{call.name}'. Bu görevde şu araçlardan seç: "
                   f"{', '.join(sorted(self.allowed))}")
            self.audit.write("tool.scope.deny", msg)
            return msg
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agent/test_registry_scoped.py tests/agent/test_registry.py -q`
Expected: PASS (new + existing registry tests — confirms no regression to unscoped path).

- [ ] **Step 5: Stage & checkpoint** (`agent/registry.py tests/agent/test_registry_scoped.py`).

---

### Task 4: `agent/subagent.py` — SubAgent + run_task

**Files:**
- Create: `agent/subagent.py`
- Test: `tests/agent/test_subagent.py`

**Interfaces:**
- Consumes: `route`, `ToolRegistry.scoped/default`, `run_tool_loop`, `ToolLoopResult`, `Message`, `roles.GENERAL`.
- Produces: `SubAgent(role: str)` with `.registry` and `.run(gorev, generate, *, skills=None, max_steps=10) -> ToolLoopResult`; `SubAgentRun(role, result)`; `run_task(gorev, generate, *, skills=None, max_steps=10) -> SubAgentRun`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_subagent.py
from agent.subagent import SubAgent, run_task, SubAgentRun

def test_run_task_routes_and_reports_role():
    run = run_task("komsu wifi WPA handshake yakala", lambda msgs: "cevap, arac yok")
    assert isinstance(run, SubAgentRun)
    assert run.role == "wireless"

def test_general_task_is_unscoped():
    run = run_task("bugun hava nasil", lambda msgs: "hava guzel")
    assert run.role == "general"
    assert SubAgent("general").registry.allowed is None

def test_scoped_subagent_self_corrects_after_scope_deny():
    # recon rolunde model ONCE yanlis (web) arac dener -> scope-deny -> SONRA dogru (nmap) arac
    calls = {"n": 0}
    def gen(messages):
        calls["n"] += 1
        if calls["n"] == 1:
            return '```arac\n{"arac":"sqlmap","parametreler":{"url":"http://x"}}\n```'
        if calls["n"] == 2:
            return '```arac\n{"arac":"nmap","parametreler":{"hedef":"10.0.0.1"}}\n```'
        return "tarama tamam."
    res = SubAgent("recon-scan").run("portlari tara", gen, max_steps=5)
    executed = [c.name for c in res.calls]
    assert "nmap" in executed          # in-role call executed
    assert "sqlmap" not in executed    # out-of-role never executed (scope-deny'd)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_subagent.py -q`
Expected: FAIL (`ModuleNotFoundError: agent.subagent`).

- [ ] **Step 3: Write minimal implementation**

```python
# agent/subagent.py
"""Rol-scoped subagent: scoped ToolRegistry + DEGISMEYEN run_tool_loop. route()->SubAgent = 'backend'.
Cikti kalitesini artirmaz; arac UZAYINI daraltir (rol-disi cagri reddedilir, model kendini duzeltir)."""
from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass, field
from agent.loop import ToolLoopResult, run_tool_loop
from agent.messages import Message
from agent.registry import ToolRegistry
from agent.roles import GENERAL
from agent.router import route
from agent.skills import SkillLibrary

Generate = Callable[[list[Message]], str]


@dataclass
class SubAgent:
    role: str
    registry: ToolRegistry = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.registry is None:
            self.registry = (ToolRegistry.default() if self.role == GENERAL
                             else ToolRegistry.scoped(self.role))

    def run(self, gorev: str, generate: Generate, *,
            skills: SkillLibrary | None = None, max_steps: int = 10) -> ToolLoopResult:
        return run_tool_loop([Message("user", gorev)], generate, self.registry,
                             max_steps=max_steps, skills=skills)


@dataclass(frozen=True)
class SubAgentRun:
    role: str
    result: ToolLoopResult


def run_task(gorev: str, generate: Generate, *,
             skills: SkillLibrary | None = None, max_steps: int = 10) -> SubAgentRun:
    """Backend girisi: gorevi rota -> rol-scoped subagent -> calistir. Rolu de dondurur (gozlem)."""
    role = route(gorev)
    result = SubAgent(role).run(gorev, generate, skills=skills, max_steps=max_steps)
    return SubAgentRun(role=role, result=result)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agent/test_subagent.py -q`
Expected: PASS (3 tests). Then full suite: `uv run pytest -q` (no regressions).

- [ ] **Step 5: Stage & checkpoint** (`agent/subagent.py tests/agent/test_subagent.py`). **This completes the FREE, offline runtime — usable and fully unit-tested with no model and no money.**

---

### Task 5: measurement — flat vs scoped-B tool-selection (needs a served model)

**Files:**
- Create: `eval/run_subagent_eval.py`
- (Reuses `eval/toolcall_eval.py` primitives + `eval/data/toolcall_eval_tr.jsonl`.)

**Interfaces:**
- Consumes: `eval.toolcall_eval.load_cases/score_reply`, `agent.subagent.run_task`, `agent.router.route`, `agent.backends.gguf_model.GgufModel`, `agent.toolcall.parse_arac_calls`.

**Why this task is separate:** Tasks 1–4 are offline/free. This one calls the real model over Ollama, so it runs on a GPU pod (**money-checkpoint with the user first**) or locally once a v10 GGUF is present. It is the gate that decides whether scoping actually beats the 62–79% flat baseline.

**What it measures (B, the default):** for each held-out case, compare the tool actually used —
- **flat:** first `parse_arac_calls` of a single-turn generate (the existing metric = 62–79%);
- **scoped-B:** `run_task(prompt, generate)`; score the **first EXECUTED** call in `run.result.calls` (post scope-deny self-correction) against the case's `expected`.
Report both `expected_tool` rates side by side on the same cases/model (v10, temp = eval default).

- [ ] **Step 1: Write `eval/run_subagent_eval.py`**

```python
"""Flat vs scoped-B arac-secim kiyasi. Ayni tutulmus istemler, ayni model; scoped = route->subagent.
Kullanim (pod ya da yerel GGUF): uv run python -m eval.run_subagent_eval --model octopus-v10 \
    --tokenizer-dir models/octopus-v8-tokenizer"""
from __future__ import annotations
import argparse
from agent.backends.gguf_model import GgufModel
from agent.messages import Message
from agent.subagent import run_task
from agent.toolcall import parse_arac_calls
from eval.toolcall_eval import load_cases

CASES = "eval/data/toolcall_eval_tr.jsonl"

def _first_tool(reply: str):
    calls = parse_arac_calls(reply or "")
    return calls[0].name if calls else None

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="octopus-v10")
    ap.add_argument("--tokenizer-dir", default="models/octopus-v8-tokenizer")
    ap.add_argument("--cases", default=CASES)
    args = ap.parse_args()

    cases = load_cases(args.cases)
    gm = GgufModel(model=args.model, tokenizer_dir=args.tokenizer_dir)

    flat_ok = scoped_ok = 0
    for c in cases:
        exp = set(c.expected)
        # flat: tek-tur, ilk cagri
        flat_tool = _first_tool(gm([Message("user", c.prompt)]))
        flat_ok += int(flat_tool in exp)
        # scoped-B: route->subagent, ILK CALISAN cagri (self-correction sonrasi)
        run = run_task(c.prompt, lambda msgs: gm(msgs))
        exec_tool = run.result.calls[0].name if run.result.calls else None
        scoped_ok += int(exec_tool in exp)
        print(f"  [{run.role:12s}] flat={flat_tool} scoped={exec_tool} exp={sorted(exp)}")

    n = len(cases) or 1
    print(f"\nflat   dogru-arac: {flat_ok}/{len(cases)} = {flat_ok/n:.0%}")
    print(f"scoped dogru-arac: {scoped_ok}/{len(cases)} = {scoped_ok/n:.0%}")

if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Dry-run offline sanity (no model needed) with a scripted stand-in**

Temporarily point `GgufModel` at nothing by unit-checking the scoring logic in isolation is optional; the real signal needs a model. Verify import + arg parsing:
Run: `uv run python -m eval.run_subagent_eval --help`
Expected: prints usage (imports resolve, no runtime error).

- [ ] **Step 3: Run on a served model (money/availability checkpoint FIRST)**

Options: (a) GPU pod — reuse the paired-eval recipe (`scratchpad/pod_eval_v11.sh` pattern), pull v10 GGUF from HF, install jinja2 (lesson!), `ollama create octopus-v10`, run this script; (b) local, once a v10 GGUF is downloaded. **Checkpoint with the user before spending.**
Expected: two side-by-side rates; scoped-B ≥ flat is the promote signal.

- [ ] **Step 4: Write the comparison report**

Save `eval/reports/subagent_scoping_<date>.md` with the flat vs scoped numbers + per-case table + verdict (does scoping beat flat? by how much? any cases it hurt?).

- [ ] **Step 5: Stage & checkpoint** (`eval/run_subagent_eval.py` + report). Decide with the user whether to wire `run_task` into `agent/cli.py` as the default entry (follow-on, only if scoping wins).

**Stretch (optional, experiment A — prompt-augment):** add `--prompt-scope` that, per case, appends the role's tool menu (`', '.join(sorted(role_tools(role)))`) to `GgufModel.system_prompt` before generating. Compare A vs B vs flat. Off-distribution (the trained prompt has no menu), so treat any A gain skeptically and re-check for regressions elsewhere.

---

## Self-Review
- **Spec coverage:** roles=domain (Task 1) ✓; deterministic router + general fallback (Task 2) ✓; scoped ToolRegistry + scope-deny + self-correction (Task 3) ✓; SubAgent/run_task backend entry (Task 4) ✓; B default + A stretch + measurement vs flat (Task 5) ✓; loop/policy/executor unchanged (Global Constraints + Task 3 note) ✓.
- **Placeholders:** none — every code step has real code; Task 5 Step 3 is intentionally a gated run, with concrete recipe, not a placeholder.
- **Type consistency:** `route()->str`, `role_tools()->frozenset[str]`, `ToolRegistry.allowed: frozenset|None`, `SubAgent.run()->ToolLoopResult`, `run_task()->SubAgentRun(role, result)`, `result.calls: list[ToolCall]` — consistent across tasks.
