<div align="center">

<img src="assets/octopus.png" alt="Octópus logo" width="160" />

# Octópus

### An agentic LLM for cybersecurity, networking, and server administration

##### _Red · blue · network · Linux — real tool execution behind an authorization gate._

<br/>

[![Version](https://img.shields.io/badge/version-v0.8.1-orange?style=for-the-badge)](https://github.com/erkanrzgc/octopus)
[![Weights](https://img.shields.io/badge/🤗%20weights-on%20Hugging%20Face-FFD21E?style=for-the-badge)](https://huggingface.co/erkanrzgcc/octopus-gemma-v0.8.1)
[![Runtime](https://img.shields.io/badge/runtime-agentic%20tool--use-8B5CF6?style=for-the-badge)](#-agent-harness)
[![License](https://img.shields.io/badge/license-MIT%20%2B%20Gemma-3DA639?style=for-the-badge)](#-license)

![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)
![PyTorch](https://img.shields.io/badge/PyTorch-2.4-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)
![Transformers](https://img.shields.io/badge/🤗%20Transformers-4.49-FFD21E?style=flat-square)
![PEFT](https://img.shields.io/badge/PEFT-LoRA%20bf16-00A98F?style=flat-square)
![Tests](https://img.shields.io/badge/tests-213%20passing-3DA639?style=flat-square)
![Use](https://img.shields.io/badge/use-authorized%2Flab--only-critical?style=flat-square)

</div>

---

## 📖 About

**Octópus** is an agentic language model for **cybersecurity** and **server administration**. It does not just
answer questions — it emits structured tool calls that a runtime executes against real tools, behind an
**authorization gate**. It spans **red team** (recon, exploitation), **blue team** (detection, hardening,
incident response), and **network + Linux** operations, and it is **authorization-aware** by design.

It is fine-tuned with **bf16 LoRA** on a strong open base (`Turkish-Gemma-9b`), giving it fluent, literary
**Turkish** alongside its security knowledge. It introduces itself as **"Ben Octópus"** — the dotted `ó`
lives only in the brand and the model's speech; file paths stay plain ASCII `octopus`.

---

## ✨ Features

- 🛠️ **Agentic tool use** — a **117-tool** catalog (`nmap`, `sqlmap`, `metasploit`, `bloodhound`, …) with a
  structured call format and a runtime that actually runs them.
- 🔴🔵 **Red + blue** — offense and defense in one model, from pentesting to incident response.
- 🖥️ **Server administration** — SSH, systemd, nginx, nftables, SELinux hardening, container & cloud security.
- 🛡️ **Authorization-aware** — lab / CTF / owned systems only; unauthorized requests are refused with an
  ethical alternative.
- 🇹🇷 **Fluent Turkish** — near-native prose; commands, code, and CVE IDs are preserved verbatim.

---

## 🏗️ Architecture

Two halves: the **model** (the brain — emits text and structured tool calls) and the **agent harness**
(the hands — parses those calls and runs real tools behind a policy gate).

```text
   security + Turkish SFT data
   (distilled Q&A + 117-tool use)
              │  build_sft.py  (normalize · persona · dedup · split)
              ▼
   open 9B base ──(bf16 LoRA, r=32)──▶  Octópus
              │
              ▼
   ┌──────────────────────── agent harness ─────────────────────────┐
   │  model text ──▶ parse ```arac``` block ──▶ policy gate (lab-only) │
   │       ▲                                          │                │
   │       │       feed result back  ◀── executor (mock | Kali | docker)
   └──────────────────────────────────────────────────────────────────┘
```

---

## 🧠 Model & Training

| | |
|---|---|
| **Base** | `Turkish-Gemma-9b` (Gemma-2 architecture) |
| **Method** | bf16 LoRA (`r=32`, `α=32`, 7 target modules) — **no 4-bit** (it corrupts the merged base) |
| **Engine** | plain `transformers` + `peft` + TRL |
| **Hardware** | RunPod · single 24–48 GB GPU · pinned `transformers/trl/peft` |
| **Data** | Turkish security Q&A + 117-tool agentic use + reasoning/persona seeds |

**Why bf16 LoRA, not QLoRA?** The base carries a continual-pretrain + SFT + DPO + **merge** history; common
4-bit (NF4) quantization corrupts those merged weights and produces multilingual garbage. In plain `bf16` the
same model stays flawless — so we load the base in bf16 and train a LoRA on top.
See [ADR 0003](docs/decisions/0003-pivot-to-turkish-gemma-bf16.md).

---

## 📦 Model Weights

Each release ships the **LoRA adapter** plus a ready-to-run **GGUF** quantization for local inference.

| Release | Hugging Face | Notes |
|---|---|---|
| **v0.8.1** _(current)_ | 🤗 [`octopus-gemma-v0.8.1`](https://huggingface.co/erkanrzgcc/octopus-gemma-v0.8.1) | adapter + GGUF Q4 |
| **v0.9** _(in evaluation)_ | 🤗 [`octopus-gemma-v0.9`](https://huggingface.co/erkanrzgcc/octopus-gemma-v0.9) | adapter + GGUF Q4 & Q8 |

```bash
# Pull the GGUF and run locally via Ollama
hf download erkanrzgcc/octopus-gemma-v0.8.1 octopus-v81-Q4_K_M.gguf --local-dir models
ollama create octopus-v81 -f models/Modelfile.v81
ollama run octopus-v81 "Merhaba, kendini tanıt."
```

---

## 🤖 Agent Harness

The model does not run tools — it emits a structured call, and the harness executes it:

```
model emits ```arac {"arac":"nmap","parametreler":{…}} ```  →  parse
   →  policy gate (authorized scope? risk level?)  →  executor runs the real tool
   →  result fed back as a tool message  →  model interprets and continues.
```

Executors are pluggable behind one interface, and every call passes a **fail-closed** authorization gate
(lab-only scope, per-tool risk level) written to an audit log:

- **Mock** — realistic simulated output; runs anywhere, zero risk (default).
- **Real** — real tools inside Kali (WSL2), `shell=False` argv, timeout.
- **Docker** — tools as containers on an isolated lab network.

```bash
uv run python -m agent.cli                 # mock end-to-end demo (runs anywhere)
uv run python -m agent.cli --gguf          # real Octópus via Ollama
uv run python -m agent.cli --gguf --docker # real model + real tool in an isolated lab
```

---

## 📂 Repository Layout

| Path | Responsibility |
|---|---|
| `agent/` | Harness: tool-call parser, 117-tool catalog, policy gate, executors, run loop. |
| `data/sft/` | SFT data pipeline: normalize to `messages`, inject persona, dedup, split. |
| `train/` | Canonical bf16 LoRA training. |
| `eval/` | Tool-call and technical-correctness evaluation. |
| `rag/` | Cybersecurity knowledge base for retrieval grounding. |
| `cloud/` | RunPod runbook and GGUF conversion recipe. |
| `docs/` | Architecture Decision Records and design specs. |
| `tests/` | Unit + data-format tests (213 passing). |

---

## 🗺️ Roadmap

- [x] Fluent Turkish + persona + authorization calibration
- [x] Cybersecurity knowledge + agentic tool use (117-tool catalog)
- [x] Agent harness — parser, policy gate, mock/real/docker executors
- [x] GGUF backend — real weights drive the harness locally via Ollama
- [ ] Technical-correctness + DPI pass (**v0.9**, in evaluation)
- [ ] RAG + isolated lab integration

---

## 🔒 Responsible Use

> **⚠️ Authorized, legal, lab / CTF / educational use only.**

Octópus teaches offensive technique to **strengthen defense** and support **authorized** testing. It assists
only on systems the operator is explicitly authorized to test, and **refuses** attack steps against
unauthorized real targets — declining clearly and offering a defensive alternative. It **must not** be used
for unauthorized access or harm; responsibility rests entirely with the user.

---

## 📜 License

- **Code** — MIT (scripts, pipeline, and docs in this repository).
- **Weights & adapters** — governed by the base model's [Gemma Terms of Use](https://ai.google.dev/gemma/terms);
  authorized / ethical use only.

---

## 👤 Author

**Erkan** ([@erkanrzgc](https://github.com/erkanrzgc)) — ethical security enthusiast building local-first AI.
Octópus is a transparent, end-to-end record of designing, fine-tuning, and evaluating a cybersecurity
assistant from the ground up.

> Issues and discussions are open for questions, ideas, or collaboration. 🐙

<div align="center">
<sub>Octópus — an agentic cybersecurity assistant. Authorized use only. 🐙</sub>
</div>
