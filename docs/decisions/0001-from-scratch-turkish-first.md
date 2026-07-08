# ADR 0001 — From-scratch model + Turkish-first tokenizer

- **Date:** 2026-06-19
- **Status:** ⛔ SUPERSEDED (2026-07-03) → replaced by [ADR 0002](0002-pivot-to-finetuning.md) (pivot to
  fine-tuning). This document is a **historical record**; see 0002 for the current strategy. The from-scratch
  artifacts are preserved under `archive/`.
- **Directory:** `C:\Users\erkanrzgc\Desktop\Octópus` (a new, clean start)

## Context

The previous project (`agentic-model`, GitHub `erkanrzgc/octopus-v0`) built Octópus with **Qwen2.5 + QLoRA**
and was ~80% mature: agent runtime (Track B), authorization gate, Obsidian memory, language-first curriculum,
a 7B pod run. Two things were **proven** on that path:

1. Turkish garbling was **not** caused by the tokenizer — `octopus-tr-base` tokenization matched the original
   Qwen exactly; the culprit was Phase 2's high learning rate (1e-4 → catastrophic forgetting).
2. **QLoRA cannot train a tokenizer** (it freezes the base + embeddings) — hence the "don't touch the
   tokenizer" decision there.

For product **ownership**, **learning**, and a **truly custom tokenizer**, the owner chose to drop the QLoRA
path and train a model **from scratch**. A well-evidenced objection was presented; the decision was made
deliberately.

## Decision

1. Octópus will be trained via **from-scratch pretraining** (random init; no Qwen base).
2. **Turkish-first.** The first and highest priority: a **Turkish-specific tokenizer.**
3. Tokenizer = **SentencePiece Unigram**, vocab ~32k, **diacritic-preserving** (NFKC, NO casefold → Turkish
   dotted-i is not broken), `byte_fallback`, `split_digits` (consistent ports/IPs). Goal: beat Qwen2.5's
   Turkish **fertility** — *measure first, then claim.*
4. Model = a modern **Llama-style decoder** (RoPE · RMSNorm · SwiGLU · GQA · tied embeddings).
5. **Scale ladder:** start small on a local 8 GB GPU (~100–160M); once the recipe is proven, scale up on
   RunPod (0.5–1B). "Prove it small first" — a lesson carried over from the QLoRA era.
6. The agentic harness (`agentic-model` Track B) is **model-agnostic** → it will be **ported** later, not
   rewritten.

## Rationale

- From scratch, a **custom tokenizer is the correct first step** (no QLoRA constraint anymore; the decision
  is consistent).
- Turkish is agglutinative → Unigram + a morphology-friendly vocab = lower fertility = a more efficient model
  (more information per context, faster training).
- Ownership: the model is entirely yours — base included.

## Consequences (honest)

- **Capability ceiling:** at this scale a from-scratch model will not match Qwen in raw knowledge/fluency;
  **data quality + tokenizer + SFT** carry it. Cyber depth needs lots of data or distillation.
- **Data-intensive:** pretraining needs billions of tokens of clean Turkish → corpus collection/cleaning is
  the MAIN job.
- **Time/compute:** small on a local 8 GB GPU; a serious run needs a rented RunPod GPU.

## Open knobs (easily changed — to be updated with evidence)

- Corpus sources (Wikipedia-tr to start; then OSCAR/mC4-tr, books, code, Turkish cyber text).
- `vocab_size` (16k / 32k / 48k — depends on model scale; a small vocab makes the embedding cheaper on a
  small model).
- Initial model parameter count + context length.
- Multilingual order: **TR → EN → ES → FR → DE → ZH** (EN near-term; the rest are distant goals).

## Related

- `agentic-model/OCTOPUS.md` — the previous north star (Qwen + QLoRA era).
- `agentic-model/SOUL.md` — persona/constitution (to be ported here).
