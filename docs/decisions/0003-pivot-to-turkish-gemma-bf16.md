# ADR 0003 — Base Qwen3-8B → Turkish-Gemma-9b, method QLoRA → bf16 LoRA

- **Date:** 2026-07-05
- **Status:** Accepted and **implemented** (v0.6 + v0.7 were trained this way)
- **Supersedes:** the base+method choice of [ADR 0002](0002-pivot-to-finetuning.md) — **superseded**
  (ADR 0002's "pivot to fine-tuning" decision is STILL VALID; only the base model and quantization method changed)
- **Directory:** `C:\Users\erkanrzgc\Desktop\Octopus` (ASCII)

## Context

ADR 0002 chose the base **Qwen3-8B** + **QLoRA (Unsloth, 4-bit NF4)**. v0.1 and v0.2 were actually trained
this way (RunPod, loss ~0.80). But two persistent problems emerged:

1. **Insufficient Turkish fluency + persona rough edges.** Qwen3-8B is multilingual but not Turkish-native →
   generation showed spelling/word rough edges like "Octópüs"/"Sevimsel", identity repeat-loops, and `<think>`
   token leakage. The "Turkish like Namık Kemal" goal (the #1 language priority) did not hold.
2. **The "language in the base" rule** (ADR 0002) logically required a Turkish-**native** base.

The search for a Turkish-expert base → **`ytu-ce-cosmos/Turkish-Gemma-9b-v0.1`** (Gemma-2 architecture,
Turkish continual-pretrain + SFT + DPO + merge). But training it with QLoRA produced **multilingual garbage.**

### Root cause (proven, 2026-07-05)

On the pod, with plain `transformers` (`scratchpad/bf16_test.py`): Turkish-Gemma-9b produces **flawless Turkish
in `bf16`** (fluent persona + correct SQLi explanation). The garbage came **entirely** from Unsloth's **4-bit
NF4** quantization. **Why:** Turkish-Gemma carries a continual-pt + SFT + DPO + **merge** history; NF4 corrupts
those merged weights. (Qwen quantized cleanly — which is why v0.1/v0.2 worked; the bug is base-specific, not
Unsloth-general.)

## Decision

1. **Base = `ytu-ce-cosmos/Turkish-Gemma-9b-v0.1`** (Turkish-native, Gemma-2). Qwen3-8B dropped.
2. **Method = bf16 LoRA** (NO quantization). Plain `transformers` (`torch_dtype=bfloat16`, `load_in_4bit=False`)
   + `peft` `LoraConfig` + TRL `SFTTrainer`. **Unsloth is not used** (its 4-bit corrupts this base).
3. **Hardware = RunPod RTX 4090 24GB.** Turkish-Gemma bf16 ≈18GB + gradient checkpointing + seq 1024 +
   batch1/accum8 ≈ 21-23GB → fits (at the edge). A local RTX 5060 8GB is not enough for training (GGUF
   inference only).
4. **Hyperparameters** (inherited from cyberm4fia, unchanged): r=32, α=32, 7 target modules
   (q/k/v/o/gate/up/down), seq 1024, lr 2e-4, ~900 steps/~3 epochs. Version pins (torch 2.4 compatibility):
   transformers 4.49 / trl 0.15.2 / peft 0.14 / accelerate 1.4.

## Results

- **v0.6** (Turkish-only, 918 distilled + seed): final loss **0.22**, token accuracy 97%. Fluent/literary
  Turkish, NO Qwen rough edges. HF `erkanrzgcc/octopus-gemma-v0.6`.
- **v0.7** (+cyber knowledge 1,029 Q&A + 117-tool use): final loss **0.048**, 98.7%. HF `erkanrzgcc/octopus-gemma-v0.7`.
- **Script:** `train/sft_bf16.py` (canonical). The old Unsloth/Qwen path is kept in `archive/train/sft_smoke.py`.

## Known traps (future runs)

- **`--max-train 0` (full ~2279 examples) → deterministic NaN** (grad nan, step 5). `--max-train 2000` (a
  subset) → clean. Data-independent (even the v0.6 recipe blew up at 0). Suspected: a dataset-size/collator
  numerical interaction. Workaround = max-train 2000. Root-cause investigation deferred to v0.7.1. Details:
  `docs/v0.7-loop-queue.md`.
- **The Gemma-2 chat template does not support the `tool` role** → `data/sft/normalize.py::flatten_tool_messages`
  converts `tool` → `user` (with an "ARAÇ ÇIKTISI:" prefix), preserving user/model alternation.
- **Double BOS:** the Gemma template emits a literal `<bos>`, and TRL adds another → `_to_text` strips the
  leading BOS.

## Related

- [ADR 0002](0002-pivot-to-finetuning.md) — pivot to fine-tuning (valid); its base/method choice was updated by this ADR.
- [ADR 0001](0001-from-scratch-turkish-first.md) — from-scratch (superseded by 0002).
- `train/sft_bf16.py` · `docs/v0.7-loop-queue.md` · `README.md`.
