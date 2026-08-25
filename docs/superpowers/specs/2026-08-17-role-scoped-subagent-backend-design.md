# Design — In-harness role-scoped subagent backend (deterministic router)

- **Date:** 2026-08-17
- **Branch:** feat/b2-assistant-sft-data
- **Status:** design approved (brainstorming), pre-implementation
- **Scope:** runtime-only change inside `agent/`. **No retrain, no external orchestrator (NOT DSH/Cordis).**

## Purpose
The catalog is a flat **130 tools / 14 domains**, always fully visible to the model. The
2026-08-17 paired eval measured tool-selection at only **62–79 % correct-tool**. Narrowing the
tool menu per task-role is a plausible, retrain-free way to improve selection and focus.

This builds Octópus's **own** subagent backend: a deterministic code-router sends each task to a
**role-scoped subagent** that runs the existing Octópus loop over only its slice of the catalog.
It is not connected to any external agent host — the user explicitly rejected the DSH/Cordis
integration DeepSeek proposed.

## Non-goals
- No connection to DeepSeek/Cordis or any external orchestrator.
- No model retrain; no changes to training data.
- No new tools; no changes to policy gate, executor, or audit behavior.
- Not a general multi-agent planner — routing is deterministic code, not a model decision.

## Architecture
```
gorev (task string)
  → route(gorev) -> rol            # agent/router.py — deterministic keyword/intent → role
  → SubAgent(rol)                  # agent/subagent.py
       → ToolRegistry(allowed=rol_tools)   # agent/registry.py — role-scoped slice + asistan
       → run_tool_loop(...)         # agent/loop.py — UNCHANGED
       → policy gate + executor + audit    # UNCHANGED
  → cevap (ToolLoopResult)
```

### Roles = catalog domains (single source of truth)
`ToolSpec.domain` already partitions the catalog. **Role ≡ domain** — no new taxonomy to maintain.
**13 routable roles** (all domains except `asistan`) + `general` (all tools = today's behavior, the
router fallback). `asistan` is a domain in the table below but is **not** a standalone routable
role — its tools ride along in every role (see the cross-cutting note):

| role (domain) | n | role (domain) | n |
|---|---|---|---|
| web | 19 | wireless | 8 |
| exploit-ad | 16 | cloud | 8 |
| osint | 15 | recon-scan | 7 |
| blue-server | 14 | traffic-mitm | 7 |
| forensic-re | 12 | password | 5 |
| asistan | 10 | mobile-social | 5 |
| privesc | 3 | secrets | 1 |

**`asistan` tools (read_file/list_dir/grep/write_file/edit_file/run_cmd/web_fetch/web_search/
hafiza_*) are cross-cutting** — included in EVERY scoped role, never a standalone subagent. So a
scoped role R = `{t : t.domain == R}` ∪ `{t : t.domain == "asistan"}`.

### Components
1. **`agent/roles.py`** — role definitions built from `CATALOG` (derive, don't duplicate):
   `role_tools(role) -> frozenset[str]` = domain slice + asistan; `ROLES` = sorted domain list;
   `GENERAL = "general"`. Pure, no I/O.
2. **`agent/router.py`** — `route(gorev: str) -> str`: lowercased keyword/intent → role table
   (Turkish + tool-name hints), first-match wins, no/ambiguous match → `general`. Pure function.
3. **`agent/registry.py`** (extend `ToolRegistry`) — add optional `allowed: frozenset[str] | None`.
   - `tool_names()` returns the scoped slice when `allowed` is set, else full `CATALOG`.
   - `invoke()` gains a pre-check: if `allowed` is set and `call.name not in allowed`, return
     `"BU ROL İÇİN DEĞİL ({rol}); şunlardan seç: <scoped names>"` (audited as `tool.scope.deny`).
     The loop appends this like any tool result (a `tool` message), so the model sees it on the
     next generation and can re-emit an in-role call — self-correction via result feedback, exactly
     like a policy-deny today. No change to `loop.py`.
   - `default()` stays unscoped (backward compatible). New `scoped(role, ...)` classmethod.
4. **`agent/subagent.py`** — `SubAgent(role)`: builds the scoped `ToolRegistry`, exposes
   `run(gorev, generate, *, skills=None, max_steps=10) -> ToolLoopResult` that seeds messages and
   calls the UNCHANGED `run_tool_loop`. A thin `run_task(gorev, generate, **kw)` convenience
   routes (`route`) then runs the chosen subagent — the "backend" entry point.

### Scoping strategy — the crux (B default, A behind a flag)
The model was trained on the **full 130-tool system prompt**. v1.1 just taught us that
off-distribution narrowing can backfire. So:

- **B — allowlist-only (DEFAULT).** Keep the trained full system prompt (on-distribution). The
  scoped `ToolRegistry` **enforces** the role: out-of-role calls are rejected with a helpful
  in-role list; the loop self-corrects. Zero prompt drift.
- **A — prompt-augmented (flag `prompt_scope=True`).** NOTE: the trained system prompt (886 chars)
  lists NO tool names — it only defines the ```arac``` format; the model knows the 130 tools from
  *training*, not the prompt. So "A" is not narrowing an existing menu — it means **appending** the
  role's tool list as a menu to a prompt that never had one. Higher selection potential, but clearly
  off-distribution (bigger change than B). Experiment only.
- Decision is **empirical**: measure both against the flat baseline with the existing toolcall eval
  (below). Ship whichever wins; default stays B until A demonstrably beats it.

## Data flow & error handling
- Router never raises: unknown/empty task → `general`. Every task is routable.
- Scoped `invoke()` never raises (matches current contract): out-of-role → text message, not an
  exception. Policy deny / approval / executor errors behave exactly as today.
- `general` role = current behavior exactly (no regression path): full catalog, unscoped registry.

## Testing & measurement (no retrain, no money)
Unit (pytest, offline, mock model):
- `router`: representative Turkish tasks → expected role; ambiguous → `general`.
- `roles`: every catalog tool belongs to exactly one role-domain; asistan ⊆ every scoped role;
  union of role slices == full catalog.
- `scoped registry`: in-role call runs; out-of-role call returns the scope-deny message + audits
  `tool.scope.deny`; unscoped default unchanged.
- `loop self-correction`: model emits an out-of-role call → gets the deny text → re-emits an
  in-role call → executes (scripted mock).

Measurement (the point of the feature):
- Extend the existing toolcall eval to run in **scoped mode** (route each case → scoped subagent).
- Compare **flat (baseline 62–79 %)** vs **B (allowlist)** vs **A (prompt-scope)** on the same
  cases/model (v10, temp per eval default). Promote scoping only if it beats flat; pick B or A by
  the numbers. Reuse the pod-paired methodology if a GPU run is needed (money-checkpoint first).

## File plan
- new: `agent/roles.py`, `agent/router.py`, `agent/subagent.py`
- edit: `agent/registry.py` (add `allowed` + `scoped()` + scope-deny in `invoke`)
- new tests: `tests/agent/test_roles.py`, `test_router.py`, `test_subagent_scope.py`
- eval: extend `eval/toolcall_eval.py` / `eval/run_toolcall_eval.py` with a `--scoped` mode
- `agent/loop.py`, `agent/policy.py`, `agent/executor.py`, `agent/catalog*.py` — **unchanged**

## Open decisions deferred to implementation (not blocking)
- Exact router keyword table (seed from domain names + common Turkish verbs + salient tool names).
- Whether to coarsen 14 roles into ~6–8 groups later if fine-grained routing proves brittle
  (start fine = role≡domain; group only if measured need).
