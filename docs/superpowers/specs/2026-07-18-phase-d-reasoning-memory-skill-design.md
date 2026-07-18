# Faz D — Reasoning + Hafıza + Skill Katmanı (tasarım)

> Büyük hamle veri genişletme: A(hedef dengeleme)✅ → B(araç temeli+asistan verisi)✅ →
> C(domain derinliği)✅ → **D(reasoning + hafıza + skill)** → tek retrain (v0.8).
> Bu faz (D1 veri üretimi) PARA HARCAMAZ. Retrain (v0.8) ayrı para-checkpoint.

## Karar özeti (kullanıcı "sen karar ver" dedi — gerekçeli tasarımcı kararı)

Faz D üç ayrı alt-sistemdir ve riskleri **çok farklıdır**. Tek dev spec + tek veri üretimi +
tek retrain yerine **decompose ediyoruz**:

| Alt-faz | İçerik | Risk | Neden |
|---|---|---|---|
| **D1** | reasoning (```dusunce``` bloğu) | **YÜKSEK** | Uzun düşünce, v0.7'nin taç mücevheri araç güvenilirliğini boğabilir (BalanceSFT) |
| **D2** | hafıza (save/recall araçları) | ORTA | Mevcut `arac` formatını genişletir; harness executor desteği de gerekir (B1 gibi) |
| **D3** | skill katmanı (ne zaman/nasıl skill) | DÜŞÜK | Kanıtlanmış `arac` desenine yönlendirme/routing verisi |

**Sıra kararı: D1 (reasoning) ÖNCE — ama katı bir KÜÇÜK PİLOT olarak.**

Gerekçe: signal-balance sorusu (uzun düşünce araç sinyalini bozar mı?) bu fazın **tek en büyük
bilinmeyeni**dir ve v0.8'in şeklini belirler. Onu erken, ucuz ve küçükken yanıtlamak tüm fazı
de-riske eder. Pilot bozulma gösterirse reasoning'i **v0.9'a erteler**, v0.8'i D2+D3 (hafıza+skill)
ile göndeririz — ama **tahminle değil, ölçümle** karar veririz. Reasoning ayrıca temelsel:
hafıza ve skill kullanımı da "önce düşün, sonra araç seç" davranışından faydalanır, o yüzden
önce onu oturtmak mantıklı.

Bu belge **D1'i detaylı** tasarlar, D2/D3'ü ana hatlarıyla eskizler (ayrı spec alacaklar).

---

## D1 — Reasoning (```dusunce``` bloğu) DETAYLI TASARIM

### Amaç
Octópus, araç çağırmadan veya cevap vermeden önce **kısa, göreve-özgü** bir muhakeme adımı
üretsin: problemi çöz, hangi aracın/bilginin gerektiğine karar ver, sonra `arac` bloğu veya
nihai cevap gelsin. Bu, "agentic LLM" konumlandırmasının çekirdeği (orkestrasyon zekâsı).

### Format kararı: ```dusunce``` fenced blok (ASCII ad, `arac` ile simetrik)
Mevcut tek yapılandırılmış çıktı `arac` bloğu (`agent/toolcall.py:10`, `` ```arac {json} ``` ``).
Reasoning bloğu onunla **simetrik** olacak:

```
```dusunce
<2-5 cümle göreve-özgü muhakeme; problem çözümü, araç/bilgi seçim gerekçesi>
```
```arac
{"arac": "...", "parametreler": {...}}
```
```

Kararlar ve gerekçeleri:
- **ASCII ad `dusunce`** (`düşünce` değil) — tıpkı `arac` (`araç` değil): tokenizer sürüklenmesini
  önler, mevcut precedent'e uyar. Marka `ó`'su yalnız modelin KONUŞMASINDA; kontrol token'ında yok.
- **Fenced blok** (tag değil) — `arac` ile aynı şekil; harness aynı regex-strip mantığıyla söker.
- **Blok assistant turunun EN BAŞINDA**, `arac`/cevaptan önce gelir.
- **Harness davranışı:** `dusunce` bloğu İÇ'tir — kullanıcıya gösterilmez (aynen `arac` gibi
  strip edilir). Bu D1'in harness tarafı: `toolcall.py`'ye kardeş bir `_DUSUNCE_RE` + strip
  fonksiyonu (küçük, izole; ayrı bir harness-değişikliği plan adımı).

### İçerik ilkesi: Natural CoT > Strateji CoT (memory notu)
Düşünce **otantik problem-çözümü** olmalı, templated boilerplate DEĞİL:
- ❌ KÖTÜ (strateji/şablon): "Önce X yapacağım. Sonra Y. En son Z." — içeriksiz iskelet.
- ✅ İYİ (natural): göreve-özgü gerçek muhakeme — "Kullanıcı 445/tcp açık diyor ama sürüm yok;
  SMB sürümü EternalBlue (MS17-010) değerlendirmesi için kritik, o yüzden önce sürüm tespiti."

### Signal-balance sertleştirmesi (KRİTİK tasarım kısıtı)
Memory uyarısı: düşünce ~350 tok, arac ~31 tok → uzun düşünce araç sinyalini boğar. Karşı-önlemler:
1. **Kısa düşünce:** 2-5 cümle, ~40-90 kelime. Deneme yazısı YASAK.
2. **Her reasoning örneği yine bir KARARLA biter** — ya `arac` bloğu ya net cevap; düşünce
   aracın YERİNE geçmez, ÖNÜNE gelir. Böylece arac sinyali korunur, azalmaz.
3. **Karışım oranı:** pilot verisinde düşünce-only (bilgi) ile düşünce→arac (agentic) dengeli;
   agentic örnekler arac bloğunu her zaman içerir (sinyal sürekliliği).
4. **Pilot ölçek küçük** (~40 örnek) — mevcut 1124 distill + 661 tools içinde reasoning oranı
   düşük tutulur; amaç "reasoning'i öğret" değil "reasoning araçları bozuyor mu ÖLÇ".

### Pilot örnek şekilleri (iki tip)
- **Tip A — reasoning→cevap (bilgi):** `{"messages":[user, assistant("```dusunce...``` + cevap")]}`.
  Zor/çok-adımlı bir soruda önce muhakeme, sonra sentez. (~15 örnek)
- **Tip B — reasoning→arac→tool→reasoning→cevap (agentic):** çok-turlu, `asistan_chains` şekli.
  Her assistant turu `dusunce` ile başlar, sonra `arac`; tool çıktısı gelince yeni `dusunce`
  (sonucu yorumla) + sonraki arac veya nihai cevap. (~25 örnek)

### Çıktı & doğrulama
- **Veri dosyası:** `data/sft/distilled/octopus_distill_d1_reasoning.jsonl` (build_sft `distilled/*`
  glob'lar → otomatik dahil). Tip B çok-turlu ise → uygun kaynağa (chains) veya distill'e
  çok-mesajlı kayıt; build_sft'in çok-turluyu nasıl aldığı plan aşamasında netleşir.
- **Üretim deseni (Faz C ile aynı):** scratchpad `gen_d1_reasoning.py` (PAIRS/kayıt listesi → append),
  gen → `build_sft --source distill seed_tr tools --seed-repeat 3` → pytest → commit.
- **Yeni test:** `dusunce` bloğu format testi (fenced, arac'tan önce, kısa) + harness strip testi.
- **Teknik doğruluk:** Faz C dersi — testler içeriği doğrulamaz; riskli spesifikleri ELLE tara.

### ÖLÇÜM KAPISI (pilot'un asıl amacı — retrain SONRASI)
v0.8-pilot eğitildikten sonra, ölçekleme/D2/D3'e geçmeden ÖNCE:
- Mevcut agent harness (39 test + `parse_arac_calls`) ile **araç-çağrı güvenilirliğini** ölç:
  v0.7 vs v0.8-pilot — arac bloğu doğru üretme oranı, JSON geçerliliği, doğru araç seçimi.
- **Eşik (öneri):** araç güvenilirliğinde belirgin düşüş (>~5 puan) YOKSA → D1 ölçekle + D2 + D3.
  VARSA → signal-balance ayarla (düşünceyi kısalt / oranı düşür / loss-masking pilotu) veya
  reasoning'i v0.9'a ertele, v0.8'i D2+D3 ile gönder.
- ⚠️ Bu ölçüm bir **retrain gerektirir** (💰 para-checkpoint) — pilot ölçek tam da bunu ucuzlatmak için.

---

## D2 — Hafıza (save/recall) — ESKİZ (ayrı spec alacak)
- **Araçlar:** `hafiza_kaydet` (save) + `hafiza_getir` (recall), `arac` formatında (yeni format YOK).
- **Harness desteği:** B1'deki asistan araçları gibi bir executor + kalıcı store (jsonl/sqlite),
  policy gate. Model save/recall'ı `arac` bloğuyla çağırır; harness yürütür, sonucu geri besler.
- **Veri:** ne zaman kaydet (kullanıcı tercihi, uzun görev durumu) / ne zaman getir (önceki
  bağlamı hatırla) — hem EMIT hem ANLA örnekleri (B2 deseni).
- **Risk:** ORTA — arac sinyalini bozmaz (aynı format), ama harness işi var.

## D3 — Skill katmanı — ESKİZ (ayrı spec alacak)
- **Amaç:** modelin "bu görev için X skill'i çağırılmalı" davranışı — reuse hazinesi
  ([[octopus-skill-layer-reference]], [[octopus-cyberm4fia-repos]] core/ai_skills).
- **Veri:** görev → doğru skill/araç-zinciri routing; "Use when…" terse eşleme örnekleri.
- **Risk:** DÜŞÜK — arac desenine yönlendirme verisi.
- Referans: steipete/agent-scripts + openclaw/agent-skills, rules↔skills ayrımı.

---

## Riskler & açık noktalar
- **En büyük risk:** reasoning araç güvenilirliğini bozar → pilot+ölçüm kapısı tam bunun için.
- **build_sft çok-turlu:** Tip B'nin build_sft'e nasıl girdiği (chains kaynağı mı, distill mi)
  plan aşamasında netleşecek; mevcut `asistan_chains` pipeline'ı referans.
- **Harness strip:** `dusunce` bloğunu kullanıcıdan gizleme — küçük ama gerekli harness değişikliği.
- **Loss-masking bağlantısı:** signal-balance kötüyse, ayrı tutulan "loss masking" işi (memory)
  burada devreye girebilir — ama önce en basit çare (kısa düşünce + düşük oran) denenecek.

## Bitince
D1 pilot verisi → v0.8-pilot retrain (💰) → ölçüm kapısı → sonuca göre D1 ölçekle veya ertele →
D2 spec+veri → D3 spec+veri → nihai v0.8 retrain (💰).

İlgili: [[octopus-dataset-expansion]] · [[octopus-agent-harness]] · [[octopus-finetune-state]] ·
[[octopus-skill-layer-reference]] · [[octopus-v08-assistant-tools]].
