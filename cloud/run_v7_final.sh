#!/bin/bash
# v0.7 TAM TUR (kanitli-temiz yol): full veri geri + max-train 2000 (smoke bununla temizdi) + 900 adim.
set -e
cd /workspace/octopus-v7
pkill -9 -f "sft_bf16|nanfind" 2>/dev/null || true
sleep 2
echo "===== v07'yi geri getir ====="
mv -f /workspace/held/octopus_distill_v07.jsonl data/sft/distilled/ 2>/dev/null || true
ls data/sft/distilled/
echo "===== rebuild: TAM v0.7 (distill+seed+tools, seed x5) ====="
python -m data.sft.build_sft --source distill seed_tr tools --seed-repeat 5
echo "--- train satir ---"; wc -l data/sft/train.jsonl
echo "===== TAM TUR: max-train 2000, 900 adim, lr 2e-4 ====="
export PYTHONUNBUFFERED=1
python train/sft_bf16.py --base ytu-ce-cosmos/Turkish-Gemma-9b-v0.1 \
  --lr 2e-4 --max-train 2000 --max-steps 900 --no-gen --out /workspace/v7-adapter-final
echo "V7_FINAL_DONE"
