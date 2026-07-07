# Octópus — Claude Code proje notu

> Bu dosya bu klasörde Claude Code açıldığında **her oturumda otomatik yüklenir** → bağlam kaybolmaz.
> Daha fazla: vizyon `OCTOPUS.md`, fazlı plan `~/.claude/plans/atomic-jumping-swan.md`.

## Ne bu proje
**Octópus** — Türkçe-önce, siber güvenlik (red+blue+network) + sunucu yönetimi odaklı bir LLM.
Güçlü bir Türkçe-uzman taban (**`ytu-ce-cosmos/Turkish-Gemma-9b-v0.1`**) **bf16 LoRA ile fine-tune**
edilir (4-bit NF4 DEĞİL — merge'li tabanı bozar). Model kendini **"Ben Octópus"** (noktalı ó) diye tanıtır.
Strateji kararları: `docs/decisions/0002-pivot-to-finetuning.md` (fine-tuning'e dönüş) +
`docs/decisions/0003-pivot-to-turkish-gemma-bf16.md` (taban Qwen3→Turkish-Gemma, yöntem QLoRA→bf16 LoRA).

## Marka & yol (ÖNEMLİ)
ó **yalnızca markada/konuşmada** ("Ben Octópus", README, dokümanlar, GitHub). **Dosya yolu/klasör
düz ASCII `octopus`** — Windows native kütüphaneler (SentencePiece, llama.cpp, torch eklentileri)
non-ASCII path'te patlıyor. Çalışma klasörü: `C:\Users\erkanrzgc\Desktop\Octopus`.

## Güncel faz (2026-07-07) — FINE-TUNING, v0.7 EĞİTİLDİ
- **Strateji:** from-scratch bırakıldı (maliyet) → fine-tuning. Taban **Turkish-Gemma-9b-v0.1**, yöntem
  **bf16 LoRA** (r=32, α=32, 7 modül, seq 1024, lr 2e-4, RunPod RTX 4090). Motor = düz `transformers`+`peft`+
  TRL (Unsloth DEĞİL — 4-bit NF4 Turkish-Gemma'yı bozuyor, kanıt `train/sft_bf16.py:1-9`).
- **Tamamlanan:** v0.6 (akıcı Türkçe + persona, loss 0.22) ✅ · v0.7 (siber bilgi + 117-araç tool-use, loss
  0.048, %98.7) ✅. Adapter: yerel `checkpoints_sft/octopus-gemma-v7-adapter/` + HF `erkanrzgcc/octopus-gemma-v0.7`.
- **Sıradaki:** GGUF Q4 (yerel RTX 5060 8GB) · v0.7.1 (yapısal ```arac``` bloğunu güçlendir). Durum tek-gerçek:
  `docs/v0.7-loop-queue.md`. ⚠️ TUZAK: `--max-train 0` (tam veri) → NaN; `--max-train 2000` → temiz.
- **Skill'ler:** `octopus-finetune` (ana reçete), `octopus-data` (SFT veri), `octopus-eval` (kalite+safety).
  Skill/subagent ne zaman hangisi → `docs/skills-and-subagents.md`.
- **Arşiv:** from-scratch işi (`tokenizer/octopus-tr`, `model/`, `checkpoints_web/`) + Qwen3-8B QLoRA denemesi
  (v0.1/v0.2, `sft_smoke.py`) silinmedi, korunuyor.

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
