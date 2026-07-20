# Faz D3 — Skill (metodoloji) katmanı — TASARIM

> Büyük hamle veri genişletme: A(hedef dengeleme)✅ → B(araç+asistan+araştırma)✅ →
> C(domain derinliği)✅ → D1(reasoning)✅ → D2(hafıza)✅ → **D3(skill/metodoloji)** → tek retrain (v0.8).
> Bu faz (D3 veri üretimi) PARA HARCAMAZ. Retrain (v0.8) ayrı para-checkpoint.

## Karar özeti (kullanıcı "sen karar ver" — gerekçeli tasarımcı kararı, advisor-doğrulandı)

**D3 = metodoloji ORKESTRASYONU. YENİ ARAÇ YOK, YENİ FORMAT YOK.** Model bir görevi görünce
görev-SINIFINI tanır, o sınıfın **içselleştirilmiş metodoloji iskeletini + disiplinini** uygular,
ve fazların **güncel detayını MEVCUT** `web_search`/`web_fetch`/`nmap`/… araçlarıyla çeker.

Bu karar iki turda oturdu:

1. **İlk eğilim (reddedildi): `beceri_getir` aracı** — steipete/openclaw'daki gibi bir skill-yükleme
   aracı ekle, harness playbook'u dönsün. **Neden reddedildi (advisor + kendi ilkelerimiz):**
   - Tez çelişkisi: "9B yeterli — zekâ orkestrasyonda, **bilgi inference'ta gelir**" ilkesi
     OLGULARA uygulanır. Bir **metodoloji** (keşif→enum→exploit; "önce say sonra saldır") =
     orchestration → **modelin İÇİNDE** olmalı, dışarıdan yüklenmemeli.
   - [[octopus-skill-layer-reference]] zaten "openclaw'in kendisi ajan, MODEL DEĞİL; symlink/skill-
     yükleme = harness infra, Octópus'a uygun değil" diye işaretliyordu — kendi notumuza aykırıydık.
   - En zayıf metriğimiz `in_catalog %50`; yeni araç tam bu kırılgan yüzeyi büyütür VE D1 ölçüm
     kapısını **karıştırır** (v0.8'de araç-güvenilirliği düşerse sebep reasoning mı yeni araç mı
     ayırt edilemez). Decomposition tablosu D3'ü **DÜŞÜK risk** diyor — yeni araç bunu YALAN yapar.

2. **Kanıt turu (belirleyici): cyberm4fia `core/ai_skills/*/SKILL.md`** (37 skill, D referansımız).
   Her SKILL.md iki katman: **(a) iskelet+disiplin** (frontmatter "Trigger Phrases / Use when" +
   faz sırası + "Follow steps UNLESS user specifies" + "rule-of-three", "archive early") ve
   **(b) 400+ satır gövde** (güncel araç/URL/CVE: Bluesky AT resolver, Chainalysis Horizon 2.0…).
   - Gövde **büyük + bayatlar** → 37×400 satırı 9B'ye SFT'yle içselleştirmek ne olası ne isabetli
     (eskir; "taze kal" argümanı bunu dışsal ister).
   - **Reconcile:** iskeleti İÇSELLEŞTİR (küçük, kararlı, orchestration), gövdeyi **mevcut**
     `web_fetch`/`web_search` ile ÇEK. Advisor bunu zaten öngörmüştü ("büyük doküman = web_fetch,
     yeni araç değil"). Kanıt "her şeyi içselleştir"i "iskeleti içselleştir, gövdeyi çek" diye
     keskinleştirir — **yeni araç kararını GÜÇLENDIRIR.**

**Sonuç:** D3, B(araçlar) + B3(grounding) + C(domain zincirleri) + D1(reasoning) üstünde oturan
META katmandır: *hangi metodolojiyi* uygulayacağını tanır ve mevcut yüzeyle orkestre eder.

---

## D3 ne ÖĞRETİR (5 davranış)

1. **Tanıma (recognition):** görev → görev-sınıfı + uygulanan metodoloji, TEK terse cümle.
   "Bu bir web-uygulama pentesti; standart keşif→enumerasyon→zafiyet→exploit akışını izliyorum."
   (Ayrı `dusunce` bloğu DEĞİL — düz asistan cümlesi; D1 ölçüm-oranını kirletmemek için, B3/D2 gibi.)
   "Use when…" disiplini: cümle, metodolojinin tetikleyicisiyle örtüşür, token-verimli (9B ideali).

2. **İskelet disiplini (içselleştirilmiş, KARARLI orchestration bilgisi):** model her metodolojinin
   **faz sırasını** ve **disiplin kurallarını** bilir:
   - web-pentest: whatweb/keşif → dizin/param enum → nuclei/nikto → hedefli exploit → doğrula.
   - AD/dahili: keşif → enum4linux/netexec → bloodhound-python graf → hedefli hareket.
   - OSINT/aktör: kapsam → gösterge topla → altyapı pivot → **atıfta üçlü-kural, tek-kaynağa dayanma**.
   - DFIR/triyaj: uçucu-önce toplama → zaman-çizelgesi → IOC → raporla.
   - Bu iskelet KÜÇÜK ve göreve-sınıf-geneldir → içselleştirilebilir; gövde değildir.

3. **Taze detayı MEVCUT araçlarla çek:** bir fazın GÜNCEL aracı/CVE'si/URL'si gerektiğinde model
   `web_search`/`web_fetch` (B3 grounding) veya doğrudan `arac` (nmap/gobuster/…) çağırır —
   **yeni bir skill-yükleyici DEĞİL.** İskelet "ne sırayla"yı, mevcut araçlar "şu anki nasıl"ı verir.

4. **Uyarlama (adaptation) — robotik değil:** gerçek bulgu iskeletle çelişince model SAPAR.
   SKILL.md'nin kendisi "Follow steps in order UNLESS the user specifies / consider applicability"
   diyor. Örn. keşifte hedef WAF arkasında → sıradaki adım yerine önce WAF-parmak-izi + bypass.

5. **Negatifler (aşırı-tören YOK):**
   - (a) Hiçbir metodoloji uymuyor / basit tek-atış: "nmap at" → sadece `nmap` çağır, ağır çerçeve
     dayatma. Metodoloji ancak çok-adımlı görevi hak eder.
   - (b) Aşırı-çekme: iskeletten bildiğin faz sırasını `web_search`'le arama; taze OLGU için çek.

---

## C'den FARKI (çökme riskine karşı net sınır)

| | C (domain derinliği) | D3 (skill/metodoloji) |
|---|---|---|
| Ne | Bir domain zincirini ÇALIŞTIR | *Hangi metodolojiyi* uygulayacağını TANI + orkestre et |
| Örnek | "theHarvester + amass ile alan enum yap" | "Bu bir aktör-soruşturması; aktör-merkezli iş akışı, atıfta üçlü-kural" |
| Katman | Yürütme | Meta (tanıma + disiplin + uyarlama) |
| cyberm4fia | tekil araç skill'leri | `offensive-osint-methodology` çerçevesi |

D3, C'siz anlamsız (yürütecek zincir gerek) ama C değildir: C **nasıl**ı, D3 **hangisini + hangi
disiplinle**yi öğretir.

---

## Format & pipeline (değişiklik yok — bu, LOW-risk garantisi)

- **Yeni araç YOK, yeni katalog girişi YOK.** Sadece mevcut `arac` + `web_search`/`web_fetch`.
- **Yeni format YOK:** çok-turlu `messages` (asistan_chains / B3 / D2 deseni), tool rolü çıktı besler.
- **`dusunce` YOK** — tanıma düz cümle. B3+D2 ile tutarlı; D1 reasoning-ölçüm oranını KİRLETMEZ.
- **Katalog-geçerlilik ZORUNLU:** her `arac` adı `get_spec()` ile doğrulanır (D1'in
  `bilinmeyen arac` dersi + kalıcı `test_arac_adlari_katalogda_gecerli` deseni).

## Veri şekilleri (~24–30 örnek, üç tip)

- **Tip A — tanıma→disiplinli plan→cevap (metodoloji bilgisi, ~8):** çok-adımlı bir istekte model
  görev-sınıfını adlandırır, iskelet+disiplini kısa anlatır, mevcut araçlarla ilk adımı atar.
- **Tip B — tanıma→zincir→uyarla→cevap (agentic, ~12):** çok-turlu; model iskeleti izler, tool
  çıktısı bulgu döndürünce (WAF/kapalı-port/beklenmedik sürüm) iskeletten SAPARAK sonraki aracı
  seçer. Gövde-detay gerektiğinde `web_search`/`web_fetch` (B3 grounding: iddia=çekilen içeriğe bağlı).
- **Tip C — negatifler (~6):** (a) basit tek-atış → tören yok, tek `arac`; (b) uymayan görev →
  çerçeve dayatma yok / net "bu metodoloji burada uygun değil".

### Üretim deseni (Faz C/D2 ile aynı)
scratchpad `gen_d3_skill.py` (kayıt listesi → append `data/sft/distilled/octopus_distill_d3_skill.jsonl`,
`ensure_ascii=False`) → `build_sft --source distill seed_tr tools --seed-repeat 3` → `uv run pytest`
→ **teknik doğruluk ELLE tara** (Faz C dersi: testler içeriği doğrulamaz) → commit.

### Doğrulama (yeni test `tests/data/test_d3_skill_format.py`)
- dosya var + ≥24 kayıt; `dusunce` YOK (her mesajda).
- her `arac` adı katalog-geçerli (`get_spec`).
- ≥N çok-turlu (tool rolü) zincir; ≥3 uyarlama (iskeletten sapma) örneği; ≥3 negatif (tören-yok/ret).
- tanıma cümlesi kısa (tek cümle, ~<25 kelime) — token-verimli disiplin.

---

## Risk & D1 ölçüm kapısıyla ilişki (KRİTİK)

- **Risk: DÜŞÜK** ve öyle KALIR — yeni araç/format/`dusunce` yok, sadece mevcut yüzeyin
  orkestrasyonu. Decomposition tablosu doğru kalır.
- **D1 ölçüm kapısından BAĞIMSIZ ama onu KİRLETMEZ:** D3 `dusunce` içermez → v0.8'de araç-
  güvenilirliği (in_catalog/expected_tool) düşerse suçlu reasoning'dir, D3 değil. D3 aksine araç
  orkestrasyonunu PEKİŞTİRİR (doğru araç seçimi + katalog-disiplini örnekleri → in_catalog'a olumlu
  baskı beklenir; v0.7 baseline in_catalog %50 → D3 iyileştirebilir).
- **Signal-balance:** D3 çıktısı kısa tanıma + `arac` zinciri (uzun deneme değil) → arac sinyalini
  bozmaz; B3/C ile aynı bütçe profili.

## Bitince (D-fazı kapanışı)
D3 verisi tamam → toplam distill A+B+C+D1+D2+**D3** → **tek v0.8 retrain (💰 para-checkpoint, DUR)** →
`run_toolcall_eval --model octopus-v8 --label v0.8-pilot` → ölçüm kapısı (in_catalog + expected_tool
v0.7 baseline'dan >~5 puan DÜŞMEMELİ) → sonuca göre D1 reasoning ölçekle/ertele.

İlgili: [[octopus-dataset-expansion]] · [[octopus-skill-layer-reference]] · [[octopus-cyberm4fia-repos]] ·
[[octopus-agent-harness]] · [[octopus-v08-assistant-tools]] · [[octopus-finetune-state]].
