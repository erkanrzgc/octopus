#!/bin/bash
# KESIN TEST (gercek trainer): distill_v07'yi cikar -> distill(918)+seed+tools ile egit.
# Temiz (max-train 0, 120 adim) -> suclu KESIN v07. NaN -> v07 degil, daha derin.
set -e
cd /workspace/octopus-v7
pkill -9 -f "sft_bf16|nanfind" 2>/dev/null || true
sleep 2
echo "===== v07'yi gecici cikar ====="
mkdir -p /workspace/held
mv -f data/sft/distilled/octopus_distill_v07.jsonl /workspace/held/ 2>/dev/null || true
ls data/sft/distilled/
echo "===== rebuild: distill(918)+seed+tools, seed x5 ====="
python -m data.sft.build_sft --source distill seed_tr tools --seed-repeat 5
echo "--- train satir ---"; wc -l data/sft/train.jsonl
echo "===== GERCEK egitim, max-train 0, 120 adim (v07 YOK) ====="
export PYTHONUNBUFFERED=1
python train/sft_bf16.py --base ytu-ce-cosmos/Turkish-Gemma-9b-v0.1 \
  --lr 2e-4 --max-train 0 --max-steps 120 --no-gen --out /workspace/v7-nov07-test
echo "NO_V07_TEST_DONE"
