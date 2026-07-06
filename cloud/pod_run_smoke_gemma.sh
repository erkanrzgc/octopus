#!/bin/bash
# Octopus v0.6 SMOKE — Turkish-Gemma + CIFT-BOS FIX dogrulama.
# Amac: fix gercekten ogretiyor mu? loss <2'ye dusuyor mu + Turkce cevap?
# UCUZ: sadece YEREL veri (distill 918 + seed, upsample) — Fenrir/HF indirmesi YOK. 40 adim.
set -e
cd /workspace/octopus-smoke

echo "===== [1/4] Bagimliliklar ====="
pip install -q unsloth trl peft datasets bitsandbytes accelerate hf_transfer 2>&1 | tail -3
export HF_HUB_ENABLE_HF_TRANSFER=1 PYTHONUNBUFFERED=1

echo "===== [2/4] Veri (SADECE yerel: distill 918 + seed x20; Fenrir YOK) ====="
python data/sft/seed_tr/build_seed.py || true
python data/sft/seed_tr/build_cyber_seed.py || true
python -m data.sft.build_sft --source distill seed_tr --seed-repeat 20
echo "--- train.jsonl satir ---"; wc -l data/sft/train.jsonl

echo "===== [3/4] SMOKE egitim: Turkish-Gemma + FIX, 40 adim ====="
python train/sft_smoke.py --base ytu-ce-cosmos/Turkish-Gemma-9b-v0.1 \
  --lr 2e-4 --max-steps 40 --max-train 2000 --out /workspace/smoke-adapter

echo "SMOKE_DONE"
