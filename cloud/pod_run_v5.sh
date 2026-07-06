#!/bin/bash
# Octopus v0.5 — DISTILLATION + EGITIM (tek pod).
# 1) Qwen3-14B teacher -> ~1000 CESITLI Turkce cyber Q&A (RAG bilgi tabanindan)
# 2) Veri: Fenrir 55k (guardrail'i korur) + InstrucTurca 12k + hand-seed x20 + distilled x1
# 3) Qwen3-8B QLoRA egit -> v0.5
set -e
cd /workspace/octopus

echo "===== [1/5] Bagimliliklar ====="
pip install -q --upgrade pip
pip install -q unsloth trl peft datasets bitsandbytes accelerate hf_transfer
export HF_HUB_ENABLE_HF_TRANSFER=1
export PYTHONUNBUFFERED=1

echo "===== [2/5] DISTILLATION (Qwen3-14B teacher, ~250 parca -> ~1000 Q&A) ====="
python data/sft/distill_tr.py --teacher unsloth/Qwen3-14B --per-chunk 4 --max-chunks 250
echo "DISTILL_COUNT=$(wc -l < data/sft/distilled/octopus_distill_tr.jsonl)"

echo "===== [3/5] Seed'ler + SFT veri (Fenrir 55k + InstrucTurca 12k + seed x20 + distill x1) ====="
python data/sft/seed_tr/build_seed.py
python data/sft/seed_tr/build_cyber_seed.py
python -m data.sft.build_sft --source fenrir instructurca seed_tr distill \
  --seed-repeat 20 --cap "fenrir=55000,instructurca=12000"

echo "===== [4/5] Egitim: Qwen3-8B QLoRA, 2000 adim (v0.5) ====="
python train/sft_smoke.py --base unsloth/Qwen3-8B --max-steps 2000 --max-train 0 \
  --out /workspace/octopus/octopus-8b-adapter

echo "===== [5/5] Adapter paketle + dogrula ====="
cd /workspace/octopus
echo "--- adapter icerik ---"; ls -la octopus-8b-adapter/
tar -czf /workspace/octopus-8b-adapter.tar.gz -C /workspace/octopus octopus-8b-adapter
# distilled veriyi de yedekle (yerele cekip saklamak icin)
cp data/sft/distilled/octopus_distill_tr.jsonl /workspace/octopus_distill_tr.jsonl
sz=$(stat -c %s /workspace/octopus-8b-adapter.tar.gz)
sha=$(sha256sum /workspace/octopus-8b-adapter.tar.gz | cut -d' ' -f1)
echo "TARBALL_SIZE=$sz"
echo "TARBALL_SHA256=$sha"
echo "POD_RUN_DONE"
