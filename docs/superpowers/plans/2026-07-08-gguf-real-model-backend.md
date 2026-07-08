# GGUF Real-Model Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Connect the real Octópus v0.7 model to the agent harness as an Ollama-backed `GgufModel` so the fine-tuned model — not a mock — drives the tool loop.

**Architecture:** Two decoupled parts. Part B (the runtime backend + CLI flag + tests) is written first, TDD, with Ollama mocked — zero spend, no pod dependency. Part A (a RunPod conversion script the user runs) comes last. The backend reproduces the exact training prompt via the saved tokenizer's `apply_chat_template` and calls Ollama in raw mode over stdlib `urllib`.

**Tech Stack:** Python 3 (stdlib `urllib` for HTTP — no new deps), pytest (Ollama mocked via monkeypatch), Ollama (local serving), llama.cpp + transformers/peft (pod-side conversion only), bash (pod script).

## Global Constraints

- File paths are plain ASCII `octopus`; the brand `ó` appears only in speech/docs, never in paths. (CLAUDE.md)
- The inference prompt must be training-identical: single leading `<bos>`, `OCTOPUS_SYSTEM_PROMPT` injected as the system message, `add_generation_prompt=True`, stop on `<end_of_turn>`. (spec §Prompt fidelity)
- The backend never raises out of `__call__` — every error path returns a string the loop appends and continues. (spec §Error handling)
- Tests must pass without Ollama and without the pod outputs (HTTP + tokenizer mocked). (spec §Test strategy)
- No new runtime dependency: use stdlib `urllib.request`. Lazy-import `transformers` only inside the `--gguf` render path. (spec §Component contract)
- Python: PEP 8, type hints on signatures. Turkish code comments (mirrors the rest of `agent/`). (repo convention)
- `OCTOPUS_SYSTEM_PROMPT` has a single source: `data/sft/persona.py` — import it, never copy the text. (persona.py DRY note)

---

### Task 1: Prompt rendering (`render_prompt` + `load_tokenizer`)

**Files:**
- Create: `agent/backends/gguf_model.py` (this task adds the two rendering functions only)
- Test: `tests/agent/test_gguf_model.py`

**Interfaces:**
- Consumes: nothing from other tasks.
- Produces: `render_prompt(dicts: list[dict], tokenizer, *, bos_token: str = "<bos>") -> str` and `load_tokenizer(tokenizer_dir: str)` — Task 2's `GgufModel._render` calls these.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_gguf_model.py
from agent.backends.gguf_model import render_prompt


class _FakeTok:
    """apply_chat_template'i taklit eder; gordugu argumanlari kaydeder."""
    def __init__(self) -> None:
        self.seen: dict | None = None

    def apply_chat_template(self, msgs, tokenize=False, add_generation_prompt=False, **kw) -> str:
        self.seen = {"msgs": msgs, "tokenize": tokenize, "agp": add_generation_prompt, "kw": kw}
        return "<bos><start_of_turn>user\nU<end_of_turn>\n<start_of_turn>model\n"


def test_render_prompt_strips_bos_and_passes_flags():
    tok = _FakeTok()
    out = render_prompt(
        [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}], tok)
    assert not out.startswith("<bos>")                 # cift-BOS tuzagi: bastaki BOS siyrilir
    assert tok.seen["agp"] is True                     # add_generation_prompt=True
    assert tok.seen["tokenize"] is False
    assert tok.seen["msgs"][0]["role"] == "system"


def test_render_prompt_falls_back_when_enable_thinking_unsupported():
    class _StrictTok:
        def apply_chat_template(self, msgs, tokenize=False, add_generation_prompt=False):
            return "no-bos-here"                        # enable_thinking kwarg'i KABUL ETMEZ
    out = render_prompt([{"role": "user", "content": "U"}], _StrictTok())
    assert out == "no-bos-here"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_gguf_model.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'agent.backends.gguf_model'` (or ImportError for `render_prompt`).

- [ ] **Step 3: Write minimal implementation**

```python
# agent/backends/gguf_model.py
"""GgufModel: gercek Octópus v0.7'yi Ollama uzerinden harness'e baglar (mock yerine).

Prompt EGITIMLE BIREBIR: kaydedilmis tokenizer'in kendi chat template'i (system rolu +
enable_thinking'i destekler) uygulanir, bastaki cift <bos> siyrilir (ADR 0003 tuzagi),
Ollama'ya RAW modda gonderilir. Ollama'nin kendi gemma2 template'ine GUVENILMEZ."""
from __future__ import annotations


def load_tokenizer(tokenizer_dir: str):
    """transformers'i LAZY import et (yalniz --gguf yolu; torch weights yuklenmez)."""
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(tokenizer_dir)


def render_prompt(dicts: list[dict], tokenizer, *, bos_token: str = "<bos>") -> str:
    """dict listesi -> egitim-birebir prompt metni (tokenize=False, add_generation_prompt=True)."""
    try:
        t = tokenizer.apply_chat_template(
            dicts, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    except TypeError:  # bazi template'ler enable_thinking kwarg'ini tanimaz
        t = tokenizer.apply_chat_template(dicts, tokenize=False, add_generation_prompt=True)
    # Gemma template metne literal <bos> basar; Ollama raw'da tek BOS yeter -> bastakini siyir.
    if bos_token and t.startswith(bos_token):
        t = t[len(bos_token):]
    return t
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agent/test_gguf_model.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add agent/backends/gguf_model.py tests/agent/test_gguf_model.py
git commit -m "feat(agent): GgufModel prompt rendering (training-identical apply_chat_template + BOS strip)"
```

---

### Task 2: `GgufModel` backend (`__call__` + Ollama raw HTTP + error paths)

**Files:**
- Modify: `agent/backends/gguf_model.py` (add imports + the `GgufModel` dataclass)
- Test: `tests/agent/test_gguf_model.py` (append)

**Interfaces:**
- Consumes: `render_prompt`, `load_tokenizer` (Task 1); `render_for_model` (`agent/toolcall.py`); `ensure_system` (`data/sft/normalize.py`); `OCTOPUS_SYSTEM_PROMPT` (`data/sft/persona.py`); `Message` (`agent/messages.py`).
- Produces: `GgufModel(model="octopus-v7", host="http://localhost:11434", tokenizer_dir="models/octopus-v7-tokenizer", renderer=None, ...)` with `__call__(messages: list[Message]) -> str` — Task 3's `run_gguf_demo` passes it to `run_tool_loop`. `renderer: Callable[[list[dict]], str] | None` lets tests inject a prompt builder and skip transformers.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_gguf_model.py  (append)
import json
import urllib.error
import urllib.request

from agent.backends.gguf_model import GgufModel
from agent.messages import Message


class _Resp:
    def __init__(self, payload: dict) -> None:
        self._data = json.dumps(payload).encode("utf-8")
    def read(self) -> bytes:
        return self._data
    def __enter__(self):
        return self
    def __exit__(self, *a):
        return False


def _urlopen_ok(capture: dict, payload: dict):
    def _fake(req, timeout=None):
        capture["url"] = req.full_url
        capture["body"] = json.loads(req.data.decode("utf-8"))
        return _Resp(payload)
    return _fake


def _urlopen_raises(exc):
    def _fake(req, timeout=None):
        raise exc
    return _fake


def test_call_builds_raw_request_and_returns_response(monkeypatch):
    cap: dict = {}
    monkeypatch.setattr(urllib.request, "urlopen",
                        _urlopen_ok(cap, {"response": "Tararim ```arac```"}))
    m = GgufModel(renderer=lambda d: "PROMPT")
    out = m([Message("user", "10.10.10.5 tara")])
    assert out == "Tararim ```arac```"
    assert cap["url"].endswith("/api/generate")
    assert cap["body"]["raw"] is True
    assert cap["body"]["prompt"] == "PROMPT"
    assert cap["body"]["options"]["stop"] == ["<end_of_turn>"]
    assert cap["body"]["options"]["temperature"] == 0.6


def test_call_injects_system_and_flattens_tool(monkeypatch):
    seen: dict = {}
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_ok({}, {"response": "ok"}))
    m = GgufModel(renderer=lambda d: seen.setdefault("dicts", d) or "P")
    m([Message("user", "U"), Message("tool", "nmap ciktisi")])
    roles = [d["role"] for d in seen["dicts"]]
    assert roles[0] == "system"                          # persona basta
    assert "ARAÇ ÇIKTISI:" in seen["dicts"][-1]["content"]  # tool -> user flatten


def test_connection_refused_returns_error_string(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen",
                        _urlopen_raises(urllib.error.URLError("refused")))
    out = GgufModel(renderer=lambda d: "P")([Message("user", "U")])
    assert out.startswith("HATA") and "Ollama" in out


def test_timeout_returns_error_string(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_raises(TimeoutError()))
    out = GgufModel(renderer=lambda d: "P")([Message("user", "U")])
    assert out.startswith("HATA") and "zaman" in out.lower()


def test_model_not_found_returns_error_string(monkeypatch):
    err = urllib.error.HTTPError("u", 404, "not found", {}, None)
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_raises(err))
    out = GgufModel(renderer=lambda d: "P")([Message("user", "U")])
    assert "ollama create" in out
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_gguf_model.py -v`
Expected: FAIL with `ImportError: cannot import name 'GgufModel'`.

- [ ] **Step 3: Write minimal implementation**

Add to the top of `agent/backends/gguf_model.py` (after the module docstring, replacing the bare `from __future__` line):

```python
from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field

from agent.messages import Message
from agent.toolcall import render_for_model
from data.sft.normalize import ensure_system
from data.sft.persona import OCTOPUS_SYSTEM_PROMPT

_EOT = "<end_of_turn>"
```

Append the dataclass at the end of the file:

```python
@dataclass
class GgufModel:
    """Ollama uzerinden gercek v0.7. __call__ mock ScriptedModel ile ayni arayuz."""
    model: str = "octopus-v7"
    host: str = "http://localhost:11434"
    tokenizer_dir: str = "models/octopus-v7-tokenizer"
    system_prompt: str = OCTOPUS_SYSTEM_PROMPT
    temperature: float = 0.6
    top_p: float = 0.95
    top_k: int = 20
    repeat_penalty: float = 1.15
    num_predict: int = 512
    timeout: int = 180
    renderer: Callable[[list[dict]], str] | None = None  # test enjeksiyonu (transformers'i atlar)
    _tokenizer: object = field(default=None, init=False, repr=False)

    def __call__(self, messages: list[Message]) -> str:
        dicts = ensure_system(render_for_model(messages), self.system_prompt)
        try:
            prompt = self._render(dicts)
        except Exception as e:  # noqa: BLE001 -- dongu asla cokmemeli
            return f"HATA: prompt/tokenizer hazirlanamadi ({type(e).__name__}: {e})"
        return self._generate(prompt)

    def _render(self, dicts: list[dict]) -> str:
        if self.renderer is not None:
            return self.renderer(dicts)
        if self._tokenizer is None:
            self._tokenizer = load_tokenizer(self.tokenizer_dir)
        return render_prompt(dicts, self._tokenizer)

    def _generate(self, prompt: str) -> str:
        body = json.dumps({
            "model": self.model, "prompt": prompt, "raw": True, "stream": False,
            "options": {
                "temperature": self.temperature, "top_p": self.top_p, "top_k": self.top_k,
                "repeat_penalty": self.repeat_penalty, "num_predict": self.num_predict,
                "stop": [_EOT],
            },
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/generate", data=body,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:  # URLError alt-sinifi -> ONCE yakala
            if e.code == 404:
                return (f"HATA: '{self.model}' Ollama'da yok "
                        f"(once: ollama create {self.model} -f models/Modelfile)")
            return f"HATA: Ollama HTTP {e.code}"
        except TimeoutError:
            return f"HATA: Ollama zaman asimi ({self.timeout}s)"
        except (urllib.error.URLError, OSError) as e:
            return (f"HATA: Ollama'ya baglanilamadi ({e}); "
                    f"'ollama serve' calisiyor mu?")
        return (data.get("response") or "").strip()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/agent/test_gguf_model.py -v`
Expected: PASS (7 passed total — 2 from Task 1 + 5 here).

- [ ] **Step 5: Commit**

```bash
git add agent/backends/gguf_model.py tests/agent/test_gguf_model.py
git commit -m "feat(agent): GgufModel Ollama raw backend (__call__ + error paths, urllib stdlib)"
```

---

### Task 3: CLI `--gguf` flag + `run_gguf_demo`

**Files:**
- Modify: `agent/cli.py` (add `run_gguf_demo` + `--gguf`/`--model` args + routing)
- Test: `tests/agent/test_cli.py` (append a routing test)

**Interfaces:**
- Consumes: `GgufModel` (Task 2); existing `ToolRegistry`, `LabPolicy`, `AuditLog`, `MockExecutor`, `run_tool_loop`, `Message`.
- Produces: `run_gguf_demo(scope: list[str] | None = None, model: str = "octopus-v7") -> str`; `main()` routes `--gguf` to it.

- [ ] **Step 1: Write the failing test**

```python
# tests/agent/test_cli.py  (append)
import sys

import agent.cli as cli


def test_main_routes_gguf(monkeypatch, capsys):
    called: dict = {}

    def _fake(scope, model="octopus-v7"):
        called["args"] = (scope, model)
        return "GGUF_DEMO_OUT"

    monkeypatch.setattr(cli, "run_gguf_demo", _fake)
    monkeypatch.setattr(sys, "argv", ["prog", "--gguf"])
    cli.main()
    out = capsys.readouterr().out
    assert "GGUF_DEMO_OUT" in out
    assert called["args"][1] == "octopus-v7"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/agent/test_cli.py::test_main_routes_gguf -v`
Expected: FAIL with `AttributeError: <module 'agent.cli'> has no attribute 'run_gguf_demo'`.

- [ ] **Step 3: Write minimal implementation**

Add `run_gguf_demo` after `run_docker_demo` in `agent/cli.py`:

```python
def run_gguf_demo(scope: list[str] | None = None, model: str = "octopus-v7") -> str:
    """GERCEK BEYIN: GgufModel (Ollama'da v0.7) dongüyü sürer, MockExecutor eller.
    Ollama yoksa GgufModel net HATA stringi döner -> döngü çökmez, onu nihai cevap alir."""
    from agent.backends.gguf_model import GgufModel
    from agent.executor import MockExecutor
    from agent.policy import LabPolicy
    from agent.audit import AuditLog
    scope = scope or ["10.10.10.0/24"]
    registry = ToolRegistry(LabPolicy(scope=scope), MockExecutor(), AuditLog.default())
    msgs = [Message("user", "10.10.10.5 yetkili lab hedefini tara")]
    result = run_tool_loop(msgs, GgufModel(model=model), registry)
    lines = [f"[{m.role}] {m.content}" for m in msgs]
    lines.append(f"(adim={result.steps}, cagri={len(result.calls)}) (gguf demo bitti)")
    return "\n".join(lines)
```

In `main()`, add the args (next to `--real`/`--docker`):

```python
    ap.add_argument("--gguf", action="store_true", help="GgufModel: Ollama'da gercek v0.7")
    ap.add_argument("--model", default=None, help="Ollama model adi (varsayilan octopus-v7)")
```

And route it **first** in the dispatch chain:

```python
    if args.gguf:
        print(run_gguf_demo(args.scope, args.model or "octopus-v7"))
    elif args.docker:
        print(run_docker_demo(args.target or "octopus-target", args.scope, port=args.port or 80))
    elif args.real:
        print(run_real_demo(args.target or "127.0.0.1", args.scope, port=args.port or 8000))
    else:
        print(run_demo(args.scope or ["10.10.10.0/24"]))
```

- [ ] **Step 4: Run the full suite to verify pass + no regressions**

Run: `uv run pytest -q`
Expected: PASS (all previous tests + the 8 new gguf/cli tests green).

- [ ] **Step 5: Commit**

```bash
git add agent/cli.py tests/agent/test_cli.py
git commit -m "feat(agent): cli --gguf flag routes real GgufModel through the loop (mock hands)"
```

---

### Task 4: Part A — RunPod conversion script + local Ollama setup files

**Files:**
- Create: `cloud/pod_gguf_v7.sh` (adapt `cloud/pod_gguf_clean.sh` v6 → v7 + emit tokenizer dir)
- Create: `models/Modelfile`
- Create: `models/README.md` (local setup runbook)
- Modify: `.gitignore` (ignore the big GGUF + tokenizer dir, keep Modelfile/README tracked)

**Interfaces:**
- Consumes: nothing in-repo (runs on the pod). Produces two artifacts the user downloads to `models/`: `octopus-v7-Q4_K_M.gguf` and `octopus-v7-tokenizer/`. `GgufModel` defaults (`model="octopus-v7"`, `tokenizer_dir="models/octopus-v7-tokenizer"`) match this.

- [ ] **Step 1: Write the conversion script**

```bash
# cloud/pod_gguf_v7.sh
#!/bin/bash
# Octopus v0.7 GGUF — v6 tarifinin (pod_gguf_clean.sh) v7 uyarlamasi.
# KOK SEBEP (onceki basarisizlik): llama.cpp requirements.txt transformers/torch'u degistirip
# peft merge'i kiriyor. COZUM: ONCE merge (pinli env), SONRA llama.cpp deps. Sira kritik.
# Onkosul: /workspace/v7-adapter (LoRA adapter) pod'da hazir olmali (scp/hf ile gonder).
# YENI (v6'dan farki): merge tokenizer'i ayri /workspace/octopus-v7-tokenizer dizinine de kaydeder
# (yerel backend apply_chat_template icin lazim; yerel adapter dizininde tokenizer.model YOK).
set -eo pipefail
BASE="ytu-ce-cosmos/Turkish-Gemma-9b-v0.1"; ADP="/workspace/v7-adapter"
MERGED="/workspace/octopus-v7-merged"; OUT="/workspace/octopus-v7-gguf"
TOKOUT="/workspace/octopus-v7-tokenizer"; mkdir -p "$OUT" "$TOKOUT"

echo "===== [1/5] Merge env (pinli) + MERGE (llama.cpp deps'ten ONCE!) ====="
pip install -q "transformers==4.49.0" "peft==0.14.0" "accelerate==1.4.0" "torch==2.4.1" 2>&1 | tail -1
python - <<PY
import torch, shutil
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from huggingface_hub import hf_hub_download
base = AutoModelForCausalLM.from_pretrained("$BASE", torch_dtype=torch.bfloat16, device_map="cpu")
m = PeftModel.from_pretrained(base, "$ADP").merge_and_unload()
try: m.generation_config.do_sample = True   # Turkish-Gemma gen_config gecersiz -> tf4.49 save patlar
except Exception: pass
m.save_pretrained("$MERGED", safe_serialization=True)
tok = AutoTokenizer.from_pretrained("$ADP")
tok.save_pretrained("$MERGED")
tok.save_pretrained("$TOKOUT")                       # YENI: backend icin ayri tokenizer dizini
tm = hf_hub_download("$BASE", "tokenizer.model")     # Gemma convert + apply_chat_template ister
shutil.copy(tm, "$MERGED/tokenizer.model")
shutil.copy(tm, "$TOKOUT/tokenizer.model")
print("MERGE_OK")
PY

echo "===== [2/5] cmake + llama.cpp (merge BITTI, artik env bozulabilir) ====="
pip install -q cmake 2>&1 | tail -1
cd /workspace
[ -d llama.cpp ] || git clone --depth 1 https://github.com/ggml-org/llama.cpp
cd llama.cpp
pip install -q -r requirements.txt 2>&1 | tail -1

echo "===== [3/5] llama-quantize build ====="
cmake -B build -DGGML_CUDA=OFF -DLLAMA_CURL=OFF 2>&1 | tail -1
cmake --build build --config Release -j --target llama-quantize 2>&1 | tail -2

echo "===== [4/5] HF -> GGUF f16 ====="
python convert_hf_to_gguf.py "$MERGED" --outfile "$OUT/octopus-v7-f16.gguf" --outtype f16

echo "===== [5/5] Quantize -> Q4_K_M ====="
[ -f "$OUT/octopus-v7-f16.gguf" ] && rm -rf "$MERGED" ~/.cache/huggingface/hub/models--ytu-ce-cosmos*
./build/bin/llama-quantize "$OUT/octopus-v7-f16.gguf" "$OUT/octopus-v7-Q4_K_M.gguf" Q4_K_M
rm -f "$OUT/octopus-v7-f16.gguf"
ls -la "$OUT" "$TOKOUT"; sha256sum "$OUT/octopus-v7-Q4_K_M.gguf"
echo "GGUF_DONE — indir: $OUT/octopus-v7-Q4_K_M.gguf + $TOKOUT/  -> yerelde models/"
```

- [ ] **Step 2: Syntax-check the script (we cannot run it — no pod/base model)**

Run: `bash -n cloud/pod_gguf_v7.sh`
Expected: no output, exit 0 (valid bash syntax).

- [ ] **Step 3: Create the Ollama Modelfile and local runbook**

```dockerfile
# models/Modelfile
# Backend prompt'u RAW modda kendisi uygular (template/system BURADA YOK) -> yalniz import + emniyet stop.
FROM ./octopus-v7-Q4_K_M.gguf
PARAMETER stop "<end_of_turn>"
```

```markdown
# models/ — local Octópus v0.7 GGUF (git-ignored artifacts)

The Q4 GGUF and the tokenizer dir are produced by `cloud/pod_gguf_v7.sh` on RunPod and are **not**
committed (too large). Only `Modelfile` and this README are tracked.

## One-off local setup (after downloading the pod outputs into this folder)

    models/
      octopus-v7-Q4_K_M.gguf      # ~5.5 GB, from the pod
      octopus-v7-tokenizer/       # tokenizer_config.json + tokenizer.model + special_tokens_map.json
      Modelfile                   # tracked

    ollama create octopus-v7 -f models/Modelfile
    python -m agent.cli --gguf     # real Octópus drives the loop (mock nmap hands)

The backend applies the training chat template itself and calls Ollama in raw mode, so the Modelfile
carries no TEMPLATE/SYSTEM directive.
```

- [ ] **Step 4: Ignore the large artifacts, keep the tracked files**

Add to `.gitignore`:

```gitignore
# Local GGUF model artifacts (produced on the pod, downloaded locally)
models/*.gguf
models/octopus-v7-tokenizer/
```

Then verify only the intended files are staged:

Run: `git add -A && git status --short`
Expected: shows `cloud/pod_gguf_v7.sh`, `models/Modelfile`, `models/README.md`, `.gitignore` — and **no** `.gguf` or `octopus-v7-tokenizer/`.

- [ ] **Step 5: Commit**

```bash
git add cloud/pod_gguf_v7.sh models/Modelfile models/README.md .gitignore
git commit -m "feat(cloud): v7 GGUF conversion script + local Ollama Modelfile/runbook"
```

---

## Self-Review

**1. Spec coverage:**
- Part A pipeline (merge → GGUF → Q4 → tokenizer dir) → Task 4. ✅
- Part B `GgufModel` contract (fields, `__call__` flow) → Tasks 1-2. ✅
- Prompt fidelity (apply_chat_template, system inject, BOS strip, raw mode, sampling params) → Tasks 1-2 (`render_prompt`, `_generate` options). ✅
- Error handling (unreachable/404/timeout/missing tokenizer, never raise) → Task 2 tests + impl. ✅
- Local Ollama setup (Modelfile, `ollama create`) → Task 4. ✅
- CLI `--gguf` mirroring `--real`/`--docker` → Task 3. ✅
- Ollama-independent tests → Tasks 1-3 (injected `renderer`, monkeypatched `urlopen`). ✅
- Acceptance #1/#2/#4 covered by automated tests; #3 (real end-to-end) is the manual runbook in Task 4 (needs pod outputs + Ollama), matching the spec's "manual/optional" posture. ✅

**2. Placeholder scan:** No TBD/TODO/"handle edge cases"/"similar to Task N" — every code step is complete. ✅

**3. Type consistency:** `render_prompt(dicts, tokenizer, *, bos_token)` and `load_tokenizer(tokenizer_dir)` defined in Task 1 are called identically in Task 2's `_render`. `GgufModel(model=..., renderer=...)` in Task 2 matches the constructor call in Task 3's `run_gguf_demo` and the test injections. `run_gguf_demo(scope, model)` signature matches the `main()` call and the Task 3 routing test. ✅

---

## Notes on ordering

Tasks 1-3 (Part B) are fully implementable and testable now with **zero spend and no pod** — Ollama and the tokenizer are mocked/injected. Task 4 (Part A) writes the pod script + local setup files but only syntax-checks them; the actual pod run (~$3, money checkpoint) and the real end-to-end smoke (Acceptance #3) are performed by the user afterward, since the assistant cannot reach the pod.
