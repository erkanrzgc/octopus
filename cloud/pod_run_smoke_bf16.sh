#!/bin/bash
# Octopus v0.6 bf16 SMOKE — Turkish-Gemma + bf16 LoRA (unsloth 4bit YOK).
# Amac: 4bit'i atlayinca loss dusuyor mu + uretim AKICI Turkce mi? (unsloth 4bit copu cozuldu mu?)
# UCUZ: sadece YEREL veri (distill 918 + seed x20). Fenrir/HF instruct indirmesi YOK. 40 adim.
set -e
cd /workspace/octopus-smoke

echo "===== [1/4] Bagimliliklar (unsloth YOK — torch-2.4 uyumlu SABIT surumler) ====="
# En yeni TRL torch 2.5+ ister (chunked CE, torch.distributed.tensor.DTensor). Pod imaji torch 2.4.0 ->
# torch-2.4 uyumlu sabit cifte cak (yoksa AttributeError: DTensor).
pip install -q "transformers==4.49.0" "trl==0.15.2" "peft==0.14.0" "accelerate==1.4.0" datasets bitsandbytes 2>&1 | tail -3
export PYTHONUNBUFFERED=1

echo "===== [2/4] Veri (SADECE yerel: distill 918 + seed x20; Fenrir YOK) ====="
python data/sft/seed_tr/build_seed.py || true
python data/sft/seed_tr/build_cyber_seed.py || true
python -m data.sft.build_sft --source distill seed_tr --seed-repeat 20
echo "--- train.jsonl satir ---"; wc -l data/sft/train.jsonl

echo "===== [3/4] SMOKE bf16 LoRA: Turkish-Gemma, 40 adim ====="
python train/sft_bf16.py --base ytu-ce-cosmos/Turkish-Gemma-9b-v0.1 \
  --lr 2e-4 --max-steps 40 --max-train 2000 --out /workspace/v6-adapter

echo "SMOKE_DONE"
