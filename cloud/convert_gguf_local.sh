#!/bin/bash
# Octopus v0.7 GGUF — YEREL build-free yol (WSL Ubuntu, py3.12 CPU). pod_gguf_v7.sh'in
# RunPod'suz muadili: GPU gereksiz (merge device_map=cpu), llama.cpp DERLENMEZ.
# Saf-Python: merge + convert_hf_to_gguf -> f16 GGUF. Niceleme (Q4_K_M) Windows'ta
# 'ollama create -q q4_K_M' ile yapilir (cmake/build-essential gerekmez).
# Cikti: models/octopus-v7-f16.gguf + models/octopus-v7-tokenizer/ (backend template icin).
set -eo pipefail
WORK="$HOME/octopus-gguf"
BASE="ytu-ce-cosmos/Turkish-Gemma-9b-v0.1"
ADP_SRC="/mnt/c/Users/erkanrzgc/Desktop/Octopus/checkpoints_sft/octopus-gemma-v7-adapter"
ADP="$WORK/v7-adapter"
MERGED="$WORK/octopus-v7-merged"
OUTDIR="/mnt/c/Users/erkanrzgc/Desktop/Octopus/models"
VENV="$WORK/venv"
mkdir -p "$WORK" "$OUTDIR/octopus-v7-tokenizer"

echo "===== [0/4] adapter'i WSL'e kopyala (mnt/c yavas 9p I/O'dan kacin) ====="
rm -rf "$ADP"; cp -r "$ADP_SRC" "$ADP"; ls -la "$ADP" | head

echo "===== [1/4] uv (sudo YOK) + venv + pinli deps (torch CPU wheel; CUDA indirmez) ====="
# Ubuntu python3.12-venv (apt/sudo) yok -> uv kendi venv'ini ensurepip'siz yaratir.
if ! command -v uv >/dev/null 2>&1; then curl -LsSf https://astral.sh/uv/install.sh | sh; fi
export PATH="$HOME/.local/bin:$PATH"
uv venv "$VENV" --python 3.12 --clear
# shellcheck disable=SC1091
source "$VENV/bin/activate"
uv pip install -q torch==2.4.1 --index-url https://download.pytorch.org/whl/cpu
uv pip install -q "transformers==4.49.0" "peft==0.14.0" "accelerate==1.4.0" huggingface_hub hf_transfer sentencepiece protobuf
# HF tek-baglanti throttle'ini as: Rust paralel indirici (cache paylasimli -> inmisler yeniden inmez).
export HF_HUB_ENABLE_HF_TRANSFER=1

echo "===== [2/4] MERGE (CPU bf16) + tokenizer disari ====="
python - <<PY
import torch, shutil
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from huggingface_hub import hf_hub_download
base = AutoModelForCausalLM.from_pretrained("$BASE", torch_dtype=torch.bfloat16, device_map="cpu")
m = PeftModel.from_pretrained(base, "$ADP").merge_and_unload()
try: m.generation_config.do_sample = True   # Turkish-Gemma gen_config gecersiz -> tf4.49 save patlar
except Exception: pass
m.save_pretrained("$MERGED", safe_serialization=True)
tok = AutoTokenizer.from_pretrained("$ADP")
tok.save_pretrained("$MERGED")
tok.save_pretrained("$OUTDIR/octopus-v7-tokenizer")
tm = hf_hub_download("$BASE", "tokenizer.model")     # Gemma convert + apply_chat_template ister
shutil.copy(tm, "$MERGED/tokenizer.model")
shutil.copy(tm, "$OUTDIR/octopus-v7-tokenizer/tokenizer.model")
print("MERGE_OK")
PY

echo "===== [3/4] convert_hf_to_gguf -> f16 (saf-Python, BUILD YOK) ====="
cd "$WORK"
[ -d llama.cpp ] || git clone --depth 1 https://github.com/ggml-org/llama.cpp
cd llama.cpp
uv pip install -q gguf numpy sentencepiece protobuf
python convert_hf_to_gguf.py "$MERGED" --outfile "$WORK/octopus-v7-f16.gguf" --outtype f16

echo "===== [4/4] f16'yi Windows models/'a kopyala + merged sil ====="
rm -rf "$MERGED"
cp "$WORK/octopus-v7-f16.gguf" "$OUTDIR/octopus-v7-f16.gguf"
ls -la "$OUTDIR"
echo "F16_DONE — sonraki (Windows): ollama create octopus-v7 -q q4_K_M -f models/Modelfile.f16"
