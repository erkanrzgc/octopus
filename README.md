<div align="center">

# 🐙 Octópus

### A Turkish-first large language model for cybersecurity and server administration
##### _Red + blue + network + Linux — with an agentic tool-use runtime. Authorized use only._

<br/>

[![Version](https://img.shields.io/badge/version-v0.7-orange?style=for-the-badge)](https://github.com/erkanrzgc/octopus)
[![Base Model](https://img.shields.io/badge/base-Turkish--Gemma--9B-4285F4?style=for-the-badge&logo=google)](https://huggingface.co/ytu-ce-cosmos/Turkish-Gemma-9b-v0.1)
[![Language](https://img.shields.io/badge/language-Turkish--first-E30A17?style=for-the-badge)](#)
[![Domain](https://img.shields.io/badge/domain-cybersecurity-000000?style=for-the-badge)](#)

[![Python](https://img.shields.io/badge/Python-3.14-3776AB?style=flat-square&logo=python&logoColor=white)](#)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.4-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)](#)
[![Transformers](https://img.shields.io/badge/🤗%20Transformers-4.49-FFD21E?style=flat-square)](#)
[![PEFT](https://img.shields.io/badge/PEFT-LoRA%20bf16-00A98F?style=flat-square)](#)
[![Tests](https://img.shields.io/badge/tests-39%20passing-3DA639?style=flat-square)](#)
[![License](https://img.shields.io/badge/code-MIT-green?style=flat-square)](#-license)
[![Use](https://img.shields.io/badge/use-authorized%2Flab--only-critical?style=flat-square)](#-responsible-use)

<em>“I am Octópus.” — it speaks Turkish, defends and attacks; but only when authorized.</em>

</div>

---

## 📖 About

**Octópus** is a Turkish-first language model fine-tuned for cybersecurity and server administration on
top of a strong Turkish-native base model (**`ytu-ce-cosmos/Turkish-Gemma-9b-v0.1`**). It introduces itself
as **“Ben Octópus”** (the dotted `ó` lives only in the brand and the model's speech; file paths stay plain
ASCII `octopus`).

Unlike English-centric security assistants, Octópus aims to be a fluent, literary **Turkish** speaker with
depth across **red team** (pentesting, recon, exploitation), **blue team** (detection, incident response,
hardening), and **network + Linux server administration** — and it is **authorization-aware** by design.

It ships with an **agent harness**: a runtime that parses the model's structured tool calls, runs the
requested security tools (through an authorization gate), and feeds the results back into the conversation.

> **Language in the base, knowledge on top.** Turkish fluency cannot be injected with a LoRA adapter, so we
> start from a Turkish-native base and add cybersecurity knowledge via SFT and (planned) RAG.

---

## ✨ Features

- 🇹🇷 **Turkish-first** — near-native fluency; commands, code, and CVE IDs are preserved verbatim.
- 🔴🔵 **Red + blue** — from pentesting to incident response, attack and defense in one model.
- 🖥️ **Server administration** — SSH/systemd/nginx/nftables/SELinux hardening, container & cloud security.
- 🛠️ **Agentic tool use** — a catalog of **117 tools** (`nmap`, `sqlmap`, `metasploit`, `bloodhound`, …) with
  a structured call format and a runtime that actually executes them.
- 🛡️ **Authorization calibration** — lab / CTF / owned systems only; unauthorized requests are refused
  clearly, with an ethical alternative offered.
- 📚 **Transparent pipeline** — data preparation → SFT → evaluation → agent runtime; every step is
  reproducible and traceable.

---

## 🏗️ Architecture

Octópus has two halves: the **model** (the brain — produces text, including structured tool calls) and the
**agent harness** (the hands — parses those calls and runs real tools behind a policy gate).

```text
   Turkish + cyber SFT data
   (distilled Q&A + 117-tool use)
              │  build_sft.py  (normalize + persona + dedup + split)
              ▼
   Turkish-Gemma-9B ──(bf16 LoRA, r=32)──▶  Octópus v0.7
              │
              ▼
   ┌──────────────────────── agent harness ─────────────────────────┐
   │  model text ──▶ parse ```arac``` block ──▶ policy gate (lab-only) │
   │       ▲                                          │                │
   │       │       feed result back  ◀── executor (mock | Kali | docker)
   └──────────────────────────────────────────────────────────────────┘
```

---

## 📂 Repository Layout

Small, focused modules — no god files.

| Path | Responsibility |
|---|---|
| `agent/` | Agent harness: tool-call parser, 117-tool catalog, policy gate, executors, run loop. |
| `agent/backends/` | Execution backends — mock model, real (Kali WSL), docker-lab. |
| `data/sft/` | SFT data pipeline: normalize to `messages`, inject persona, dedup, split. |
| `data/sft/tools/` | Hand-written agentic tool-use examples (117 tools, multi-step chains, refusals). |
| `train/sft_bf16.py` | Canonical bf16 LoRA training (plain `transformers` + `peft` + TRL). |
| `rag/` | Cybersecurity knowledge base for retrieval grounding. |
| `cloud/` | RunPod runbook and GGUF conversion recipe. |
| `docs/` | Architecture Decision Records (ADRs) and design specs. |
| `archive/` | Superseded approaches (from-scratch pretraining, Qwen QLoRA), kept for provenance. |
| `tests/` | Unit tests (agent harness). |

---

## 🧠 Model & Training

| | |
|---|---|
| **Base** | `ytu-ce-cosmos/Turkish-Gemma-9b-v0.1` (Gemma-2 architecture, strong in Turkish) |
| **Method** | bf16 LoRA (`r=32`, `α=32`, 7 target modules) — **no 4-bit** (it corrupts the merged base) |
| **Engine** | plain `transformers` + `peft` + TRL (not Unsloth) |
| **Hardware** | RunPod · RTX 4090 (24 GB) · torch 2.4 · pinned `transformers/trl/peft` |
| **Data (v0.7)** | 1,029 Turkish knowledge Q&A + 125 tool-use examples (117 tools) + persona seed |
| **Result (v0.7)** | final loss **0.048** · token accuracy **98.7%** · ~3 epochs |

**Why bf16 LoRA (not QLoRA)?** Turkish-Gemma carries a continual-pretrain + SFT + DPO + **merge** history;
common 4-bit (NF4) quantization corrupts those merged weights and produces multilingual garbage. The same
model in plain `bf16` produces flawless Turkish — so we load the base in bf16 and train a LoRA on top.
See [ADR 0003](docs/decisions/0003-pivot-to-turkish-gemma-bf16.md).

---

## 🤖 Agent Harness

The model does not run tools — it emits a structured call, and the harness executes it:

```
User → model emits ```arac {"arac":"nmap","parametreler":{...}} ``` → harness parses it
     → policy gate (target in authorized scope? risk level?) → executor runs the real tool
     → result fed back as a tool message → model interprets and continues.
```

Executors are pluggable behind one interface:

- **MockExecutor** — realistic simulated output; runs anywhere, zero risk (default).
- **RealExecutor** — runs real tools inside Kali (WSL2), `shell=False` argv, timeout.
- **DockerExecutor** — runs tools as containers on an isolated lab network, reaching containerized targets.

Every call passes a **fail-closed** authorization gate (lab-only scope, per-tool risk level) and is written
to an audit log. Try it:

```bash
uv run python -m agent.cli            # mock end-to-end demo
uv run python -m agent.cli --real     # real nmap via Kali WSL (requires WSL2 + Kali)
```

---

## 🗺️ Roadmap

- [x] **v0.6** — Turkish-Gemma bf16 LoRA · fluent Turkish + persona + authorization calibration
- [x] **v0.7** — cybersecurity knowledge depth + agentic tool use (117-tool catalog)
- [x] **Agent harness** — tool-call parser, policy gate, mock/real/docker executors (39 tests)
- [ ] **v0.7.1** — strengthen the structured `arac` block · full-dataset training
- [ ] **GGUF Q4** — run locally on 8 GB (offline-first)
- [ ] **RAG + Lab Mode** — knowledge base retrieval + isolated lab integration

---

## ⚙️ Tech Stack

`Python 3.14` · `PyTorch 2.4` · `Transformers 4.49` · `PEFT (LoRA)` · `TRL` · `Datasets` · `llama.cpp (GGUF)` ·
`uv` (packaging) · `RunPod` (training) · `Hugging Face Hub` · `pytest`

---

## 🔒 Responsible Use

> **⚠️ Authorized, legal, lab/CTF/educational use only.**

Octópus teaches offensive techniques in order to **strengthen defense** and to support **authorized
penetration testing and security research**. By design, the model:

- Assists only on systems the operator is **explicitly authorized** to test.
- **Refuses** to provide attack steps against unauthorized real targets (someone else's
  Wi-Fi/account/network/system, phishing, malware intended to cause harm).
- On such requests it **declines clearly**, explains why, and offers an ethical/defensive alternative.

This repository and model **must not** be used for criminal activity, unauthorized access, or harm.
Responsibility rests entirely with the user.

---

## 👤 Author

**Erkan** ([@erkanrzgc](https://github.com/erkanrzgc)) — ethical (white/grey-hat) security enthusiast working
on local-first AI. Octópus is an end-to-end, transparent record of designing, building data for, fine-tuning,
and evaluating a Turkish cybersecurity assistant from the ground up.

> Issues are open for questions, suggestions, or collaboration. 🐙

---

## 📜 License

- **Code:** MIT (the scripts, pipeline, and documentation in this repository).
- **Base model:** governed by the [Gemma Terms of Use](https://ai.google.dev/gemma/terms) (via
  `ytu-ce-cosmos/Turkish-Gemma-9b-v0.1`).
- **Derived weights / adapters:** subject to the base model's license terms; authorized/ethical use only.

<div align="center">
<sub>A model that thinks, defends, and — only when authorized — attacks, in Turkish. 🐙</sub>
</div>
