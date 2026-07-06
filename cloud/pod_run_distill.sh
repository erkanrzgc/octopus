#!/bin/bash
# Octopus distillation — KUCUK TEST: Qwen3-14B teacher, RAG bilgi tabanindan Turkce cyber Q&A.
# Amac: pipeline + kalite dogrulama (JSON ayristirma calisiyor mu, cevaplar iyi mi) TAM turdan once.
set -e
cd /workspace/octopus

echo "===== [1/2] Bagimliliklar ====="
pip install -q --upgrade pip
pip install -q unsloth trl peft datasets bitsandbytes accelerate hf_transfer
export HF_HUB_ENABLE_HF_TRANSFER=1
export PYTHONUNBUFFERED=1

echo "===== [2/2] Distillation KUCUK TEST (Qwen3-14B teacher, 15 parca) ====="
python data/sft/distill_tr.py \
  --teacher unsloth/Qwen3-14B \
  --per-chunk 4 \
  --max-chunks 15 \
  --out /workspace/octopus/distill_test.jsonl

echo "===== ORNEK CIKTI (ilk 3) ====="
head -3 /workspace/octopus/distill_test.jsonl
echo "DISTILL_TOTAL=$(wc -l < /workspace/octopus/distill_test.jsonl)"
echo "DISTILL_DONE"
