# ADR 0001 — Sıfırdan model + Türkçe-önce tokenizer

- **Tarih:** 2026-06-19
- **Durum:** ⛔ SUPERSEDED (2026-07-03) → yerini [ADR 0002](0002-pivot-to-finetuning.md) aldı (fine-tuning'e dönüş).
  Bu belge **tarihsel kayıt**tır; güncel strateji için 0002'ye bak. From-scratch artefaktları arşivde korunuyor.
- **Dizin:** `C:\Users\erkanrzgc\Desktop\Octópus` (yeni, temiz başlangıç)

## Bağlam

Önceki proje (`agentic-model`, GitHub `erkanrzgc/octopus-v0`) octopus'u **Qwen2.5 + QLoRA** ile
kuruyordu ve ~%80 olgundu: agent runtime (Track B), yetki kapısı, Obsidian hafıza, dil-önce
müfredat, 7B pod turu. O yolda iki şey **kanıtlanmıştı**:

1. Türkçe garbling'in sebebi **tokenizer değil** — `octopus-tr-base` ile orijinal Qwen tokenization
   birebir aynıydı; suçlu Faz2'nin yüksek lr'ı (1e-4 → catastrophic forgetting).
2. **QLoRA tokenizer'ı eğitemez** (tabanı + embedding'i dondurur) — bu yüzden orada "tokenizer'a
   dokunma" kararı verilmişti.

Sahip; ürün **sahipliği**, **öğrenme** ve **gerçek kendi tokenizer**'ı için QLoRA yolunu bırakıp
**sıfırdan** bir model eğitmeyi seçti. Kanıtlı itiraz sunuldu, karar bilinçli verildi.

## Karar

1. octopus **sıfırdan pretraining** ile eğitilecek (random init; Qwen tabanı yok).
2. **Türkçe-önce.** İlk ve en yüksek öncelik: **Türkçe'ye özel tokenizer.**
3. Tokenizer = **SentencePiece Unigram**, vocab ~32k, **diakritik-korur** (NFKC, casefold YOK →
   Türkçe-i bozulmaz), `byte_fallback`, `split_digits` (port/IP tutarlı). Hedef: Qwen2.5
   tokenizer'ının Türkçe **fertility**'sinin altına inmek — *önce ölç, sonra iddia et.*
4. Model = modern **Llama-style decoder** (RoPE · RMSNorm · SwiGLU · GQA · tied embeddings).
5. **Ölçek merdiveni:** yerel 8GB'de küçük başla (~100–160M), reçete kanıtlanınca RunPod'da büyüt
   (0.5–1B). "Önce küçükte kanıtla" — QLoRA döneminden taşınan ders.
6. Agentic harness (`agentic-model` Track B) **modelden bağımsız** → sonra **port** edilecek,
   yeniden yazılmayacak.

## Gerekçe

- Sıfırdan dünyada **kendi tokenizer doğru ilk adımdır** (artık QLoRA kısıtı yok; karar tutarlı).
- Türkçe sondan eklemeli → Unigram + morfoloji-dostu vocab = düşük fertility = daha verimli model
  (aynı context'te daha çok bilgi, daha hızlı eğitim).
- Sahiplik: model bütünüyle senin — taban dahil.

## Sonuçlar (dürüst)

- **Yetenek tavanı:** bu ölçekte from-scratch model, ham bilgi/akıcılıkta Qwen seviyesinde olmaz;
  onu **veri kalitesi + tokenizer + SFT** taşır. Siber derinlik için çok veri ya da distillation gerekir.
- **Veri-yoğun:** pretraining milyarlarca token temiz Türkçe ister → korpus toplama/temizleme ANA iş.
- **Zaman/compute:** yerel 8GB ile küçük; ciddi tur kiralık RunPod GPU ile.

## Açık knoblar (kolay değişir — kanıtla güncellenecek)

- Korpus kaynakları (Wikipedia-tr başlangıç; sonra OSCAR/mC4-tr, kitap, kod, siber-tr metinleri).
- `vocab_size` (16k / 32k / 48k — model ölçeğine bağlı; küçük modelde küçük vocab embedding'i ucuzlatır).
- İlk model param sayısı + context uzunluğu.
- Çok-dilli sıra: **TR → EN → ES → FR → DE → ZH** (EN yakın gelecek; gerisi uzak hedef).

## İlgili

- `agentic-model/OCTOPUS.md` — önceki north-star (Qwen+QLoRA dönemi).
- `agentic-model/SOUL.md` — persona/anayasa (buraya port edilecek).
