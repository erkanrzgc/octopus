#!/bin/bash
# Octopus 8B QLoRA — RunPod pod'unda calisir (RTX 4090 24GB).
# Bundle /workspace/octopus'a acildiktan sonra: bash cloud/pod_run.sh
set -e
cd /workspace/octopus

echo "===== [1/4] Bagimliliklar ====="
pip install -q --upgrade pip
pip install -q unsloth trl peft datasets bitsandbytes accelerate hf_transfer
export HF_HUB_ENABLE_HF_TRANSFER=1
export PYTHONUNBUFFERED=1

echo "===== [2/4] SFT verisi (pod'da yeniden derle, seed x20 upsample) ====="
python data/sft/seed_tr/build_seed.py
python data/sft/seed_tr/build_cyber_seed.py     # v0.3: bilgi-tabanli Turkce cyber Q&A
python -m data.sft.build_sft --seed-repeat 20   # fenrir(tum) + instructurca(10k) + seed(87) x20

echo "===== [3/4] Egitim: Qwen3-8B QLoRA, 2000 adim, tam veri (v0.2) ====="
python train/sft_smoke.py \
  --base unsloth/Qwen3-8B \
  --max-steps 2000 \
  --max-train 0 \
  --out /workspace/octopus/octopus-8b-adapter

echo "===== [4/4] Adapter paketleniyor + dogrulama ====="
cd /workspace/octopus
echo "--- adapter icerik (config var mi?) ---"; ls -la octopus-8b-adapter/
tar -czf /workspace/octopus-8b-adapter.tar.gz -C /workspace/octopus octopus-8b-adapter
sz=$(stat -c %s /workspace/octopus-8b-adapter.tar.gz)
sha=$(sha256sum /workspace/octopus-8b-adapter.tar.gz | cut -d' ' -f1)
echo "TARBALL_SIZE=$sz"
echo "TARBALL_SHA256=$sha"
echo "POD_RUN_DONE"
