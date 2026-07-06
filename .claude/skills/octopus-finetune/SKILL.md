---
name: octopus-finetune
description: Use when planning or running a QLoRA fine-tune of Octópus (Türkçe-önce siber LLM) — the full data→train→eval→merge→GGUF→serve workflow on a Qwen3 base with Unsloth. Triggers on "octopus eğit", "fine-tune", "QLoRA", "modeli eğit", "RunPod turu".
---

# Octópus Fine-tune (QLoRA + Unsloth)

Octópus'un ana eğitim reçetesi. Taban: **`Qwen3-8B`** (QLoRA için `unsloth/Qwen3-8B`
bnb-4bit). Strateji + gerekçe: `docs/decisions/0002-pivot-to-finetuning.md`. Çalışan referans desen:
`Desktop\cyberm4fiaModel` (Qwen2.5-3B QLoRA + Fenrir → loss 0.77 / ppl 2.39).

## 🚨 Değişmez kurallar (her koşuda)
- **Para harcayan RunPod tam turundan ÖNCE kullanıcıyla checkpoint.** Önce yerel duman turu yeşil olmalı.
- API key/token = SIR: sohbete/`!` komutuna yapıştırma. RunPod/HF auth'u **kullanıcı kendi terminalinde** koşar.
- Asistan pod'a doğrudan erişemez → komutu ver, kullanıcı koşar, çıktıyı yapıştırır.
- Guardrail system prompt (`octopus-data`'daki persona) train verisine gömülür — red+blue yalnızca yetkili.

## Adımlar
1. **Veri** — `octopus-data` skill'iyle SFT verisi hazır (`messages` JSONL, train/val/test). Yoksa önce onu koş.
2. **Ortam** (Blackwell / RTX 5060, sm_120):
   ```bash
   uv venv --python 3.12 .venv && source .venv/Scripts/activate
   uv pip install torch --index-url https://download.pytorch.org/whl/cu129
   uv pip install unsloth trl peft bitsandbytes datasets accelerate
   ```
3. **Duman turu (yerel, ÜCRETSİZ, para-checkpoint ÖNCESİ):** ~1k örnek, kısa. Kabul: loss düşüyor,
   `messages` formatı + "Ben Octópus" persona doğru, örnek Türkçe siber cevap makul. Bkz. cyberm4fia `02_train.py`.
4. **Tam tur (RunPod, 💰 checkpoint SONRASI):** `cloud/RUNPOD.md` runbook → cache'li template `runpod-torch-v240`,
   SECURE, `--terminate-after`. Adaptör küçük (~200-400MB) → HF'ye yükle (`uv run hf upload`).
5. **Eval** — `octopus-eval` skill (ppl + safety/balance + brittleness). Yeşil değilse hiperparametre/veri ayarla.
6. **Merge + GGUF** — LoRA merge (16-bit) → GGUF Q4 (llama.cpp). Referans: cyberm4fia `05b_merge_peft.py`.
7. **Serve** — yerel Ollama/llama.cpp ya da Unsloth doğrudan. (Not: cyberm4fia'da Ollama GGUF Blackwell'de
   kararsızdı → gerekirse Unsloth ile serve.)

## Hiperparametre başlangıcı (cyberm4fia'dan, ölçerek ayarla)
| Knob | Başlangıç | Not |
|---|---|---|
| LoRA r / alpha | 32 / 32 | kapasite; 16↔64 dene |
| target_modules | q,k,v,o,gate,up,down_proj | tam kapsama |
| seq_len | 1024 → 2048 | 8GB'de 1024 güvenli |
| batch / grad_accum | 1 / 8 | efektif 8 (8GB gerçeği) |
| lr / scheduler | 2e-4 / cosine | QLoRA tipik |
| optimizer | adamw_8bit (paged) | bitsandbytes |
| load_in_4bit | True | QLoRA temeli |
| epochs | 1 | veri büyükse yeter |

## Yükseltme yolu
Pipeline oturunca `Qwen3-14B` (env değiştir). Opsiyonel: `fdtn-ai/Foundation-Sec-8B-Reasoning`'i öğretmen
yapıp İngilizce siber-reasoning'i Türkçe SFT'ye damıt (agentic-model `scripts/distill_teacher_tr.py`).

## Sorun çıkarsa
- CUDA/tensor/OOM çökmesi → **`pytorch-build-resolver`** subagent (izole context).
- 8GB'de 8B QLoRA OOM verirse: seq 1024, batch 1, grad_accum ↑, ya da RunPod'a al.
