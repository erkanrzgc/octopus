# ADR 0002 — From-scratch'ten fine-tuning'e dönüş + taban model kararı

- **Tarih:** 2026-07-03
- **Durum:** **Kısmen superseded.** "Fine-tuning'e dönüş" kararı GEÇERLİ. Ama **taban modeli ve kuantizasyon
  yöntemi değişti** → [ADR 0003](0003-pivot-to-turkish-gemma-bf16.md): taban `Qwen3-8B` → `Turkish-Gemma-9b-v0.1`,
  yöntem `QLoRA (Unsloth 4-bit)` → `bf16 LoRA (düz transformers)`. (Qwen3-8B QLoRA yalnız v0.1/v0.2'de kullanıldı;
  v0.6+ Turkish-Gemma bf16.) Aşağıdaki "Qwen3-8B / QLoRA / Unsloth" ifadeleri bu yüzden TARİHSEL — güncel yol için ADR 0003'e bak.
- **Yerini aldığı:** [ADR 0001](0001-from-scratch-turkish-first.md) (from-scratch pretraining) — **superseded**
- **Dizin:** `C:\Users\erkanrzgc\Desktop\Octopus` (ASCII)

## Bağlam

ADR 0001 ile Octópus **sıfırdan** eğitiliyordu: kendi Türkçe tokenizer (`octopus-tr`, fertility 1.735 vs
Qwen 2.674, -%35) + nanoGPT-tarzı Llama + pretraining. Faz 1-4 yerelde uçtan uca ayağa kalktı (100M model,
E2E smoke yeşil). Ama **ölçek turu maliyeti** somutlaştı:

- From-scratch = **tüm** parametreleri milyarlarca token'da eğitmek. Chinchilla ~20 tok/param → 0.5B için
  ~15B token; FLOP = 6 × param × token. RunPod'da gerçek tur **~$60-150+** ve saatler/günler.
- Fine-tuning (QLoRA) = tabanın ~%0.1-1'ini (LoRA adaptörleri) ~10-50M token'da eğitmek → **birkaç saat,
  ~$3-15**. 100-1000× daha ucuz compute.

Sahip, maliyet gerçeği netleşince **fine-tuning'e dönmeyi** seçti. Vurgu: **"fine-tune edeceğimiz modeli
çok iyi seçmeliyiz."**

## Karar

1. **Strateji = fine-tuning (QLoRA + Unsloth).** From-scratch pretraining bırakıldı (artefaktlar arşivde).
2. **Birincil taban = `Qwen3-8B`** (QLoRA için `unsloth/Qwen3-8B` bnb-4bit).
   > NOT: 8B'nin "-Instruct-2507" sürümü YOK — Qwen3-2507 güncellemesi yalnız 4B/30B-A3B/235B çıktı.
   > 8B = orijinal `Qwen3-8B` (hibrit thinking). Duman turu 4B'de `Qwen3-4B-Instruct-2507` kullandı (o var).
   - Türkçe-native (100+ dil), Apache 2.0, en olgun fine-tune ekosistemi, 256K context.
   - Yerel-önce sweet spot: Q4 ~5GB (RTX 5060 8GB'de uçar), QLoRA ~12GB VRAM (RunPod ~$3-8).
3. **Yükseltme yolu = `Qwen3-14B`** (pipeline oturunca; Q4 ~8.5GB yerel/offload, QLoRA ~$8-15).
4. **Opsiyonel öğretmen = `fdtn-ai/Foundation-Sec-8B-Reasoning`** — İngilizce siber-reasoning derinliğini
   Türkçe SFT verisine damıtmak için (agentic-model `distill_teacher_tr.py` reuse).

## Gerekçe (kanıta dayalı)

- **Kural: DİL tabanda olmalı, BİLGİ sonradan eklenir.** Türkçe akıcılığı LoRA ile bir İngilizce-only tabana
  (Foundation-Sec) enjekte etmek çok zor; siber bilgiyi Qwen3'e QLoRA ile eklemek ise **kanıtlı**:
  - `DexopT/Qwen3-4B-Cybersecurity` — Qwen3-4B-Instruct-2507, 1.28M siber örnek (red+blue+network+AD+
    malware+web), Unsloth SFT r16, bir Colab T4'te; GGUF'u var.
  - `CyberSecQwen-4B` — Qwen3-4B, CTI-MCQ'da Foundation-Sec-Instruct-8B'yi yarı parametreyle geçiyor.
- **Çalışan atadan kanıt:** kardeş `cyberm4fiaModel` — Qwen2.5-3B + Unsloth QLoRA + Fenrir v2.1, r=32 →
  train loss 0.77 / ppl 2.39. Aynı aile/desen Qwen3'e taşınır.

## Sonuçlar (dürüst)

- **Tokenizer bedeli:** fine-tuning Qwen tokenizer'ını miras alır → `octopus-tr`'nin -%35 fertility zaferi
  bu yolda **kullanılmaz** (Qwen Türkçede ~%35 daha çok token = biraz daha pahalı ama tamamen kullanılır).
  From-scratch artefaktları (`tokenizer/octopus-tr.*`, `checkpoints_web/`) **silinmez, arşivlenir.**
- **Kazanç:** çok daha ucuz/hızlı, çok daha yüksek yetenek tavanı (8B taban >> 100M from-scratch), Türkçe +
  siber ikisi de kanıtlı yolla erişilebilir.
- **Cisco 2026 uyarısı:** siber fine-tuning "representation drift"/kırılganlık yaratabilir → eval'de
  obfuscation-varyantı red-team şart (bkz. `octopus-eval` skill).

## Açık knoblar (kanıtla güncellenecek)

- Taban boyutu: 8B (başlangıç) → 14B (yükseltme). MoE (Qwen3-30B-A3B) sonra değerlendirilebilir.
- LoRA r / seq / lr / epoch — cyberm4fia başlangıcı (r=32, seq 1024, lr 2e-4) ile başla, ölçerek ayarla.
- SFT veri karışımı: Fenrir + secdata + AlicanKiraz CVE + Türkçe persona/sunucu; distillation opsiyonel.
- Deploy: GGUF Q4 → yerel (Ollama/llama.cpp); bulut sonra.

## İlgili

- [ADR 0001](0001-from-scratch-turkish-first.md) — superseded (from-scratch dönemi).
- `Desktop\cyberm4fiaModel` — çalışan referans pipeline (Qwen2.5 QLoRA + Fenrir + RAG + agent).
- `Desktop\agentic-model` — Qwen QLoRA + agent runtime + `distill_teacher_tr.py`.
