#!/bin/bash
# Octopus v0.6 GGUF — TEMIZ tarif (bagimlilik cakismasi cozulmus).
# KOK SEBEP (onceki basarisizlik): llama.cpp requirements.txt, transformers/torch'u degistirip
# peft merge'i kiriyordu (BloomPreTrainedModel / torchvision::nms). COZUM: ONCE merge (pinli env
# saglamken), SONRA llama.cpp deps. Sira kritik.
# Onkosul: /workspace/v6-adapter (LoRA adapter) pod'da hazir olmali (scp ile gonder).
set -eo pipefail
BASE="ytu-ce-cosmos/Turkish-Gemma-9b-v0.1"; ADP="/workspace/v6-adapter"
MERGED="/workspace/octopus-v6-merged"; OUT="/workspace/octopus-v6-gguf"; mkdir -p "$OUT"

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
AutoTokenizer.from_pretrained("$ADP").save_pretrained("$MERGED")
shutil.copy(hf_hub_download("$BASE", "tokenizer.model"), "$MERGED/tokenizer.model")  # Gemma convert ister
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
python convert_hf_to_gguf.py "$MERGED" --outfile "$OUT/octopus-v6-f16.gguf" --outtype f16

echo "===== [5/5] Quantize -> Q4_K_M ====="
[ -f "$OUT/octopus-v6-f16.gguf" ] && rm -rf "$MERGED" ~/.cache/huggingface/hub/models--ytu-ce-cosmos*
./build/bin/llama-quantize "$OUT/octopus-v6-f16.gguf" "$OUT/octopus-v6-Q4_K_M.gguf" Q4_K_M
rm -f "$OUT/octopus-v6-f16.gguf"
ls -la "$OUT"; sha256sum "$OUT/octopus-v6-Q4_K_M.gguf"
echo "GGUF_DONE"
