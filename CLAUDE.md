# Octópus — Claude Code project notes

> This file is **auto-loaded every session** when Claude Code opens in this folder, so context is not lost.
> More: vision in `OCTOPUS.md`, decisions in `docs/decisions/`.

## What this project is
**Octópus** — a Turkish-first LLM for cybersecurity (red + blue + network) and server administration.
A strong Turkish-native base (**`ytu-ce-cosmos/Turkish-Gemma-9b-v0.1`**) is **fine-tuned with bf16 LoRA**
(NOT 4-bit NF4 — that corrupts the merged base). The model introduces itself as **“Ben Octópus”** (dotted ó).
Strategy decisions: `docs/decisions/0002-pivot-to-finetuning.md` (pivot to fine-tuning) +
`docs/decisions/0003-pivot-to-turkish-gemma-bf16.md` (base Qwen3 → Turkish-Gemma, method QLoRA → bf16 LoRA).

## Brand & paths (IMPORTANT)
The dotted `ó` appears **only in the brand and the model's speech** (“Ben Octópus”, README, docs, GitHub).
**File paths/folders are plain ASCII `octopus`** — Windows-native libraries (SentencePiece, llama.cpp, torch
extensions) break on non-ASCII paths. Working directory: `C:\Users\erkanrzgc\Desktop\Octopus`.

## Language policy
The **product** is Turkish-first (the model speaks literary Turkish; SFT data is Turkish). But **GitHub-facing
docs are written in English** (README, ADRs, this file) — GitHub is a global platform and the repo should read
professionally. Turkish-first is an internal product priority, not a documentation-language rule.

## Current phase (2026-07) — fine-tuning done (v0.7) + agent harness
- **Strategy:** from-scratch pretraining dropped (cost) → fine-tuning. Base **Turkish-Gemma-9b-v0.1**,
  method **bf16 LoRA** (r=32, α=32, 7 modules, seq 1024, lr 2e-4, RunPod RTX 4090). Engine = plain
  `transformers` + `peft` + TRL (NOT Unsloth — 4-bit NF4 breaks Turkish-Gemma; see `train/sft_bf16.py:1-9`).
- **Done:** v0.6 (fluent Turkish + persona) · v0.7 (cyber knowledge + 117-tool use, loss 0.048) ·
  **v0.8 (2026-07-21) — the "big move": trained on the FULL expanded dataset (3485 ex: A/B/C + D1 reasoning
  + D2 memory + D3 skill/methodology). Measurement gate PASSED HARD: tool-call in_catalog 50→83%,
  correct-tool 46→75%, emitted/valid 100%. Adapter+GGUF Q4 on HF `erkanrzgcc/octopus-gemma-v0.8` + local
  `models/octopus-v8-Q4_K_M.gguf` + `ollama octopus-v8`. Persona/Türkçe/refusal verified.**
  **v0.8.1 (2026-07-22) — CURRENT DEFAULT: persona v0.3 retrain. Identity = "Ben siber güvenlik yapay
  zeka modeli Octópus" (dropped "asistan" + "sunucu yönetimi uzmanı" self-title), low-friction (assume good
  faith, don't interrogate for permission/scope), kept the malicious-real-victim refusal + added 4
  reframing-refusal negatives (education/fiction pretext + real-person target = REFUSE). Trained A40 48GB,
  full data (train=3501, `--max-train 0`), 1570 steps, final loss 0.2913, NaN-free. Adapter+GGUF Q4 on HF
  `erkanrzgcc/octopus-gemma-v0.8.1` + local `models/octopus-v81-Q4_K_M.gguf` + `ollama octopus-v81`.
  Persona VERIFIED locally (6/6: identity fixed, low-friction help, v0.8 reframing safety gap CLOSED,
  neighbor-WiFi refused, authorized-help direct). Tool-call eval: emitted/valid 100%, in_catalog 83→96%
  (hallucination 17%→4%), correct-tool 75→71% (1-case noise). Net promote.**
- **Agent harness (`agent/`):** parses the model's ```arac``` tool-call block → policy gate → executor
  (mock / real Kali WSL / docker-lab) → feeds result back. 39 tests. Design: `docs/superpowers/specs/`.
- **Next:** full quality/safety eval of v0.8 (`octopus-eval`: perplexity, safety balance, brittleness — the
  tool-call eval only measured tool reliability). Readiness/how: `docs/v0.8-retrain-readiness.md`.
  ⚠️ NaN TRAP was v0.7-SPECIFIC: v0.8 trained on FULL data (`--max-train 0`) with NO NaN (40-step smoke +
  1570-step run both clean) — no cap needed. GGUF lesson: write f16 to container disk not the network volume.
- **Skills:** `octopus-finetune` (main recipe), `octopus-data` (SFT data), `octopus-eval` (quality + safety).
  Which skill/subagent when → `docs/skills-and-subagents.md`.
- **Archive:** the from-scratch attempt (`archive/model`, `archive/tokenizer`, `archive/train`, …) and the
  Qwen3-8B QLoRA experiment (`archive/train/sft_smoke.py`) are kept under `archive/` (see `archive/README.md`).

## Working rules
- Packaging: **uv** (`uv sync`, `uv run python ...`); venv `.venv` (on an ASCII path). Tests: `uv run pytest`.
- GPU: local RTX 5060 8 GB (small runs); large runs on **RunPod**. The assistant CAN now drive the pod
  end-to-end via `runpodctl` + SSH (proven in the v0.8 run: create → train → download → delete), with the
  user's access. **Still checkpoint with the user before any step that spends money.** Pod tips (v0.8 lessons):
  cached template `runpod-torch-v240`; slow local scp → pull adapter on the pod from HF; `setsid` for detach;
  `--terminate-after` is unreliable, delete the pod yourself as soon as the artifact is downloaded.
- Don't dive blindly into large work → enter **plan mode** first (user preference).

## Reuse (reverse-engineered — pattern, not copy)
- **`Desktop\cyberm4fiaModel`** — Octópus's working ancestor: Qwen2.5-3B + Unsloth QLoRA + Fenrir v2.1
  → loss 0.77 / ppl 2.39. The 00-06 pipeline + Chroma RAG (`rag/knowledge/`) + safety eval + 15-tool agent +
  a Turkish guardrail system prompt (`cyberm4fia/config.py`). Data shape + persona + eval pattern come from here.
- **`Desktop\agentic-model`** — Qwen QLoRA + agent runtime + Turkish teacher distillation
  (`scripts/distill_teacher_tr.py`). The agent harness pattern was ported from here (model-agnostic).
