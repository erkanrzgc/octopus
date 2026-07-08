# Agent Harness (Phase 1 — skeleton) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **Note:** Code blocks below mirror the actual source in `agent/` — their inline comments/docstrings are in
> Turkish (the product is Turkish-first). The plan prose is English.

**Goal:** a working agentic-runtime skeleton that parses the v0.7 model's ```arac``` blocks, runs them (mock), and feeds the result back to the model — on Windows today, without running any real binary.

**Architecture:** small single-responsibility `agent/` modules. A data-driven 117-tool catalog (derived from training data) feeds the parser + registry + policy + mock executor + loop. The backend is abstract (`generate: list[Message] -> str`) → a mock/real model plugs in.

**Tech Stack:** Python 3.14, pytest, stdlib (dataclasses, re, json, subprocess[Phase 2]). NO new dependencies.

## Global Constraints

- Package manager: **uv**. Tests: `uv run pytest`. Venv: `.venv` (on an ASCII path).
- Brand: the model says "Ben Octópus" (ó) in speech; **code/files/paths are plain ASCII `agent/`**.
- Tool names + parameter keys are derived from training data — **`data/sft/tools/build_tools.py::MASTER_TOOLS` (117) is the canonical list**.
- The feedback format is identical to training: **reuse `data/sft/normalize.py::flatten_tool_messages`** (tool result → an "ARAÇ ÇIKTISI:\n…" user turn).
- Prefer immutable data types (`@dataclass(frozen=True)` where appropriate). Files < 400 lines.
- Every tool is authorization-gated: lab/CTF/authorized only. Policy defaults to lab-only.

---

### Task 1: Message data type + package skeleton

**Files:**
- Create: `agent/__init__.py`
- Create: `agent/messages.py`
- Create: `tests/agent/__init__.py`
- Test: `tests/agent/test_messages.py`

**Interfaces:**
- Produces: `Message(role: str, content: str)` — `.to_dict() -> dict[str, str]`; `Message.from_dict(d) -> Message`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_messages.py
from agent.messages import Message

def test_roundtrip_dict():
    m = Message(role="user", content="selam")
    assert m.to_dict() == {"role": "user", "content": "selam"}
    assert Message.from_dict({"role": "user", "content": "selam"}) == m
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_messages.py -v`
Expected: FAIL (`ModuleNotFoundError: agent.messages`)

- [ ] **Step 3: Write minimal implementation**

```python
# agent/__init__.py
"""Octópus agent harness — arac bloklarini parse edip calistiran runtime."""
```
```python
# tests/agent/__init__.py
```
```python
# agent/messages.py
"""Sohbet mesaji: rol + icerik. Roller: system|user|assistant|tool."""
from __future__ import annotations
from dataclasses import dataclass


@dataclass(frozen=True)
class Message:
    role: str
    content: str

    def to_dict(self) -> dict[str, str]:
        return {"role": self.role, "content": self.content}

    @classmethod
    def from_dict(cls, d: dict[str, str]) -> "Message":
        return cls(role=str(d["role"]), content=str(d["content"]))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agent/test_messages.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/__init__.py agent/messages.py tests/agent/__init__.py tests/agent/test_messages.py
git commit -m "feat(agent): Message veri tipi + paket iskeleti"
```

---

### Task 2: Tool catalog (117, derived from training data)

**Files:**
- Create: `agent/build_catalog.py` (generator script)
- Create: `agent/catalog.py` (ToolSpec + CATALOG loader)
- Create: `agent/catalog_data.py` (generated data — written by the script)
- Test: `tests/agent/test_catalog.py`

**Interfaces:**
- Produces: `ToolSpec(name: str, domain: str, risk: str, params: tuple[str, ...])`;
  `CATALOG: dict[str, ToolSpec]`; `get_spec(name: str) -> ToolSpec | None`.
- Consumes: `data/sft/tools/build_tools.py::MASTER_TOOLS`, `data/sft/tools/*.jsonl`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_catalog.py
from agent.catalog import CATALOG, get_spec, ToolSpec
from data.sft.tools.build_tools import MASTER_TOOLS

def test_all_master_tools_present():
    # Katalog kanonik 117 aracin HEPSINI kapsamali (parser/model eslesmesi).
    missing = [t for t in MASTER_TOOLS if t not in CATALOG]
    assert missing == [], f"katalogda eksik: {missing}"

def test_spec_shape():
    spec = get_spec("nmap")
    assert isinstance(spec, ToolSpec)
    assert spec.domain and spec.risk in {"low", "medium", "high"}
    assert "secenekler" in spec.params  # egitim verisinde nmap secenekler kullaniyor

def test_unknown_tool_is_none():
    assert get_spec("boyle_bir_arac_yok") is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_catalog.py -v`
Expected: FAIL (`ModuleNotFoundError: agent.catalog`)

- [ ] **Step 3: Write the generator**

```python
# agent/build_catalog.py
"""catalog_data.py'yi URET: MASTER_TOOLS (alan) + egitim verisi (parametreler) + alan->risk.
Kosul:  uv run python -m agent.build_catalog
Cikti sadece uretim; catalog.py runtime'da catalog_data.py'yi okur."""
from __future__ import annotations
import json, glob, re
from pathlib import Path
from collections import defaultdict
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data.sft.tools.build_tools import MASTER_TOOLS

ROOT = Path(__file__).resolve().parent.parent
ARAC_RE = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)

# MASTER_TOOLS'taki alan yorumlarindan alan haritasi (build_tools.py ile senkron).
DOMAINS: dict[str, list[str]] = {
    "recon-scan": ["nmap","rustscan","masscan","netdiscover","arp-scan","fping","ss"],
    "traffic-mitm": ["wireshark","tshark","tcpdump","bettercap","ettercap","mitmproxy","responder"],
    "osint": ["theHarvester","maltego","amass","subfinder","spiderfoot","recon-ng","sherlock","shodan",
              "dnsrecon","dnsenum","fierce","whois","dig","host"],
    "web": ["burpsuite","zap","nuclei","gobuster","ffuf","feroxbuster","dirsearch","dirb","nikto",
            "sqlmap","wpscan","wfuzz","arjun","paramspider","dalfox","xsstrike","httpx","katana","whatweb"],
    "exploit-ad": ["metasploit","msfvenom","searchsploit","sliver","netexec","bloodhound-python","impacket",
                   "secretsdump","evil-winrm","mimikatz","rubeus","routersploit","beef","enum4linux-ng",
                   "smbclient","smbmap"],
    "password": ["hydra","john","hashcat","medusa","hashid"],
    "wireless": ["aircrack-ng","airodump-ng","aireplay-ng","wifite","hcxdumptool","kismet","reaver","mdk4"],
    "forensic-re": ["volatility3","autopsy","sleuthkit","binwalk","foremost","ghidra","radare2","gdb",
                    "strings","yara","capa"],
    "privesc": ["linpeas","winpeas","shell"],
    "blue-server": ["fail2ban","iptables","nftables","ufw","auditd","osquery","wazuh","suricata","snort",
                    "clamav","lynis","rkhunter","chkrootkit","aide"],
    "cloud": ["trivy","prowler","scoutsuite","kube-hunter","kube-bench","docker-bench","checkov","tfsec"],
    "mobile-social": ["apktool","jadx","mobsf","gophish","setoolkit"],
}
# Alan -> varsayilan risk. Offansif=high, recon/pasif=low, savunma=low, degisiklik=medium.
DOMAIN_RISK = {
    "recon-scan": "low", "osint": "low", "blue-server": "low", "privesc": "high",
    "traffic-mitm": "high", "web": "medium", "exploit-ad": "high", "password": "high",
    "wireless": "high", "forensic-re": "low", "cloud": "low", "mobile-social": "medium",
}

def _domain_of(tool: str) -> str:
    for dom, tools in DOMAINS.items():
        if tool in tools:
            return dom
    return "other"

def _params_from_training() -> dict[str, list[str]]:
    tp: dict[str, set] = defaultdict(set)
    for f in glob.glob(str(ROOT / "data" / "sft" / "tools" / "*.jsonl")):
        if "build_tools" in f:
            continue
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            for m in o.get("messages", []):
                if m.get("role") != "assistant":
                    continue
                for blk in ARAC_RE.findall(m["content"]):
                    try:
                        d = json.loads(blk)
                    except Exception:
                        continue
                    t = d.get("arac")
                    if t:
                        tp[t].update((d.get("parametreler") or {}).keys())
    return {k: sorted(v) for k, v in tp.items()}

def main() -> None:
    params = _params_from_training()
    lines = ['"""URETILDI: agent/build_catalog.py. Elle duzenleme; yeniden uret."""', "CATALOG_DATA = ["]
    for t in MASTER_TOOLS:
        dom = _domain_of(t)
        risk = DOMAIN_RISK.get(dom, "medium")
        prm = params.get(t, ["secenekler"])  # egitimde yoksa makul varsayilan
        lines.append(f"    {{'name': {t!r}, 'domain': {dom!r}, 'risk': {risk!r}, 'params': {tuple(prm)!r}}},")
    lines.append("]")
    (ROOT / "agent" / "catalog_data.py").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] catalog_data.py yazildi: {len(MASTER_TOOLS)} arac")

if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the generator**

Run: `uv run python -m agent.build_catalog`
Expected: `[OK] catalog_data.py yazildi: 117 arac` (dosya `agent/catalog_data.py` olusur)

- [ ] **Step 5: Write catalog.py loader**

```python
# agent/catalog.py
"""117-arac katalog: TEK GERCEK KAYNAK. catalog_data.py'den ToolSpec yukler.
Yeniden uret:  uv run python -m agent.build_catalog"""
from __future__ import annotations
from dataclasses import dataclass
from agent.catalog_data import CATALOG_DATA


@dataclass(frozen=True)
class ToolSpec:
    name: str
    domain: str
    risk: str
    params: tuple[str, ...]


CATALOG: dict[str, ToolSpec] = {
    d["name"]: ToolSpec(name=d["name"], domain=d["domain"], risk=d["risk"], params=tuple(d["params"]))
    for d in CATALOG_DATA
}


def get_spec(name: str) -> ToolSpec | None:
    return CATALOG.get(name)
```

- [ ] **Step 6: Run tests to verify pass**

Run: `uv run pytest tests/agent/test_catalog.py -v`
Expected: PASS (3 test)

- [ ] **Step 7: Commit**

```bash
git add agent/build_catalog.py agent/catalog.py agent/catalog_data.py tests/agent/test_catalog.py
git commit -m "feat(agent): 117-arac katalog (egitim verisinden turetildi)"
```

---

### Task 3: arac block parser + feedback

**Files:**
- Create: `agent/toolcall.py`
- Test: `tests/agent/test_toolcall.py`

**Interfaces:**
- Consumes: `data/sft/normalize.py::flatten_tool_messages`, `agent.messages.Message`.
- Produces: `ToolCall(name: str, params: dict)`; `parse_arac_calls(text: str) -> list[ToolCall]`;
  `render_for_model(messages: list[Message]) -> list[dict]` (flatten reuse).

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_toolcall.py
from agent.toolcall import ToolCall, parse_arac_calls, render_for_model
from agent.messages import Message

def test_parse_single_call():
    txt = 'Tararim.\n```arac\n{"arac":"nmap","parametreler":{"hedef":"1.2.3.4","secenekler":"-sV"}}\n```'
    calls = parse_arac_calls(txt)
    assert len(calls) == 1
    assert calls[0].name == "nmap"
    assert calls[0].params == {"hedef": "1.2.3.4", "secenekler": "-sV"}

def test_malformed_skipped():
    txt = "```arac\n{bozuk json}\n```\n```arac\n{\"arac\":\"whois\",\"parametreler\":{}}\n```"
    calls = parse_arac_calls(txt)
    assert [c.name for c in calls] == ["whois"]

def test_no_calls_returns_empty():
    assert parse_arac_calls("Sadece Turkce cevap, arac yok.") == []

def test_render_flattens_tool_role():
    msgs = [Message("user", "tara"), Message("tool", "22/ssh 80/http")]
    out = render_for_model(msgs)
    # tool rolu -> user, "ARAC CIKTISI" oneki (Gemma-2 tool desteklemez)
    assert out[-1]["role"] == "user"
    assert "ARAÇ ÇIKTISI" in out[-1]["content"]
    assert "22/ssh 80/http" in out[-1]["content"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_toolcall.py -v`
Expected: FAIL (`ModuleNotFoundError: agent.toolcall`)

- [ ] **Step 3: Write minimal implementation**

```python
# agent/toolcall.py
"""arac blok parse + modele render. Format: ```arac {"arac":..,"parametreler":{..}} ```.
Geri-besleme egitimle birebir: normalize.flatten_tool_messages reuse (tool->user 'ARAC CIKTISI')."""
from __future__ import annotations
from dataclasses import dataclass
import json
import re
from agent.messages import Message
from data.sft.normalize import flatten_tool_messages

_ARAC_RE = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)


@dataclass(frozen=True)
class ToolCall:
    name: str
    params: dict


def parse_arac_calls(text: str) -> list[ToolCall]:
    """Metindeki her ```arac``` blogunu ToolCall'a cevir; bozuk/eksik blogu atla (asla cokme)."""
    calls: list[ToolCall] = []
    for m in _ARAC_RE.finditer(text or ""):
        try:
            d = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if not isinstance(d, dict) or "arac" not in d:
            continue
        calls.append(ToolCall(name=str(d["arac"]), params=dict(d.get("parametreler") or {})))
    return calls


def render_for_model(messages: list[Message]) -> list[dict]:
    """Message listesini modele verilecek dict listesine cevir (tool rolu flatten'lanir)."""
    return flatten_tool_messages([m.to_dict() for m in messages])
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/agent/test_toolcall.py -v`
Expected: PASS (4 test)

- [ ] **Step 5: Commit**

```bash
git add agent/toolcall.py tests/agent/test_toolcall.py
git commit -m "feat(agent): arac blok parser + flatten geri-besleme"
```

---

### Task 4: LabPolicy (authorization/risk gate)

**Files:**
- Create: `agent/policy.py`
- Test: `tests/agent/test_policy.py`

**Interfaces:**
- Consumes: `agent.catalog.ToolSpec`.
- Produces: `Decision(allowed: bool, requires_approval: bool, reason: str)`;
  `LabPolicy(scope: list[str], allow_high: bool = False)`; `.default() -> LabPolicy`;
  `.decide(spec: ToolSpec, params: dict) -> Decision`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_policy.py
from agent.policy import LabPolicy, Decision
from agent.catalog import ToolSpec

low = ToolSpec("nmap", "recon-scan", "low", ("hedef", "secenekler"))
high = ToolSpec("msfvenom", "exploit-ad", "high", ("secenekler",))

def test_low_risk_in_scope_allowed():
    p = LabPolicy(scope=["10.10.10.0/24"])
    d = p.decide(low, {"hedef": "10.10.10.5"})
    assert d.allowed and not d.requires_approval

def test_out_of_scope_denied():
    p = LabPolicy(scope=["10.10.10.0/24"])
    d = p.decide(low, {"hedef": "8.8.8.8"})
    assert not d.allowed and "kapsam" in d.reason.lower()

def test_high_risk_requires_approval():
    p = LabPolicy(scope=["10.10.10.0/24"], allow_high=False)
    d = p.decide(high, {})
    assert not d.allowed and d.requires_approval

def test_no_scope_means_lab_only_deny_targeted():
    p = LabPolicy.default()  # bos kapsam = hicbir dis hedef
    d = p.decide(low, {"hedef": "10.10.10.5"})
    assert not d.allowed
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_policy.py -v`
Expected: FAIL (`ModuleNotFoundError: agent.policy`)

- [ ] **Step 3: Write minimal implementation**

```python
# agent/policy.py
"""Lab-only yetki + risk kapisi. Varsayilan: dis hedef yok, high-risk onay ister.
Hedef IP/CIDR kapsam allow-list'iyle karsilastirilir; kapsam disi -> reddet (modelin
kendi reddiyle cift kilit)."""
from __future__ import annotations
from dataclasses import dataclass, field
import ipaddress
from agent.catalog import ToolSpec

# Hedef tasiyan parametre anahtarlari (egitim verisinden).
_TARGET_KEYS = ("hedef", "url", "hedef_url", "domain")


@dataclass(frozen=True)
class Decision:
    allowed: bool
    requires_approval: bool
    reason: str


@dataclass
class LabPolicy:
    scope: list[str] = field(default_factory=list)  # izinli IP/CIDR (bos = dis hedef yok)
    allow_high: bool = False

    @classmethod
    def default(cls) -> "LabPolicy":
        return cls(scope=[], allow_high=False)

    def _target(self, params: dict) -> str | None:
        for k in _TARGET_KEYS:
            if k in params and params[k]:
                return str(params[k])
        return None

    def _in_scope(self, target: str) -> bool:
        # IP/CIDR ise kapsamla karsilastir; degilse (domain vs) kapsam bos degilse ret.
        for cidr in self.scope:
            try:
                net = ipaddress.ip_network(cidr, strict=False)
                host = target.split(":")[0].split("/")[0]
                if ipaddress.ip_address(host) in net:
                    return True
            except ValueError:
                if target == cidr:
                    return True
        return False

    def decide(self, spec: ToolSpec, params: dict) -> Decision:
        target = self._target(params)
        if target is not None and not self._in_scope(target):
            return Decision(False, False, f"hedef '{target}' izinli kapsam disinda (lab-only)")
        if spec.risk == "high" and not self.allow_high:
            return Decision(False, True, f"'{spec.name}' yuksek riskli, acik onay gerekir")
        return Decision(True, False, "izinli")
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/agent/test_policy.py -v`
Expected: PASS (4 test)

- [ ] **Step 5: Commit**

```bash
git add agent/policy.py tests/agent/test_policy.py
git commit -m "feat(agent): LabPolicy yetki/risk kapisi"
```

---

### Task 5: AuditLog

**Files:**
- Create: `agent/audit.py`
- Test: `tests/agent/test_audit.py`

**Interfaces:**
- Produces: `AuditLog(path: Path)`; `.write(event: str, detail: str) -> None`; `.default() -> AuditLog`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_audit.py
import json
from agent.audit import AuditLog

def test_write_appends_jsonl(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    log.write("tool.start", "nmap")
    log.write("tool.done", "3 port")
    lines = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    rec = json.loads(lines[0])
    assert rec["event"] == "tool.start" and rec["detail"] == "nmap" and "ts" in rec
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_audit.py -v`
Expected: FAIL (`ModuleNotFoundError: agent.audit`)

- [ ] **Step 3: Write minimal implementation**

```python
# agent/audit.py
"""Denetim gunlugu: her arac cagrisi jsonl'e (event, detail, zaman)."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path


@dataclass
class AuditLog:
    path: Path

    @classmethod
    def default(cls) -> "AuditLog":
        return cls(Path("lab") / "logs" / "audit.jsonl")

    def write(self, event: str, detail: str) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        rec = {"ts": datetime.now(timezone.utc).isoformat(), "event": event, "detail": detail}
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/agent/test_audit.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/audit.py tests/agent/test_audit.py
git commit -m "feat(agent): AuditLog jsonl denetim gunlugu"
```

---

### Task 6: Executor protocol + MockExecutor

**Files:**
- Create: `agent/executor.py`
- Test: `tests/agent/test_executor.py`

**Interfaces:**
- Consumes: `agent.catalog.CATALOG`, `agent.catalog.ToolSpec`.
- Produces: `Executor` (Protocol: `run(tool: str, params: dict) -> str`);
  `MockExecutor()` alan-bazli gercekci sahte cikti.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_executor.py
from agent.executor import MockExecutor

def test_scan_domain_returns_ports():
    out = MockExecutor().run("nmap", {"hedef": "10.10.10.5", "secenekler": "-sV"})
    assert "10.10.10.5" in out and "/" in out  # port listesi gibi

def test_unknown_tool_message():
    out = MockExecutor().run("boyle_arac_yok", {})
    assert "bilinmeyen" in out.lower()

def test_output_is_str():
    assert isinstance(MockExecutor().run("whois", {"hedef": "ornek.com"}), str)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_executor.py -v`
Expected: FAIL (`ModuleNotFoundError: agent.executor`)

- [ ] **Step 3: Write minimal implementation**

```python
# agent/executor.py
"""Araci calistiran katman. Faz 1: MockExecutor (alan-bazli gercekci sahte cikti) —
gercek binary YOK, Windows'ta calisir. Faz 2: RealExecutor (WSL2/Kali subprocess)."""
from __future__ import annotations
from typing import Protocol
from agent.catalog import get_spec


class Executor(Protocol):
    def run(self, tool: str, params: dict) -> str: ...


def _target(params: dict) -> str:
    for k in ("hedef", "url", "hedef_url", "domain", "arayuz", "dosya"):
        if params.get(k):
            return str(params[k])
    return "hedef"


class MockExecutor:
    """Alan-bazli gercekci sahte cikti (egitim verisi tarzinda). Gercekten calistirmaz."""

    def run(self, tool: str, params: dict) -> str:
        spec = get_spec(tool)
        if spec is None:
            return f"HATA: bilinmeyen arac '{tool}'"
        t = _target(params)
        dom = spec.domain
        if dom in {"recon-scan"}:
            return f"{t} -> 22/ssh 80/http 443/https 445/smb  (mock tarama)"
        if dom == "web":
            return f"{t}: olasi zafiyet — /admin (200), SQLi parametre id (mock)"
        if dom in {"exploit-ad", "password"}:
            return f"{tool}: mock sonuc — kimlik/oturum elde edildi (lab)"
        if dom == "osint":
            return f"{t}: 3 alt alan, 2 e-posta, 1 acik port (mock OSINT)"
        return f"{tool} calisti (mock, alan={dom}), hedef={t}"
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/agent/test_executor.py -v`
Expected: PASS (3 test)

- [ ] **Step 5: Commit**

```bash
git add agent/executor.py tests/agent/test_executor.py
git commit -m "feat(agent): Executor protokolu + MockExecutor"
```

---

### Task 7: ToolRegistry (catalog + policy + executor + audit)

**Files:**
- Create: `agent/registry.py`
- Test: `tests/agent/test_registry.py`

**Interfaces:**
- Consumes: `agent.catalog`, `agent.policy.LabPolicy`, `agent.executor.Executor`, `agent.audit.AuditLog`,
  `agent.toolcall.ToolCall`.
- Produces: `ToolRegistry(policy, executor, audit)`; `.invoke(call: ToolCall) -> str`;
  `.tool_names() -> list[str]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_registry.py
from agent.registry import ToolRegistry
from agent.policy import LabPolicy
from agent.executor import MockExecutor
from agent.audit import AuditLog
from agent.toolcall import ToolCall

def _reg(tmp_path, scope=None, allow_high=False):
    return ToolRegistry(
        policy=LabPolicy(scope=scope or ["10.10.10.0/24"], allow_high=allow_high),
        executor=MockExecutor(),
        audit=AuditLog(tmp_path / "a.jsonl"),
    )

def test_invoke_in_scope_runs(tmp_path):
    out = _reg(tmp_path).invoke(ToolCall("nmap", {"hedef": "10.10.10.5", "secenekler": "-sV"}))
    assert "10.10.10.5" in out

def test_invoke_out_of_scope_returns_policy_reason(tmp_path):
    out = _reg(tmp_path).invoke(ToolCall("nmap", {"hedef": "8.8.8.8"}))
    assert "kapsam" in out.lower()

def test_invoke_unknown_tool(tmp_path):
    out = _reg(tmp_path).invoke(ToolCall("yok_boyle", {}))
    assert "bilinmeyen" in out.lower()

def test_high_risk_blocked_without_approval(tmp_path):
    out = _reg(tmp_path).invoke(ToolCall("msfvenom", {"secenekler": "-p x"}))
    assert "onay" in out.lower()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_registry.py -v`
Expected: FAIL (`ModuleNotFoundError: agent.registry`)

- [ ] **Step 3: Write minimal implementation**

```python
# agent/registry.py
"""Katalog + policy + executor + audit'i baglar. invoke(): yetki kontrol -> calistir -> logla.
Asla exception firlatmaz; hatayi metin olarak modele geri dondurur (dongu olmesin)."""
from __future__ import annotations
from dataclasses import dataclass
from agent.audit import AuditLog
from agent.catalog import CATALOG, get_spec
from agent.executor import Executor, MockExecutor
from agent.policy import LabPolicy
from agent.toolcall import ToolCall


@dataclass
class ToolRegistry:
    policy: LabPolicy
    executor: Executor
    audit: AuditLog

    @classmethod
    def default(cls) -> "ToolRegistry":
        return cls(LabPolicy.default(), MockExecutor(), AuditLog.default())

    def tool_names(self) -> list[str]:
        return list(CATALOG)

    def invoke(self, call: ToolCall) -> str:
        self.audit.write("tool.start", f"{call.name} {call.params}")
        spec = get_spec(call.name)
        if spec is None:
            msg = f"HATA: bilinmeyen arac '{call.name}'"
            self.audit.write("tool.error", msg)
            return msg
        decision = self.policy.decide(spec, call.params)
        if not decision.allowed:
            kind = "tool.policy.approval" if decision.requires_approval else "tool.policy.deny"
            self.audit.write(kind, decision.reason)
            prefix = "ONAY GEREKLI" if decision.requires_approval else "REDDEDILDI"
            return f"{prefix}: {decision.reason}"
        try:
            out = self.executor.run(call.name, call.params)
        except Exception as exc:  # noqa: BLE001 - modele bildir, cokme
            out = f"HATA: {type(exc).__name__}: {exc}"
        self.audit.write("tool.done", f"{call.name} -> {out[:80]}")
        return out
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/agent/test_registry.py -v`
Expected: PASS (4 test)

- [ ] **Step 5: Commit**

```bash
git add agent/registry.py tests/agent/test_registry.py
git commit -m "feat(agent): ToolRegistry (katalog+policy+executor+audit)"
```

---

### Task 8: Loop (run_tool_loop)

**Files:**
- Create: `agent/loop.py`
- Test: `tests/agent/test_loop.py`

**Interfaces:**
- Consumes: `agent.messages.Message`, `agent.toolcall.parse_arac_calls`, `agent.registry.ToolRegistry`.
- Produces: `ToolLoopResult(final: str, steps: int, calls: list)`;
  `run_tool_loop(messages, generate, registry, max_steps=10) -> ToolLoopResult`
  where `generate: Callable[[list[Message]], str]`.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_loop.py
from agent.loop import run_tool_loop, ToolLoopResult
from agent.messages import Message
from agent.registry import ToolRegistry
from agent.policy import LabPolicy
from agent.executor import MockExecutor
from agent.audit import AuditLog

def _reg(tmp_path):
    return ToolRegistry(LabPolicy(scope=["10.10.10.0/24"]), MockExecutor(), AuditLog(tmp_path / "a.jsonl"))

def test_single_tool_then_final(tmp_path):
    # scripted model: 1. tur arac cagirir, 2. tur duz cevap
    scripted = iter([
        '```arac\n{"arac":"nmap","parametreler":{"hedef":"10.10.10.5","secenekler":"-sV"}}\n```',
        "Tarama bitti: 3 acik port var.",
    ])
    def generate(msgs): return next(scripted)
    res = run_tool_loop([Message("user", "tara")], generate, _reg(tmp_path))
    assert isinstance(res, ToolLoopResult)
    assert res.steps == 2 and "3 acik port" in res.final
    assert len(res.calls) == 1

def test_plain_answer_no_tools(tmp_path):
    res = run_tool_loop([Message("user", "selam")], lambda m: "Merhaba, ben Octópus.", _reg(tmp_path))
    assert res.steps == 1 and "Octópus" in res.final and res.calls == []

def test_max_steps_guard(tmp_path):
    # her turda arac cagiran sonsuz model -> max_steps'te durur
    call = '```arac\n{"arac":"nmap","parametreler":{"hedef":"10.10.10.5"}}\n```'
    res = run_tool_loop([Message("user", "x")], lambda m: call, _reg(tmp_path), max_steps=3)
    assert res.steps == 3
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_loop.py -v`
Expected: FAIL (`ModuleNotFoundError: agent.loop`)

- [ ] **Step 3: Write minimal implementation**

```python
# agent/loop.py
"""Model<->arac dongusu (Hermes recursive loop deseni, agentic-model'den uyarlandi).
model uret -> arac blogu var mi? yoksa nihai cevap; varsa calistir, sonucu tool mesaji
olarak ekle, tekrarla. max_steps sonsuz-dongu korumasi."""
from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass, field
from agent.messages import Message
from agent.registry import ToolRegistry
from agent.toolcall import ToolCall, parse_arac_calls

Generate = Callable[[list[Message]], str]


@dataclass
class ToolLoopResult:
    final: str
    steps: int
    calls: list[ToolCall] = field(default_factory=list)


def run_tool_loop(
    messages: list[Message],
    generate: Generate,
    registry: ToolRegistry,
    *,
    max_steps: int = 10,
) -> ToolLoopResult:
    executed: list[ToolCall] = []
    for step in range(max_steps):
        reply = generate(messages)
        messages.append(Message("assistant", reply))
        calls = parse_arac_calls(reply)
        if not calls:
            return ToolLoopResult(final=reply, steps=step + 1, calls=executed)
        for call in calls:
            result = registry.invoke(call)
            executed.append(call)
            messages.append(Message("tool", result))
    final = generate(messages)
    messages.append(Message("assistant", final))
    return ToolLoopResult(final=final, steps=max_steps, calls=executed)
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/agent/test_loop.py -v`
Expected: PASS (3 test)

- [ ] **Step 5: Commit**

```bash
git add agent/loop.py tests/agent/test_loop.py
git commit -m "feat(agent): run_tool_loop model<->arac dongusu"
```

---

### Task 9: Mock model backend

**Files:**
- Create: `agent/backends/__init__.py`
- Create: `agent/backends/mock_model.py`
- Test: `tests/agent/test_mock_model.py`

**Interfaces:**
- Consumes: `agent.messages.Message`.
- Produces: `ScriptedModel(replies: list[str])` — `__call__(messages: list[Message]) -> str`
  (sirayla yanit dondurur, tukenince duz cevap).

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_mock_model.py
from agent.backends.mock_model import ScriptedModel
from agent.messages import Message

def test_returns_replies_in_order():
    m = ScriptedModel(["birinci", "ikinci"])
    assert m([Message("user", "x")]) == "birinci"
    assert m([Message("user", "x")]) == "ikinci"

def test_exhausted_returns_default():
    m = ScriptedModel([])
    assert isinstance(m([Message("user", "x")]), str)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_mock_model.py -v`
Expected: FAIL (`ModuleNotFoundError: agent.backends.mock_model`)

- [ ] **Step 3: Write minimal implementation**

```python
# agent/backends/__init__.py
```
```python
# agent/backends/mock_model.py
"""Scripted model backend: onceden verilen yanitlari sirayla dondurur (test + demo).
Gercek model (GGUF/HF) Faz 2'de ayni __call__(messages)->str arayuzune takilir."""
from __future__ import annotations
from agent.messages import Message

_DEFAULT = "Ben Octópus. Baska bir sey ekleyemiyorum (mock)."


class ScriptedModel:
    def __init__(self, replies: list[str]) -> None:
        self._replies = list(replies)
        self._i = 0

    def __call__(self, messages: list[Message]) -> str:
        if self._i < len(self._replies):
            r = self._replies[self._i]
            self._i += 1
            return r
        return _DEFAULT
```

- [ ] **Step 4: Run tests to verify pass**

Run: `uv run pytest tests/agent/test_mock_model.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add agent/backends/__init__.py agent/backends/mock_model.py tests/agent/test_mock_model.py
git commit -m "feat(agent): ScriptedModel mock backend"
```

---

### Task 10: CLI (end-to-end demo) + full test run

**Files:**
- Create: `agent/cli.py`
- Test: `tests/agent/test_cli.py`

**Interfaces:**
- Consumes: `agent.loop.run_tool_loop`, `agent.registry.ToolRegistry`, `agent.backends.mock_model.ScriptedModel`,
  `agent.messages.Message`.
- Produces: `run_demo(scope: list[str]) -> str` (scripted end-to-end turn, returns transcript text);
  `main()` (argparse giris).

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_cli.py
from agent.cli import run_demo

def test_demo_runs_end_to_end():
    transcript = run_demo(scope=["10.10.10.0/24"])
    assert "nmap" in transcript
    assert "ARAÇ ÇIKTISI" in transcript or "10.10.10.5" in transcript
    assert transcript.strip().endswith("(demo bitti)")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_cli.py -v`
Expected: FAIL (`ModuleNotFoundError: agent.cli`)

- [ ] **Step 3: Write minimal implementation**

```python
# agent/cli.py
"""Uctan uca demo/giris. run_demo: scripted modelle tam tur (Windows'ta calisir).
Faz 2'de ScriptedModel yerine gercek GGUF modeli takilir, ayni dongu."""
from __future__ import annotations
import argparse
from agent.backends.mock_model import ScriptedModel
from agent.loop import run_tool_loop
from agent.messages import Message
from agent.registry import ToolRegistry


def run_demo(scope: list[str]) -> str:
    from agent.policy import LabPolicy
    from agent.executor import MockExecutor
    from agent.audit import AuditLog
    registry = ToolRegistry(LabPolicy(scope=scope), MockExecutor(), AuditLog.default())
    model = ScriptedModel([
        'Yetkili testte tararim.\n```arac\n{"arac":"nmap","parametreler":'
        '{"hedef":"10.10.10.5","secenekler":"-sV"}}\n```',
        "Tarama tamam: SSH/HTTP/SMB acik. Sirada web yuzeyini inceleyebilirim.",
    ])
    msgs = [Message("user", "10.10.10.5 hedefini yetkili testte tara")]
    result = run_tool_loop(msgs, model, registry)
    lines = [f"[{m.role}] {m.content}" for m in msgs]
    lines.append(f"(adim={result.steps}, cagri={len(result.calls)}) (demo bitti)")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="Octópus agent harness demo (Faz 1, mock)")
    ap.add_argument("--scope", nargs="*", default=["10.10.10.0/24"], help="izinli IP/CIDR")
    args = ap.parse_args()
    print(run_demo(args.scope))


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run full agent test suite**

Run: `uv run pytest tests/agent/ -v`
Expected: PASS (tum modul testleri, ~24 test)

- [ ] **Step 5: Manual smoke — CLI works**

Run: `uv run python -m agent.cli --scope 10.10.10.0/24`
Expected: transcript basilir, nmap araci cagrilir, "ARAÇ ÇIKTISI" geri beslenir, "(demo bitti)" ile biter.

- [ ] **Step 6: Commit**

```bash
git add agent/cli.py tests/agent/test_cli.py
git commit -m "feat(agent): CLI uctan uca demo (Faz 1 iskelet tamam)"
```

---

## Phase 2 (OUT of scope for this plan — a separate plan later)

- `agent/backends/gguf_model.py` — the real v0.7 model (GGUF Q4, llama.cpp) `__call__(messages)->str`;
  flatten + chat template via `render_for_model`.
- `agent/executor.py::RealExecutor` — WSL2/Kali subprocess, command template, timeout, policy-gated.
- Add a `command_template` field to the catalog (for the real CLI).
- Policy hardening: high-risk approval flow, dry-run mode, scope file.

## Self-Review (author check)

- **Spec coverage:** parser(T3)·catalog(T2)·registry(T7)·policy(T4)·executor(T6)·loop(T8)·audit(T5)·
  backend(T9)·CLI(T10)·flatten-reuse(T3) → all mapped to tasks ✅. Phase 2 marked out of scope.
- **Placeholder scan:** every step has real code, no TBD/TODO ✅.
- **Type consistency:** `Message(role,content)`, `ToolCall(name,params)`, `ToolSpec(name,domain,risk,params)`,
  `Decision(allowed,requires_approval,reason)`, `run_tool_loop(...)->ToolLoopResult` consistent across tasks ✅.
