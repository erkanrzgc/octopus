# SFT Target Rebalancing & Hostname Handling — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Break the `10.10.10.5` target-memorization and teach hostname-verbatim tool calls by rebalancing the tool-use SFT data via conversation-coherent target remapping — no training-code changes.

**Architecture:** A seeded, deterministic augmentation step reads the hand-written tool examples, extracts every network entity (IP / CIDR / hostname) per example, builds one consistent old→new mapping, and renders K balanced variants — preserving intra-conversation coherence (scan output ↔ follow-up target). A distribution audit gates the result. Output feeds the existing `build_tools.py` → `build_sft.py` pipeline unchanged.

**Tech Stack:** Python 3.14, stdlib only (`random`, `re`, `ipaddress`, `json`, `glob`), `pytest`, `uv`.

## Global Constraints

- Packaging/tests: `uv run pytest`, `uv run python ...` (venv `.venv` on ASCII path).
- File paths stay plain ASCII `octopus`; brand `ó` only in speech/docs.
- Every augmented example must keep: system-role first, ≥1 valid ```arac``` block or a refusal, scope-safe "authorized lab" framing, Turkish interpretation of tool output.
- Determinism: same `--seed` ⇒ byte-identical output (reproducible dataset).
- Distribution audit (hard gate): no single concrete target > **6%** of tool examples; hostnames ≥ **20%** of examples that have a network target.
- Do NOT touch `train/sft_bf16.py`, `data/sft/build_sft.py`, or `data/sft/persona.py` in this plan (masking is a separate item).
- Target pool: hostnames + private ranges `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` + minority `203.0.113.0/24` (RFC 5737 TEST-NET-3).

---

### Task 1: Balanced target pool sampler

**Files:**
- Create: `data/sft/tools/target_pool.py`
- Test: `tests/data/test_target_pool.py`

**Interfaces:**
- Produces:
  - `PRIVATE_RANGES: tuple[IPv4Network, ...]`, `DOC_RANGE: IPv4Network`, `HOSTNAMES: tuple[str, ...]`, `HOSTNAME_SHARE: float`
  - `sample_subnet(rng: random.Random, prefix: int = 24, doc_prob: float = 0.08) -> IPv4Network`
  - `sample_host(rng: random.Random, subnet: IPv4Network | None = None) -> IPv4Address`
  - `sample_hostname(rng: random.Random) -> str`
  - `use_hostname(rng: random.Random, share: float = HOSTNAME_SHARE) -> bool`

- [ ] **Step 1: Write the failing test**

```python
# tests/data/test_target_pool.py
import random
from ipaddress import IPv4Address, IPv4Network
from data.sft.tools import target_pool as tp


def test_sample_host_falls_inside_given_subnet():
    rng = random.Random(1)
    net = IPv4Network("192.168.7.0/24")
    for _ in range(200):
        host = tp.sample_host(rng, net)
        assert host in net.hosts()


def test_sample_subnet_is_private_or_doc():
    rng = random.Random(2)
    allowed = tp.PRIVATE_RANGES + (tp.DOC_RANGE,)
    for _ in range(200):
        sub = tp.sample_subnet(rng, prefix=24)
        assert any(sub.subnet_of(r) or sub == r for r in allowed)


def test_use_hostname_share_is_roughly_calibrated():
    rng = random.Random(3)
    hits = sum(tp.use_hostname(rng, share=0.28) for _ in range(5000))
    assert 0.24 < hits / 5000 < 0.32


def test_determinism_same_seed_same_draw():
    a = [str(tp.sample_host(random.Random(9))) for _ in range(5)]
    b = [str(tp.sample_host(random.Random(9))) for _ in range(5)]
    assert a == b
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/data/test_target_pool.py -v`
Expected: FAIL — `ModuleNotFoundError: data.sft.tools.target_pool`

- [ ] **Step 3: Write minimal implementation**

```python
# data/sft/tools/target_pool.py
"""Dengeli hedef havuzu — ezberi kirmak icin cesitli IP/CIDR/hostname uretir.
stdlib-only, seed'le deterministik (ayni seed -> ayni cikti)."""
from __future__ import annotations

import random
from ipaddress import IPv4Address, IPv4Network, ip_network

PRIVATE_RANGES: tuple[IPv4Network, ...] = (
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
)
DOC_RANGE: IPv4Network = ip_network("203.0.113.0/24")  # RFC 5737 TEST-NET-3

HOSTNAMES: tuple[str, ...] = (
    "octopus-target", "web01.lab.local", "dc01.corp.local", "app-staging.internal",
    "kali-victim", "db-01.internal", "gitlab.lab.local", "vpn-gw.corp.local",
    "mail.corp.local", "jenkins.lab.local", "fileserver.internal", "portal.kurum.local",
    "wordpress.lab.local", "api-gw.internal", "ad01.corp.local", "backup.lab.local",
)

HOSTNAME_SHARE: float = 0.28  # tek-host hedeflerin ~%28'i hostname olur


def sample_subnet(rng: random.Random, prefix: int = 24, doc_prob: float = 0.08) -> IPv4Network:
    """Ozel araliklardan (nadiren TEST-NET) rastgele bir /prefix blogu."""
    base = DOC_RANGE if rng.random() < doc_prob else rng.choice(PRIVATE_RANGES)
    if base.prefixlen >= prefix:
        return base
    n_blocks = 2 ** (prefix - base.prefixlen)
    net_int = int(base.network_address) + (rng.randrange(n_blocks) << (32 - prefix))
    return ip_network((net_int, prefix))


def sample_host(rng: random.Random, subnet: IPv4Network | None = None) -> IPv4Address:
    """subnet icinde gecerli bir host adresi (network/broadcast disi)."""
    if subnet is None:
        subnet = sample_subnet(rng, prefix=24)
    max_octet = min(254, subnet.num_addresses - 2)
    return IPv4Address(int(subnet.network_address) + rng.randint(1, max_octet))


def sample_hostname(rng: random.Random) -> str:
    return rng.choice(HOSTNAMES)


def use_hostname(rng: random.Random, share: float = HOSTNAME_SHARE) -> bool:
    return rng.random() < share
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/data/test_target_pool.py -v`
Expected: PASS (4 passed)

- [ ] **Step 5: Commit**

```bash
git add data/sft/tools/target_pool.py tests/data/test_target_pool.py
git commit -m "feat(data): dengeli hedef havuzu sampler (IP/CIDR/hostname, seed-deterministik)"
```

---

### Task 2: Network-entity extractor

**Files:**
- Create: `data/sft/tools/augment_targets.py`
- Test: `tests/data/test_augment_targets.py`

**Interfaces:**
- Consumes: `target_pool` (Task 1).
- Produces:
  - `Entities` (dataclass): `cidrs: list[str]`, `hosts: list[str]`, `hostnames: list[str]`
  - `extract_entities(example: dict) -> Entities` — scans every message `content` string.

- [ ] **Step 1: Write the failing test**

```python
# tests/data/test_augment_targets.py
from data.sft.tools import augment_targets as aug

_CIDR_EXAMPLE = {"messages": [
    {"role": "system", "content": "Sen Octópus'sun."},
    {"role": "user", "content": "10.10.10.0/24 agini tara."},
    {"role": "assistant", "content": "```arac\n{\"arac\":\"rustscan\",\"parametreler\":{\"hedef\":\"10.10.10.0/24\"}}\n```"},
    {"role": "tool", "content": "10.10.10.5 -> [22,80]\n10.10.10.20 -> [443]"},
    {"role": "assistant", "content": "```arac\n{\"arac\":\"nmap\",\"parametreler\":{\"hedef\":\"10.10.10.20\"}}\n```"},
]}


def test_extract_finds_cidr_and_hosts():
    ent = aug.extract_entities(_CIDR_EXAMPLE)
    assert "10.10.10.0/24" in ent.cidrs
    assert "10.10.10.5" in ent.hosts
    assert "10.10.10.20" in ent.hosts


def test_extract_does_not_list_cidr_network_as_bare_host():
    ent = aug.extract_entities(_CIDR_EXAMPLE)
    assert "10.10.10.0" not in ent.hosts  # CIDR agi bare-host sayilmaz


def test_extract_finds_hostname():
    ex = {"messages": [{"role": "user", "content": "web01.lab.local uzerinde nikto calistir"}]}
    ent = aug.extract_entities(ex)
    assert "web01.lab.local" in ent.hostnames
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/data/test_augment_targets.py -v`
Expected: FAIL — `ModuleNotFoundError: data.sft.tools.augment_targets`

- [ ] **Step 3: Write minimal implementation**

```python
# data/sft/tools/augment_targets.py
"""Konusma-tutarli hedef remapping — her ornekteki TUM IP/CIDR/host'u tutarli
bir haritayla yeni bir sete cevir, K varyant uret. Kor find-replace DEGIL:
ayni ornek icinde tarama-ciktisi <-> takip-hedefi baglantisi korunur."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from ipaddress import IPv4Address, IPv4Network, ip_address, ip_network

_CIDR_RE = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d{1,3}){3})/(\d{1,2})(?![\d.])")
_IP_RE = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d{1,3}){3})(?![\d.])")
# Lab hostname'leri: bilinen suffiksler (over-match'i onlemek icin dar).
_HOST_RE = re.compile(
    r"\b(?:[a-z0-9][a-z0-9-]*\.)*[a-z0-9][a-z0-9-]*\."
    r"(?:local|internal|lab\.local|corp\.local|kurum\.local|kurum\.com)\b"
)
_BARE_HOSTS = ("octopus-target", "kali-victim")


@dataclass
class Entities:
    cidrs: list[str] = field(default_factory=list)
    hosts: list[str] = field(default_factory=list)
    hostnames: list[str] = field(default_factory=list)


def _all_text(example: dict) -> str:
    return "\n".join(m.get("content", "") for m in example.get("messages", []))


def extract_entities(example: dict) -> Entities:
    text = _all_text(example)
    cidrs, cidr_nets = [], []
    for m in _CIDR_RE.finditer(text):
        c = f"{m.group(1)}/{m.group(2)}"
        if c not in cidrs:
            cidrs.append(c)
            cidr_nets.append(ip_network(c, strict=False))
    hosts = []
    for m in _IP_RE.finditer(text):
        ip = m.group(1)
        try:
            addr = ip_address(ip)
        except ValueError:
            continue
        # CIDR agi/broadcast adresini bare-host sayma
        if any(addr == n.network_address or addr == n.broadcast_address for n in cidr_nets):
            continue
        if ip not in hosts:
            hosts.append(ip)
    hostnames = []
    for m in _HOST_RE.finditer(text):
        if m.group(0) not in hostnames:
            hostnames.append(m.group(0))
    for bare in _BARE_HOSTS:
        if bare in text and bare not in hostnames:
            hostnames.append(bare)
    return Entities(cidrs=cidrs, hosts=hosts, hostnames=hostnames)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/data/test_augment_targets.py -v`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add data/sft/tools/augment_targets.py tests/data/test_augment_targets.py
git commit -m "feat(data): ag-varlik cikarici (IP/CIDR/hostname), CIDR agini bare-host'tan ayirir"
```

---

### Task 3: Coherent mapping + apply

**Files:**
- Modify: `data/sft/tools/augment_targets.py`
- Test: `tests/data/test_augment_targets.py`

**Interfaces:**
- Consumes: `Entities`, `extract_entities` (Task 2), `target_pool` (Task 1).
- Produces:
  - `build_mapping(ent: Entities, rng: random.Random) -> dict[str, str]` — old→new, consistent; hosts inside a source CIDR map into the mapped subnet; a lone standalone host may become a hostname (quota).
  - `apply_mapping(example: dict, mapping: dict[str, str]) -> dict` — boundary-safe literal substitution across all message contents; returns a NEW example (no mutation).

- [ ] **Step 1: Write the failing test**

```python
# append to tests/data/test_augment_targets.py
import json
import random
from ipaddress import ip_address, ip_network
from data.sft.tools import augment_targets as aug  # (already imported above)


def test_mapping_keeps_hosts_inside_mapped_cidr():
    ent = aug.extract_entities(_CIDR_EXAMPLE)
    mapping = aug.build_mapping(ent, random.Random(4))
    new_cidr = mapping["10.10.10.0/24"]
    net = ip_network(new_cidr, strict=False)
    for old_host in ("10.10.10.5", "10.10.10.20"):
        assert ip_address(mapping[old_host]) in net  # takip-hedefi hala ag icinde


def test_apply_is_coherent_and_replaces_all():
    ent = aug.extract_entities(_CIDR_EXAMPLE)
    mapping = aug.build_mapping(ent, random.Random(4))
    out = aug.apply_mapping(_CIDR_EXAMPLE, mapping)
    blob = json.dumps(out, ensure_ascii=False)
    assert "10.10.10." not in blob                       # hicbir eski hedef kalmadi
    # nmap takip-hedefi, tarama ciktisinda gecen bir host olmali (tutarlilik)
    follow = json.loads(out["messages"][4]["content"].split("```arac\n")[1].split("\n```")[0])
    assert follow["parametreler"]["hedef"] in out["messages"][3]["content"]


def test_apply_does_not_mutate_source():
    before = json.dumps(_CIDR_EXAMPLE, ensure_ascii=False)
    aug.apply_mapping(_CIDR_EXAMPLE, {"10.10.10.0/24": "192.168.9.0/24"})
    assert json.dumps(_CIDR_EXAMPLE, ensure_ascii=False) == before


def test_boundary_safe_substitution():
    # "10.10.10.5" -> "1.1.1.1" iken "10.10.10.50" BOZULMAMALI
    ex = {"messages": [{"role": "user", "content": "10.10.10.5 ve 10.10.10.50"}]}
    out = aug.apply_mapping(ex, {"10.10.10.5": "1.1.1.1"})
    assert out["messages"][0]["content"] == "1.1.1.1 ve 10.10.10.50"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/data/test_augment_targets.py -k "mapping or apply or boundary" -v`
Expected: FAIL — `AttributeError: module ... has no attribute 'build_mapping'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to data/sft/tools/augment_targets.py
import random  # noqa: E402
from data.sft.tools import target_pool as tp  # noqa: E402


def build_mapping(ent: Entities, rng: random.Random) -> dict[str, str]:
    mapping: dict[str, str] = {}
    src_net_to_new: dict[str, IPv4Network] = {}
    # 1) CIDR'lari yeni subnet'lere esle
    for c in ent.cidrs:
        src = ip_network(c, strict=False)
        new = tp.sample_subnet(rng, prefix=src.prefixlen)
        mapping[c] = str(new)
        src_net_to_new[c] = new
    used: set[str] = set()

    def _fresh_host(subnet: IPv4Network | None) -> str:
        for _ in range(64):
            h = str(tp.sample_host(rng, subnet))
            if h not in used:
                used.add(h)
                return h
        used.add(h)
        return h

    # 2) host'lari esle: bir kaynak CIDR'a aitse -> ilgili yeni subnet icine
    lone_standalone = (not ent.cidrs) and len(ent.hosts) == 1
    for ip in ent.hosts:
        addr = ip_address(ip)
        parent = next((c for c in ent.cidrs
                       if addr in ip_network(c, strict=False)), None)
        if parent is not None:
            mapping[ip] = _fresh_host(src_net_to_new[parent])
        elif lone_standalone and tp.use_hostname(rng):
            mapping[ip] = tp.sample_hostname(rng)   # tek-host -> hostname (ezber kirar)
        else:
            mapping[ip] = _fresh_host(None)
    # 3) hostname'leri yeni hostname'lere esle
    for hn in ent.hostnames:
        mapping[hn] = tp.sample_hostname(rng)
    return mapping


def _sub_all(text: str, mapping: dict[str, str]) -> str:
    # Uzun anahtar once (CIDR "x/24" bare IP'den once); IP'ler icin rakam/nokta siniri.
    for key in sorted(mapping, key=len, reverse=True):
        val = mapping[key]
        if "/" in key:                       # CIDR: literal degistir
            text = text.replace(key, val)
        elif _IP_RE.fullmatch(key):          # bare IP: sinir-guvenli
            text = re.sub(rf"(?<![\d.]){re.escape(key)}(?![\d.])", val, text)
        else:                                # hostname
            text = re.sub(rf"(?<![\w.-]){re.escape(key)}(?![\w.-])", val, text)
    return text


def apply_mapping(example: dict, mapping: dict[str, str]) -> dict:
    msgs = [dict(m) for m in example["messages"]]
    for m in msgs:
        if "content" in m:
            m["content"] = _sub_all(m["content"], mapping)
    return {**example, "messages": msgs}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/data/test_augment_targets.py -v`
Expected: PASS (7 passed)

- [ ] **Step 5: Commit**

```bash
git add data/sft/tools/augment_targets.py tests/data/test_augment_targets.py
git commit -m "feat(data): konusma-tutarli remap (CIDR-ici host korunur, tek-host->hostname, sinir-guvenli)"
```

---

### Task 4: File augmentation + CLI

**Files:**
- Modify: `data/sft/tools/augment_targets.py`
- Test: `tests/data/test_augment_targets.py`

**Interfaces:**
- Consumes: `extract_entities`, `build_mapping`, `apply_mapping`.
- Produces:
  - `augment_example(example: dict, k: int, rng: random.Random) -> list[dict]` — returns the original plus `k` coherent variants.
  - `main(argv: list[str] | None = None) -> None` — CLI: `--src` (default `tools/` sibling files), `--out` (default `data/sft/tools_aug/`), `--k` (default 3), `--seed` (default 3407). Reads each `*.jsonl` (excluding build outputs), writes augmented `*.jsonl` per source into `--out`.

- [ ] **Step 1: Write the failing test**

```python
# append to tests/data/test_augment_targets.py
def test_augment_example_returns_original_plus_k():
    variants = aug.augment_example(_CIDR_EXAMPLE, k=3, rng=random.Random(5))
    assert len(variants) == 4                     # 1 orijinal + 3 varyant
    assert variants[0] == _CIDR_EXAMPLE           # ilk = orijinal (aynen)
    blobs = {json.dumps(v, ensure_ascii=False) for v in variants}
    assert len(blobs) == 4                         # hepsi farkli


def test_augment_variants_stay_valid_arac():
    for v in aug.augment_example(_CIDR_EXAMPLE, k=3, rng=random.Random(6)):
        txt = " ".join(m["content"] for m in v["messages"] if m["role"] == "assistant")
        assert "```arac" in txt                    # arac blogu korundu
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/data/test_augment_targets.py -k augment_example -v`
Expected: FAIL — `AttributeError: ... 'augment_example'`

- [ ] **Step 3: Write minimal implementation**

```python
# append to data/sft/tools/augment_targets.py
import argparse  # noqa: E402
import glob  # noqa: E402
import json  # noqa: E402
import sys  # noqa: E402
from pathlib import Path  # noqa: E402

_HERE = Path(__file__).resolve().parent
_SKIP = {"octopus_tools_tr.jsonl"}  # build ciktisi — kaynak degil


def augment_example(example: dict, k: int, rng: random.Random) -> list[dict]:
    out = [example]
    for _ in range(k):
        ent = extract_entities(example)
        out.append(apply_mapping(example, build_mapping(ent, rng)))
    return out


def main(argv: list[str] | None = None) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Hedef dengeleme augmentasyonu")
    ap.add_argument("--src", default=str(_HERE), help="kaynak *.jsonl klasoru")
    ap.add_argument("--out", default=str(_HERE.parent / "tools_aug"))
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--seed", type=int, default=3407)
    args = ap.parse_args(argv)
    out_dir = Path(args.out)
    out_dir.mkdir(exist_ok=True)
    rng = random.Random(args.seed)
    total_in = total_out = 0
    for f in sorted(glob.glob(str(Path(args.src) / "*.jsonl"))):
        name = Path(f).name
        if name in _SKIP:
            continue
        rows_out = []
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            ex = json.loads(line)
            total_in += 1
            rows_out.extend(augment_example(ex, args.k, rng))
        with open(out_dir / name, "w", encoding="utf-8") as w:
            for r in rows_out:
                w.write(json.dumps(r, ensure_ascii=False) + "\n")
        total_out += len(rows_out)
        print(f"   {name}: {len(rows_out)} satir")
    print(f"[OK] {total_in} kaynak -> {total_out} augmented ({out_dir})")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/data/test_augment_targets.py -v`
Expected: PASS (9 passed)

- [ ] **Step 5: Commit**

```bash
git add data/sft/tools/augment_targets.py tests/data/test_augment_targets.py
git commit -m "feat(data): dosya augmentasyonu + CLI (--src/--out/--k/--seed, orijinal+K varyant)"
```

---

### Task 5: Hostname-verbatim seed examples

**Files:**
- Create: `data/sft/tools/hostname_tr.jsonl`
- Test: `tests/data/test_hostname_seed.py`

**Interfaces:**
- Consumes: nothing (data file). Validated structurally.
- Produces: ≥15 examples where the user gives a **hostname** target and the assistant copies it **verbatim** into the `arac` `hedef` field.

Author ≥15 multi-turn examples. Each: system (persona/arac spec), user (hostname target), assistant (```arac``` with the SAME hostname in `hedef`), tool (output referencing the hostname), assistant (Turkish interpretation). Vary tool + hostname across: `nmap`/`web01.lab.local`, `nikto`/`wordpress.lab.local`, `gobuster`/`portal.kurum.local`, `nuclei`/`api-gw.internal`, `smbclient`/`fileserver.internal`, `hydra`/`vpn-gw.corp.local`, `wpscan`/`wordpress.lab.local`, `sqlmap`/`app-staging.internal`, `dnsrecon`/`corp.local`, `enum4linux-ng`/`dc01.corp.local`, `feroxbuster`/`gitlab.lab.local`, `whatweb`/`mail.corp.local`, `ffuf`/`api-gw.internal`, `netexec`/`ad01.corp.local`, `nmap`/`octopus-target`.

Two complete reference rows (write the rest in the same shape):

```json
{"messages":[{"role":"system","content":"Sen Octópus'sun: yetkili siber güvenlik asistanı. Araçları ```arac\n{\"arac\":\"<ad>\",\"parametreler\":{...}}\n``` bloğuyla çağırırsın; çıktı `tool` rolüyle döner, Türkçe yorumlarsın. Yalnızca kapsam-içi/izinli hedeflerde çalışırsın."},{"role":"user","content":"Yetkili testte web01.lab.local sunucusunda servis ve sürüm taraması yap."},{"role":"assistant","content":"Hedefi verildiği gibi (hostname) kullanıyorum; `-sV` ile servis/sürüm tespiti yaparım.\n```arac\n{\"arac\":\"nmap\",\"parametreler\":{\"hedef\":\"web01.lab.local\",\"secenekler\":\"-sV -Pn\"}}\n```"},{"role":"tool","content":"web01.lab.local (resolved)\n80/tcp  open http nginx 1.18.0\n443/tcp open ssl/http nginx 1.18.0"},{"role":"assistant","content":"**web01.lab.local** üzerinde 80/443 açık, nginx 1.18.0 çalışıyor. Web yüzeyi var; sıradaki mantıklı adım `nuclei`/`nikto` ile bu iki portu zafiyet açısından taramak. Devam edeyim mi?"}]}
{"messages":[{"role":"system","content":"Sen Octópus'sun: yetkili siber güvenlik asistanı. Araçları ```arac``` bloğuyla çağırır, çıktıyı Türkçe yorumlarsın. Yalnızca izinli hedef."},{"role":"user","content":"portal.kurum.local üzerinde gizli dizinleri bul."},{"role":"assistant","content":"Hedefi hostname olarak koruyup `gobuster` ile dizin brute-force yapıyorum.\n```arac\n{\"arac\":\"gobuster\",\"parametreler\":{\"hedef\":\"http://portal.kurum.local\",\"secenekler\":\"dir -w /usr/share/wordlists/dirb/common.txt\"}}\n```"},{"role":"tool","content":"/admin (301)\n/backup (200)\n/login (200)"},{"role":"assistant","content":"**portal.kurum.local** üzerinde `/admin`, `/backup`, `/login` bulundu. `/backup` (200) ilgi çekici — yanlış yapılandırılmış yedek olabilir. Yetkili kapsamda içeriğini incelememi ister misin?"}]}
```

- [ ] **Step 1: Write the failing test**

```python
# tests/data/test_hostname_seed.py
import json
import re
from pathlib import Path

_PATH = Path("data/sft/tools/hostname_tr.jsonl")
_ARAC = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)


def _rows():
    return [json.loads(l) for l in _PATH.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_at_least_15_examples():
    assert len(_rows()) >= 15


def test_user_hostname_appears_verbatim_in_arac_hedef():
    host_re = re.compile(r"[a-z0-9][a-z0-9.-]*\.(?:local|internal)|octopus-target")
    for row in _rows():
        user = next(m["content"] for m in row["messages"] if m["role"] == "user")
        hosts = set(host_re.findall(user))
        assert hosts, f"kullanici mesajinda hostname yok: {user[:60]}"
        arac_txt = " ".join(m["content"] for m in row["messages"] if m["role"] == "assistant")
        hedefs = " ".join(json.loads(b).get("parametreler", {}).get("hedef", "")
                          for b in _ARAC.findall(arac_txt))
        assert any(h in hedefs for h in hosts), f"hostname arac hedefinde yok: {hosts}"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/data/test_hostname_seed.py -v`
Expected: FAIL — `FileNotFoundError` (file not authored yet)

- [ ] **Step 3: Author the data file**

Create `data/sft/tools/hostname_tr.jsonl` with ≥15 rows following the two reference rows and the tool/hostname list above. Each row: system → user(hostname) → assistant(```arac``` with hostname verbatim in `hedef`) → tool → assistant(Turkish interpretation).

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/data/test_hostname_seed.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add data/sft/tools/hostname_tr.jsonl tests/data/test_hostname_seed.py
git commit -m "feat(data): hostname-verbatim tohum ornekleri (>=15, model hostname'i birebir onurlandirir)"
```

---

### Task 6: Distribution audit in build_tools

**Files:**
- Modify: `data/sft/tools/build_tools.py`
- Test: `tests/data/test_build_audit.py`

**Interfaces:**
- Consumes: augmented examples.
- Produces:
  - `target_audit(rows: list[dict], cap: float = 0.06, host_floor: float = 0.20) -> tuple[bool, str]` — returns `(ok, report)`; `ok=False` if any concrete target exceeds `cap` or hostname share < `host_floor`.
  - `main()` calls it, prints the report, and `sys.exit(1)` when not ok.

- [ ] **Step 1: Write the failing test**

```python
# tests/data/test_build_audit.py
from data.sft.tools.build_tools import target_audit


def _row(hedef):
    return {"messages": [
        {"role": "system", "content": "s"},
        {"role": "user", "content": f"{hedef} tara"},
        {"role": "assistant", "content": f"```arac\n{{\"arac\":\"nmap\",\"parametreler\":{{\"hedef\":\"{hedef}\"}}}}\n```"},
    ]}


def test_audit_flags_over_concentration():
    rows = [_row("10.10.10.5") for _ in range(90)] + [_row(f"10.0.0.{i}") for i in range(10)]
    ok, report = target_audit(rows)
    assert ok is False
    assert "10.10.10.5" in report


def test_audit_passes_balanced_with_hostnames():
    rows = [_row(f"10.{i}.{i}.{i}") for i in range(1, 40)]
    rows += [_row(h) for h in ("web01.lab.local", "dc01.corp.local", "api-gw.internal",
                               "portal.kurum.local", "fileserver.internal",
                               "app-staging.internal", "octopus-target", "mail.corp.local",
                               "gitlab.lab.local", "vpn-gw.corp.local", "ad01.corp.local")]
    ok, report = target_audit(rows)
    assert ok is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/data/test_build_audit.py -v`
Expected: FAIL — `ImportError: cannot import name 'target_audit'`

- [ ] **Step 3: Write minimal implementation**

```python
# add to data/sft/tools/build_tools.py (after _tools_of), and call from main()
def target_audit(rows: list[dict], cap: float = 0.06, host_floor: float = 0.20) -> tuple[bool, str]:
    """Hedef dagilimi denetimi: tek hedef <= cap; hostname payi >= host_floor."""
    from collections import Counter
    hedefs: Counter = Counter()
    for o in rows:
        for m in o.get("messages", []):
            if m.get("role") != "assistant":
                continue
            for blk in ARAC_RE.findall(m.get("content", "")):
                try:
                    v = json.loads(blk).get("parametreler", {})
                except Exception:
                    continue
                for key in ("hedef", "url", "hedef_url", "domain"):
                    if key in v and isinstance(v[key], str):
                        hedefs[v[key].replace("http://", "").replace("https://", "").split("/")[0]] += 1
    total = sum(hedefs.values()) or 1
    is_host = lambda t: not re.match(r"^\d{1,3}(\.\d{1,3}){3}$", t)  # noqa: E731
    host_share = sum(c for t, c in hedefs.items() if is_host(t)) / total
    worst = hedefs.most_common(1)[0] if hedefs else ("-", 0)
    ok = (worst[1] / total <= cap) and (host_share >= host_floor)
    lines = [f"[DENETIM] toplam hedef cagrisi={total} | en yogun={worst[0]} ({worst[1]}, "
             f"{worst[1]/total:.1%}) | hostname payi={host_share:.1%}",
             f"          esik: tek<= {cap:.0%}, hostname>= {host_floor:.0%} -> "
             f"{'GECTI' if ok else 'KALDI'}"]
    return ok, "\n".join(lines)
```

Then in `main()`, after writing `OUT`, add:

```python
    ok, report = target_audit(rows)
    print(report)
    if not ok:
        sys.exit(1)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/data/test_build_audit.py -v`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add data/sft/tools/build_tools.py tests/data/test_build_audit.py
git commit -m "feat(data): dagilim denetimi (tek hedef<=6%, hostname>=20%) build_tools'a gate"
```

---

### Task 7: End-to-end regenerate + verify

**Files:**
- Modify: `data/sft/manifest.json` (regenerated), `data/sft/train.jsonl` / `val.jsonl` / `test.jsonl` (regenerated), `data/sft/tools_dist/octopus_tools_tr.jsonl` (regenerated)
- Create: none (uses Tasks 1-6)

**Interfaces:**
- Consumes: all prior tasks.

- [ ] **Step 1: Run the augmentation**

Run: `uv run python -m data.sft.tools.augment_targets --k 3 --seed 3407`
Expected: `[OK] <N> kaynak -> <~4N> augmented (data/sft/tools_aug)`

- [ ] **Step 2: Build the merged tool set from augmented dir (audit gates it)**

Run: `uv run python data/sft/tools/build_tools.py --src data/sft/tools_aug`
Expected: coverage report + `[DENETIM] ... -> GECTI` (exit 0). If `KALDI`, raise `--k` or widen hostname list and re-run.

> If `build_tools.py` does not yet accept `--src`, add an argparse `--src` (default `str(HERE)`) whose value replaces `HERE` in the `glob` on line ~90. Include this one-line change here and commit it with Task 6.

- [ ] **Step 3: Rebuild the SFT splits**

Run: `uv run python -m data.sft.build_sft`
Expected: new `manifest.json` with `tools` count ≈ 4× previous (~500), `train/val/test` updated.

- [ ] **Step 4: Verify the whole suite is green**

Run: `uv run pytest -q`
Expected: all tests pass (Tasks 1-6 + existing 63).

- [ ] **Step 5: Commit the regenerated dataset**

```bash
git add data/sft/tools_aug data/sft/tools_dist/octopus_tools_tr.jsonl \
        data/sft/train.jsonl data/sft/val.jsonl data/sft/test.jsonl data/sft/manifest.json
git commit -m "data: hedef-dengeli SFT seti yeniden uretildi (125->~500, denetim GECTI)"
```

---

## Self-Review

**Spec coverage:**
- §4.1 coherent remapper → Tasks 2, 3, 4 ✅
- §4.2 balanced pool + cap → Task 1 (sampler) + Task 6 (audit enforces cap) ✅
- §4.3 hostname-verbatim seeds → Task 5 ✅
- §4.4 pipeline integration (augment before build_tools) → Task 4 (`--out tools_aug`) + Task 7 (`build_tools --src`) ✅
- §6 validation (balance, coherence, validity, no-leak) → Task 6 audit + Task 3 coherence tests; **split-leak**: augmented variants of one source could split across train/val/test. `build_sft` splits after dedup — variants differ, so they are distinct rows and MAY split. Mitigation noted below.
- §8 acceptance (≈500, audit green, hostname honored) → Task 7 ✅

**Split-leak gap (from §6):** variants of one source example are near-duplicates; letting them split across train/test slightly inflates eval optimism. Low risk for this dataset (val/test are 25 each of 1763). Accept for A; if stricter isolation is wanted later, group-by-source before splitting in `build_sft` — tracked as a follow-up, not blocking.

**Placeholder scan:** no TBD/TODO; all code steps show complete code. Task 5 authored-data has 2 full reference rows + explicit scenario list (standard for data-authoring tasks).

**Type consistency:** `extract_entities → Entities`; `build_mapping(Entities, Random) → dict[str,str]`; `apply_mapping(dict, dict) → dict`; `augment_example(dict, int, Random) → list[dict]`; `target_audit(list, float, float) → tuple[bool,str]` — consistent across Tasks 2-7. `_IP_RE`/`_CIDR_RE`/`ARAC_RE` reused, not redefined.
