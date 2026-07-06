#!/bin/bash
# EN KESIN AYRIM: v0.6'nin BIREBIR recetesi (distill 918 + seed, tools YOK, v07 YOK) gercek trainer.
# TEMIZ -> suclu tools/flatten (v0.6 reprodukte). NaN -> sorun VERI DEGIL, ORTAM (surum/pod/torch).
set -e
cd /workspace/octopus-v7
pkill -9 -f "sft_bf16|nanfind" 2>/dev/null || true
sleep 2
echo "===== distilled/ icerigi (v07 cikmis olmali) ====="
ls data/sft/distilled/
echo "===== rebuild: SADECE distill(918)+seed (v0.6 deseni), seed x10 ====="
python -m data.sft.build_sft --source distill seed_tr --seed-repeat 10
echo "--- train satir ---"; wc -l data/sft/train.jsonl
echo "===== GERCEK egitim, max-train 0, 120 adim (v0.6 birebir) ====="
export PYTHONUNBUFFERED=1
python train/sft_bf16.py --base ytu-ce-cosmos/Turkish-Gemma-9b-v0.1 \
  --lr 2e-4 --max-train 0 --max-steps 120 --no-gen --out /workspace/v06repro
echo "V06REPRO_DONE"
