# B1 — Assistant Tool Foundation (file / cmd / web + security)

**Date:** 2026-07-10
**Status:** Design — approved, pending implementation plan
**Scope:** Part **B1** of the dataset-expansion "big push" (A done). B = assistant tools +
deep-research + harness display. **B1 = the harness-code foundation** for general-assistant tools,
with a fail-closed security model. Later slices: B2 (tool SFT data), B3 (deep-research loop),
B4 (Claude-Code-style display).

---

## 1. Problem

Octópus's harness has 117 **security** tools (nmap, sqlmap, …) plus a generic `shell`, but no
standard **general-assistant** tools. To become an agentic assistant (coding + research) it needs
file, command, and web tools. These are **dangerous** — `run_cmd` is arbitrary execution,
`write_file`/`edit_file` mutate the filesystem, `web_fetch` can be pointed at internal services
(SSRF). The current policy (`LabPolicy`) only reasons about **network scope** (IP/CIDR allowlist);
it has no model for filesystem, command, or web safety.

## 2. Goals / Non-goals

**Goals (B1):**
- Add 8 assistant tools under a new catalog domain `asistan`: `read_file`, `write_file`,
  `edit_file`, `list_dir`, `grep`, `run_cmd`, `web_fetch`, `web_search`.
- A **fail-closed** security model per tool group: filesystem jail, command isolation + denylist,
  web SSRF guard.
- Fit the existing interfaces (`Executor.run`, `policy.decide`, `ToolRegistry`) with minimal,
  well-bounded additions — no rewrite of the security-tool path.
- Everything testable locally with mocks; zero network/host risk in tests.

**Non-goals (separate slices):**
- **SFT data** teaching the model to emit these tools → B2 (feeds the big retrain).
- **Deep-research loop** (multi-step research) → B3.
- **Claude-Code-style tool display** → B4.
- Reasoning / memory / context management → sub-project D.
- Extra tools (`glob`, `run_python`, `run_tests`, `git`, `browse`) → later; B1 is the core 8.

## 3. Security model (the crux)

Fail-closed by default; a tool with no matching guard is **denied**.

### 3.1 Filesystem jail (`read_file`, `write_file`, `edit_file`, `list_dir`, `grep`)
- All paths resolve under a single configured `workspace_root`.
- Reject: absolute paths that escape root, `..` traversal, and **symlink escape** (resolve the real
  path, require it to stay under the real `workspace_root`).
- `read_file`/`list_dir`/`grep` are read-only; `write_file`/`edit_file` mutate — both still jailed.
- Deny if `workspace_root` is unset (fail-closed).

### 3.2 Command isolation (`run_cmd`)
- **Never runs on the host.** Execution delegates to the existing sandboxed executor
  (`DockerExecutor` / `RealExecutor` in Kali-WSL, `shell=False` argv). In mock mode → simulated.
- Defense-in-depth **denylist** guard blocks obviously destructive patterns before dispatch
  (`rm -rf /`, `mkfs`, `dd of=/dev/…`, fork bombs, `:(){ :|:& };:`, shutdown/reboot). This is a
  guard, not a security boundary — the boundary is the sandbox.
- `run_cmd` is **high** risk → requires approval unless `allow_high` (existing policy behavior).

### 3.3 Web SSRF guard (`web_fetch`, `web_search`)
- `web_fetch`: only `http`/`https`; resolve the target host and **deny** private (RFC 1918),
  loopback (`127.0.0.0/8`, `::1`), link-local (`169.254.0.0/16` incl. cloud metadata
  `169.254.169.254`), and unspecified addresses. Enforce timeout + max response size.
- `web_search`: hits a fixed, pluggable search backend (not an arbitrary URL) → SSRF-safe by
  construction; still timeout + size capped.

## 4. Architecture (fits existing interfaces)

Two bounded additions, both implementing existing Protocols:

### 4.1 `CompositeExecutor` (routes `run` by domain)
`ToolRegistry` holds one `Executor`. Add a `CompositeExecutor(Executor)` that dispatches `run(tool,
params)` by `get_spec(tool).domain`: `asistan` → `AssistantExecutor`; any other domain → the
configured security executor (Mock/Real/Docker). Unknown domain → error string (loop never dies).

### 4.2 `AssistantExecutor(Executor)`
`run(tool, params)` dispatches by tool name:
- file tools → jailed filesystem ops under `workspace_root`
- `web_fetch` → guarded HTTP GET; `web_search` → pluggable search backend (default: a stub that
  returns a clear "no backend configured" message; real: DDG/API injected)
- `run_cmd` → delegates to an injected **sandbox executor** (default `MockExecutor`); never host.

Returns a plain string (the tool result), like all executors. Never raises (registry already wraps,
but AssistantExecutor also returns error strings for guard failures surfaced at execution time).

### 4.3 Policy dispatch (guards)
Guards are **pure functions** in `agent/guards/` (`fs.py`, `cmd.py`, `web.py`), each returning a
`Decision`. Extend the policy so `decide(spec, params)`:
- network domains → existing scope check (unchanged)
- `asistan` file tools → `fs.guard(params, workspace_root)`
- `run_cmd` → `cmd.guard(params)` then existing high-risk approval
- web tools → `web.guard(params)`

`workspace_root` and web/cmd config live on the policy (new fields, defaulting to fail-closed).
This keeps the security decision in the policy layer (audited, testable) and execution in the
executor layer.

## 5. Catalog additions (`agent/catalog_data.py`)

New domain `asistan`. Param keys are **not** network-scope keys (existing note in `catalog.py`
already excludes file/interface params from `TARGET_KEYS`):

| tool | params | risk |
|---|---|---|
| `read_file` | `yol` | low |
| `list_dir` | `yol` | low |
| `grep` | `desen`, `yol` | low |
| `write_file` | `yol`, `icerik` | medium |
| `edit_file` | `yol`, `eski`, `yeni` | medium |
| `run_cmd` | `komut` | high |
| `web_fetch` | `url` | low |
| `web_search` | `sorgu` | low |

`web_fetch`/`web_search` use `url`/`sorgu`; `url` is already a `TARGET_KEY`, but web tools are
guarded by the SSRF guard, not the network-scope check — the policy dispatch routes web tools to
`web.guard` regardless. (`run_cmd`/file tools carry no `TARGET_KEYS`, so the fail-closed
missing-target rule does not misfire on them.)

## 6. Data flow

```
model ```arac``` (asistan tool)
        │
        ▼  ToolRegistry.invoke
   policy.decide(spec, params)  ──►  guards/{fs,cmd,web}.guard  (fail-closed)
        │ allowed
        ▼
   CompositeExecutor.run  ──►  AssistantExecutor.run
        │                         ├─ file: jailed fs op
        │                         ├─ web: SSRF-guarded HTTP / search backend
        │                         └─ run_cmd: delegate to sandbox executor (never host)
        ▼
   audit.write(tool.done)  ──►  result string back to model
```

## 7. Validation / Testing

- **fs guard:** traversal (`../../etc/passwd`), absolute escape, symlink escape all denied; in-jail
  paths allowed; unset root → denied.
- **cmd guard:** destructive patterns denied; benign commands pass; `run_cmd` never calls host
  subprocess in tests (delegates to mock).
- **web guard:** `169.254.169.254`, `127.0.0.1`, `10.x`, `192.168.x`, non-http scheme denied;
  public host allowed (host-resolution mockable).
- **CompositeExecutor:** `asistan` tool → AssistantExecutor; `nmap` → security executor; unknown
  domain → error string.
- **AssistantExecutor:** each file op round-trips within a temp workspace; `run_cmd` delegates;
  `web_fetch` uses an injected fake HTTP client (no real network in tests).
- **Registry integration:** a denied guard returns `REDDEDILDI: …`; `run_cmd` returns
  `ONAY GEREKLI` without `allow_high`.

## 8. Acceptance criteria

- All 8 tools in the catalog; `python -m agent.cli` still runs (security path unbroken).
- A `write_file` with a traversal path is denied by policy (audited), never touches disk.
- A `web_fetch` at `http://169.254.169.254/…` is denied (SSRF), never issues the request.
- `run_cmd` routes through a sandbox executor in real mode and never invokes a host shell.
- Full suite green (existing 81 + B1 tests).

## 9. Related

- Interfaces: `agent/{policy,executor,registry,catalog}.py` (unchanged contracts, extended).
- Memory: [[octopus-v08-assistant-tools]], [[octopus-dataset-expansion]], [[octopus-agent-harness]].
- Reuse for schemas/examples (B2 later): OpenHands / Hermes / xLAM / ToolACE function-call datasets.
