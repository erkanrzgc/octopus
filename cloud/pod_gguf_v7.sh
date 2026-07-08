#!/bin/bash
# Octopus v0.7 GGUF — v6 tarifinin (pod_gguf_clean.sh) v7 uyarlamasi.
# KOK SEBEP (onceki basarisizlik): llama.cpp requirements.txt transformers/torch'u degistirip
# peft merge'i kiriyor. COZUM: ONCE merge (pinli env), SONRA llama.cpp deps. Sira kritik.
# Onkosul: /workspace/v7-adapter (LoRA adapter) pod'da hazir olmali (scp/hf ile gonder).
# YENI (v6'dan farki): merge tokenizer'i ayri /workspace/octopus-v7-tokenizer dizinine de kaydeder
# (yerel backend apply_chat_template icin lazim; yerel adapter dizininde tokenizer.model YOK).
set -eo pipefail
BASE="ytu-ce-cosmos/Turkish-Gemma-9b-v0.1"; ADP="/workspace/v7-adapter"
MERGED="/workspace/octopus-v7-merged"; OUT="/workspace/octopus-v7-gguf"
TOKOUT="/workspace/octopus-v7-tokenizer"; mkdir -p "$OUT" "$TOKOUT"

echo "===== [1/5] Merge env (pinli) + MERGE (llama.cpp deps'ten ONCE!) ====="
pip install -q "transformers==4.49.0" "peft==0.14.0" "accelerate==1.4.0" "torch==2.4.1" 2>&1 | tail -1
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
tok.save_pretrained("$TOKOUT")                       # YENI: backend icin ayri tokenizer dizini
tm = hf_hub_download("$BASE", "tokenizer.model")     # Gemma convert + apply_chat_template ister
shutil.copy(tm, "$MERGED/tokenizer.model")
shutil.copy(tm, "$TOKOUT/tokenizer.model")
print("MERGE_OK")
PY

echo "===== [2/5] cmake + llama.cpp (merge BITTI, artik env bozulabilir) ====="
pip install -q cmake 2>&1 | tail -1
cd /workspace
[ -d llama.cpp ] || git clone --depth 1 https://github.com/ggml-org/llama.cpp
cd llama.cpp
pip install -q -r requirements.txt 2>&1 | tail -1

echo "===== [3/5] llama-quantize build ====="
cmake -B build -DGGML_CUDA=OFF -DLLAMA_CURL=OFF 2>&1 | tail -1
cmake --build build --config Release -j --target llama-quantize 2>&1 | tail -2

echo "===== [4/5] HF -> GGUF f16 ====="
python convert_hf_to_gguf.py "$MERGED" --outfile "$OUT/octopus-v7-f16.gguf" --outtype f16

echo "===== [5/5] Quantize -> Q4_K_M ====="
[ -f "$OUT/octopus-v7-f16.gguf" ] && rm -rf "$MERGED" ~/.cache/huggingface/hub/models--ytu-ce-cosmos*
./build/bin/llama-quantize "$OUT/octopus-v7-f16.gguf" "$OUT/octopus-v7-Q4_K_M.gguf" Q4_K_M
rm -f "$OUT/octopus-v7-f16.gguf"
ls -la "$OUT" "$TOKOUT"; sha256sum "$OUT/octopus-v7-Q4_K_M.gguf"
echo "GGUF_DONE — indir: $OUT/octopus-v7-Q4_K_M.gguf + $TOKOUT/  -> yerelde models/"
