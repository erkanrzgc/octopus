# Skill Layer — Pilot Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the Octópus agent harness a runtime skill layer so the model reads a tool's correct-usage `.md` *before* the harness executes that tool (post-call correction), plus load the existing methodology skills and a small set of workflow skills — measured on a pilot of ~10 tools + 4 workflows.

**Architecture:** A new pure module `agent/skills.py` discovers and loads three skill families (tool skills `agent/skills/tools/`, workflow skills `agent/skills/workflows/`, methodology skills `rag/knowledge/methodologies/`) from YAML-frontmatter markdown. `run_tool_loop` gains an optional `skills` parameter: after parsing an `arac` block, if a called tool has a skill not yet shown this conversation, the harness injects that tool's `.md` as a **user** turn and regenerates so the model can revise its call; each tool is injected at most once (cache). When `skills=None`, the loop behaves exactly as today (backward compatible).

**Tech Stack:** Python 3.10+, stdlib + `pyyaml` (already transitive via huggingface-hub), pytest. No network at load time; skills are version-controlled data files.

## Global Constraints

- **No new heavy deps.** Only `pyyaml` is added, and it is already installed transitively — add it explicitly to `pyproject.toml` `dependencies`.
- **Backward compatibility (HARD):** `run_tool_loop(messages, generate, registry)` with no `skills` arg MUST keep current behavior. All existing `tests/agent/test_loop.py` tests pass unchanged.
- **Loop never crashes.** Skill loading/matching failures degrade to "no skill" — never raise into the loop (mirror `registry.invoke` discipline).
- **Language:** skill file bodies + injection text are Turkish (product is Turkish-first internally); tool names, flags, CVE-IDs, commands stay verbatim/English.
- **Loader selects real skills only:** a `.md` counts as a skill iff its YAML frontmatter has BOTH `name` and `description`. Methodology dir is scanned **non-recursively** (excludes the `osint/` subpack, `AGENTS.md`, `SOURCE.md`, `_scope-guard.md`).
- **Tool-skill injection is a `user` turn** (never `tool` — `flatten_tool_messages` would mislabel it "ARAÇ ÇIKTISI:").
- **Pilot scope only.** Do NOT auto-generate all 117 tool stubs in this plan; that generator is the post-pilot scaling step (see Out of Scope).
- **Branch sync:** commit on `feat/b2-assistant-sft-data`; after the plan lands and tests are green, fast-forward `main` (`git push origin feat/b2-assistant-sft-data:main`) per the branch-sync rule.

---

## File Structure

| File | Responsibility | New/Modify |
|---|---|---|
| `agent/skills.py` | Skill dataclass, frontmatter parser, `SkillLibrary` (load/get/match_tool/match/manifest_text), injection formatter | Create |
| `agent/skills/tools/*.md` | 10 pilot tool skills (canonical syntax, key flags, pitfalls, safety) | Create |
| `agent/skills/workflows/*.md` | 4 workflow skills (methodology-of-work) | Create |
| `agent/loop.py` | Add optional `skills` param + post-call correction (inject-once cache) | Modify |
| `rag/knowledge/methodologies/*.md` | Existing methodology skills — wired in by loader, unchanged | Read-only |
| `pyproject.toml` | Add `pyyaml` to dependencies | Modify |
| `tests/agent/test_skills.py` | Loader unit tests | Create |
| `tests/agent/test_loop_skills.py` | Correction-loop integration tests | Create |
| `eval/skill_correction_eval.py` | Fabricated-flag / correct-usage eval (real model, Ollama-gated) | Create |
| `tests/eval/test_skill_correction_eval.py` | Scripted-model proxy test of the eval harness | Create |

Pilot tools (13): 10 already in catalog — **nmap, masscan, gobuster, ffuf, sqlmap, nikto, nuclei, metasploit, netexec, hydra** — plus 3 runtime-added in Task 0 — **trufflehog, magika, ghunt**.
Pilot workflows: **engagement-plan, finding-synthesis, report-write, verify-before-claim**.

Catalog-extension files (Task 0):

| File | Responsibility | New/Modify |
|---|---|---|
| `agent/build_catalog.py` | Add `EXTENSION_TOOLS` (trufflehog/magika/ghunt) alongside `ASSISTANT_TOOLS`; emit into `catalog_data.py` | Modify |
| `agent/catalog_data.py` | Regenerated output (117 security + 10 assistant + 3 extension) | Regenerate |
| `agent/catalog.py` | Docstring "117-arac" → "117 güvenlik + eklenti" | Modify |
| `tests/agent/test_catalog.py` | Assert the 3 extension tools are present + specs valid | Modify |

---

### Task 0: Catalog extension — trufflehog / magika / ghunt (runtime-added tools)

**Why:** The skill layer lets us add tools WITHOUT retraining — the model learns them from the injected skill md. These 3 real tools fill catalog gaps (secret-scan, ML file-type/forensics, Google OSINT). `MASTER_TOOLS` (the *trained* 117) stays pure; the 3 are added via a new explicit `EXTENSION_TOOLS` list (same pattern as `ASSISTANT_TOOLS`).

**Files:**
- Modify: `agent/build_catalog.py`
- Regenerate: `agent/catalog_data.py`
- Modify: `agent/catalog.py` (docstring only)
- Modify: `tests/agent/test_catalog.py`

**Interfaces:**
- Produces: `get_spec("trufflehog")`, `get_spec("magika")`, `get_spec("ghunt")` return valid `ToolSpec`s. Domains/risks/params:
  - `trufflehog` — domain `secrets`, risk `low`, params `("kaynak", "hedef")` (`kaynak`=git/github/s3/filesystem/docker; `hedef`=uri/org/bucket — a TARGET_KEY, so scope-gated).
  - `magika` — domain `forensic-re`, risk `low`, params `("yol",)` (local file → NOT scope-gated).
  - `ghunt` — domain `osint`, risk `low`, params `("modul", "hedef")` (`modul`=email/gaia/drive/geolocate; `hedef` scope-gated — targeting a real account needs authorization).

- [ ] **Step 1: Write the failing catalog test**

Add to `tests/agent/test_catalog.py`:

```python
def test_extension_tools_present():
    for name in ("trufflehog", "magika", "ghunt"):
        spec = get_spec(name)
        assert spec is not None, name
        assert spec.risk in {"low", "medium", "high"}
        assert spec.domain and spec.params


def test_extension_tool_domains():
    assert get_spec("trufflehog").domain == "secrets"
    assert get_spec("magika").domain == "forensic-re"
    assert get_spec("ghunt").domain == "osint"
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/agent/test_catalog.py::test_extension_tools_present -v`
Expected: FAIL — `get_spec("trufflehog")` is None.

- [ ] **Step 3: Add `EXTENSION_TOOLS` to `agent/build_catalog.py`**

After the `ASSISTANT_TOOLS` list, add:

```python
# Runtime-eklenen araclar (egitim evreninde YOK; skill katmani modele tanitir).
# MASTER_TOOLS'u KIRLETME — bu 3'u ayri, explicit domain/risk/param ile ekle.
EXTENSION_TOOLS: list[dict] = [
    {"name": "trufflehog", "domain": "secrets",     "risk": "low", "params": ("kaynak", "hedef")},
    {"name": "magika",     "domain": "forensic-re", "risk": "low", "params": ("yol",)},
    {"name": "ghunt",      "domain": "osint",       "risk": "low", "params": ("modul", "hedef")},
]
```

Then, in `main()`, after the `ASSISTANT_TOOLS` emit loop and before `lines.append("]")`, add:

```python
    for e in EXTENSION_TOOLS:
        lines.append(f"    {{'name': {e['name']!r}, 'domain': {e['domain']!r}, "
                     f"'risk': {e['risk']!r}, 'params': {tuple(e['params'])!r}}},")
```

And update the final print to include the extension count:

```python
    print(f"[OK] catalog_data.py yazildi: {len(MASTER_TOOLS)} guvenlik + "
          f"{len(ASSISTANT_TOOLS)} asistan + {len(EXTENSION_TOOLS)} eklenti araci")
```

- [ ] **Step 4: Regenerate the catalog**

Run: `uv run python -m agent.build_catalog`
Expected: prints `117 guvenlik + 10 asistan + 3 eklenti araci`; `agent/catalog_data.py` now ends with the 3 extension dicts.

- [ ] **Step 5: Run the catalog tests**

Run: `uv run pytest tests/agent/test_catalog.py -v`
Expected: all PASS (including the new extension tests + existing `test_all_master_tools_present`).

- [ ] **Step 6: Update the catalog docstring**

In `agent/catalog.py`, change the first docstring line:

```python
"""117 guvenlik + 10 asistan + 3 runtime-eklenti araci: TEK GERCEK KAYNAK. catalog_data.py'den ToolSpec yukler.
```

- [ ] **Step 7: Commit**

```bash
git add agent/build_catalog.py agent/catalog_data.py agent/catalog.py tests/agent/test_catalog.py
git commit -m "feat(catalog): add trufflehog/magika/ghunt as runtime-extension tools (EXTENSION_TOOLS)"
```

---

### Task 1: `agent/skills.py` — loader + frontmatter + matching

**Files:**
- Create: `agent/skills.py`
- Create: `tests/agent/test_skills.py`
- Modify: `pyproject.toml` (add `pyyaml>=6.0`)

**Interfaces:**
- Produces:
  - `Skill(name: str, description: str, body: str, kind: str, tool: str | None, path: str)` — frozen dataclass. `kind` ∈ {"tool","workflow","methodology"}.
  - `parse_frontmatter(text: str) -> tuple[dict, str]` — returns (metadata, body); `({}, text)` when no leading `---` block.
  - `SkillLibrary` with:
    - `load(root: Path = Path(".")) -> SkillLibrary`
    - `match_tool(tool_name: str) -> Skill | None`
    - `get(name: str) -> Skill | None`
    - `match(query: str) -> list[Skill]` (keyword overlap over workflow+methodology name/description)
    - `manifest_text(kinds: tuple[str, ...] = ("tool","workflow","methodology")) -> str`
    - `tool_skill_injection(skill: Skill) -> str`
    - fields: `tools: dict[str, Skill]`, `workflows: dict[str, Skill]`, `methodologies: dict[str, Skill]`

- [ ] **Step 1: Add pyyaml dependency**

In `pyproject.toml`, add to `[project].dependencies`:

```toml
    "pyyaml>=6.0",
```

Then verify it imports:

Run: `uv run python -c "import yaml; print(yaml.__version__)"`
Expected: prints a version (e.g. `6.0.x`), no error.

- [ ] **Step 2: Write the failing test for frontmatter parsing**

Create `tests/agent/test_skills.py`:

```python
from pathlib import Path
from agent.skills import parse_frontmatter, Skill, SkillLibrary


def test_parse_frontmatter_extracts_meta_and_body():
    text = "---\nname: nmap\ndescription: port tarayici\ntool: nmap\n---\n\nGovde metni.\n"
    meta, body = parse_frontmatter(text)
    assert meta["name"] == "nmap"
    assert meta["description"] == "port tarayici"
    assert meta["tool"] == "nmap"
    assert body.strip() == "Govde metni."


def test_parse_frontmatter_no_frontmatter_returns_empty_meta():
    meta, body = parse_frontmatter("# Just markdown\nno frontmatter here")
    assert meta == {}
    assert "Just markdown" in body


def test_parse_frontmatter_handles_folded_scalar():
    text = "---\nname: attack-planner\ndescription: >-\n  cok satirli\n  aciklama\n---\nbody"
    meta, _ = parse_frontmatter(text)
    assert meta["name"] == "attack-planner"
    assert "cok satirli" in meta["description"]
```

- [ ] **Step 3: Run the test to verify it fails**

Run: `uv run pytest tests/agent/test_skills.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'agent.skills'`.

- [ ] **Step 4: Implement `parse_frontmatter` + `Skill`**

Create `agent/skills.py`:

```python
"""Runtime skill katmani: model bir araci KULLANMADAN once dogru kullanimini
okur (post-call correction). Uc aile: arac skilleri, is-akisi skilleri, metodoloji
skilleri. SAF/IO-ince: yalniz dosya oku; asla dongude exception firlatma."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Skill kaynaklari (repo koku'ne gore). Metodoloji dizini NON-RECURSIVE taranir
# (osint/ alt-paketi, AGENTS.md, SOURCE.md, _scope-guard.md haric — frontmatter kapisi).
TOOL_SKILLS_DIR = Path("agent/skills/tools")
WORKFLOW_SKILLS_DIR = Path("agent/skills/workflows")
METHODOLOGY_SKILLS_DIR = Path("rag/knowledge/methodologies")

_FM_DELIM = "---"


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str
    kind: str            # "tool" | "workflow" | "methodology"
    tool: str | None     # arac skilleri icin katalog arac adi; digerlerinde None
    path: str


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Bastaki ---...--- YAML blogunu ayir. Blok yoksa ({}, text). Asla cokmez."""
    t = text or ""
    if not t.lstrip().startswith(_FM_DELIM):
        return {}, t
    # ilk satir --- ; kapanis --- 'e kadar
    lines = t.splitlines()
    # bastaki bos satirlari atla
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    if start >= len(lines) or lines[start].strip() != _FM_DELIM:
        return {}, t
    end = None
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == _FM_DELIM:
            end = i
            break
    if end is None:
        return {}, t
    fm_text = "\n".join(lines[start + 1:end])
    body = "\n".join(lines[end + 1:])
    try:
        meta = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return {}, t
    if not isinstance(meta, dict):
        return {}, t
    return meta, body
```

- [ ] **Step 5: Run the frontmatter tests to verify they pass**

Run: `uv run pytest tests/agent/test_skills.py -v`
Expected: the 3 frontmatter tests PASS.

- [ ] **Step 6: Write the failing loader/match tests**

Append to `tests/agent/test_skills.py`:

```python
def _write(p: Path, name: str, desc: str, body: str = "govde", extra: str = "") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"---\nname: {name}\ndescription: {desc}\n{extra}---\n\n{body}\n", encoding="utf-8")


def test_load_indexes_three_families_and_skips_non_skills(tmp_path):
    _write(tmp_path / "agent/skills/tools/nmap.md", "nmap", "port tarayici", extra="tool: nmap\n")
    _write(tmp_path / "agent/skills/workflows/report-write.md", "report-write", "rapor yaz")
    _write(tmp_path / "rag/knowledge/methodologies/recon-advisor.md", "recon-advisor", "kesif")
    # frontmatter'siz dosya -> skill DEGIL
    (tmp_path / "rag/knowledge/methodologies/AGENTS.md").write_text("# index\nno fm", encoding="utf-8")
    # alt-dizin (osint/) -> metodoloji non-recursive oldugu icin ALINMAZ
    _write(tmp_path / "rag/knowledge/methodologies/osint/core__SKILL.md", "core", "engine")

    lib = SkillLibrary.load(root=tmp_path)
    assert "nmap" in lib.tools
    assert "report-write" in lib.workflows
    assert "recon-advisor" in lib.methodologies
    assert "core" not in lib.methodologies          # osint/ alt-paketi haric
    assert all("AGENTS" not in n for n in lib.methodologies)


def test_match_tool_and_get(tmp_path):
    _write(tmp_path / "agent/skills/tools/sqlmap.md", "sqlmap", "sqli otomasyonu", extra="tool: sqlmap\n")
    lib = SkillLibrary.load(root=tmp_path)
    assert lib.match_tool("sqlmap").name == "sqlmap"
    assert lib.match_tool("bilinmeyen") is None
    assert lib.get("sqlmap").kind == "tool"


def test_match_ranks_by_keyword_overlap(tmp_path):
    _write(tmp_path / "agent/skills/workflows/report-write.md", "report-write", "bulguyu rapora cevir")
    _write(tmp_path / "rag/knowledge/methodologies/recon-advisor.md", "recon-advisor", "kesif ve varlik")
    lib = SkillLibrary.load(root=tmp_path)
    hits = lib.match("rapor yazma")
    assert hits and hits[0].name == "report-write"


def test_manifest_text_lists_name_and_description(tmp_path):
    _write(tmp_path / "agent/skills/tools/nmap.md", "nmap", "port tarayici", extra="tool: nmap\n")
    lib = SkillLibrary.load(root=tmp_path)
    m = lib.manifest_text()
    assert "nmap" in m and "port tarayici" in m


def test_load_missing_dirs_is_empty_not_error(tmp_path):
    lib = SkillLibrary.load(root=tmp_path)   # hic dosya yok
    assert lib.tools == {} and lib.workflows == {} and lib.methodologies == {}
```

- [ ] **Step 7: Run to verify the loader tests fail**

Run: `uv run pytest tests/agent/test_skills.py -v`
Expected: FAIL — `SkillLibrary` has no `load`/`match_tool`/etc.

- [ ] **Step 8: Implement `SkillLibrary`**

Append to `agent/skills.py`:

```python
def _load_dir(directory: Path, kind: str, *, recursive: bool) -> dict[str, Skill]:
    """Dizindeki *.md dosyalarindan frontmatter'i name+description olanlari Skill yap.
    recursive=False -> yalniz o dizin (alt-paketler haric). IO hatasi -> o dosyayi atla."""
    out: dict[str, Skill] = {}
    if not directory.is_dir():
        return out
    paths = directory.rglob("*.md") if recursive else directory.glob("*.md")
    for p in sorted(paths):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        meta, body = parse_frontmatter(text)
        name = meta.get("name")
        desc = meta.get("description")
        if not name or not desc:
            continue
        tool = meta.get("tool", name) if kind == "tool" else None
        key = str(tool) if kind == "tool" else str(name)
        out[key] = Skill(
            name=str(name), description=str(desc).strip(), body=body.strip(),
            kind=kind, tool=(str(tool) if tool is not None else None), path=str(p),
        )
    return out


@dataclass
class SkillLibrary:
    tools: dict[str, Skill] = field(default_factory=dict)
    workflows: dict[str, Skill] = field(default_factory=dict)
    methodologies: dict[str, Skill] = field(default_factory=dict)

    @classmethod
    def load(cls, root: Path = Path(".")) -> "SkillLibrary":
        root = Path(root)
        return cls(
            tools=_load_dir(root / TOOL_SKILLS_DIR, "tool", recursive=False),
            workflows=_load_dir(root / WORKFLOW_SKILLS_DIR, "workflow", recursive=False),
            methodologies=_load_dir(root / METHODOLOGY_SKILLS_DIR, "methodology", recursive=False),
        )

    def match_tool(self, tool_name: str) -> Skill | None:
        return self.tools.get(tool_name)

    def get(self, name: str) -> Skill | None:
        for table in (self.tools, self.workflows, self.methodologies):
            for s in table.values():
                if s.name == name:
                    return s
        return None

    def match(self, query: str) -> list[Skill]:
        """Basit anahtar-kelime ortusmesi (embedding YAGNI). workflow+methodology uzerinde."""
        terms = {w for w in (query or "").lower().split() if len(w) > 2}
        if not terms:
            return []
        scored: list[tuple[int, Skill]] = []
        for table in (self.workflows, self.methodologies):
            for s in table.values():
                hay = f"{s.name} {s.description}".lower()
                score = sum(1 for t in terms if t in hay)
                if score:
                    scored.append((score, s))
        scored.sort(key=lambda x: (-x[0], x[1].name))
        return [s for _, s in scored]

    def manifest_text(self, kinds: tuple[str, ...] = ("tool", "workflow", "methodology")) -> str:
        """Kompakt kesif manifesti: her skill icin 'name — description' satiri."""
        tables = {"tool": self.tools, "workflow": self.workflows, "methodology": self.methodologies}
        lines: list[str] = []
        for k in kinds:
            for s in tables[k].values():
                lines.append(f"- {s.name} — {s.description}")
        return "\n".join(lines)

    def tool_skill_injection(self, skill: Skill) -> str:
        """Harness'in modele enjekte ettigi 'once oku' kilavuz metni (user turu)."""
        return (
            f"ARAÇ KILAVUZU — {skill.name}: bu aracı çalıştırmadan önce doğru kullanımını oku, "
            f"gerekiyorsa ```arac``` bloğunu düzelt, sonra tekrar çağır.\n\n{skill.body}"
        )
```

- [ ] **Step 9: Run all skills tests to verify they pass**

Run: `uv run pytest tests/agent/test_skills.py -v`
Expected: all PASS.

- [ ] **Step 10: Verify against the REAL methodology dir (sanity, not asserted)**

Run: `uv run python -c "from agent.skills import SkillLibrary; l=SkillLibrary.load(); print('methodologies', len(l.methodologies)); print('tools', len(l.tools)); print('sample', list(l.methodologies)[:3])"`
Expected: `methodologies` ≈ 40, `tools` 0 (pilot tool files not written yet), a sample of real methodology names (e.g. `attack-planner`), and NO `core`/`AGENTS`/`_scope-guard`.

- [ ] **Step 11: Commit**

```bash
git add agent/skills.py tests/agent/test_skills.py pyproject.toml
git commit -m "feat(skills): SkillLibrary loader + frontmatter parser (methodology dir wired)"
```

---

### Task 2: Pilot tool skills (13 hand-written `.md`)

**Files:**
- Create: `agent/skills/tools/nmap.md`, `masscan.md`, `gobuster.md`, `ffuf.md`, `sqlmap.md`, `nikto.md`, `nuclei.md`, `metasploit.md`, `netexec.md`, `hydra.md`, `trufflehog.md`, `magika.md`, `ghunt.md`
- Test: reuse `tests/agent/test_skills.py`

**Interfaces:**
- Consumes: `SkillLibrary.load()` from Task 1.
- Produces: `lib.match_tool("<tool>")` returns each pilot skill; keyed by the catalog tool name.

Every file uses frontmatter `name`, `description`, `tool: <catalog-name>`, then a body with: **Kanonik kullanım**, **Ana flag'ler**, **Tuzaklar**, **Güvenlik/kapsam**. Content below is final — write verbatim.

- [ ] **Step 1: Write `agent/skills/tools/nmap.md`**

```markdown
---
name: nmap
description: TCP/UDP port ve servis tarayıcı; recon'un ilk adımı. Versiyon/OS tespiti ve NSE scriptleri.
tool: nmap
---

## Kanonik kullanım
`arac`: `nmap`, `parametreler`: `{"hedef": "<ip/cidr/host>", "secenekler": "<flag'ler>"}`.
Tipik: `-sV -sC -Pn -p-` (tüm portlar + servis + varsayılan scriptler). Hedef parametreye ayrı yaz, `secenekler` içine gömme.

## Ana flag'ler
- `-sV` servis/versiyon, `-O` OS tespiti, `-sC` varsayılan NSE scriptleri, `-A` agresif (hepsi).
- `-p-` tüm 65535 port, `-p 80,443` seçili, `--top-ports 100` hızlı.
- `-Pn` ping'i atla (host ping'e cevap vermiyorsa şart), `-T4` hız, `-oN/-oX` çıktı dosyası.
- `-sU` UDP (yavaş), `-sS` SYN (root gerekir).

## Tuzaklar
- `-sS`/`-O` root ister; yetki yoksa `-sT` (connect) kullan.
- `--script vuln` LOUD'dur, IDS tetikler; varsayılan `-sC`'den başla.
- `masscan` çok geniş aralıkta daha hızlı — sonra nmap ile derinleştir.

## Güvenlik/kapsam
Yalnızca yetkili/lab hedefi. Hedef IP/host kapsam (scope) içinde olmalı; policy scope dışını reddeder.
```

- [ ] **Step 2: Write `agent/skills/tools/masscan.md`**

```markdown
---
name: masscan
description: Internet ölçeğinde çok hızlı asenkron port tarayıcı; geniş aralıkta ilk süpürme için.
tool: masscan
---

## Kanonik kullanım
`{"hedef": "<cidr>", "secenekler": "-p<portlar> --rate <pps>"}`. Örn: `-p1-65535 --rate 1000`.
Geniş aralığı masscan ile süpür, açık portları sonra nmap `-sV` ile derinleştir.

## Ana flag'ler
- `-p80,443` veya `-p1-65535` port aralığı, `--rate` saniyedeki paket (dikkat: yüksek = LOUD/ağ yükü).
- `-oL/-oJ/-oX` çıktı, `--banners` basit banner (nmap kadar güvenilir değil).

## Tuzaklar
- root/raw-socket gerekir. `--rate` çok yüksek ağı boğar ve tespit edilir — lab'da bile makul tut.
- Tek host için abartı; orada doğrudan nmap kullan.

## Güvenlik/kapsam
Yüksek hız = yüksek gürültü + yanlışlıkla DoS riski. Yalnızca yetkili geniş kapsamda, sınırlı `--rate` ile.
```

- [ ] **Step 3: Write `agent/skills/tools/gobuster.md`**

```markdown
---
name: gobuster
description: Dizin/dosya, DNS subdomain ve vhost brute-force keşif aracı (wordlist tabanlı).
tool: gobuster
---

## Kanonik kullanım
`{"url": "<hedef>", "mod": "dir", "wordlist": "<yol>", "secenekler": "<ek>"}`.
Mod ZORUNLU: `dir` (dizin), `dns` (subdomain), `vhost`. Örn dir: `-x php,txt -t 50`.

## Ana flag'ler
- `dir`: `-u <url> -w <wordlist> -x <uzantilar> -t <thread>`; `-s`/`-b` status kodu allow/deny.
- `dns`: `-d <domain> -w <wordlist>`; `vhost`: `-u <url> -w <wordlist>`.
- Wordlist: `/usr/share/wordlists/dirbuster/...` veya seclists.

## Tuzaklar
- Mod belirtmezsen çalışmaz — `mod` her zaman ver.
- `dns` modunda `-u` değil `-d` kullanılır; karıştırma.
- Çok yüksek `-t` sunucuyu yorar / rate-limit'e takılır.

## Güvenlik/kapsam
Aktif tarama (MODERATE). Hedef URL/domain kapsam içinde olmalı.
```

- [ ] **Step 4: Write `agent/skills/tools/ffuf.md`**

```markdown
---
name: ffuf
description: Hızlı web fuzzer; dizin, parametre, vhost ve POST verisi fuzzing için FUZZ anahtar kelimesi.
tool: ffuf
---

## Kanonik kullanım
`{"url": "<url-FUZZ>", "wordlist": "<yol>", "secenekler": "<ek>"}`.
`FUZZ` yer tutucusu URL/başlık/gövdede nereye konursa oraya wordlist basılır. Örn: `-u https://h/FUZZ -w list.txt`.

## Ana flag'ler
- `-w <wordlist>` (`-w a.txt:W1 -w b.txt:W2` çoklu), `-u` URL, `-X POST -d "FUZZ"` gövde fuzzing.
- `-mc 200,301` status eşle, `-fc 404` filtrele, `-fs <boyut>` boyuta göre ele, `-t` thread.
- `-H "Header: FUZZ"` başlık fuzzing.

## Tuzaklar
- `FUZZ` anahtarını koymayı unutma — yoksa hiçbir yere basmaz.
- Filtresiz çıktı 404 gürültüsüyle dolar; `-fc 404` veya `-fs` ile ele.

## Güvenlik/kapsam
Aktif (MODERATE). Yalnızca yetkili hedef; agresif thread rate-limit/WAF tetikler.
```

- [ ] **Step 5: Write `agent/skills/tools/sqlmap.md`**

```markdown
---
name: sqlmap
description: SQL injection tespit ve sömürü otomasyonu; DB dump, dosya okuma, OS shell.
tool: sqlmap
---

## Kanonik kullanım
`{"url": "<enjekte-edilebilir-url>", "secenekler": "<ek>"}`.
Tespitle başla: `-u "<url>" --batch`. Sonra kademeli: `--dbs` → `-D <db> --tables` → `-T <t> --dump`.

## Ana flag'ler
- `--batch` etkileşimsiz (varsayılan cevaplar), `--level 1-5`/`--risk 1-3` derinlik.
- `-r <istek.txt>` ham HTTP isteği (POST/başlık enjeksiyonu için ideal), `-p <param>` hedef parametre.
- `--dbs --tables --columns --dump`, `--current-user --is-dba`, `--os-shell` (yüksek risk).

## Tuzaklar
- `--os-shell`/`--dump-all` yüksek etkili ve gürültülü — önce tespiti doğrula.
- `--level/--risk` yükseltmek yavaşlatır ve LOUD yapar; 1'den başla.
- POST/JSON için `-r` ile ham istek ver; URL'ye sıkıştırma.

## Güvenlik/kapsam
Yüksek etki (veri sömürüsü). Yalnızca yetkili hedef; dump/os-shell öncesi kapsamı ve gereği teyit et.
```

- [ ] **Step 6: Write `agent/skills/tools/nikto.md`**

```markdown
---
name: nikto
description: Web sunucu zafiyet/yapılandırma tarayıcı; bilinen dosyalar, başlıklar, eski yazılım.
tool: nikto
---

## Kanonik kullanım
`{"hedef": "<host/url>", "secenekler": "-h <host> <ek>"}`. Örn: `-h https://hedef -ssl`.

## Ana flag'ler
- `-h` host (zorunlu), `-ssl` HTTPS, `-p` port, `-Tuning <x>` test sınıfı seçimi.
- `-o rapor.html -Format htm` çıktı, `-useproxy` proxy üzerinden.

## Tuzaklar
- Doğası gereği LOUD ve imza tabanlı — WAF/IDS kolayca yakalar; sessiz recon değildir.
- Yüksek yanlış-pozitif; bulguları elle doğrula.

## Güvenlik/kapsam
Aktif tarama. Yalnızca yetkili hedef; sonuçları teyit etmeden "zafiyet var" deme.
```

- [ ] **Step 7: Write `agent/skills/tools/nuclei.md`**

```markdown
---
name: nuclei
description: Şablon (template) tabanlı hızlı zafiyet tarayıcı; CVE/misconfig/exposure tespiti.
tool: nuclei
---

## Kanonik kullanım
`{"url": "<hedef>", "secenekler": "<ek>"}` veya toplu `-l <hosts.txt>`. Örn: `-u https://h -severity high,critical`.

## Ana flag'ler
- `-u` tek hedef / `-l` liste, `-t <template/dizin>` seçili şablon, `-tags cve,exposure`.
- `-severity low..critical` filtre, `-rl <rate>` istek hızı, `-o` çıktı.
- `-update-templates` şablonları güncelle.

## Tuzaklar
- Eski şablonlar = eksik/yanlış sonuç; gerekirse `-update-templates`.
- Tüm şablonları çalıştırmak çok LOUD; `-tags`/`-severity` ile daralt.

## Güvenlik/kapsam
Aktif tarama. Kapsam içi hedef; kritik bulguları elle doğrula (nuclei eşleşmesi = ipucu, kanıt değil).
```

- [ ] **Step 8: Write `agent/skills/tools/metasploit.md`**

```markdown
---
name: metasploit
description: Sömürü/post-exploit framework; modül seçimi, payload, oturum yönetimi. Yüksek risk.
tool: metasploit
---

## Kanonik kullanım
`{"komutlar": "<msfconsole komut dizisi>"}`. Komutları ayrı ver (resource script mantığı):
`use <modul>; set RHOSTS <ip>; set LHOST <ip>; set PAYLOAD <p>; run`.

## Ana komutlar
- `search <cve/urun>`, `use <exploit/...>`, `show options`, `set <OPT> <val>`, `check` (varsa non-exploit doğrulama).
- `set PAYLOAD`, `exploit`/`run`, `sessions -l`, `background`.
- Post: `use post/...`, `set SESSION <id>`.

## Tuzaklar
- `RHOSTS/LHOST/PAYLOAD` set etmeden `run` = başarısız; `show options` ile eksikleri gör.
- `check` destekleyen modülde önce doğrula (gürültü/çökme riskini azaltır).
- Yanlış payload/arch hedefi çökertebilir.

## Güvenlik/kapsam
Aktif sömürü (yüksek etki, geri-dönülmez olabilir). Yalnızca yetkili hedef; exploit öncesi kapsamı teyit et.
```

- [ ] **Step 9: Write `agent/skills/tools/netexec.md`**

```markdown
---
name: netexec
description: Ağ protokol sömürü/enum (SMB/WinRM/LDAP/MSSQL...); credential doğrulama ve lateral hareket. (eski adı crackmapexec)
tool: netexec
---

## Kanonik kullanım
`{"hedef": "<ip/cidr>", "protokol": "<smb|winrm|ldap|mssql|ssh>", "secenekler": "<ek>"}`.
Örn: `-u <kullanici> -p <parola>` veya `-H <ntlm-hash>` (pass-the-hash).

## Ana flag'ler
- Protokol ilk argüman (`smb`, `winrm`, ...). `-u`/`-p` veya `-H` hash, `--local-auth` yerel hesap.
- SMB: `--shares`, `--sam`, `--lsa`, `-x <komut>`; `--continue-on-success` spray.

## Tuzaklar
- Protokolü belirtmezsen çalışmaz — `protokol` her zaman ver.
- Parola spray hesap kilitler; `--continue-on-success` + kilitleme politikasına dikkat.
- `-x`/`--sam`/`--lsa` LOUD ve EDR tetikler.

## Güvenlik/kapsam
Aktif/intrusive (kimlik doğrulama, kod çalıştırma). Yalnızca yetkili domain/hedef; spray öncesi kilit riskini değerlendir.
```

- [ ] **Step 10: Write `agent/skills/tools/hydra.md`**

```markdown
---
name: hydra
description: Ağ servisi online parola brute-force (SSH/FTP/HTTP-form/RDP...). Yüksek gürültü/kilit riski.
tool: hydra
---

## Kanonik kullanım
`{"hedef": "<ip/host>", "secenekler": "-l <kullanici> -P <parola-listesi> <servis>"}`.
Örn SSH: `-l admin -P rockyou.txt ssh://10.10.10.5`. HTTP form: `http-post-form "<path>:<body>:<fail-string>"`.

## Ana flag'ler
- `-l <tek-kullanici>` / `-L <liste>`, `-p <tek-parola>` / `-P <liste>`, `-t <paralel>` (varsayılan 16).
- Servis URL biçimi: `ssh://`, `ftp://`, `rdp://`, `http-post-form`/`http-get-form`.
- `-f` ilk bulunanda dur, `-o` çıktı, `-s <port>` özel port.

## Tuzaklar
- HTTP form'da `fail-string` yanlışsa her denemeyi "başarılı" sanar — geçersiz login'in dönüş metnini doğru ver.
- Yüksek `-t` hesap kilitler ve servisi boğar; kilitleme politikası olan hedefte düşür.
- Büyük listeler çok LOUD; hedefli küçük listeyle başla.

## Güvenlik/kapsam
Intrusive (kilit + DoS riski). Yalnızca yetkili hedef; başkasının hesabına brute-force = red çizgisi.
```

- [ ] **Step 10a: Write `agent/skills/tools/trufflehog.md`**

```markdown
---
name: trufflehog
description: Sızmış sır/credential tarayıcı (git, GitHub, S3, dosya sistemi, Docker); 800+ tip, canlı doğrulama.
tool: trufflehog
---

## Kanonik kullanım
`{"kaynak": "<git|github|s3|filesystem|docker>", "hedef": "<uri/org/bucket/yol>"}`.
Örn: `git https://github.com/org/repo`, `github --org=<org>`, `filesystem <yol>`, `docker --image <imaj>`.

## Ana flag'ler
- Alt-komut (kaynak) ZORUNLU: `git`, `github`, `s3`, `filesystem`, `docker`.
- `--results=verified,unknown` çıktı filtresi (yalnız doğrulanmış sırlar için `verified`).
- `--json` makine-okur çıktı, `--fail` sır bulununca exit 183 (CI gate).
- `--only-verified` gürültüyü keser (canlı doğrulanan credential'lar).

## Tuzaklar
- Kaynağı (git/github/...) belirtmezsen çalışmaz.
- `--only-verified` olmadan yüksek yanlış-pozitif; triage için önce doğrulanmışlara bak.
- GitHub org taraması API rate-limit'e takılabilir; token ver.

## Güvenlik/kapsam
Çoğunlukla defansif/pasif (kendi repolarında sır avı). Başkasının özel kaynağına erişim yetki ister; hedef kapsam içinde olmalı.
```

- [ ] **Step 10b: Write `agent/skills/tools/magika.md`**

```markdown
---
name: magika
description: Google'ın ML tabanlı dosya-tipi tespiti; içerikten ~%99 doğrulukla 200+ format, forensics/triyaj.
tool: magika
---

## Kanonik kullanım
`{"yol": "<dosya/dizin>"}`. Bilinmeyen dosyanın gerçek türünü içerikten belirler (uzantıya güvenmeden).
Örn: şüpheli örnek/DFIR artefaktı türünü hızlı tanı.

## Ana flag'ler
- `-r` özyinelemeli dizin, `--json` makine-okur, `--mime-type` MIME çıktısı, `-s` güven skoru.
- Girdi tek dosya veya dizin; ikili/metin ayrımı ve gerçek format (ör. uzantısız PE, gizlenmiş script).

## Tuzaklar
- Uzantı yanıltıcıysa magika içeriğe bakar — bu güçlü yanı; yine de düşük-güven skorlarını elle teyit et.
- Şifreli/paketlenmiş dosyada tür "generic" dönebilir; binwalk/strings ile derinleştir.

## Güvenlik/kapsam
Pasif, yerel içerik analizi (ağ hedefi yok). Şüpheli örneği izole/lab ortamında incele.
```

- [ ] **Step 10c: Write `agent/skills/tools/ghunt.md`**

```markdown
---
name: ghunt
description: Google hesap OSINT çerçevesi (email, Gaia ID, Drive, geolocate); pasif hesap keşfi.
tool: ghunt
---

## Kanonik kullanım
`{"modul": "<email|gaia|drive|geolocate|spiderdal>", "hedef": "<eposta/id/url/bssid>"}`.
Örn: `email <adres>`, `gaia <id>`, `drive <url>`. Kimlik doğrulama (Google cookie) gerekir — `ghunt login`.

## Ana modüller
- `email` e-postadan hesap bilgisi, `gaia` Gaia ID'den veri, `drive` Drive dosya/klasör analizi.
- `geolocate` BSSID konumu, `spiderdal` Digital Asset Links üzerinden varlık keşfi.
- `--json` dışa aktarım; asenkron çalışır.

## Tuzaklar
- Önce `ghunt login` (tarayıcı eklentisiyle cookie) yoksa modüller çalışmaz.
- Cookie'ler süresi dolar; hata alırsan yeniden login.

## Güvenlik/kapsam
Gerçek bir kişinin Google hesabına OSINT = kişiyi hedefleme. Yalnızca yetkili/rızalı hedef; kapsam (hedef) kilidi uygulanır.
```

- [ ] **Step 11: Verify the loader indexes all 13 pilot tools**

Run: `uv run python -c "from agent.skills import SkillLibrary; l=SkillLibrary.load(); print(sorted(l.tools)); assert len(l.tools)==13, len(l.tools)"`
Expected: prints the 13 tool names, assertion passes.

- [ ] **Step 12: Add a real-file assertion test**

Append to `tests/agent/test_skills.py`:

```python
def test_pilot_tool_skills_present_in_repo():
    lib = SkillLibrary.load()
    for name in ["nmap", "masscan", "gobuster", "ffuf", "sqlmap",
                 "nikto", "nuclei", "metasploit", "netexec", "hydra",
                 "trufflehog", "magika", "ghunt"]:
        s = lib.match_tool(name)
        assert s is not None and s.kind == "tool" and s.body, name
```

Run: `uv run pytest tests/agent/test_skills.py::test_pilot_tool_skills_present_in_repo -v`
Expected: PASS.

- [ ] **Step 13: Commit**

```bash
git add agent/skills/tools/ tests/agent/test_skills.py
git commit -m "feat(skills): 10 pilot tool skills (nmap..hydra) with canonical usage + pitfalls"
```

---

### Task 3: Workflow skills (4 hand-written `.md`)

**Files:**
- Create: `agent/skills/workflows/engagement-plan.md`, `finding-synthesis.md`, `report-write.md`, `verify-before-claim.md`
- Test: reuse `tests/agent/test_skills.py`

**Interfaces:**
- Consumes: `SkillLibrary.load()`.
- Produces: `lib.workflows` contains the 4; `lib.match("...")` can surface them.

- [ ] **Step 1: Write `agent/skills/workflows/engagement-plan.md`**

```markdown
---
name: engagement-plan
description: Yetkili bir siber güvenlik işini planla — kapsam netleştir, aşamalara böl, en küçük etkili adımı seç.
---

## Ne zaman
Kullanıcı çok adımlı bir iş istediğinde (pentest, CTF, değerlendirme) ilk adımdan önce.

## Akış
1. **Kapsam + yetki**: hedef(ler) kapsam içinde mi, yıkıcı/geri-dönülmez adım var mı? Belirsizlik sonucu değiştirecekse sor, değilse en makul varsayımla devam et.
2. **Aşamalar**: recon → enumerasyon → zafiyet analizi → (yetkiliyse) sömürü → post → rapor. Her aşamada en sessiz yeterli aracı seç.
3. **Araç seçimi**: her adım için doğru aracı ve o aracın skill'ini kullan; gürültü (QUIET/MODERATE/LOUD) seviyesini not et.
4. **Çıktı**: "şu an ne yapıyorum + sırada ne var" olarak net adımlar üret.

## İlke
Süreci işin kendisinden ağır yapma. Düşük riskte izin kovalama; yıkıcı/geri-dönülmez işte önce teyit al.
```

- [ ] **Step 2: Write `agent/skills/workflows/finding-synthesis.md`**

```markdown
---
name: finding-synthesis
description: Birden çok araç çıktısını korele et, bulguları önem sırasına koy, saldırı zincirine bağla.
---

## Ne zaman
Elde birden çok tarama/enum çıktısı olunca; ham çıktı yerine karar üretmek için.

## Akış
1. **Normalize**: her bulguyu (host, port, servis, zafiyet, güven) tek biçime getir.
2. **İlişkilendir**: aynı subnet/domain, ortak kimlik bilgisi, pivot noktaları.
3. **Önceliklendir**: etki × olasılık × gürültü. Tek başına orta bir bulgu, bir zincirin ilk halkasıysa kritiktir.
4. **Zincirle**: initial access → execution → privesc → lateral → impact olarak anlatıya bağla.

## İlke
Güven seviyesini dürüst işaretle (Confirmed/High/Moderate/Speculative). Doğrulanmamış halkayı doğrulanmış gibi sunma.
```

- [ ] **Step 3: Write `agent/skills/workflows/report-write.md`**

```markdown
---
name: report-write
description: Bir bulguyu triage-hazır rapora çevir — başlık, etki, tekrar-üretim, kanıt, düzeltme.
---

## Ne zaman
Bir zafiyet/bulgu doğrulandıktan sonra, teslim edilebilir çıktı üretirken.

## Şablon
- **Başlık**: kısa, etki odaklı.
- **Önem**: CVSS/severity + iş etkisi (bir cümle).
- **Etkilenen**: host/endpoint/parametre.
- **Tekrar-üretim**: adım adım komut/istek (verbatim).
- **Kanıt**: çıktı/ekran/loglar (uydurma yok — yalnızca gerçekten gözlemleneni yaz).
- **Düzeltme**: somut, uygulanabilir öneri.
- **Tespit (blue)**: savunmanın nerede yakalayabileceği.

## İlke
Kanıtsız iddia yok. Doğrulamadıysan "muhtemel" de, "doğrulandı" deme.
```

- [ ] **Step 4: Write `agent/skills/workflows/verify-before-claim.md`**

```markdown
---
name: verify-before-claim
description: Önemli bir teknik iddiaya dayanmadan önce doğrula — çalıştır, kaynağa bak, çıktıyı gör.
---

## Ne zaman
"Şu port açık / şu zafiyet var / şu exploit çalışır" gibi karara girecek her iddiadan önce.

## Akış
1. İddiayı **çalıştırılabilir bir kontrole** indir (komut, istek, kaynak).
2. Çıktıyı **gerçekten gör**; tahminle doldurma.
3. Sonucu güven seviyesiyle raporla; doğrulayamadıysan neyin eksik olduğunu söyle.
4. Sahip olmadığın yeteneği uydurma: araç/erişim yoksa "yaptım/kaydettim" deme.

## İlke
Faydalı > uyumlu; dürüst > etkileyici. Doğruluğun önemli olduğu yerde "herhalde olur"u reddet.
```

- [ ] **Step 5: Add a workflow assertion test**

Append to `tests/agent/test_skills.py`:

```python
def test_pilot_workflow_skills_present_in_repo():
    lib = SkillLibrary.load()
    for name in ["engagement-plan", "finding-synthesis", "report-write", "verify-before-claim"]:
        assert name in lib.workflows, name
    # match() bir is-akisini yuzeye cikarabiliyor
    assert any(s.name == "report-write" for s in lib.match("rapor yaz"))
```

Run: `uv run pytest tests/agent/test_skills.py::test_pilot_workflow_skills_present_in_repo -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add agent/skills/workflows/ tests/agent/test_skills.py
git commit -m "feat(skills): 4 workflow skills (engagement-plan, finding-synthesis, report-write, verify-before-claim)"
```

---

### Task 4: `run_tool_loop` post-call correction

**Files:**
- Modify: `agent/loop.py`
- Create: `tests/agent/test_loop_skills.py`

**Interfaces:**
- Consumes: `SkillLibrary` (`match_tool`, `tool_skill_injection`) from Task 1; `Message`, `parse_arac_calls`, `ToolLoopResult` (existing).
- Produces: `run_tool_loop(messages, generate, registry, *, max_steps=10, skills=None)` — when `skills` is a `SkillLibrary`, a called tool with a skill not yet shown triggers a one-time `user`-turn injection + regenerate before execution.

- [ ] **Step 1: Write the failing integration tests**

Create `tests/agent/test_loop_skills.py`:

```python
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


def test_no_skill_for_tool_executes_normally(tmp_path):
    # skill kutuphanesi bos -> davranis eskisi gibi (enjeksiyon yok)
    replies = iter([
        '```arac\n{"arac":"nmap","parametreler":{"hedef":"10.10.10.5","secenekler":"-sV"}}\n```',
        "bitti",
    ])
    res = run_tool_loop([Message("user", "tara")], lambda m: next(replies), _reg(tmp_path),
                        skills=SkillLibrary())
    assert len(res.calls) == 1 and "bitti" in res.final
```

- [ ] **Step 2: Run to verify the new tests fail**

Run: `uv run pytest tests/agent/test_loop_skills.py -v`
Expected: FAIL — `run_tool_loop() got an unexpected keyword argument 'skills'`.

- [ ] **Step 3: Implement the correction loop**

Replace the body of `agent/loop.py` with:

```python
"""Model<->arac dongusu (Hermes recursive loop deseni, agentic-model'den uyarlandi).
model uret -> arac blogu var mi? yoksa nihai cevap; varsa (skill katmani acikken) yeni
arac icin once skill enjekte et + regenerate, sonra calistir, sonucu tool mesaji olarak
ekle, tekrarla. max_steps sonsuz-dongu korumasi."""
from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass, field
from agent.messages import Message
from agent.registry import ToolRegistry
from agent.skills import SkillLibrary
from agent.toolcall import ToolCall, parse_arac_calls, strip_dusunce

Generate = Callable[[list[Message]], str]


@dataclass
class ToolLoopResult:
    final: str
    steps: int
    calls: list[ToolCall] = field(default_factory=list)


def _inject_tool_skills(
    messages: list[Message], calls: list[ToolCall],
    skills: SkillLibrary, shown: set[str],
) -> bool:
    """Cagrilan araclardan skill'i olan + bu konusmada henuz gosterilmemis olanlar icin
    skill md'sini USER turu olarak ekle (once oku). Cache: her arac en fazla 1 kez.
    En az bir enjeksiyon yapildiysa True (dongu regenerate etsin)."""
    injected = False
    for call in calls:
        if call.name in shown:
            continue
        skill = skills.match_tool(call.name)
        if skill is None:
            continue
        messages.append(Message("user", skills.tool_skill_injection(skill)))
        shown.add(call.name)
        injected = True
    return injected


def run_tool_loop(
    messages: list[Message],
    generate: Generate,
    registry: ToolRegistry,
    *,
    max_steps: int = 10,
    skills: SkillLibrary | None = None,
) -> ToolLoopResult:
    executed: list[ToolCall] = []
    shown: set[str] = set()
    for step in range(max_steps):
        reply = generate(messages)
        messages.append(Message("assistant", reply))
        calls = parse_arac_calls(reply)
        if not calls:
            return ToolLoopResult(final=strip_dusunce(reply), steps=step + 1, calls=executed)
        if skills is not None and _inject_tool_skills(messages, calls, skills, shown):
            continue  # skill eklendi -> model cagriyi duzeltsin diye yeniden uret
        for call in calls:
            result = registry.invoke(call)
            executed.append(call)
            messages.append(Message("tool", result))
    final = generate(messages)
    messages.append(Message("assistant", final))
    return ToolLoopResult(final=strip_dusunce(final), steps=max_steps, calls=executed)
```

- [ ] **Step 4: Run the new integration tests**

Run: `uv run pytest tests/agent/test_loop_skills.py -v`
Expected: all PASS.

- [ ] **Step 5: Run the EXISTING loop tests (backward compat gate)**

Run: `uv run pytest tests/agent/test_loop.py -v`
Expected: all 3 existing tests PASS unchanged (no `skills` arg → identical behavior).

- [ ] **Step 6: Run the full agent suite**

Run: `uv run pytest tests/agent -q`
Expected: green (no regressions).

- [ ] **Step 7: Commit**

```bash
git add agent/loop.py tests/agent/test_loop_skills.py
git commit -m "feat(skills): post-call correction in run_tool_loop (inject-once tool skills, backward compatible)"
```

---

### Task 5: Fabricated-flag / correct-usage eval

**Files:**
- Create: `eval/skill_correction_eval.py`
- Create: `tests/eval/test_skill_correction_eval.py`

**Interfaces:**
- Consumes: `run_tool_loop` + `skills` from Task 4; a `generate` callable (real `GgufModel` when Ollama+GGUF present, or a scripted stand-in in tests).
- Produces:
  - `evaluate(generate, cases, registry, skills) -> EvalResult` where
    `EvalResult(total: int, valid_flags_before: int, valid_flags_after: int)` — measures, per case, whether the FINAL executed tool call uses only real flags for that tool (fabricated-flag proxy), with skills OFF vs ON.
  - `known_flags(tool: str) -> set[str]` — small curated flag allow-list per pilot tool for scoring.

- [ ] **Step 1: Write the failing proxy test**

Create `tests/eval/test_skill_correction_eval.py`:

```python
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
```

- [ ] **Step 2: Run to verify it fails**

Run: `uv run pytest tests/eval/test_skill_correction_eval.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'eval.skill_correction_eval'`.

- [ ] **Step 3: Implement the eval module**

Create `eval/skill_correction_eval.py`:

```python
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
```

Note: `generate_factory` is a **factory** (returns a fresh callable per case) so the model/scripted state does not leak across cases. The proxy test passes `make_gen` (a factory).

- [ ] **Step 4: Run the proxy test**

Run: `uv run pytest tests/eval/test_skill_correction_eval.py -v`
Expected: PASS.

- [ ] **Step 5: Add a real-model runner entry point (Ollama-gated, no test)**

Append to `eval/skill_correction_eval.py`:

```python
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
```

- [ ] **Step 6: Run the full suite**

Run: `uv run pytest -q`
Expected: green across the repo (agent + eval + data).

- [ ] **Step 7: Commit**

```bash
git add eval/skill_correction_eval.py tests/eval/test_skill_correction_eval.py
git commit -m "feat(skills): fabricated-flag correction eval (scripted proxy test + Ollama runner)"
```

---

## Self-Review

**Spec coverage** (against `docs/superpowers/specs/2026-07-25-skill-layer-design.md`):
- §Konum RUNTIME harness → Tasks 1,4 (skills.py + loop wiring). ✅
- §Üç tür (tool/methodology/workflow) → Task 2 (tools), Task 1 loads methodologies, Task 3 (workflows). ✅
- §Mekanizma post-call correction + cache → Task 4 (`_inject_tool_skills`, `shown` set, `continue`). ✅
- §Discovery manifest → `manifest_text()` implemented+tested (Task 1). System-prompt wiring intentionally deferred (see Out of Scope) to avoid destabilizing the untrained model — API is ready. ✅ (partial-by-design)
- §`agent/skills.py` API (load_index/get/match_tool/match) → Task 1 (`load`/`get`/`match_tool`/`match`; `manifest_text` == index). ✅
- §Yazım auto-draft + PİLOT ÖNCE → pilot = 10 hand-written tools + 4 workflows + harness + eval; 117-generator deferred. ✅
- §Test loader unit + correction integration + fabricated-flag eval → Tasks 1,4,5. ✅
- §İzolasyon: skills.py tek sorumluluk; policy gate değişmez → loop injects only; `registry.invoke`/policy untouched. ✅

**Placeholder scan:** No "TBD/similar to/handle edge cases". All tool/workflow bodies are final text; all code steps show full code.

**Type consistency:** `Skill`, `SkillLibrary`, `match_tool`, `tool_skill_injection`, `Case`, `EvalResult`, `evaluate(generate_factory,...)`, `has_only_known_flags` are used consistently across Tasks 1→4→5. `run_tool_loop(..., skills=None)` signature identical in loop.py and both test files.

## Out of Scope (post-pilot)

- **117-tool auto-draft generator** (`agent/build_skills.py` from `CATALOG`, write-if-absent so hand-enriched files survive) — the scaling step after the pilot measures a positive effect.
- **Manifest → system prompt wiring** (augment `OCTOPUS_TOOL_SYSTEM_PROMPT` with `manifest_text()`), measured separately; risks destabilizing the untrained model, so gate it behind an eval.
- **SFT distillation** of proven skills into the model (the "ikisi de" later phase).
- **Embedding-based `match`** (keyword is enough for the pilot).
- **v0.9 GGUF download + `run_against_ollama` real-model numbers** — blocked on the interrupted download (`octopus-v0.9` Q4, sha `c98f6a06`).

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-07-27-skill-layer-pilot.md`.
