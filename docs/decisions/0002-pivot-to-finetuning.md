# ADR 0002 — Pivot from from-scratch to fine-tuning + base model decision

- **Date:** 2026-07-03
- **Status:** **Partially superseded.** The "pivot to fine-tuning" decision is STILL VALID. But the **base
  model and quantization method changed** → [ADR 0003](0003-pivot-to-turkish-gemma-bf16.md): base `Qwen3-8B`
  → `Turkish-Gemma-9b-v0.1`, method `QLoRA (Unsloth 4-bit)` → `bf16 LoRA (plain transformers)`. (Qwen3-8B
  QLoRA was used only in v0.1/v0.2; v0.6+ is Turkish-Gemma bf16.) The "Qwen3-8B / QLoRA / Unsloth" statements
  below are therefore HISTORICAL — see ADR 0003 for the current path.
- **Supersedes:** [ADR 0001](0001-from-scratch-turkish-first.md) (from-scratch pretraining)
- **Directory:** `C:\Users\erkanrzgc\Desktop\Octopus` (ASCII)

## Context

Under ADR 0001, Octópus was trained **from scratch**: a custom Turkish tokenizer (`octopus-tr`, fertility
1.735 vs Qwen 2.674, −35%) + a nanoGPT-style Llama + pretraining. Phases 1-4 stood up end-to-end locally
(100M model, E2E smoke green). But the **cost of a scaling run** became concrete:

- From-scratch = training **all** parameters over billions of tokens. Chinchilla ~20 tok/param → ~15B tokens
  for 0.5B; FLOPs = 6 × params × tokens. A real run on RunPod is **~$60-150+** and takes hours/days.
- Fine-tuning (QLoRA) = training ~0.1-1% of the base (LoRA adapters) over ~10-50M tokens → **a few hours,
  ~$3-15.** 100-1000× cheaper compute.

Once the cost reality was clear, the owner chose to **pivot to fine-tuning.** Emphasis: **"we must choose the
model we fine-tune very carefully."**

## Decision

1. **Strategy = fine-tuning (QLoRA + Unsloth).** From-scratch pretraining dropped (artifacts archived).
2. **Primary base = `Qwen3-8B`** (`unsloth/Qwen3-8B` bnb-4bit for QLoRA).
   > NOTE: there is no "-Instruct-2507" for 8B — the Qwen3-2507 update shipped only for 4B/30B-A3B/235B.
   > 8B = the original `Qwen3-8B` (hybrid thinking). The smoke test used `Qwen3-4B-Instruct-2507` (which exists).
   - Turkish-native (100+ languages), Apache 2.0, the most mature fine-tune ecosystem, 256K context.
   - Local-first sweet spot: Q4 ~5GB (flies on RTX 5060 8GB), QLoRA ~12GB VRAM (RunPod ~$3-8).
3. **Upgrade path = `Qwen3-14B`** (once the pipeline settles; Q4 ~8.5GB local/offload, QLoRA ~$8-15).
4. **Optional teacher = `fdtn-ai/Foundation-Sec-8B-Reasoning`** — to distill English cyber-reasoning depth
   into the Turkish SFT data (reuse `agentic-model` `distill_teacher_tr.py`).

## Rationale (evidence-based)

- **Rule: language must live in the base, knowledge is added on top.** Injecting Turkish fluency into an
  English-only base (Foundation-Sec) with a LoRA is very hard; adding cyber knowledge to Qwen3 with QLoRA is
  **proven:**
  - `DexopT/Qwen3-4B-Cybersecurity` — Qwen3-4B-Instruct-2507, 1.28M cyber examples (red+blue+network+AD+
    malware+web), Unsloth SFT r16, on a single Colab T4; has a GGUF.
  - `CyberSecQwen-4B` — Qwen3-4B, beats Foundation-Sec-Instruct-8B on CTI-MCQ with half the parameters.
- **Evidence from the working ancestor:** sibling `cyberm4fiaModel` — Qwen2.5-3B + Unsloth QLoRA + Fenrir
  v2.1, r=32 → train loss 0.77 / ppl 2.39. The same family/pattern carries to Qwen3.

## Consequences (honest)

- **Tokenizer cost:** fine-tuning inherits the Qwen tokenizer → `octopus-tr`'s −35% fertility win is **not
  used** on this path (Qwen uses ~35% more tokens in Turkish = slightly more expensive but fully usable). The
  from-scratch artifacts (`tokenizer/octopus-tr.*`, `checkpoints_web/`) are **archived, not deleted.**
- **Gain:** much cheaper/faster, a much higher capability ceiling (8B base >> 100M from-scratch), and both
  Turkish + cyber are reachable via proven paths.
- **Cisco 2026 warning:** cyber fine-tuning can create "representation drift"/brittleness → obfuscation-variant
  red-teaming in eval is mandatory (see the `octopus-eval` skill).

## Open knobs (to be updated with evidence)

- Base size: 8B (start) → 14B (upgrade). MoE (Qwen3-30B-A3B) can be evaluated later.
- LoRA r / seq / lr / epoch — start from the cyberm4fia baseline (r=32, seq 1024, lr 2e-4), tune by measurement.
- SFT data mix: Fenrir + secdata + AlicanKiraz CVE + Turkish persona/server; distillation optional.
- Deploy: GGUF Q4 → local (Ollama/llama.cpp); cloud later.

## Related

- [ADR 0001](0001-from-scratch-turkish-first.md) — superseded (from-scratch era).
- `Desktop\cyberm4fiaModel` — the working reference pipeline (Qwen2.5 QLoRA + Fenrir + RAG + agent).
- `Desktop\agentic-model` — Qwen QLoRA + agent runtime + `distill_teacher_tr.py`.
