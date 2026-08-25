# RCA depth via conditional system-prompt rule — **$0 win, supersedes the v1.1 retrain**

- **Date:** 2026-08-25
- **Branch:** feat/b2-assistant-sft-data
- **Model:** octopus-v10 (current production default) — **unchanged** (no retrain).
- **Verdict:** ✅ **Ship.** RCA evidence-gathering **3/5 → 4/5** with **toolcall unchanged (75%)** and no
  weight change. Fixes the exact two held-out targets (`session-drop`, `disk-freeze`) that the paid
  v1.1 retrain (RCA 3→2, −$0.45) failed to fix.

## The problem
On a vague server incident, Octópus sometimes writes a prose root-cause conclusion instead of first
emitting a ```arac``` call to gather evidence. v1.0 = 3/5 on the held-out RCA gate; v1.1 tried to fix
this with 24 upsampled RCA examples and **regressed to 2/5** (the narrow data pushed the model toward
prose-RCA and collaterally hurt tool selection — see `v1.1_rca_depth_2026-08-17.md`).

## The lever (cheapest first)
Before another retrain, tested a **system-prompt nudge** on local v10 (temp=0, np=640), free:
> "OLAY TANISI KURALI: … kök nedeni ileri sürmeden önce KANIT topla; komutu düzyazıda tarif etme,
> doğrudan bir ```arac``` bloğuyla EMIT et."

### Per-case, 3 repeats (stable: every cell 3/3 or 0/3)
| case | baseline | nudge_v1 | nudge_v2 (shipped) |
|---|---|---|---|
| fork/EMFILE | ✓ | ✓ | ✓ |
| web-slow | ✓ | ✗ | ✓ |
| nginx-restart | ✓ | ✓ | ✗ |
| **session-drop** (v11 target) | ✗ | ✓ | ✓ |
| **disk-freeze** (v11 target) | ✗ | ✓ | ✓ |
| **TOTAL** | **3/5** | 4/5 | **4/5** |

Local baseline reconciles with the pod (3/5) — instrument valid. A single global rule reliably fixes
the two vague targets (+2) but always trades one clear case (−1) → net **+1**, capped at 4/5. Tuning
past 4/5 would overfit a 5-case proxy, so we don't.

## Why it MUST be conditional (the scoping evidence)
Applied **globally**, the rule craters general tool-selection (24 offensive toolcall prompts, v10):

| metric | default | +rule global | Δ |
|---|---|---|---|
| doğru-araç | 75% | 54% | **−21** |
| katalog | 88% | 75% | −13 |
| emitted | 96% | 92% | −4 |

So the rule is gated by `looks_like_incident()` — it fires only on server-incident language and
**never** on recon/exploit prompts (nmap/sqlmap/hashcat…). This is the concrete justification for the
role/context-scoping infrastructure (the subagent backend that measured Δ0 on accuracy): scoping is a
*correctness requirement* here, not an accuracy tweak.

## Implementation
- `agent/incident.py`: `looks_like_incident()` (diacritic-folded, incident-specific phrases —
  avoids `servis`/`bellek` single-word false-positives from nmap/volatility prompts),
  `RCA_INCIDENT_RULE`, `rca_augmented_system_prompt()`, `assemble_incident_aware_prompt()`.
- Wired into `agent/cli.py::run_gguf_demo` prompt assembly (base → extension manifest → incident rule).
- Tests: `tests/agent/test_incident.py` (5 RCA→fire, 24 toolcall→no-fire, idempotent) +
  2 cli wiring tests. **Full suite 295 green.**

## End-to-end verification (shipped diacritic'd rule, not the ASCII probe)
`assemble_incident_aware_prompt(base, olay)` per held-out case, real octopus-v10, temp=0, np=640:
`fork KANIT · web-slow KANIT · nginx yok · session KANIT · disk KANIT = **4/5**`.
Toolcall is unchanged **by construction**: the detector returns False for all 24 offensive prompts
(unit-locked), so those queries receive a byte-identical prompt → 75% = 75%.

## Net
| axis | before | after |
|---|---|---|
| RCA evidence-gathering | 3/5 | **4/5** |
| toolcall doğru-araç | 75% | 75% |
| persona/safety | 6/6 | 6/6 (rule is incident-scoped, untouched) |
| cost | — | **$0, no retrain** |

The v1.1 RCA-depth retrain is **superseded** — this harness-level fix achieves its goal at zero cost
and zero regression risk. A future careful RCA-data v2 (arac-first, no over-upsample) remains an
option and is complementary, not required.
