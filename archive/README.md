# Archive — Superseded Approaches

This directory preserves earlier, **abandoned** approaches for reference. None of it is
on the active code path; the live pipeline lives at the repository root (`data/sft/`,
`train/sft_bf16.py`, `agent/`).

## `model/`, `tokenizer/`, `train/pretrain.py`, `train/dataset.py`, `data/*`
The original **from-scratch pretraining** attempt: a custom Turkish SentencePiece tokenizer
(`tokenizer/octopus-tr.*`, ~35% lower fertility than Qwen), a nanoGPT-style Llama model, and the
pretraining data pipeline. Abandoned on cost grounds — see
[`docs/decisions/0002-pivot-to-finetuning.md`](../docs/decisions/0002-pivot-to-finetuning.md).

## `train/sft_smoke.py`, `train/_ddp_smoke.py`
The **Qwen3-8B QLoRA + Unsloth** fine-tuning attempt (v0.1 / v0.2). Superseded by
Turkish-Gemma-9b + bf16 LoRA — see
[`docs/decisions/0003-pivot-to-turkish-gemma-bf16.md`](../docs/decisions/0003-pivot-to-turkish-gemma-bf16.md).

Kept for provenance and possible future reference. Full history is in git.
