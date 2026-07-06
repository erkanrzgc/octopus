#!/bin/bash
# TESHIS: v0.7 NaN'in kaynagi tools mu? tools'suz (v0.6 deseni + yeni distill_v07) yeniden kur + egit.
# Temiz kalirsa -> suclu tool verisi. NaN -> ortam/stabilite.
set -e
cd /workspace/octopus-v7
pkill -9 -f sft_bf16 2>/dev/null || true
sleep 2
echo "===== [1/2] tools'SUZ yeniden kur (distill + seed_tr, seed x10) ====="
python -m data.sft.build_sft --source distill seed_tr --seed-repeat 10
echo "--- train.jsonl satir (tools'suz) ---"; wc -l data/sft/train.jsonl
echo "===== [2/2] gercek egitim, 150 adim, tools YOK ====="
export PYTHONUNBUFFERED=1
python train/sft_bf16.py --base ytu-ce-cosmos/Turkish-Gemma-9b-v0.1 \
  --lr 2e-4 --max-train 0 --max-steps 150 --no-gen --out /workspace/v7-notools-test
echo "NOTOOLS_TEST_DONE"
