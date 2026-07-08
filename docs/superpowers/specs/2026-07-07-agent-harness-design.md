# Octópus Agent Harness — Design (Spec)

- **Date:** 2026-07-07
- **Status:** Approved (the user approved it section by section during brainstorming)
- **Goal:** an **agentic runtime** that parses the ```arac``` blocks produced by the v0.7 model, runs the
  requested tools, and feeds the results back to the model. Model = the brain (produces text); harness = the
  hands (runs the tools).

## Context

Octópus v0.7 (Turkish-Gemma-9b bf16 LoRA) has learned tool use over a 117-tool catalog. The model produces a
tool call **as text**, in this format:

```arac
{"arac":"nmap","parametreler":{"hedef":"10.10.10.5","secenekler":"-sV"}}
```

But the repo has NO runtime that parses this block and **actually runs it**. This spec defines that runtime.
Reference (port/adaptation, not a copy): `Desktop\agentic-model\src\octopus\agent` (Hermes tool-loop pattern,
`ToolRegistry`, `LabPolicy`, `AuditLog`).

## Scope (two phases, incremental)

- **Phase 1 (the main deliverable of this spec) — A WORKING SKELETON that runs on Windows today:** parser +
  loop + catalog + registry + **MockExecutor** (realistic simulated output) + mock/real model backend + CLI +
  tests. NO real binary execution → zero security risk. It verifies end-to-end whether the model reliably
  produces the ```arac``` block.
- **Phase 2 (later):** a real model backend (GGUF Q4, local RTX 5060 8GB) + **RealExecutor** (WSL2/Kali
  subprocess) + policy hardening. Because the skeleton is pluggable, only the backends change.

## Architecture

Small, single-responsibility modules (a new `agent/` package):

```
agent/
  messages.py     Message(role, content) — a plain data type
  catalog.py      117-tool CATALOG (SINGLE SOURCE OF TRUTH, derived from training data)
  toolcall.py     ```arac``` block parsing + tool-result feedback
  registry.py     catalog → tool-spec + invoke(call) → dispatch to the executor
  executor.py     Executor protocol + MockExecutor (Phase 1)
  policy.py       LabPolicy — scope allow-list, risk gate, dry-run
  audit.py        AuditLog — every tool call to jsonl
  loop.py         run_tool_loop — the model↔tool loop
  backends/
    mock_model.py scripted/mock `generate` (test + demo)
    (Phase 2) gguf_model.py
  cli.py          `python -m agent.cli` — chat entry point
tests/agent/      parser, catalog-integrity, loop, policy, executor tests
```

### Component contracts

- **catalog.py** — 117 entries, each: `{name, domain, risk(low/med/high), params(key list), command_template}`.
  Names + parameter keys are **derived from the training data** (guaranteed model match). Evidence: 117/117
  tools appear in `arac` blocks, 38 unique parameter keys, mostly `secenekler` (raw flags).
- **toolcall.py** — `parse_arac_calls(text) -> list[ToolCall]` (regex over ```arac``` blocks, skips broken
  JSON, never crashes). Feedback: `data/sft/normalize.py::flatten_tool_messages` is **reused verbatim**
  (tool result → an "ARAÇ ÇIKTISI:\n…" `user` turn; the Gemma-2 chat template does not support the tool role).
- **registry.py** — produces tool-specs from the catalog (for the system prompt) and dispatches `invoke(call)`
  to policy + executor. Unknown tool → an error (returned to the model; the loop does not die).
- **executor.py** — an `Executor` protocol: `run(tool, params) -> str`. `MockExecutor` produces domain-based
  realistic output (nmap→port list, sqlmap→injection finding). Phase 2: `RealExecutor` (subprocess+policy).
- **policy.py** — `decide(tool, params) -> Decision(allowed, requires_approval, reason)`. Default lab-only;
  `low`-risk recon passes within scope, `high` requires approval/dry-run. Out-of-scope target → refuse.
- **loop.py** — `run_tool_loop(messages, generate, registry, max_steps=10)`: generate → any `arac`? if not,
  final answer; if yes, invoke each call, append the result as a `tool` message, repeat. `max_steps` guard.
  Backend-agnostic (`generate: list[Message] -> str`).

## Data flow (one turn)

```
USER "scan 10.10.10.5" → generate() → ASSISTANT (reasoning + ```arac nmap```)
  → parse_arac_calls → [nmap call]
  → policy.decide (scope+risk) → allow
  → executor.run("nmap", {...}) → output (Phase 1 mock / Phase 2 real)
  → flatten to an "ARAÇ ÇIKTISI:\n…" TOOL message → generate() → ASSISTANT (interpretation / next tool)
  → no arac → final answer, the loop ends
```

## Error handling

- Broken/incomplete `arac` block → the parser skips it (the loop continues).
- Unknown tool / executor error → an `ERROR: …` string is returned to the model (never crash on an exception).
- `max_steps` → infinite-loop guard; a final plain answer is taken.
- Out-of-scope/risk → policy refusal, reason returned to the model.

## Test strategy (TDD, 80%+)

- **parser:** valid/broken/multiple `arac` blocks, refusal examples.
- **catalog-integrity:** are all 117 tools present, do names match the training data (a canonical test).
- **loop:** a full turn with a scripted `generate` + `MockExecutor` (single tool, multi-step chain, final answer).
- **policy:** in/out-of-scope target, low/high risk, dry-run decisions.
- **executor:** MockExecutor's domain-based output shape.

## Decisions (approved in brainstorming)

1. Goal: skeleton first (mock), then real execution (WSL2/Kali) plugged on top — **1 as the base, 2 on top**.
2. Registry = a **data-driven single catalog** (117 tools, derived from training data). NOT 117 hand-written handlers.
3. The feedback format must be **identical** to training (`flatten_tool_messages` reuse) — the most critical
   correctness point.
4. Backend abstraction: model (mock→GGUF) and executor (mock→real) are independently pluggable.

## Related

- `data/sft/tools/build_tools.py` (MASTER_TOOLS = the canonical 117 list) · `data/sft/normalize.py` (flatten reuse)
- `docs/v0.7-tools-catalog.md` · `Desktop\agentic-model\src\octopus\agent\*` (reference pattern)
