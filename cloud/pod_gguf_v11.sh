#!/bin/bash
# Octopus v1.0 GGUF — pod_gguf_v9'un v11 uyarlamasi. TEK quant: Q4_K_M (dagitilan quant).
# HF PUSH YOK: pod sadece Q4 uretir; yerele scp indirilir, sha dogrulanir, ollama'ya verilir.
# HF'e yukleme SADECE eval GECERSE + kullanici promote-onayindan SONRA yerelden yapilir
# (token komut-metnine asla girmesin). f16 CONTAINER-DISK'e (/root) yazilir (v8/v9 dersi).
# Onkosul: /workspace/v11-adapter (egitim ciktisi) pod'da hazir.
set -eo pipefail
BASE="ytu-ce-cosmos/Turkish-Gemma-9b-v0.1"; ADP="/workspace/v11-adapter"
MERGED="/workspace/v11-merged"; OUT="/workspace/octopus-v11-gguf"; TOKOUT="/workspace/octopus-v11-tokenizer"
mkdir -p "$OUT" "$TOKOUT"

echo "===== [1/5] MERGE (pinli env — llama.cpp deps'ten ONCE) ====="
pip install -q "transformers==4.49.0" "peft==0.14.0" "accelerate==1.4.0" "torch==2.4.1" sentencepiece protobuf 2>&1 | tail -1
python - <<PY
import torch, shutil
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from huggingface_hub import hf_hub_download
base = AutoModelForCausalLM.from_pretrained("$BASE", torch_dtype=torch.bfloat16, device_map="cpu")
m = PeftModel.from_pretrained(base, "$ADP").merge_and_unload()
try: m.generation_config.do_sample = True          # Turkish-Gemma gen_config gecersiz -> tf4.49 save patlar
except Exception: pass
m.save_pretrained("$MERGED", safe_serialization=True)
tok = AutoTokenizer.from_pretrained("$ADP"); tok.save_pretrained("$MERGED"); tok.save_pretrained("$TOKOUT")
tm = hf_hub_download("$BASE", "tokenizer.model")
shutil.copy(tm, "$MERGED/tokenizer.model"); shutil.copy(tm, "$TOKOUT/tokenizer.model")
print("MERGE_OK")
PY

echo "===== [2/5] llama.cpp (merge BITTI, env bozulabilir) ====="
pip install -q cmake 2>&1 | tail -1
cd /workspace
[ -d llama.cpp ] || git clone --depth 1 https://github.com/ggml-org/llama.cpp
cd llama.cpp
pip install -q -r requirements.txt 2>&1 | tail -1

echo "===== [3/5] build llama-quantize ====="
cmake -B build -DGGML_CUDA=OFF -DLLAMA_CURL=OFF 2>&1 | tail -1
cmake --build build --config Release -j --target llama-quantize 2>&1 | tail -2

echo "===== [4/5] HF -> GGUF f16 (container-disk /root) ====="
python convert_hf_to_gguf.py "$MERGED" --outfile /root/v11-f16.gguf --outtype f16
rm -rf "$MERGED"

echo "===== [5/5] quantize Q4_K_M ====="
./build/bin/llama-quantize /root/v11-f16.gguf "$OUT/octopus-v11-Q4_K_M.gguf" Q4_K_M
rm -f /root/v11-f16.gguf
ls -la "$OUT" "$TOKOUT"
echo "Q4 sha:"; sha256sum "$OUT/octopus-v11-Q4_K_M.gguf"
echo "GGUF10_DONE"
