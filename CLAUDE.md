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
- **Done:** v0.6 (fluent Turkish + persona, loss 0.22) · v0.7 (cyber knowledge + 117-tool use, loss 0.048,
  98.7%). Adapter local at `checkpoints_sft/octopus-gemma-v7-adapter/` + HF `erkanrzgcc/octopus-gemma-v0.7`.
- **Agent harness (`agent/`):** parses the model's ```arac``` tool-call block → policy gate → executor
  (mock / real Kali WSL / docker-lab) → feeds result back. 39 tests. Design: `docs/superpowers/specs/`.
- **Next:** GGUF Q4 (local RTX 5060 8GB) · v0.7.1 (strengthen the structured ```arac``` block). Single source
  of truth: `docs/v0.7-loop-queue.md`. ⚠️ TRAP: `--max-train 0` (full data) → NaN; `--max-train 2000` → clean.
- **Skills:** `octopus-finetune` (main recipe), `octopus-data` (SFT data), `octopus-eval` (quality + safety).
  Which skill/subagent when → `docs/skills-and-subagents.md`.
- **Archive:** the from-scratch attempt (`archive/model`, `archive/tokenizer`, `archive/train`, …) and the
  Qwen3-8B QLoRA experiment (`archive/train/sft_smoke.py`) are kept under `archive/` (see `archive/README.md`).

## Working rules
- Packaging: **uv** (`uv sync`, `uv run python ...`); venv `.venv` (on an ASCII path). Tests: `uv run pytest`.
- GPU: local RTX 5060 8 GB (small runs); large runs on **RunPod** — the assistant cannot reach the pod
  (it issues commands, the user runs them). **Checkpoint with the user before any step that spends money.**
- Don't dive blindly into large work → enter **plan mode** first (user preference).

## Reuse (reverse-engineered — pattern, not copy)
- **`Desktop\cyberm4fiaModel`** — Octópus's working ancestor: Qwen2.5-3B + Unsloth QLoRA + Fenrir v2.1
  → loss 0.77 / ppl 2.39. The 00-06 pipeline + Chroma RAG (`rag/knowledge/`) + safety eval + 15-tool agent +
  a Turkish guardrail system prompt (`cyberm4fia/config.py`). Data shape + persona + eval pattern come from here.
- **`Desktop\agentic-model`** — Qwen QLoRA + agent runtime + Turkish teacher distillation
  (`scripts/distill_teacher_tr.py`). The agent harness pattern was ported from here (model-agnostic).
