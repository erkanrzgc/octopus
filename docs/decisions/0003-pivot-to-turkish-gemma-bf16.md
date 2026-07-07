# ADR 0003 — Taban Qwen3-8B → Turkish-Gemma-9b, yöntem QLoRA → bf16 LoRA

- **Tarih:** 2026-07-05
- **Durum:** Kabul edildi ve **uygulandı** (v0.6 + v0.7 bu yolla eğitildi)
- **Yerini aldığı:** [ADR 0002](0002-pivot-to-finetuning.md)'nin taban+yöntem seçimi — **superseded**
  (ADR 0002'nin "fine-tuning'e dönüş" kararı GEÇERLİ; yalnız taban modeli ve kuantizasyon yöntemi değişti)
- **Dizin:** `C:\Users\erkanrzgc\Desktop\Octopus` (ASCII)

## Bağlam

ADR 0002 tabanı **Qwen3-8B** + **QLoRA (Unsloth, 4-bit NF4)** seçmişti. Bu yolla v0.1 ve v0.2 gerçekten
eğitildi (RunPod, loss ~0.80). Ama iki kalıcı sorun çıktı:

1. **Türkçe akıcılık yetersiz + persona pürüzleri.** Qwen3-8B çok-dilli ama Türkçe-native değil → üretimde
   "Octópüs"/"Sevimsel" gibi yazım/kelime pürüzleri, kimlik tekrar-döngüsü, `<think>` token sızıntısı.
   "Namık Kemal gibi Türkçe" hedefi (dil #1 önceliği) tutmadı.
2. **Dil tabanda olmalı kuralı** (ADR 0002) mantıken Türkçe-**native** bir taban gerektiriyordu.

Türkçe-uzman taban arayışı → **`ytu-ce-cosmos/Turkish-Gemma-9b-v0.1`** (Gemma-2 mimarisi, Türkçe
continual-pretrain + SFT + DPO + merge). Ama bunu QLoRA ile eğitince üretim **çok-dilli çöp** çıktı.

### Kök sebep (kanıtlanmış, 2026-07-05)

Pod'da düz `transformers` ile `scratchpad/bf16_test.py`: Turkish-Gemma-9b **`bf16`'da KUSURSUZ Türkçe**
üretiyor (akıcı persona + hatasız SQLi anlatımı). Çöp **tamamen** Unsloth'un **4-bit NF4** kuantizasyonundan
geliyordu. **Neden:** Turkish-Gemma continual-pt + SFT + DPO + **merge** geçmişi taşır; NF4 bu merge'li
ağırlıkları bozar. (Qwen temiz kuantalanıyordu — bu yüzden v0.1/v0.2 çalıştı; bug taban-özel, Unsloth-genel değil.)

## Karar

1. **Taban = `ytu-ce-cosmos/Turkish-Gemma-9b-v0.1`** (Türkçe-native, Gemma-2). Qwen3-8B bırakıldı.
2. **Yöntem = bf16 LoRA** (kuantizasyon YOK). Düz `transformers` (`torch_dtype=bfloat16`, `load_in_4bit=False`)
   + `peft` `LoraConfig` + TRL `SFTTrainer`. **Unsloth kullanılmıyor** (4-bit'i bu tabanı bozuyor).
3. **Donanım = RunPod RTX 4090 24GB.** Turkish-Gemma bf16 ≈18GB + grad-checkpointing + seq 1024 + batch1/
   accum8 ≈ 21-23GB → sığar (sınırda). Yerel RTX 5060 8GB eğitim İÇİN yetmez (yalnız GGUF inference).
4. **Hiperparametre** (cyberm4fia'dan miras, değişmedi): r=32, α=32, target 7 modül (q/k/v/o/gate/up/down),
   seq 1024, lr 2e-4, ~900 adım/~3 epoch. Sürüm pini (torch 2.4 uyumu): transformers 4.49 / trl 0.15.2 /
   peft 0.14 / accelerate 1.4.

## Sonuçlar

- **v0.6** (Türkçe-only, 918 distill + seed): son loss **0.22**, token doğruluğu %97. Akıcı/edebî Türkçe,
  Qwen pürüzleri YOK. HF `erkanrzgcc/octopus-gemma-v0.6`.
- **v0.7** (+siber bilgi 1029 Q&A + 117-araç tool-use): son loss **0.048**, %98.7. HF `erkanrzgcc/octopus-gemma-v0.7`.
- **Script:** `train/sft_bf16.py` (kanonik). Eski Unsloth/Qwen yolu `train/sft_smoke.py`'de arşiv olarak duruyor.

## Bilinen tuzaklar (gelecek turlar)

- **`--max-train 0` (tam ~2279 veri) → deterministik NaN** (grad nan, step 5). `--max-train 2000` (alt küme)
  → temiz. Veri-bağımsız (v0.6 reçetesi bile 0'da patladı). Şüpheli: dataset-size/collator sayısal etkileşim.
  Workaround = max-train 2000. Kök-sebep araştırması v0.7.1'e ertelendi. Detay: `docs/v0.7-loop-queue.md`.
- **Gemma-2 chat template `tool` rolünü desteklemez** → `data/sft/normalize.py::flatten_tool_messages` `tool`→
  `user` ("ARAÇ ÇIKTISI:" önekiyle) çevirir, user/model alternasyonu korunur.
- **Çift-BOS:** Gemma template literal `<bos>` basar, TRL yeniden ekler → `_to_text`'te baştaki bos sıyrılır.

## İlgili

- [ADR 0002](0002-pivot-to-finetuning.md) — fine-tuning'e dönüş (geçerli); taban/yöntem seçimi bu ADR'ce güncellendi.
- [ADR 0001](0001-from-scratch-turkish-first.md) — from-scratch (superseded by 0002).
- `train/sft_bf16.py` · `docs/v0.7-loop-queue.md` · `README.md`.
