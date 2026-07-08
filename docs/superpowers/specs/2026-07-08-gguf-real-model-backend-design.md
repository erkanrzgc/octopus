# Octópus GGUF Real-Model Backend — Design (Spec)

- **Date:** 2026-07-08
- **Status:** Approved (the user approved it section by section during brainstorming)
- **Goal:** connect the **real Octópus v0.7 model** to the agent harness as a pluggable backend, so
  the actual fine-tuned model — not a scripted mock — drives the tool loop. The model becomes the brain
  (produces the ```arac``` block); the existing harness remains the hands.

## Context

The agent harness (`agent/`) parses the model's ```arac``` blocks, gates them through policy, runs the
tool, and feeds the result back. Until now the "brain" has been `ScriptedModel` (a mock that returns
canned replies). Phase 1 proved the plumbing; the Docker Model B run (2026-07-08) proved real tool
execution against a live vulnerable target. The remaining gap: a **real model backend**.

v0.7 (Turkish-Gemma-9b bf16 LoRA, loss 0.048) exists as a LoRA adapter, both locally
(`checkpoints_sft/octopus-gemma-v7-adapter/`) and on HF (`erkanrzgcc/octopus-gemma-v0.7`). It has not
yet been merged, converted to GGUF, or served. This spec covers merging + conversion + a runtime backend
that matches the existing `__call__(messages) -> str` interface.

## Scope (minimal proof — YAGNI)

Deliver: `agent/backends/gguf_model.py` (`GgufModel`) + a `--gguf` CLI flag mirroring `--real`/`--docker`.
When run, the real model drives the loop with `MockExecutor` as the hands — this proves the model
**reliably emits the ```arac``` block and interprets tool results**, without depending on real tools.
Tests are Ollama-independent (HTTP mocked). A full REPL and a combined `--gguf --docker` real+real run are
explicitly **out of scope** for this deliverable.

## Two independent parts

### Part A — Offline conversion pipeline (RunPod, one-off, ~$3)

`cloud/pod_gguf_v7.sh` — adapt the proven `cloud/pod_gguf_clean.sh` recipe from v6 to v7. Ordering is
critical (llama.cpp's `requirements.txt` mutates transformers/torch and breaks the peft merge, so **merge
first under a pinned env, then install llama.cpp deps**):

1. Pinned env (`transformers==4.49.0 peft==0.14.0 accelerate==1.4.0 torch==2.4.1`) → load base
   `ytu-ce-cosmos/Turkish-Gemma-9b-v0.1` in bf16 on CPU → `PeftModel.from_pretrained(base, v7-adapter)`
   → `merge_and_unload()` → save merged HF dir.
2. Build llama.cpp (`llama-quantize` target) after the merge is done.
3. `convert_hf_to_gguf.py <merged> --outtype f16` → `octopus-v7-f16.gguf`.
4. `llama-quantize … Q4_K_M` → **`octopus-v7-Q4_K_M.gguf`** (~5.5 GB), delete the f16 intermediate.
5. **NEW vs v6 recipe:** also save the merged tokenizer to a standalone `octopus-v7-tokenizer/` directory
   (tokenizer_config.json with the chat template + tokenizer.model + special_tokens_map.json). The runtime
   backend needs this to reproduce the training prompt; the local adapter dir lacks `tokenizer.model`.

**Operational boundary:** the assistant cannot reach the pod. The assistant delivers the script
ready-to-run; the user launches the pod and runs it in their own terminal, then downloads the two outputs
(the Q4 GGUF + the tokenizer dir) into the local `models/` directory. This is a money checkpoint (~$3),
pre-authorized by the user.

### Part B — Runtime backend (local, durable)

`agent/backends/gguf_model.py` — serves the local Q4 GGUF through **Ollama** (already installed, GPU/CUDA
automatic on the RTX 5060 8 GB; Q4_K_M ≈ 5.5 GB fits). The backend is a thin client; Ollama manages the
model process.

**Part B does not depend on Part A.** It is written and tested against a mocked Ollama HTTP endpoint, so
the entire codebase can be completed with zero spend; the pod step and the real end-to-end smoke run come
last.

## Component contract — `gguf_model.py`

```python
@dataclass
class GgufModel:
    model: str = "octopus-v7"                       # Ollama model name
    host: str = "http://localhost:11434"
    tokenizer_dir: str = "models/octopus-v7-tokenizer"
    system_prompt: str = OCTOPUS_SYSTEM_PROMPT       # from data.sft.persona (single source)
    temperature: float = 0.6
    top_p: float = 0.95
    top_k: int = 20
    repeat_penalty: float = 1.15
    num_predict: int = 512
    timeout: int = 180

    def __call__(self, messages: list[Message]) -> str: ...
```

`__call__` flow:

1. `dicts = render_for_model(messages)` — reuse the harness helper (tool → user "ARAÇ ÇIKTISI:" flatten),
   identical to training's `flatten_tool_messages`.
2. `dicts = ensure_system(dicts, self.system_prompt)` — prepend the Octópus persona/guardrail as the
   system message (training prepends it to every example via `apply_octopus_system`).
3. `prompt = _apply_template(dicts)` — the saved tokenizer's
   `apply_chat_template(dicts, tokenize=False, add_generation_prompt=True, enable_thinking=False)`; strip a
   leading duplicate `<bos>` (ADR 0003 double-BOS trap). `transformers.AutoTokenizer` is **lazy-imported**
   inside this path only (no torch model weights loaded; tests and other backends never import it).
4. POST Ollama `/api/generate` with `{"model", "prompt", "raw": true, "stream": false, "options": {
   temperature, top_p, top_k, repeat_penalty, num_predict, "stop": ["<end_of_turn>"]}}`.
5. Return the `response` field (the loop parses any ```arac``` block from it).

### Prompt fidelity (the critical correctness point)

The prompt the model sees at inference must be **byte-identical** to training. The single source of truth
is the saved tokenizer's own chat template (Turkish-Gemma carries a custom template that accepts a `system`
role and an `enable_thinking` flag). Therefore the backend **must not** rely on Ollama's built-in `gemma2`
template — it renders the prompt itself via `apply_chat_template` and sends it to Ollama in **raw mode**
(`raw: true`), reproducing training's `_to_text` / smoke-test rendering exactly, including the
`OCTOPUS_SYSTEM_PROMPT` injection and the sampling parameters used in the training smoke test.

### Error handling (harness philosophy: never crash the loop)

- Ollama unreachable (connection refused) → clear string: hint `ollama serve` / `ollama create`.
- Model not found (Ollama 404) → "octopus-v7 model missing, create it from the Modelfile".
- Timeout → `HATA: model zaman aşımı`.
- `tokenizer_dir` missing → a clear error at first use.

All error paths return a string (the loop appends it and continues), never raise.

## Local Ollama setup (one-off, after Part A outputs land)

`models/Modelfile` → `FROM ./octopus-v7-Q4_K_M.gguf` (plus `PARAMETER stop "<end_of_turn>"` as a safety
net). It carries **no** TEMPLATE/SYSTEM directive — the backend applies those itself in raw mode. Then
`ollama create octopus-v7 -f models/Modelfile`.

## CLI integration (`agent/cli.py`)

Add `--gguf`, mirroring `--real`/`--docker`:

```python
def run_gguf_demo(scope, model="octopus-v7") -> str:
    """REAL BRAIN: GgufModel drives the loop, MockExecutor is the hands."""
    from agent.backends.gguf_model import GgufModel
    from agent.executor import MockExecutor
    registry = ToolRegistry(LabPolicy(scope=scope), MockExecutor(), AuditLog.default())
    msgs = [Message("user", "10.10.10.5 yetkili lab hedefini tara")]
    result = run_tool_loop(msgs, GgufModel(model=model), registry)
    ...
```

Note: `_scan_demo` cannot be reused here — it hard-codes `ScriptedModel`. The real model produces its own
`arac` block, so `run_gguf_demo` is a separate thin function. `main()` routes `--gguf` → `run_gguf_demo`.

## Test strategy (`tests/agent/test_gguf_model.py`, Ollama-independent)

- `_apply_template` produces the correct prompt (real tokenizer if loadable, else a monkeypatched fake
  exercising the flatten + system-prepend + BOS-strip logic).
- The Ollama HTTP call is **mocked** (stub `urllib`/`requests`): assert the request body is correct
  (`raw: true`, the options block, `stop: ["<end_of_turn>"]`) and the `response` field is parsed out.
- Error paths: connection refused → clear string; timeout → clear string; 404 → clear string.
- Ordering: `render_for_model` then `ensure_system` (system first, tool flattened).
- The real end-to-end run (needs Ollama + the GGUF) is **manual/optional**, not in CI — same posture as
  `--real` / `--docker`.

## Acceptance criteria

1. All existing tests + the new gguf tests pass **without Ollama**.
2. `--gguf` wires the loop with the mock executor and, when Ollama is absent, returns a clear error
   instead of crashing.
3. (After the user runs the pod conversion, downloads the outputs, and `ollama create`s the model)
   `python -m agent.cli --gguf` → the **real Octópus** produces Turkish reasoning + an `arac` block → the
   mock nmap output is fed back → the model interprets it.
4. The prompt is training-identical (single BOS, system injected, `stop` on `<end_of_turn>`).

## Build order (handed to writing-plans)

1. `cloud/pod_gguf_v7.sh` (conversion recipe + tokenizer output) — user runs it on the pod 💰.
2. `gguf_model.py` + tests (TDD, Ollama-mocked) — **can be written without waiting for the pod**.
3. `cli.py` `--gguf` + `run_gguf_demo`.
4. Local `ollama create` + real end-to-end smoke run (once Part A outputs arrive).

## Decisions (approved in brainstorming)

1. Conversion on **RunPod** (~$3, fast, proven recipe), Q4 GGUF served **locally via Ollama**.
2. Prompt fidelity via **in-process `apply_chat_template`** (saved tokenizer) + Ollama **raw mode**, not
   Ollama's built-in template.
3. Scope = minimal proof: `gguf_model.py` + `--gguf`, real brain + mock hands, Ollama-independent tests.
4. Part B is decoupled from Part A → the whole backend is completable with zero spend before the pod step.

## Related

- `docs/superpowers/specs/2026-07-07-agent-harness-design.md` (the harness this plugs into)
- `docs/decisions/0003-pivot-to-turkish-gemma-bf16.md` (bf16 base, double-BOS trap, chat template notes)
- `cloud/pod_gguf_clean.sh` (v6 recipe to adapt) · `train/sft_bf16.py::_to_text` / `_generate_smoke`
  (the exact training/inference rendering to reproduce) · `data/sft/normalize.py` (flatten + ensure_system)
  · `data/sft/persona.py` (`OCTOPUS_SYSTEM_PROMPT`)
