#!/bin/bash
# Octopus v0.4 — REBALANCE hipotez testi (Ingilizce baskinligini kir).
# Fenrir 50k (99k degil) + InstrucTurca 30k (cesitli Turkce) + seed(87) x20 -> Turkce ~%39.
set -e
cd /workspace/octopus

echo "===== [1/4] Bagimliliklar ====="
pip install -q --upgrade pip
pip install -q unsloth trl peft datasets bitsandbytes accelerate hf_transfer
export HF_HUB_ENABLE_HF_TRANSFER=1
export PYTHONUNBUFFERED=1

echo "===== [2/4] SFT verisi (REBALANCE: Fenrir 50k + InstrucTurca 30k + seed x20) ====="
python data/sft/seed_tr/build_seed.py
python data/sft/seed_tr/build_cyber_seed.py
python -m data.sft.build_sft --seed-repeat 20 --cap "fenrir=50000,instructurca=30000"

echo "===== [3/4] Egitim: Qwen3-8B QLoRA, 2000 adim (v0.4 rebalance) ====="
python train/sft_smoke.py \
  --base unsloth/Qwen3-8B \
  --max-steps 2000 \
  --max-train 0 \
  --out /workspace/octopus/octopus-8b-adapter

echo "===== [4/4] Adapter paketleniyor + dogrulama ====="
cd /workspace/octopus
echo "--- adapter icerik ---"; ls -la octopus-8b-adapter/
tar -czf /workspace/octopus-8b-adapter.tar.gz -C /workspace/octopus octopus-8b-adapter
sz=$(stat -c %s /workspace/octopus-8b-adapter.tar.gz)
sha=$(sha256sum /workspace/octopus-8b-adapter.tar.gz | cut -d' ' -f1)
echo "TARBALL_SIZE=$sz"
echo "TARBALL_SHA256=$sha"
echo "POD_RUN_DONE"
