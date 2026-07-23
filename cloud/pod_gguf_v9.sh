#!/bin/bash
# Octopus v0.9 GGUF — pod_gguf_v81'in v9 uyarlamasi. IKI quant: Q4_K_M + Q8_0 (niceleme eksenini
# eval'de olcmek icin). f16 CONTAINER-DISK'e (/root) yazilir (v8 dersi). Adapter zaten pod'da:
# /workspace/v9-adapter (egitim ciktisi). Sonunda GGUF'lar + tokenizer HF'e yuklenir.
set -eo pipefail
BASE="ytu-ce-cosmos/Turkish-Gemma-9b-v0.1"; ADP="/workspace/v9-adapter"
MERGED="/workspace/v9-merged"; OUT="/workspace/octopus-v9-gguf"; TOKOUT="/workspace/octopus-v9-tokenizer"
REPO="erkanrzgcc/octopus-gemma-v0.9"
mkdir -p "$OUT" "$TOKOUT"

echo "===== [1/6] MERGE ====="
pip install -q "transformers==4.49.0" "peft==0.14.0" "accelerate==1.4.0" "torch==2.4.1" sentencepiece protobuf 2>&1 | tail -1
python - <<PY
import torch, shutil
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
from huggingface_hub import hf_hub_download
base = AutoModelForCausalLM.from_pretrained("$BASE", torch_dtype=torch.bfloat16, device_map="cpu")
m = PeftModel.from_pretrained(base, "$ADP").merge_and_unload()
try: m.generation_config.do_sample = True
except Exception: pass
m.save_pretrained("$MERGED", safe_serialization=True)
tok = AutoTokenizer.from_pretrained("$ADP"); tok.save_pretrained("$MERGED"); tok.save_pretrained("$TOKOUT")
tm = hf_hub_download("$BASE", "tokenizer.model")
shutil.copy(tm, "$MERGED/tokenizer.model"); shutil.copy(tm, "$TOKOUT/tokenizer.model")
print("MERGE_OK")
PY

echo "===== [2/6] llama.cpp ====="
pip install -q cmake 2>&1 | tail -1
cd /workspace
[ -d llama.cpp ] || git clone --depth 1 https://github.com/ggml-org/llama.cpp
cd llama.cpp
pip install -q -r requirements.txt 2>&1 | tail -1

echo "===== [3/6] build ====="
cmake -B build -DGGML_CUDA=OFF -DLLAMA_CURL=OFF 2>&1 | tail -1
cmake --build build --config Release -j --target llama-quantize 2>&1 | tail -2

echo "===== [4/6] f16 (container-disk /root) ====="
python convert_hf_to_gguf.py "$MERGED" --outfile /root/v9-f16.gguf --outtype f16
rm -rf "$MERGED"

echo "===== [5/6] quantize Q4_K_M + Q8_0 ====="
./build/bin/llama-quantize /root/v9-f16.gguf "$OUT/octopus-v9-Q4_K_M.gguf" Q4_K_M
./build/bin/llama-quantize /root/v9-f16.gguf "$OUT/octopus-v9-Q8_0.gguf" Q8_0
rm -f /root/v9-f16.gguf
ls -la "$OUT" "$TOKOUT"
echo "Q4 sha:"; sha256sum "$OUT/octopus-v9-Q4_K_M.gguf"
echo "Q8 sha:"; sha256sum "$OUT/octopus-v9-Q8_0.gguf"

echo "===== [6/6] HF upload ====="
python - <<PY
from huggingface_hub import HfApi
api=HfApi()
for f in ["octopus-v9-Q4_K_M.gguf","octopus-v9-Q8_0.gguf"]:
    api.upload_file(path_or_fileobj=f"$OUT/{f}", path_in_repo=f, repo_id="$REPO",
                    commit_message=f"v0.9 GGUF {f}")
api.upload_folder(folder_path="$TOKOUT", path_in_repo="tokenizer-v9", repo_id="$REPO",
                  commit_message="v0.9 tokenizer")
print("GGUF_HF_OK")
PY
echo "GGUF9_DONE"
