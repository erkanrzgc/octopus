# Octópus — Claude Code proje notu

> Bu dosya bu klasörde Claude Code açıldığında **her oturumda otomatik yüklenir** → bağlam kaybolmaz.
> Daha fazla: vizyon `OCTOPUS.md`, fazlı plan `~/.claude/plans/atomic-jumping-swan.md`.

## Ne bu proje
**Octópus** — Türkçe-önce, siber güvenlik (red+blue+network) + sunucu yönetimi odaklı bir LLM.
Güçlü bir taban (**Qwen3-8B**) **QLoRA ile fine-tune** edilir. Model kendini
**"Ben Octópus"** (noktalı ó) diye tanıtır. Strateji kararı: `docs/decisions/0002-pivot-to-finetuning.md`.

## Marka & yol (ÖNEMLİ)
ó **yalnızca markada/konuşmada** ("Ben Octópus", README, dokümanlar, GitHub). **Dosya yolu/klasör
düz ASCII `octopus`** — Windows native kütüphaneler (SentencePiece, llama.cpp, torch eklentileri)
non-ASCII path'te patlıyor. Çalışma klasörü: `C:\Users\erkanrzgc\Desktop\Octopus`.

## Güncel faz (2026-07-03) — FINE-TUNING
- **Strateji:** from-scratch bırakıldı (maliyet), **QLoRA fine-tuning**e dönüldü. Taban = `Qwen3-8B`.
- **Sıradaki:** SFT veri hazırla (Fenrir + secdata + AlicanKiraz CVE + Türkçe persona) → yerel duman turu →
  (💰 checkpoint) → RunPod QLoRA turu → eval/safety → merge → GGUF.
- **Skill'ler:** `octopus-finetune` (ana reçete), `octopus-data` (SFT veri), `octopus-eval` (kalite+safety).
  Skill/subagent ne zaman hangisi → `docs/skills-and-subagents.md`.
- **Arşiv:** from-scratch işi (`tokenizer/octopus-tr`, `model/`, `checkpoints_web/`) silinmedi, korunuyor.

## Çalışma kuralları
- Paket: **uv** (`uv sync`, `uv run python ...`); venv `.venv` (ASCII yolda).
- GPU: RTX 5060 8GB yerel (~150M v0); büyük tur **RunPod** — asistan pod'a erişemez (komut verir,
  kullanıcı koşar). Para harcayan her adımdan ÖNCE kullanıcıyla checkpoint.
- Büyük işe körlemesine girme → önce **plan modu** (kullanıcı tercihi).

## Reuse (tersine mühendislik yapıldı — kopya değil desen)
- **`Desktop\cyberm4fiaModel`** — Octópus'un çalışan atası: Qwen2.5-3B + Unsloth QLoRA + Fenrir v2.1
  → loss 0.77 / ppl 2.39. 00-06 pipeline + Chroma RAG (`rag/knowledge/`) + safety eval + 15-araç agent +
  Türkçe guardrail system prompt (`cyberm4fia/config.py`). Veri-şekli + persona + eval deseni buradan.
- **`Desktop\agentic-model`** — Qwen QLoRA + agent runtime + Türkçe teacher distillation
  (`scripts/distill_teacher_tr.py`), bol test. Agentic harness sonra port edilir (model-bağımsız).
