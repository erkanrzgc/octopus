#!/bin/bash
# Octopus v0.7 bf16 SMOKE — Turkish-Gemma + bf16 LoRA + TOOL-USE (unsloth 4bit YOK).
# Amac (v0.6'dan fark): tool-use (```arac``` blok) + tool-rolu render (flatten_tool_messages)
# pod'da SAGLAM mi + loss dusuyor mu? UCUZ: sadece YEREL veri. 40 adim (~$0.40).
set -e
cd /workspace/octopus-v7

echo "===== [1/5] Bagimliliklar (unsloth YOK — torch-2.4 uyumlu SABIT surumler) ====="
# En yeni TRL torch 2.5+ ister (DTensor) -> torch-2.4 pod imajinda patlar. Sabit cifte cak.
pip install -q "transformers==4.49.0" "trl==0.15.2" "peft==0.14.0" "accelerate==1.4.0" datasets bitsandbytes 2>&1 | tail -3
export PYTHONUNBUFFERED=1

echo "===== [2/5] Veri: distill(1029) + seed_tr(143) + tools(125), upsample x5 ====="
python data/sft/seed_tr/build_seed.py || true
python data/sft/seed_tr/build_cyber_seed.py || true
# tools_dist zaten transfer edildi; guvenlik icin build_tools.py'yi tekrar kosarak dogrula
python data/sft/tools/build_tools.py 2>&1 | tail -3 || true
python -m data.sft.build_sft --source distill seed_tr tools --seed-repeat 5
echo "--- train.jsonl satir ---"; wc -l data/sft/train.jsonl

echo "===== [3/5] TOOL-ROLU RENDER SAGLAMASI (egitimden ONCE, ucuz kontrol) ====="
# Gemma-2 'tool' rolunu tanimaz; flatten_tool_messages tool->user cevirir.
# Bir tool-use ornegini gercek tokenizer'la render edip HATA vermedigini + icerigin korundugunu dogrula.
python - <<'PY'
import sys; sys.path.insert(0,'.')
from transformers import AutoTokenizer
from data.sft.normalize import flatten_tool_messages
import json
tok=AutoTokenizer.from_pretrained('ytu-ce-cosmos/Turkish-Gemma-9b-v0.1')
ex=next(json.loads(l) for l in open('data/sft/tools_dist/octopus_tools_tr.jsonl',encoding='utf-8')
        if 'tool' in [m['role'] for m in json.loads(l)['messages']])
flat=flatten_tool_messages(ex['messages'])
assert 'tool' not in [m['role'] for m in flat], 'tool rolu kalmis!'
r=tok.apply_chat_template(flat, tokenize=False)
assert 'ARAÇ ÇIKTISI' in r, 'arac ciktisi oneki kayip!'
print('[OK] tool-use render SAGLAM (tool->user, icerik korundu, hata yok)')
PY

echo "===== [4/5] SMOKE bf16 LoRA: Turkish-Gemma, 40 adim ====="
python train/sft_bf16.py --base ytu-ce-cosmos/Turkish-Gemma-9b-v0.1 \
  --lr 2e-4 --max-steps 40 --max-train 2000 --out /workspace/v7-adapter-smoke

echo "===== [5/5] SMOKE_DONE — kabul: loss dustu + AKICI Turkce + arac-cagrisi format + OOM yok ====="
