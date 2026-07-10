# SFT Target Rebalancing & Hostname Handling (Sub-project A)

**Date:** 2026-07-10
**Status:** Design — approved for spec, pending implementation plan
**Scope:** Data foundation for the next Octópus retrain. Part **A** of a 4-part dataset
expansion (A: data foundation → B: assistant tools → C: domain depth → D: reasoning + memory).
One retrain at the end; data built in pieces.

---

## 1. Problem

The v0.7 model reproduces a memorized scan target (`10.10.10.5`) instead of honoring the
target given in the prompt — it misses hostnames entirely, falling back to the memorized IP.

**Root cause (confirmed): class imbalance, not loss masking.** Target-value distribution across
the 125 tool examples:

| Target | Count |
|---|---|
| `10.10.10.5` | 30 |
| `10.10.10.20` | 30 |
| `10.0.0.8` | 15 |
| `10.10.10.99` | 14 |
| … long tail … | ≤ 11 each |

The memorized IP lives in the **assistant `arac` block** (the completion the model is trained to
emit). Two dominant targets at 30× each teach the model to emit them reflexively. This is the
textbook tool-use-SFT failure: *"if training is 90% one target, the model rarely emits the
others — audit distribution and oversample the under-represented."* Fixing it is a pure **data**
lever, independent of the training-config (masking) question.

## 2. Goals / Non-goals

**Goals (A):**
- Break single-target dominance so the model emits the prompt's target, not a memorized one.
- Teach the model to place a **hostname verbatim** in the `arac` block (not resolve to a
  memorized IP).
- Grow the tool-example pool from 125 toward ~500 **balanced, internally-consistent** trajectories.
- Preserve every existing quality property: valid `arac` blocks, persona/guardrail system prompt,
  scope-safe ("authorized lab") framing, Turkish interpretation of tool output.

**Explicit non-goals (separate items — do NOT fold into A):**
- **Loss masking** (`assistant_only_loss` / `completion_only_loss`). Uncertain benefit, requires
  restructuring the flat-text data feed, and does **not** cause the memorization. Handle as a
  standalone training-config item, de-risked with one small pilot run before the big retrain.
- **Reasoning↔arac signal balance** (long `<düşünce>` drowning the short `arac` block). A
  sub-project **D** concern needing loss/signal balancing, not target data.
- **New tool coverage** (filling 0-example catalog tools). Sub-project **C** (domain depth).

## 3. Key design constraint: conversation-coherent remapping

Targets are **threaded through the whole conversation**, not stored in one field. In a single
example the same network appears as: the user's CIDR, the `arac` `hedef` parameter, the `tool`
output lines (discovered hosts), and the assistant's interpretation. A follow-up `arac` call
often targets a host that the **previous tool output produced**.

Therefore augmentation MUST remap the entire conversation with **one consistent mapping**, not a
blind global find-replace. Blind replacement breaks the scan-output ↔ follow-up-target link.

## 4. Components

### 4.1 Coherent target remapper (`data/sft/tools/augment_targets.py`)

For each source example, produce `K` variants:

1. **Extract** every distinct network entity in the example across all message contents:
   IPv4 addresses, CIDRs, and lab hostnames. Preserve relationships (which hosts fall inside
   which CIDR).
2. **Sample** a fresh coherent target set from the balanced pool (§4.2): a base subnet + host
   octets, or a hostname, keeping intra-example structure (a CIDR maps to a new CIDR; hosts inside
   it map to hosts inside the new CIDR; a standalone host maps to a standalone host).
3. **Build one mapping dict** old→new for the whole example, then apply it to every message
   content by literal substitution. Because the mapping is consistent, scan output and follow-up
   targets stay linked.
4. **Re-validate** the rendered variant with the existing `build_tools._valid` check (system-first,
   ≥1 `arac` or refusal, parseable `arac` JSON).

The remapper is deterministic given a seed (reproducible dataset).

### 4.2 Balanced target pool (`data/sft/tools/target_pool.py`)

A sampler that draws targets with a hard distribution cap so no single target dominates.

- **Hostnames** (lab/authorized framing): `octopus-target`, `web01.lab.local`, `dc01.corp.local`,
  `app-staging.internal`, `kali-victim`, … (a curated list, all clearly internal/lab).
- **Private IP ranges:** `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` — sampled subnets/hosts.
- **CIDRs:** `/24` and `/28` blocks drawn from the ranges above.
- **Documentation/TEST-NET:** a minority slice of `203.0.113.0/24` (RFC 5737) for public-target
  shapes without pointing at a real host.
- **Distribution rule:** across the whole augmented set, **no single concrete target exceeds ~6%**;
  hostnames collectively make up a deliberate share (target ~25–30%) so hostname-honoring is
  well-represented. Sampling is round-robin/quota-based, not uniform-random, to guarantee the cap.

### 4.3 Hostname-verbatim seed examples (`data/sft/tools/hostname_tr.jsonl`)

A small hand-authored set (~15–25 examples) where the target is expressed **only as a hostname**
in the user prompt and the model must copy that hostname **verbatim** into the `arac` `hedef`
field — never substitute an IP. These directly counter the "fall back to memorized IP" behavior
and seed the pattern the remapper then amplifies.

### 4.4 Pipeline integration

- New augment step runs **before** `build_tools.py`: `tools/*.jsonl` (+ `hostname_tr.jsonl`) →
  `augment_targets.py` → expanded per-domain set → existing `build_tools.py` (dedup, validate,
  coverage report) → `tools_dist/octopus_tools_tr.jsonl` → `build_sft.py` (unchanged).
- No change to `build_sft.py`, persona, or the training script in A.

## 5. Data flow

```
tools/*.jsonl  +  hostname_tr.jsonl
        │
        ▼  augment_targets.py  (coherent remap × K, seeded)
   augmented per-domain examples
        │
        ▼  build_tools.py  (dedup + _valid + coverage/distribution report)
   tools_dist/octopus_tools_tr.jsonl
        │
        ▼  build_sft.py  (normalize + persona + split)   ← unchanged
   train.jsonl / val.jsonl / test.jsonl
```

## 6. Validation

The build must emit a **distribution audit** and fail loudly on regressions:

- **Balance:** no concrete target > 6% of tool examples; hostnames ≥ ~20%.
- **Coherence:** in each augmented example, every follow-up `arac` target either appears in a
  preceding `tool` output or matches the user-stated target (no dangling/inconsistent targets).
- **Validity:** all `arac` blocks parse; system-first; scope framing intact.
- **No leakage:** augmented variants of the same source stay within one split (train/val/test) —
  do not let a remap of a train example land in test.

## 7. Testing

- Unit tests for `augment_targets`: coherence (scan-output ↔ follow-up link preserved), determinism
  (same seed → same output), mapping completeness (no old target survives in a variant).
- Unit tests for `target_pool`: distribution cap honored over a large draw; hostname share in range.
- Golden example: the `net_scan` CIDR case remapped correctly (CIDR + three hosts stay consistent).

## 8. Acceptance criteria

- Augmented tool set ≈ 500 examples, distribution audit green (no target > 6%, hostnames ≥ ~20%).
- On a held-out eval prompt that gives a **hostname** target, the model emits that hostname
  verbatim in the `arac` block (measured after the retrain, alongside B).
- On a prompt giving an explicit non-`10.10.10.x` IP, the model targets that IP, not a memorized one.

> The real-time web query test ("İspanya–Belçika maçı saat kaçta") is a **sub-project B** acceptance
> criterion (web tools), listed here only to keep the end-to-end picture; A does not add web tools.

## 9. Related

- Positioning & harness context: `docs/decisions/`, agent-harness memory.
- Research basis: tool-use SFT best practice (class balance, 500–2000 quality trajectories),
  BalanceSFT (reasoning/arac signal imbalance → D), deep-research harness ports (B/C).
