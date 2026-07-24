# 🐙 Octópus — North Star

> The project's **vision, story, and goal** — so a new session can understand what this project is for.
> Current strategy: fine-tuning ([ADR 0002](docs/decisions/0002-pivot-to-finetuning.md)), base
> **Turkish-Gemma-9b bf16 LoRA** ([ADR 0003](docs/decisions/0003-pivot-to-turkish-gemma-bf16.md)).
> Rules: `CLAUDE.md`.

## In one sentence
Octópus is a **Turkish-speaking**, autonomous AI — expert in cybersecurity (red + blue + network) and
**server/system administration** — meant to run on your own server. Not a bot that memorizes theory: an
expert that knows, does, and uses tools — **only within the operator's authorization.** In conversation the
model says **“Ben Octópus.”**

## Why fine-tuning (not from-scratch)
We first chose from-scratch pretraining ([ADR 0001](docs/decisions/0001-from-scratch-turkish-first.md)); a
custom Turkish tokenizer + a 100M model stood up locally. But the **cost of a real scaling run** (RunPod
$60-150+, billions of tokens) was decisive. **Decision: fine-tune a strong base** (~$3-15, a few hours,
100-1000× cheaper with a much higher capability ceiling).

**Rule:** language must live in the base, knowledge is added on top. Turkish fluency cannot be injected into
an English base with a LoRA; adding cybersecurity knowledge to a Turkish-**native** base with a LoRA is
proven. → **Turkish-first goal = a Turkish-expert base** (Qwen3-8B was tried first, then dropped for
Turkish-Gemma due to Turkish-fluency rough edges).

## Base model
- **Primary (current):** `ytu-ce-cosmos/Turkish-Gemma-9b-v0.1` — Turkish continual-pretrain + SFT + DPO,
  Gemma-2 architecture. Method: **bf16 LoRA** (NOT 4-bit NF4 — it corrupts the merged weights into
  multilingual garbage).
- **Why not Qwen3-8B:** v0.1/v0.2 were trained with Qwen3-8B QLoRA, but Turkish fluency/persona were rough
  (`<think>` leakage, "Octópüs" spelling). Rationale + evidence: [ADR 0003](docs/decisions/0003-pivot-to-turkish-gemma-bf16.md).
- **Optional teacher:** `fdtn-ai/Foundation-Sec-8B-Reasoning` (distill English cyber depth into Turkish SFT).

## Four pillars (target capability)
- 🔴 **Red team** (authorized): recon/OSINT, scanning, web/AD attacks, MITRE ATT&CK with correct IDs.
- 🔵 **Blue team:** logs/SIEM, threat hunting, incident response, hardening, Sigma/YARA, D3FEND.
- 🌐 **Network:** TCP/IP, DNS/TLS, packet analysis, firewall/VPN.
- 🖥️ **Server** (main goal): Linux, nginx/TLS, Docker, ufw/iptables, fail2ban, journald — actionable Turkish.

## Red line
All offensive capability is limited to **authorized lab / CTF / training / the operator's own systems**.
Owner = authorization. Someone else's / unauthorized target → refuse clearly, redirect to a lab. The guardrail
system prompt is baked into the SFT data.

## Brand & paths
In conversation the model says **“Ben Octópus”** (dotted ó). Code/paths/repo are plain ASCII `octopus`
(Windows-native libraries break on non-ASCII paths). Folder: `Desktop\Octopus`.

## Roadmap (fine-tuning)
1. **Choose base** ✅ Turkish-Gemma-9b-v0.1, bf16 LoRA (ADR 0003; Qwen3-8B tried → dropped).
2. **SFT data** ✅ Turkish distilled knowledge (1,029 Q&A) + 117-tool use (125 examples) + persona seed →
   normalize to `messages`, dedup, split (skill `octopus-data`, `data/sft/build_sft.py`).
3. **bf16 LoRA training** ✅ plain `transformers` + `peft` + TRL (not Unsloth), r=32, seq 1024, lr 2e-4,
   RunPod RTX 4090 (skill `octopus-finetune`, `train/sft_bf16.py`).
4. **Eval + safety** ✅ persona/Turkish/knowledge/refusal gen-test passed (skill `octopus-eval`);
   brittleness ongoing.
5. **Agent harness** ✅ tool-call parser + policy gate + mock/real/docker executors (`agent/`, 39 tests).
6. **Merge + deploy** ⏳ LoRA merge → GGUF Q4 → local RTX 5060 8GB (Ollama/llama.cpp); cloud later.
7. **(later)** strengthen the structured ```arac``` block (v0.7.1) + RAG grounding (MITRE/CVE/OWASP).

## Archive (from-scratch attempt)
The custom tokenizer (`archive/tokenizer/octopus-tr.*`, ~35% lower fertility), from-scratch data pipeline
(`archive/data/`), and 100M model (`archive/model/`, `archive/train/`) are **preserved** but off the active
path. No knowledge lost; kept for reference/experiments. Details:
[ADR 0001](docs/decisions/0001-from-scratch-turkish-first.md).

## Status (2026-07)
The fine-tuning path is complete: **v0.6** (fluent Turkish + persona, loss 0.22) ✅ · **v0.7** (cyber
knowledge + 117-tool use, loss 0.048, 98.7%) ✅. Adapter on HF (`erkanrzgcc/octopus-gemma-v0.7`) + local.
The **agent harness** runs the model's tool calls (mock/real/docker). Next: GGUF Q4 (local) · v0.7.1
(structured ```arac``` block). Single source of truth: `docs/v0.7-loop-queue.md`.
