# Octópus — Skills & Subagents Guide

> This document clarifies skills vs subagents and maps them to the Octópus fine-tune workflow.
> Project skills: `.claude/skills/`. Global agents: `~/.claude/agents/` (ECC package).

## The difference (summary)
- **🧩 Skill = RECIPE / knowledge.** A `.md` recipe; when triggered it loads into the **current session's
  context** — no new agent is spawned. "Always do X this way." Cheap, deterministic, your convention.
  → `.claude/skills/`.
- **🤖 Subagent = WORKER / isolation.** A fresh Claude spawned with a clean context; takes a narrow task, runs
  tools, and returns **only a summary.** Value: context isolation + parallelism + specialization. Cost: cold
  start (expensive).
- **Rule:** Skill = *how* (in-context, cheap). Subagent = *go do it & report* (isolated, expensive). A skill
  may say "call this subagent" → they work together.

## Octópus project skills (installed)
| Skill | When | What it does |
|---|---|---|
| `octopus-data` | need SFT data | normalize Turkish+cyber sources into `messages` + persona + dedup + split |
| `octopus-finetune` | train the model | bf16 LoRA (Turkish-Gemma-9b, transformers+peft+TRL): data→train→eval→merge→GGUF + money checkpoint |
| `octopus-eval` | training done | perplexity + safety/balance + brittleness red-team |

## Subagent map (use existing global agents — don't invent new ones)
| Situation | Agent | Why |
|---|---|---|
| Training crash (CUDA/tensor/OOM/DataLoader) | `pytorch-build-resolver` | fixes it in an isolated context, keeps the main context clean |
| Python code quality | `python-reviewer` | reviews pipeline code |
| Security / persona guardrail concern | `security-reviewer` | red+blue guardrail, secret leaks |
| Broad exploration / code search / research | `Explore` or `general-purpose` | fan-out search with context isolation |
| Build/dependency error (torch/transformers) | `build-error-resolver` | get back to green quickly |

> **Parallelism:** dispatch independent jobs in parallel in one message (e.g. code review while data is prepared).
> **Write a custom agent ONLY for a real gap** (e.g. an Octópus-specific automated evaluator) — none needed right now.

## Which one, when? (practical)
- Repeated, convention-carrying work (training recipe, data shape) → **skill**.
- Heavy/isolated/parallel work that would pollute context (debugging, broad search) → **subagent**.
- Both together: the `octopus-finetune` skill recommends the `pytorch-build-resolver` subagent on a training crash.
