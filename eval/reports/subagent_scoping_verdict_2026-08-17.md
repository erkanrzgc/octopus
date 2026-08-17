# Subagent role-scoping — measurement verdict (Task 5)

- **Date:** 2026-08-17
- **Model:** octopus-v10 (current default), A6000 pod, paired same-run.
- **Instrument:** `eval/run_subagent_eval.py` on the 24 held-out toolcall cases.
- **Verdict:** ❌ **Role-scoping (B) does NOT improve tool-selection. Do NOT wire it as the default.**
  The subagent runtime is sound infrastructure (committed), but the hypothesis it targeted is not
  supported by this eval. `agent/cli.py` stays flat/`general`.

## Result
| | correct-tool |
|---|---|
| **flat** (single-turn, first call) | 20/24 = **83%** |
| **scoped-B** (route → role registry → first executed) | 20/24 = **83%** |
| **Δ** | **0** |

Data table: `subagent_scoping_octopus-v10_2026-08-17.md`.

## Why scoping had zero net effect (three identifiable reasons)
1. **Router falls back to `general` ~46% of the time.** Routing distribution this run:
   `general 11 · web 5 · password 2 · osint 2 · exploit-ad 2 · wireless 1 · traffic-mitm 1`.
   Nearly half the cases were never scoped → identical to flat by construction.
2. **The fixable errors were `asistan` tools, which scoping can't block.** The two wrong picks
   scoping might have corrected were `web_fetch` (routed osint) and `web_search` (routed password).
   Both are `asistan` domain = **cross-cutting, allowed in every role by design** → structurally
   immune to role-scoping. Scoping targets the wrong failure mode.
3. **The model's domain-selection is already good (83%).** The 4 failures are not
   "picked a tool from the wrong offensive domain" (which scoping fixes) — they are generic
   assistant-tool substitutions (`web_fetch`/`web_search`) or non-emission (`traffic-mitm → None`).
   Where scoping did pick a different tool (amass↔subfinder, theHarvester↔spiderfoot,
   subfinder↔dnsrecon, xsstrike↔nuclei), it was already correct either way — no gain, no loss.

## Was the measurement trustworthy?
Yes. Paired on the same pod/model/cases; the flat leg reproduced v10's known ~75–83% range
(temp=0.6 default, single run — the 83% here vs 75% in the 2026-08-17 paired eval is within
temp-0.6 noise, and irrelevant: the verdict is the **within-run flat-vs-scoped delta = 0**).
jinja2 present (sanity generations were real Octópus output). No truncation/instrument bug.

## Options (user's call)
1. **Keep the infra, don't default it** _(recommended)_. The role-scoped subagent runtime exists as
   a capability; the auto-router+scoping simply doesn't improve accuracy, so it doesn't become the
   default path. Zero further spend.
2. **Iterate the hypothesis** (speculative, diminishing returns from an 83% base): (a) widen router
   keywords so fewer cases hit `general`; (b) drop `web_fetch`/`web_search` from offensive-role
   slices so the model must pick a real domain tool; re-measure. Only worth it if selection becomes
   a priority metric.
3. **Repurpose for SAFETY, not accuracy.** Role-scoping's real value may be *containment* — a
   `recon`-scoped subagent structurally CANNOT invoke exploit/AD tools regardless of what the model
   emits. That's a policy/blast-radius guarantee (already enforced + unit-tested), independent of
   whether it raises correct-tool. If offered as an explicit safety mode (not an accuracy default),
   the infra earns its keep.

## Cost
~$0.45 pod (A6000 SECURE $0.53/hr, ~40 min: setup + v10 pull + 24×(flat+scoped) generations). Pod
deleted; billing stopped. Balance ≈ $7.8.
