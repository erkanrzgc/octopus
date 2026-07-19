# D2 — Hafıza (save/recall) araçları + SFT verisi (tasarım)

> Faz D decomposition: D1(reasoning)✅ → **D2(hafıza)** → D3(skill) → tek retrain v0.8.
> Bağımsızlık: D2 araç/veri ekler (reasoning bloğu değil) → D1'in ölçüm kapısından (reasoning
> tools'u bozuyor mu) BAĞIMSIZ; v0.8 retrain'ine reasoning sonucundan bağımsız girer.
> Bu faz PARA HARCAMAZ.

## Amaç
Octópus uzun/çok-adımlı görevlerde ve kullanıcı tercihlerinde **kalıcı hafıza** kullanabilsin:
önemli bir olguyu/tercihi/ara-sonucu KAYDET, sonra gerektiğinde GETİR. Bu, 8K context sınırına
karşı ([[octopus-dataset-expansion]] D notu) ve kişiselleştirme için kaldıraçtır.

## Kapsam kararı (dar, doğru sıra)
D2 iki parçadır ve bu spec **veri + katalog kaydını** hedefler; kalıcı store/executor'ı (inference-
zamanı çalışması) AYRI takip işine bırakır — çünkü:
- SFT DATA'nın amacı modele "ne zaman kaydet / ne zaman getir" DAVRANIŞINI öğretmek.
- Ama D1 dersi: veri, katalogda OLMAYAN araç adı içeremez (yoksa model 'bilinmeyen arac' öğrenir +
  eval geçersiz sayar). → **Önce katalog kaydı (bu spec), sonra veri (bu spec), sonra executor (takip).**

### 2 araç (arac formatı, YENİ format yok)
`build_catalog.py` `ASSISTANT_TOOLS` listesine (domain='asistan') eklenir:

| Araç | risk | params | anlam |
|---|---|---|---|
| `hafiza_kaydet` | medium | `(anahtar, deger)` | bir olguyu/tercihi anahtar altında kalıcı kaydet |
| `hafiza_getir` | low | `(anahtar,)` | daha önce kaydedilmiş değeri anahtarla getir |

- **medium/low risk** gerekçe: kaydet=durum değiştirir (medium, B1'deki write_file gibi), getir=okur (low).
- `build_catalog` çalıştırılıp `catalog_data.py` yeniden üretilir → `get_spec("hafiza_kaydet")` çalışır.

## Veri şekli (distilled/, D1 Tip B gibi çok-turlu)
Çıktı: `data/sft/distilled/octopus_distill_d2_memory.jsonl`. `dusunce` YOK (D1 ölçüm-oranını
kirletmesin — D2 araç/routing verisidir). İki tip:

- **Tip A — KAYDET+GETİR zinciri (agentic):** user tercih/olgu verir → assistant `hafiza_kaydet`
  arac → tool onay → assistant kısa teyit. Sonra (aynı veya sonraki turda) ilgili soru →
  assistant `hafiza_getir` arac → tool değer → assistant değeri KULLANARAK cevap. (~14)
- **Tip B — ANLA/negatif (comprehension):** hafıza getir BOŞ/yok dönerse → assistant hayal kurmadan
  "kayıtlı değil" der, uydurmaz (B2 dersi); ne zaman kaydetMEme (geçici/hassas veri — parola
  kaydetme) örnekleri. (~8)

Grounding/dürüstlük: getirilen değer YOKSA uydurma; kaydedileni sadık kullan.

## Doğrulama (Faz C + D1 dersleri)
- Katalog: her `hafiza_*` arac get_spec ile geçerli (yeni test `test_d2_memory_format.py`).
- Format: çok-turlu, tool rolü var, `dusunce` yok, hafiza araçları kullanılıyor + katalog-geçerli.
- Davranış: en az N örnekte getirilen değer cevapta KULLANILIYOR; M negatifte "kayıtlı değil/uydurmam".
- Pipeline: `build_sft --source distill seed_tr tools --seed-repeat 3` geçerli↑, 0 yeni dup; `pytest` yeşil.
- Teknik doğruluk: elle gözden geçir (hassas-veri-kaydetme negatifleri güvenlik-doğru olsun).

## Kapsam DIŞI (takip işleri)
- **Hafıza executor + kalıcı store** (jsonl/sqlite, workspace altında) + policy + composite yönlendirme
  — inference-zamanı çalışması; B1 assistant_executor deseni. Ayrı görev (retrain'i beklemez ama
  veri retrain'i için yeterli; executor demo/gerçek-kullanım için).
- **D3 skill katmanı** — ayrı spec.

## Bitince
D2 verisi hazır → D3 → tek retrain v0.8 (💰 para-checkpoint). Executor takip işinde.

İlgili: [[octopus-dataset-expansion]] · [[octopus-agent-harness]] · [[octopus-v08-assistant-tools]] ·
[[octopus-skill-layer-reference]].
