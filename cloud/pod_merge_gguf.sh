#!/bin/bash
# Octopus v0.6 FAZ 4 — LoRA adapter'i tabanla merge et + GGUF Q4'e cevir (POD'da).
# Merge'li model ~18GB (ev baglantisi indiremez) -> pod'da uret, sadece ~5.5GB GGUF Q4 indir.
# Q4_K_M 9B ~5.5GB -> RTX 5060 8GB'a sigar (yerel calistirma, egitim degil).
set -e
BASE="ytu-ce-cosmos/Turkish-Gemma-9b-v0.1"
ADP="/workspace/v6-adapter"
MERGED="/workspace/octopus-v6-merged"
OUT="/workspace/octopus-v6-gguf"
mkdir -p "$OUT"

echo "===== [1/4] Merge: taban bf16 + LoRA -> tam model ====="
python - <<PY
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel
base = AutoModelForCausalLM.from_pretrained("$BASE", torch_dtype=torch.bfloat16, device_map="cpu")
model = PeftModel.from_pretrained(base, "$ADP")
model = model.merge_and_unload()
# Turkish-Gemma generation_config gecersiz (do_sample=False + temp/top_p/top_k) -> tf4.49 save'de patlar.
try:
    model.generation_config.do_sample = True
except Exception:
    pass
model.save_pretrained("$MERGED", safe_serialization=True)
AutoTokenizer.from_pretrained("$ADP").save_pretrained("$MERGED")
print("MERGE_OK")
PY

echo "===== [2/4] llama.cpp kur (convert + quantize) ====="
cd /workspace
if [ ! -d llama.cpp ]; then git clone --depth 1 https://github.com/ggml-org/llama.cpp; fi
cd llama.cpp
pip install -q -r requirements.txt 2>&1 | tail -1
cmake -B build -DGGML_CUDA=OFF > /dev/null 2>&1
cmake --build build --config Release -j --target llama-quantize > /dev/null 2>&1
echo "LLAMACPP_OK"

echo "===== [3/4] HF -> GGUF f16 ====="
python convert_hf_to_gguf.py "$MERGED" --outfile "$OUT/octopus-v6-f16.gguf" --outtype f16 2>&1 | tail -3
# Disk tasarrufu (60GB container): f16 GGUF cikinca merge'li HF modeli + HF cache gereksiz.
rm -rf "$MERGED" ~/.cache/huggingface/hub/models--ytu-ce-cosmos* 2>/dev/null || true

echo "===== [4/4] Quantize -> Q4_K_M ====="
./build/bin/llama-quantize "$OUT/octopus-v6-f16.gguf" "$OUT/octopus-v6-Q4_K_M.gguf" Q4_K_M 2>&1 | tail -3
ls -la "$OUT"
sha256sum "$OUT/octopus-v6-Q4_K_M.gguf"
echo "GGUF_DONE"
