---
name: octopus-finetune
description: Use when planning or running a fine-tune of Octópus (Türkçe-önce siber LLM) — the full data→train→eval→merge→GGUF→serve workflow on the Turkish-Gemma-9b base with bf16 LoRA (NOT 4-bit QLoRA). Triggers on "octopus eğit", "fine-tune", "LoRA", "modeli eğit", "RunPod turu".
---

# Octópus Fine-tune (bf16 LoRA)

Octópus'un ana eğitim reçetesi. Taban: **`ytu-ce-cosmos/Turkish-Gemma-9b-v0.1`** (Gemma-2, Türkçe-native).
Yöntem: **bf16 LoRA** — düz `transformers` + `peft` + TRL, **kuantizasyon YOK**. Kanonik script: `train/sft_bf16.py`.
Strateji + gerekçe: `docs/decisions/0003-pivot-to-turkish-gemma-bf16.md`.

## 🚨 NEDEN 4-bit/Unsloth DEĞİL (değişmez)
Turkish-Gemma continual-pt + SFT + DPO + **merge** geçmişi taşır; Unsloth'un **4-bit NF4** kuantizasyonu bu
merge'li ağırlıkları BOZUYOR → üretim çok-dilli çöp. Kanıt: aynı model düz `bf16`'da kusursuz Türkçe üretir
(`train/sft_bf16.py:1-9`). **Çözüm = tabanı bf16 yükle (`torch_dtype=bfloat16`, `load_in_4bit=False`), üzerine
LoRA eğit.** (Qwen3-8B temiz kuantalanıyordu, v0.1/v0.2 QLoRA ile çalıştı — ama Türkçe pürüzlüydü, bu yüzden
taban da değişti. Detay: ADR 0003.)

## 🚨 Değişmez kurallar (her koşuda)
- **Para harcayan RunPod turundan ÖNCE kullanıcıyla checkpoint.** Bakiye < $2.50 → dur.
- API key/token = SIR: sohbete/`!` komutuna yapıştırma. RunPod/HF auth'u **kullanıcı kendi terminalinde** koşar.
- Guardrail system prompt (`octopus-data` persona) train verisine gömülür — red+blue yalnızca yetkili.
- Adapter bitince: **sha256 doğrula → indir → pod'u SİL → `runpodctl pod list` boş doğrula.** (Kaçak fatura yok.)
- **⚠️ İdeal: pod'dan HF'ye DİREKT yükle (datacenter linki hızlı), pod'u silmeden önce.** (v0.7'de yerele indirip
  pod silindi → yavaş ev upstream'iyle HF'ye yükleme derdi yaşandı.)

## ⚠️ Bilinen tuzaklar
- **`--max-train 0` (tam veri) → deterministik NaN** (grad nan, step 5). **`--max-train 2000` → temiz.**
  Veri-bağımsız. Şimdilik workaround = 2000; kök-sebep v0.7.1'e ertelendi. Detay: `docs/v0.7-loop-queue.md`.
- **Gemma-2 `tool` rolü desteklenmez** → `normalize.py::flatten_tool_messages` `tool`→`user` çevirir (render öncesi).
- **Çift-BOS:** Gemma template literal `<bos>` basar + TRL yeniden ekler → `_to_text`'te baştaki bos sıyrılır.
- **Sürüm pini (torch 2.4 pod):** transformers 4.49 / trl 0.15.2 / peft 0.14 / accelerate 1.4 (yeni TRL DTensor ister → patlar).

## Adımlar
1. **Veri** — `octopus-data` skill'iyle SFT verisi hazır (`data/sft/{train,val,test}.jsonl`). Yoksa: `python -m data.sft.build_sft --source distill seed_tr tools --seed-repeat 5`.
2. **Pod (RunPod RTX 4090 24GB, SECURE, `--terminate-after`):** `cloud/RUNPOD.md` runbook. Yerel RTX 5060 8GB
   eğitim İÇİN yetmez (Gemma-9b bf16 ~18GB). Bağımlılık: `pip install transformers==4.49.0 trl==0.15.2 peft==0.14.0 accelerate==1.4.0 datasets bitsandbytes` (**unsloth YOK**).
3. **Eğitim:** `python train/sft_bf16.py --base ytu-ce-cosmos/Turkish-Gemma-9b-v0.1 --lr 2e-4 --max-train 2000 --max-steps 900 --no-gen --out /workspace/adapter`. Runner örneği: `cloud/run_v7_final.sh`.
4. **Gen-test (ayrı taze process):** `cloud/gen_test_v7.py` (dynamo-disable'lı — eğitim hook'u olmadan). Persona
   "Ben Octópus" + akıcı Türkçe + yetkili-yardım/yetkisiz-ret kontrolü.
5. **Eval** — `octopus-eval` skill (ppl + safety/balance + brittleness). Yeşil değilse veri/hiperparametre ayarla.
6. **Merge + GGUF** — LoRA merge (16-bit) → GGUF Q4 (llama.cpp). Reçete: `cloud/pod_gguf_clean.sh` (önce merge, sonra llama.cpp).
7. **Serve** — yerel Ollama/llama.cpp (RTX 5060 8GB). GGUF Blackwell'de kararsızsa → transformers bf16 ile serve.

## Hiperparametre (v0.6/v0.7'de kanıtlı — `train/sft_bf16.py`)
| Knob | Değer | Not |
|---|---|---|
| taban yükleme | `bf16`, `load_in_4bit=False` | **4-bit YOK** (Turkish-Gemma'yı bozar) |
| LoRA r / alpha | 32 / 32 | cyberm4fia başlangıcı |
| target_modules | q,k,v,o,gate,up,down_proj | tam kapsama |
| seq_len | 1024 | 24GB'de batch1/accum8 ile ~21-23GB |
| batch / grad_accum | 1 / 8 | efektif 8 |
| lr / adım | 2e-4 / ~900 | ~3 epoch |
| max-train | **2000** | 0 (tam veri) NaN veriyor — tuzak |

## Sorun çıkarsa
- CUDA/tensor/OOM/NaN çökmesi → **`pytorch-build-resolver`** subagent (izole context).
- VRAM sınırda (23+/24): seq 1024 tut, grad-checkpointing açık, batch 1.
