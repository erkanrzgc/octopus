#!/bin/bash
# Octopus v0.6 — TURKCE-UZMAN TABAN (dil #1: "Namik Kemal Turkcesi").
# Taban: ytu-ce-cosmos/Turkish-Gemma-9b-v0.1 (Turkcede Qwen3-32B'yi geciyor).
# Veri TURKCE-BASKIN: Fenrir 35k (az, guardrail+siber) + tr_native 20k (native Turkce akicilik)
#   + seed x20 (persona/ret) + distill x1 (918 Turkce cyber, bundle'da hazir).
# Distillation TEKRAR YOK (918 elde). sft_smoke Gemma-uyumlu (enable_thinking try/except).
set -e
cd /workspace/octopus

echo "===== [1/4] Bagimliliklar ====="
pip install -q --upgrade pip
pip install -q unsloth trl peft datasets bitsandbytes accelerate hf_transfer
export HF_HUB_ENABLE_HF_TRANSFER=1
export PYTHONUNBUFFERED=1

echo "===== [2/4] Veri (TURKCE-BASKIN: Fenrir 35k + tr_native 20k + seed x20 + distill 918) ====="
python data/sft/seed_tr/build_seed.py
python data/sft/seed_tr/build_cyber_seed.py
echo "distill elde: $(wc -l < data/sft/distilled/octopus_distill_tr.jsonl) satir"
python -m data.sft.build_sft --source fenrir tr_native seed_tr distill \
  --seed-repeat 20 --cap "fenrir=35000,tr_native=20000"

echo "===== [3/4] Egitim: Turkish-Gemma-9b QLoRA, LR-fix KISA TEST (300 adim, lr 5e-5) ====="
python train/sft_smoke.py --base ytu-ce-cosmos/Turkish-Gemma-9b-v0.1 \
  --lr 5e-5 --max-steps 300 --max-train 8000 --out /workspace/octopus/octopus-gemma-adapter

echo "===== [4/4] Adapter paketle + dogrula ====="
cd /workspace/octopus
echo "--- adapter icerik ---"; ls -la octopus-gemma-adapter/
tar -czf /workspace/octopus-gemma-adapter.tar.gz -C /workspace/octopus octopus-gemma-adapter
sz=$(stat -c %s /workspace/octopus-gemma-adapter.tar.gz)
sha=$(sha256sum /workspace/octopus-gemma-adapter.tar.gz | cut -d' ' -f1)
echo "TARBALL_SIZE=$sz"
echo "TARBALL_SHA256=$sha"
echo "POD_RUN_DONE"
