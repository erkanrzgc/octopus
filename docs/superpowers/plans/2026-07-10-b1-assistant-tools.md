# B1 — Assistant Tool Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 8 general-assistant tools (file / cmd / web) to the harness behind a fail-closed security model (fs jail, command sandbox+denylist, web SSRF guard), fitting existing interfaces.

**Architecture:** Pure guard functions (`agent/guards/`) return `Decision`; `LabPolicy.decide` dispatches `asistan`-domain tools to them. A `CompositeExecutor` routes `run()` by domain to a new `AssistantExecutor` (file/web/cmd) or the existing security executor. `run_cmd` delegates to an injected sandbox executor — never the host.

**Tech Stack:** Python 3.14, stdlib (`pathlib`, `ipaddress`, `urllib`, `re`, `socket`), `pytest`, `uv`.

## Global Constraints

- Tests/run: `uv run pytest`, `uv run python ...`.
- Existing interfaces are contracts — do not change their signatures:
  - `Executor` Protocol: `run(tool: str, params: dict) -> str` (`agent/executor.py`).
  - `Decision(allowed: bool, requires_approval: bool, reason: str)` frozen (`agent/policy.py`).
  - `ToolSpec(name, domain, risk, params)` frozen; `get_spec(name) -> ToolSpec | None`, `CATALOG` (`agent/catalog.py`).
  - `LabPolicy.decide(spec, params) -> Decision`.
- `catalog_data.py` is GENERATED — never hand-edit; change `agent/build_catalog.py` and regenerate.
- Fail-closed: a tool with no matching guard is denied.
- `run_cmd` must never call a host subprocess from `AssistantExecutor` — always delegate to an injected executor.
- New catalog domain is exactly `asistan`; the 8 tool names/params/risks are fixed by the spec table.
- Turkish param keys: `yol`, `icerik`, `eski`, `yeni`, `komut`, `url`, `sorgu`, `desen`.

---

### Task 1: Catalog — `asistan` tools

**Files:**
- Modify: `agent/build_catalog.py`
- Regenerate: `agent/catalog_data.py` (via the script)
- Test: `tests/agent/test_catalog_assistant.py`

**Interfaces:**
- Produces: 8 `CATALOG` entries under domain `asistan` with fixed risks/params.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_catalog_assistant.py
from agent.catalog import get_spec

_EXPECTED = {
    "read_file": ("low", ("yol",)),
    "list_dir": ("low", ("yol",)),
    "grep": ("low", ("desen", "yol")),
    "write_file": ("medium", ("yol", "icerik")),
    "edit_file": ("medium", ("yol", "eski", "yeni")),
    "run_cmd": ("high", ("komut",)),
    "web_fetch": ("low", ("url",)),
    "web_search": ("low", ("sorgu",)),
}


def test_assistant_tools_registered():
    for name, (risk, params) in _EXPECTED.items():
        spec = get_spec(name)
        assert spec is not None, f"{name} katalogda yok"
        assert spec.domain == "asistan"
        assert spec.risk == risk
        assert spec.params == params
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_catalog_assistant.py -v`
Expected: FAIL — `read_file katalogda yok` (spec is None)

- [ ] **Step 3: Extend the generator + regenerate**

Add to `agent/build_catalog.py` (after `DOMAIN_RISK`):

```python
# Asistan araclari: egitim verisinde YOK + per-tool risk -> explicit tanim (domain='asistan').
ASSISTANT_TOOLS: list[dict] = [
    {"name": "read_file",  "risk": "low",    "params": ("yol",)},
    {"name": "list_dir",   "risk": "low",    "params": ("yol",)},
    {"name": "grep",       "risk": "low",    "params": ("desen", "yol")},
    {"name": "write_file", "risk": "medium", "params": ("yol", "icerik")},
    {"name": "edit_file",  "risk": "medium", "params": ("yol", "eski", "yeni")},
    {"name": "run_cmd",    "risk": "high",   "params": ("komut",)},
    {"name": "web_fetch",  "risk": "low",    "params": ("url",)},
    {"name": "web_search", "risk": "low",    "params": ("sorgu",)},
]
```

In `main()`, before the closing `lines.append("]")`, add the assistant rows:

```python
    for a in ASSISTANT_TOOLS:
        lines.append(f"    {{'name': {a['name']!r}, 'domain': 'asistan', "
                     f"'risk': {a['risk']!r}, 'params': {tuple(a['params'])!r}}},")
```

Regenerate: `uv run python -m agent.build_catalog`
Expected: `[OK] catalog_data.py yazildi: <N> arac` and `git diff` shows 8 new `asistan` rows.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agent/test_catalog_assistant.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/build_catalog.py agent/catalog_data.py tests/agent/test_catalog_assistant.py
git commit -m "feat(agent): asistan domain — 8 asistan araci katalogda (file/cmd/web)"
```

---

### Task 2: Filesystem jail guard

**Files:**
- Create: `agent/guards/__init__.py` (empty), `agent/guards/fs.py`
- Test: `tests/agent/test_guard_fs.py`

**Interfaces:**
- Produces: `guard(params: dict, workspace_root: str | None) -> Decision`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_guard_fs.py
from agent.guards import fs
from agent.policy import Decision


def test_denies_when_root_unset():
    assert fs.guard({"yol": "a.txt"}, None).allowed is False


def test_denies_missing_path():
    assert fs.guard({}, "/tmp/ws").allowed is False


def test_allows_path_inside_root(tmp_path):
    (tmp_path / "sub").mkdir()
    d = fs.guard({"yol": "sub/a.txt"}, str(tmp_path))
    assert d.allowed is True


def test_denies_traversal(tmp_path):
    assert fs.guard({"yol": "../../etc/passwd"}, str(tmp_path)).allowed is False


def test_denies_absolute_escape(tmp_path):
    assert fs.guard({"yol": "/etc/passwd"}, str(tmp_path)).allowed is False


def test_denies_symlink_escape(tmp_path):
    outside = tmp_path.parent / "outside_secret"
    outside.mkdir(exist_ok=True)
    link = tmp_path / "link"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        import pytest
        pytest.skip("symlink olusturulamiyor (izin/OS)")
    assert fs.guard({"yol": "link/x.txt"}, str(tmp_path)).allowed is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_guard_fs.py -v`
Expected: FAIL — `ModuleNotFoundError: agent.guards`

- [ ] **Step 3: Write minimal implementation**

```python
# agent/guards/__init__.py
```

```python
# agent/guards/fs.py
"""Dosya araclari icin workspace hapishane guard'i. workspace_root disina cikis
(traversal/absolute/symlink) fail-closed reddedilir. Saf fonksiyon -> test kolay."""
from __future__ import annotations

from pathlib import Path

from agent.policy import Decision


def guard(params: dict, workspace_root: str | None) -> Decision:
    if not workspace_root:
        return Decision(False, False, "workspace_root tanimsiz (fail-closed)")
    yol = params.get("yol")
    if not yol:
        return Decision(False, False, "'yol' parametresi eksik")
    root = Path(workspace_root).resolve()
    candidate = Path(yol)
    target = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    if target == root or root in target.parents:
        return Decision(True, False, "izinli")
    return Decision(False, False, f"workspace disina cikis reddedildi: {yol}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agent/test_guard_fs.py -v`
Expected: PASS (6 passed, or 5 + 1 skipped if no symlink perm)

- [ ] **Step 5: Commit**

```bash
git add agent/guards/__init__.py agent/guards/fs.py tests/agent/test_guard_fs.py
git commit -m "feat(agent): fs-jail guard (traversal/absolute/symlink kacisi fail-closed)"
```

---

### Task 3: Command denylist guard

**Files:**
- Create: `agent/guards/cmd.py`
- Test: `tests/agent/test_guard_cmd.py`

**Interfaces:**
- Produces: `guard(params: dict) -> Decision`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_guard_cmd.py
import pytest
from agent.guards import cmd


@pytest.mark.parametrize("komut", [
    "rm -rf /", "rm  -rf   /", "rm -rf ~", "mkfs.ext4 /dev/sda",
    "dd if=/dev/zero of=/dev/sda", ":(){ :|:& };:", "shutdown -h now", "reboot",
    "chmod -R 777 /", "> /dev/sda",
])
def test_denies_destructive(komut):
    assert cmd.guard({"komut": komut}).allowed is False


@pytest.mark.parametrize("komut", [
    "nmap -sV 10.0.0.5", "ls -la", "cat notes.txt", "python3 script.py", "grep -r TODO .",
])
def test_allows_benign(komut):
    assert cmd.guard({"komut": komut}).allowed is True


def test_denies_missing_command():
    assert cmd.guard({}).allowed is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_guard_cmd.py -v`
Expected: FAIL — `AttributeError: module 'agent.guards.cmd' has no attribute 'guard'` (or ModuleNotFound)

- [ ] **Step 3: Write minimal implementation**

```python
# agent/guards/cmd.py
"""run_cmd icin yikici-desen denylist'i. NOT sinir DEGIL (asil sinir sandbox);
savunma-derinligi. Saf fonksiyon."""
from __future__ import annotations

import re

from agent.policy import Decision

# Yikici desenler (bosluga toleransli). Eslesme -> fail-closed ret.
_DENY = [
    re.compile(r"\brm\s+-[a-z]*r[a-z]*f[a-z]*\s+(/|~)(\s|$)"),   # rm -rf / veya ~
    re.compile(r"\bmkfs(\.[a-z0-9]+)?\b"),                        # mkfs...
    re.compile(r"\bdd\b.*\bof=/dev/"),                            # dd of=/dev/...
    re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"),      # fork bomb
    re.compile(r"\b(shutdown|reboot|halt|poweroff)\b"),
    re.compile(r"\bchmod\s+-[a-z]*R[a-z]*\s+777\s+/"),
    re.compile(r">\s*/dev/(sd|nvme|hd)"),                          # cihaza yazma
]


def guard(params: dict) -> Decision:
    komut = params.get("komut")
    if not komut or not str(komut).strip():
        return Decision(False, False, "'komut' parametresi eksik")
    text = str(komut)
    for rx in _DENY:
        if rx.search(text):
            return Decision(False, False, f"yikici komut deseni reddedildi: {rx.pattern}")
    return Decision(True, False, "izinli")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agent/test_guard_cmd.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/guards/cmd.py tests/agent/test_guard_cmd.py
git commit -m "feat(agent): run_cmd denylist guard (rm -rf /, mkfs, dd, fork-bomb, shutdown...)"
```

---

### Task 4: Web SSRF guard

**Files:**
- Create: `agent/guards/web.py`
- Test: `tests/agent/test_guard_web.py`

**Interfaces:**
- Produces: `guard(params: dict, resolve: Callable[[str], str] = _default_resolve) -> Decision`.
  `resolve(host) -> ip_str`; injectable for tests. `web_search` (`sorgu`) is always allowed
  (fixed backend); `web_fetch` (`url`) is SSRF-checked.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_guard_web.py
from agent.guards import web


def _fake_resolve(mapping):
    return lambda host: mapping.get(host, "203.0.113.10")  # varsayilan public


def test_web_search_always_allowed():
    assert web.guard({"sorgu": "ispanya belcika mac saati"}).allowed is True


def test_fetch_public_allowed():
    d = web.guard({"url": "https://example.com/x"}, resolve=_fake_resolve({"example.com": "93.184.216.34"}))
    assert d.allowed is True


def test_fetch_denies_metadata_ip():
    d = web.guard({"url": "http://metadata.internal/latest"},
                  resolve=_fake_resolve({"metadata.internal": "169.254.169.254"}))
    assert d.allowed is False


def test_fetch_denies_loopback_and_private():
    assert web.guard({"url": "http://localhost/"}, resolve=_fake_resolve({"localhost": "127.0.0.1"})).allowed is False
    assert web.guard({"url": "http://x/"}, resolve=_fake_resolve({"x": "10.1.2.3"})).allowed is False


def test_fetch_denies_non_http_scheme():
    assert web.guard({"url": "file:///etc/passwd"}).allowed is False


def test_fetch_denies_missing_url():
    assert web.guard({}).allowed is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_guard_web.py -v`
Expected: FAIL — module/attr missing

- [ ] **Step 3: Write minimal implementation**

```python
# agent/guards/web.py
"""web_fetch icin SSRF guard: sadece http(s), host'u coz, private/loopback/link-local/
metadata IP'lerini reddet. web_search sabit backend -> her zaman izinli. Saf + resolver enjekte."""
from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urlparse

from agent.policy import Decision


def _default_resolve(host: str) -> str:
    return socket.gethostbyname(host)


def _blocked(ip_str: str) -> bool:
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # cozulemedi -> fail-closed
    return (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_unspecified or ip.is_multicast)


def guard(params: dict, resolve: Callable[[str], str] = _default_resolve) -> Decision:
    if "sorgu" in params:                       # web_search: sabit backend, SSRF-guvenli
        if not str(params.get("sorgu") or "").strip():
            return Decision(False, False, "'sorgu' parametresi eksik")
        return Decision(True, False, "izinli (arama backend)")
    url = params.get("url")
    if not url:
        return Decision(False, False, "'url' parametresi eksik")
    parsed = urlparse(str(url))
    if parsed.scheme not in ("http", "https"):
        return Decision(False, False, f"sema reddedildi: {parsed.scheme or '(yok)'} (yalniz http/https)")
    host = parsed.hostname
    if not host:
        return Decision(False, False, "url host'u yok")
    try:
        ip = resolve(host)
    except OSError:
        return Decision(False, False, f"host cozulemedi: {host} (fail-closed)")
    if _blocked(ip):
        return Decision(False, False, f"SSRF: {host} -> {ip} ic/ozel adres reddedildi")
    return Decision(True, False, "izinli")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agent/test_guard_web.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/guards/web.py tests/agent/test_guard_web.py
git commit -m "feat(agent): web SSRF guard (http(s)-only, private/loopback/metadata IP bloklu)"
```

---

### Task 5: Policy dispatch to guards

**Files:**
- Modify: `agent/policy.py`
- Test: `tests/agent/test_policy_assistant.py`

**Interfaces:**
- Consumes: `guards.fs/cmd/web` (Tasks 2-4).
- Produces: `LabPolicy` gains `workspace_root: str | None = None`; `decide` routes `asistan`-domain
  tools to guards (network tools unchanged).

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_policy_assistant.py
from agent.catalog import get_spec
from agent.policy import LabPolicy


def test_write_file_traversal_denied(tmp_path):
    pol = LabPolicy(scope=[], workspace_root=str(tmp_path))
    d = pol.decide(get_spec("write_file"), {"yol": "../escape.txt", "icerik": "x"})
    assert d.allowed is False


def test_read_file_in_workspace_allowed(tmp_path):
    pol = LabPolicy(scope=[], workspace_root=str(tmp_path))
    d = pol.decide(get_spec("read_file"), {"yol": "notes.txt"})
    assert d.allowed is True


def test_web_fetch_metadata_denied_not_scope_checked():
    # url bir TARGET_KEY ama asistan araci -> ag-scope'a DEGIL web guard'a gider
    pol = LabPolicy(scope=[])
    d = pol.decide(get_spec("web_fetch"),
                   {"url": "http://x/"})  # x -> gercek DNS; ozel/cozumsuz -> ret beklenir
    assert d.allowed is False


def test_run_cmd_requires_approval(tmp_path):
    pol = LabPolicy(scope=[], workspace_root=str(tmp_path), allow_high=False)
    d = pol.decide(get_spec("run_cmd"), {"komut": "ls -la"})
    assert d.allowed is False and d.requires_approval is True


def test_run_cmd_destructive_denied_before_approval(tmp_path):
    pol = LabPolicy(scope=[], workspace_root=str(tmp_path), allow_high=True)
    d = pol.decide(get_spec("run_cmd"), {"komut": "rm -rf /"})
    assert d.allowed is False and d.requires_approval is False


def test_network_tool_unchanged():
    pol = LabPolicy(scope=["10.0.0.0/24"])
    d = pol.decide(get_spec("nmap"), {"hedef": "10.0.0.5", "secenekler": "-sV"})
    assert d.allowed is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_policy_assistant.py -v`
Expected: FAIL — `TypeError: __init__() got an unexpected keyword 'workspace_root'`

- [ ] **Step 3: Write minimal implementation**

In `agent/policy.py`, add the field and dispatch. Change the `LabPolicy` dataclass:

```python
@dataclass
class LabPolicy:
    scope: list[str] = field(default_factory=list)
    allow_high: bool = False
    workspace_root: str | None = None
```

Add a dispatch branch at the TOP of `decide` (before the existing network logic):

```python
    def decide(self, spec: ToolSpec, params: dict) -> Decision:
        if spec.domain == "asistan":
            return self._decide_assistant(spec, params)
        target = target_value(params)
        # ... EXISTING network logic unchanged ...
```

Add the helper method:

```python
    def _decide_assistant(self, spec: ToolSpec, params: dict) -> Decision:
        from agent.guards import cmd, fs, web
        name = spec.name
        if name in ("read_file", "write_file", "edit_file", "list_dir", "grep"):
            return fs.guard(params, self.workspace_root)
        if name in ("web_fetch", "web_search"):
            return web.guard(params)
        if name == "run_cmd":
            d = cmd.guard(params)
            if not d.allowed:
                return d
            if spec.risk == "high" and not self.allow_high:
                return Decision(False, True, f"'{spec.name}' yuksek riskli, acik onay gerekir")
            return d
        return Decision(False, False, f"bilinmeyen asistan araci '{name}' (fail-closed)")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agent/test_policy_assistant.py -v`
Expected: PASS (network tool test confirms existing path intact)

- [ ] **Step 5: Commit**

```bash
git add agent/policy.py tests/agent/test_policy_assistant.py
git commit -m "feat(agent): policy asistan-domain dispatch -> fs/cmd/web guard (ag yolu degismedi)"
```

---

### Task 6: AssistantExecutor

**Files:**
- Create: `agent/backends/assistant_executor.py`
- Test: `tests/agent/test_assistant_executor.py`

**Interfaces:**
- Consumes: `Executor` Protocol; `MockExecutor` as default sandbox.
- Produces: `AssistantExecutor(workspace_root, sandbox=None, http_get=None, search=None)` with
  `run(tool, params) -> str`. `run_cmd` delegates to `sandbox.run("run_cmd", params)` (never host);
  `web_fetch` uses injected `http_get(url) -> str`; `web_search` uses injected `search(sorgu) -> str`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_assistant_executor.py
from agent.backends.assistant_executor import AssistantExecutor


def test_write_then_read(tmp_path):
    ex = AssistantExecutor(str(tmp_path))
    ex.run("write_file", {"yol": "a.txt", "icerik": "merhaba"})
    assert "merhaba" in ex.run("read_file", {"yol": "a.txt"})


def test_edit_file(tmp_path):
    ex = AssistantExecutor(str(tmp_path))
    ex.run("write_file", {"yol": "a.txt", "icerik": "eski deger"})
    ex.run("edit_file", {"yol": "a.txt", "eski": "eski", "yeni": "yeni"})
    assert "yeni deger" in ex.run("read_file", {"yol": "a.txt"})


def test_list_dir(tmp_path):
    (tmp_path / "x.txt").write_text("1", encoding="utf-8")
    out = AssistantExecutor(str(tmp_path)).run("list_dir", {"yol": "."})
    assert "x.txt" in out


def test_grep(tmp_path):
    (tmp_path / "x.txt").write_text("TODO: fix\nnope", encoding="utf-8")
    out = AssistantExecutor(str(tmp_path)).run("grep", {"desen": "TODO", "yol": "."})
    assert "TODO" in out


def test_run_cmd_delegates_to_sandbox(tmp_path):
    calls = {}

    class FakeSandbox:
        def run(self, tool, params):
            calls["got"] = (tool, params)
            return "SANDBOX_OUT"

    ex = AssistantExecutor(str(tmp_path), sandbox=FakeSandbox())
    out = ex.run("run_cmd", {"komut": "ls"})
    assert out == "SANDBOX_OUT"
    assert calls["got"][1]["komut"] == "ls"   # host'a gitmedi, sandbox'a gitti


def test_web_fetch_uses_injected_client(tmp_path):
    ex = AssistantExecutor(str(tmp_path), http_get=lambda url: f"FETCHED:{url}")
    assert ex.run("web_fetch", {"url": "https://x/"}) == "FETCHED:https://x/"


def test_web_search_uses_injected_backend(tmp_path):
    ex = AssistantExecutor(str(tmp_path), search=lambda q: f"RESULTS:{q}")
    assert ex.run("web_search", {"sorgu": "mac saati"}) == "RESULTS:mac saati"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_assistant_executor.py -v`
Expected: FAIL — `ModuleNotFoundError: agent.backends.assistant_executor`

- [ ] **Step 3: Write minimal implementation**

```python
# agent/backends/assistant_executor.py
"""Asistan araclari (file/web/cmd) executor'i. Dosya islemleri workspace_root altinda;
run_cmd HOST'a DEGIL enjekte sandbox'a delege (guvenlik siniri sandbox'ta); web enjekte
istemci/backend ile (varsayilan urllib, test'te sahte)."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from agent.executor import MockExecutor


def _default_http_get(url: str) -> str:
    import urllib.request
    with urllib.request.urlopen(url, timeout=15) as r:  # noqa: S310 - guard SSRF'i policy'de yapildi
        return r.read(200_000).decode("utf-8", "replace")


def _default_search(sorgu: str) -> str:
    return f"[web_search backend tanimsiz] sorgu: {sorgu}"


class AssistantExecutor:
    def __init__(self, workspace_root: str, sandbox=None,
                 http_get: Callable[[str], str] | None = None,
                 search: Callable[[str], str] | None = None) -> None:
        self.root = Path(workspace_root).resolve()
        self.sandbox = sandbox or MockExecutor()
        self.http_get = http_get or _default_http_get
        self.search = search or _default_search

    def _path(self, yol: str) -> Path:
        p = Path(yol)
        return p.resolve() if p.is_absolute() else (self.root / p).resolve()

    def run(self, tool: str, params: dict) -> str:
        try:
            if tool == "read_file":
                return self._path(params["yol"]).read_text(encoding="utf-8")
            if tool == "write_file":
                p = self._path(params["yol"])
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(params.get("icerik", ""), encoding="utf-8")
                return f"yazildi: {params['yol']} ({len(params.get('icerik', ''))} bayt)"
            if tool == "edit_file":
                p = self._path(params["yol"])
                text = p.read_text(encoding="utf-8")
                eski = params["eski"]
                if eski not in text:
                    return f"HATA: '{eski}' bulunamadi"
                p.write_text(text.replace(eski, params["yeni"]), encoding="utf-8")
                return f"duzenlendi: {params['yol']}"
            if tool == "list_dir":
                p = self._path(params.get("yol", "."))
                return "\n".join(sorted(c.name + ("/" if c.is_dir() else "") for c in p.iterdir())) or "(bos)"
            if tool == "grep":
                p = self._path(params.get("yol", "."))
                desen = params["desen"]
                hits = []
                files = p.rglob("*") if p.is_dir() else [p]
                for f in files:
                    if not f.is_file():
                        continue
                    try:
                        for i, line in enumerate(f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                            if desen in line:
                                hits.append(f"{f.relative_to(self.root)}:{i}: {line.strip()}")
                    except OSError:
                        continue
                return "\n".join(hits) or f"(eslesme yok: {desen})"
            if tool == "run_cmd":
                return self.sandbox.run("run_cmd", params)   # HOST'a DEGIL sandbox'a
            if tool == "web_fetch":
                return self.http_get(params["url"])
            if tool == "web_search":
                return self.search(params["sorgu"])
        except KeyError as e:
            return f"HATA: eksik parametre {e}"
        except OSError as e:
            return f"HATA: {type(e).__name__}: {e}"
        return f"HATA: bilinmeyen asistan araci '{tool}'"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agent/test_assistant_executor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/backends/assistant_executor.py tests/agent/test_assistant_executor.py
git commit -m "feat(agent): AssistantExecutor (jailed file ops, run_cmd->sandbox, web enjekte)"
```

---

### Task 7: CompositeExecutor (route by domain)

**Files:**
- Create: `agent/composite_executor.py`
- Test: `tests/agent/test_composite_executor.py`

**Interfaces:**
- Consumes: `Executor` Protocol, `get_spec`.
- Produces: `CompositeExecutor(security, assistant)` with `run(tool, params) -> str`; routes by
  `get_spec(tool).domain` (`asistan` → assistant, else → security, unknown → error string).

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_composite_executor.py
from agent.composite_executor import CompositeExecutor


class _Tag:
    def __init__(self, tag): self.tag = tag
    def run(self, tool, params): return f"{self.tag}:{tool}"


def test_routes_assistant_domain():
    ce = CompositeExecutor(security=_Tag("SEC"), assistant=_Tag("ASST"))
    assert ce.run("read_file", {"yol": "a"}) == "ASST:read_file"


def test_routes_security_domain():
    ce = CompositeExecutor(security=_Tag("SEC"), assistant=_Tag("ASST"))
    assert ce.run("nmap", {"hedef": "10.0.0.5"}) == "SEC:nmap"


def test_unknown_tool_is_error_string():
    ce = CompositeExecutor(security=_Tag("SEC"), assistant=_Tag("ASST"))
    assert "bilinmeyen" in ce.run("yok_boyle_arac", {}).lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_composite_executor.py -v`
Expected: FAIL — `ModuleNotFoundError: agent.composite_executor`

- [ ] **Step 3: Write minimal implementation**

```python
# agent/composite_executor.py
"""Domaine gore yonlendiren executor: asistan araclari -> AssistantExecutor;
diger (guvenlik) araclari -> secili guvenlik executor'i (Mock/Real/Docker).
Executor Protocol'unu uygular; asla firlatmaz."""
from __future__ import annotations

from agent.catalog import get_spec
from agent.executor import Executor


class CompositeExecutor:
    def __init__(self, security: Executor, assistant: Executor) -> None:
        self.security = security
        self.assistant = assistant

    def run(self, tool: str, params: dict) -> str:
        spec = get_spec(tool)
        if spec is None:
            return f"HATA: bilinmeyen arac '{tool}'"
        if spec.domain == "asistan":
            return self.assistant.run(tool, params)
        return self.security.run(tool, params)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agent/test_composite_executor.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/composite_executor.py tests/agent/test_composite_executor.py
git commit -m "feat(agent): CompositeExecutor — domaine gore asistan/guvenlik yonlendirme"
```

---

### Task 8: Registry integration + CLI wiring

**Files:**
- Modify: `agent/cli.py` (add an `--assistant` demo path wiring CompositeExecutor + AssistantExecutor)
- Test: `tests/agent/test_assistant_integration.py`

**Interfaces:**
- Consumes: all prior tasks + `ToolRegistry`, `LabPolicy`, `AuditLog`, `ToolCall`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_assistant_integration.py
from agent.audit import AuditLog
from agent.backends.assistant_executor import AssistantExecutor
from agent.composite_executor import CompositeExecutor
from agent.executor import MockExecutor
from agent.policy import LabPolicy
from agent.registry import ToolRegistry
from agent.toolcall import ToolCall


def _registry(tmp_path):
    pol = LabPolicy(scope=["10.0.0.0/24"], workspace_root=str(tmp_path), allow_high=False)
    execu = CompositeExecutor(security=MockExecutor(), assistant=AssistantExecutor(str(tmp_path)))
    return ToolRegistry(pol, execu, AuditLog.default())


def test_write_file_end_to_end(tmp_path):
    reg = _registry(tmp_path)
    out = reg.invoke(ToolCall(name="write_file", params={"yol": "a.txt", "icerik": "veri"}))
    assert "yazildi" in out
    assert (tmp_path / "a.txt").read_text(encoding="utf-8") == "veri"


def test_traversal_denied_never_writes(tmp_path):
    reg = _registry(tmp_path)
    out = reg.invoke(ToolCall(name="write_file", params={"yol": "../evil.txt", "icerik": "x"}))
    assert "REDDEDILDI" in out
    assert not (tmp_path.parent / "evil.txt").exists()   # diske hic dokunmadi


def test_run_cmd_needs_approval(tmp_path):
    reg = _registry(tmp_path)
    out = reg.invoke(ToolCall(name="run_cmd", params={"komut": "ls -la"}))
    assert "ONAY GEREKLI" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_assistant_integration.py -v`
Expected: FAIL — `TypeError` on `LabPolicy(workspace_root=...)` only if Task 5 missing; otherwise the
demo wiring assertion. (If Tasks 1-7 done, this should pass without cli change — see Step 3.)

- [ ] **Step 3: Wire the CLI demo path (make it runnable)**

Confirm the integration test passes as-is (it wires objects directly). Then add a user-facing demo
to `agent/cli.py` so `python -m agent.cli --assistant` exercises the path. Add this function:

```python
def run_assistant_demo(workspace: str | None = None) -> str:
    """Asistan araclari demo: gercek jailed dosya islemi + policy reddi (mock eller)."""
    import tempfile
    from agent.audit import AuditLog
    from agent.backends.assistant_executor import AssistantExecutor
    from agent.composite_executor import CompositeExecutor
    from agent.executor import MockExecutor
    from agent.policy import LabPolicy
    ws = workspace or tempfile.mkdtemp(prefix="octopus-ws-")
    execu = CompositeExecutor(security=MockExecutor(), assistant=AssistantExecutor(ws))
    registry = ToolRegistry(LabPolicy(scope=[], workspace_root=ws), execu, AuditLog.default())
    steps = [
        ToolCall(name="write_file", params={"yol": "not.txt", "icerik": "Octópus lab notu"}),
        ToolCall(name="read_file", params={"yol": "not.txt"}),
        ToolCall(name="write_file", params={"yol": "../kacis.txt", "icerik": "x"}),  # reddedilmeli
    ]
    lines = [f"[workspace] {ws}"]
    for c in steps:
        lines.append(f"[{c.name}] -> {registry.invoke(c)}")
    lines.append("(asistan demo bitti)")
    return "\n".join(lines)
```

Add `from agent.toolcall import ToolCall` to the imports if not present, and in `main()` add the flag
and route (before the `else` mock branch):

```python
    ap.add_argument("--assistant", action="store_true", help="asistan araclari demo (jailed file + policy)")
    ...
    elif args.assistant:
        print(run_assistant_demo())
```

- [ ] **Step 4: Run tests + smoke the CLI**

Run: `uv run pytest tests/agent/test_assistant_integration.py -v`
Expected: PASS
Run: `uv run python -m agent.cli --assistant`
Expected: writes `not.txt`, reads it back, and the `../kacis.txt` step prints `REDDEDILDI: ...`.
Run: `uv run python -m agent.cli` (mock security path)
Expected: still runs (existing demo unbroken).

- [ ] **Step 5: Commit**

```bash
git add agent/cli.py tests/agent/test_assistant_integration.py
git commit -m "feat(agent): asistan araclari uctan uca (registry+CompositeExecutor) + --assistant demo"
```

---

## Self-Review

**Spec coverage:**
- §5 catalog (8 tools, `asistan`) → Task 1 ✅
- §3.1 fs jail → Task 2 + Task 5 dispatch ✅
- §3.2 cmd denylist + isolation → Task 3 (denylist) + Task 6 (`run_cmd`→sandbox, never host) + Task 5 (high-risk approval) ✅
- §3.3 web SSRF → Task 4 + Task 5 dispatch ✅
- §4.1 CompositeExecutor → Task 7 ✅
- §4.2 AssistantExecutor → Task 6 ✅
- §4.3 policy dispatch → Task 5 ✅
- §8 acceptance (traversal denied never writes, SSRF denied, run_cmd never host, suite green) → Task 8 integration + Tasks 2/4/6 ✅

**Placeholder scan:** no TBD/TODO; every code step is complete runnable code.

**Type consistency:** guards all return `Decision(bool, bool, str)`; `guard(params, workspace_root)` (fs),
`guard(params)` (cmd), `guard(params, resolve=...)` (web) — matched in Task 5 dispatch. `AssistantExecutor`
and `CompositeExecutor` both implement `run(tool, params) -> str`. `LabPolicy.workspace_root` added in
Task 5, consumed in Tasks 5/8. `sandbox.run("run_cmd", params)` delegation matches `Executor.run`.

**Note (deferred, not blocking):** real Docker/WSL wiring of `run_cmd`'s sandbox (beyond MockExecutor)
and a real `web_search` backend are follow-ups — B1 proves the security path with injected fakes; B2/B3
supply data and a live backend.
