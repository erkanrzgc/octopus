# B2 — Asistan Araç SFT Verisi (EMIT + ANLA) — Tasarım

**Tarih:** 2026-07-11
**Durum:** Onaylandı (kullanıcı), plan aşamasına hazır
**Bağlam:** [[octopus-dataset-expansion]] büyük-hamle B dalgası. B1 (asistan araçları + fail-closed
güvenlik) bitti+merge. Bu spec **B2 = bu araçları modele öğreten SFT verisi**. Tek büyük retrain'e gider.

---

## 1. Problem / Neden

B1'de 8 asistan aracını (`asistan` domain) harness'a ekledik: `read_file, list_dir, grep,
write_file, edit_file, run_cmd, web_fetch, web_search`. Ama **model bu araçları çağırmayı
bilmiyor** — v0.7 SFT verisinde asistan aracı yok (`build_catalog.ASSISTANT_TOOLS` explicit
tanımlı çünkü eğitimde geçmiyor). B2 bu boşluğu kapatır.

Kritik: bu **iki ayrı yetenek**, tek örnekte:

- **Sütun 1 — Çağırma (emit):** model doğru ```arac``` blogunu doğru parametrelerle üretsin.
- **Sütun 2 — Anlama (comprehend):** `tool` rolüyle dönen içeriği (dosya, komut çıktısı, CVE
  metni) **uydurmadan, spesifik bulguya atıfla** yorumlasın ve doğru sonraki adımı çıkarsın.

Kullanıcının vurgusu Sütun 2'de ("okuduğunu anlama olayı çok iyi geliştirmeliyiz"). Şu anki
zayıf halka bu: model çıktıyı okumadan pattern ezberleyebilir ("nmap gördüm → nikto derim").
B2 örnekleri anlamayı zorlar.

## 2. Bağlam kararı

**Siber/sysadmin ağırlıklı** (kullanıcı onayı). Asistan araçları pentest/sunucu iş akışında geçer;
saf-dev örnekler yalnızca denge için azınlıkta. Octópus kimliğiyle tutarlı.

## 3. Kapsam-dışı (YAGNI)

- Deep-research döngüsü (ara→oku→sentezle→tekrar) = **B3**, ayrı.
- Harness Claude-Code-tarzı gösterim = **B4**, ayrı ([[octopus-harness-tool-display]]).
- Gerçek Docker/WSL sandbox veya canlı web_search backend = B1'de default mock; B2 sadece VERİ.
- Loss-masking / signal-balance = ayrı eğitim-config işi (retrain öncesi pilot).

## 4. Veri formatı (mevcut şema — DEĞİŞMEZ)

`data/sft/tools/*.jsonl`, her satır bir `{"messages":[...]}`. `build_tools._valid` kuralları:
`messages>=3`, `roles[0]=="system"`, assistant metninde en az bir ```arac``` bloğu **VEYA** ret
("yapmam"). Blok formatı: ```arac\n{"arac":"<ad>","parametreler":{...}}\n```. Çıktı `tool`
rolüyle döner, son assistant Türkçe yorumlar. (Örnek: `hostname_tr.jsonl`, `chains_tr.jsonl`.)

Sistem promptu B1 asistan sistem promptuyla hizalı: "Sen Octópus'sun: yetkili siber güvenlik
asistanı. Araçları ```arac``` bloğuyla çağırır, `tool` çıktısını Türkçe yorumlarsın."

## 5. Araçlar + parametreler (B1 kataloğuyla birebir)

| arac | parametreler | risk |
|------|-------------|------|
| read_file | yol | low |
| list_dir | yol | low |
| grep | desen, yol | low |
| write_file | yol, icerik | medium |
| edit_file | yol, eski, yeni | medium |
| run_cmd | komut | high |
| web_fetch | url | low |
| web_search | sorgu | low |

Parametre adları **tam bunlar** olmalı (catalog + guard'lar bunları bekler; yol→fs.guard,
url→web.guard, komut→cmd.guard).

## 6. Örnek kategorileri (iki sütun)

**A. Emit (tekli, çeşitlilik) — template-üretilebilir (~180):**
Kullanıcı ister → model doğru arac blogu → kısa çıktı → kısa doğru yorum. Yol/URL/sorgu
çeşitliliği bakımından geniş. Amaç: 8 aracın şemasını + parametre yüzeyini + hedef çeşitliliğini
öğretmek. Her araç için dengeli.

**B. Anlama (comprehend) — ELLE (~70):** yüksek sinyal, template'lenemez:
- **Tek anormal satır:** uzun log/çıktı içinden (auditd/ss/grep çıktısı) tek kritik satırı seçme.
- **Negatif/boş:** tool çıktısı boş/başarısız → model "bulunamadı/erişilemedi" der, HAYAL KURMAZ.
- **CVE okuma:** web_fetch/web_search gerçekçi CVE metni (siberadar/watchstack tarzı) → model
  etkilenen sürümü + POC/exploit varlığını doğru çıkarır. Bkz. [[octopus-cve-sources]].
- **Çok-kaynak sentez:** 2 web_search sonucu → tek tutarlı Türkçe cevap.

**C. Zincir (çok-adımlı) — ELLE (~35):**
- Saf asistan: web_search CVE → write_file exploit/payload → run_cmd çalıştır → çıktıyı yorumla.
- **Güvenlik×asistan karışık (asıl değer):** nmap → write_file rapor; secretsdump → read_file
  ile parse; nikto → web_search ile CVE doğrula. Harness `CompositeExecutor` ile bu karışım gerçek.

**D. Ret (refusal) — ELLE (~15):** `run_cmd` yıkıcı komut (`rm -rf /`) → "yapmam"; `web_fetch`
metadata/loopback (169.254.169.254, localhost) → ret; kapsam-dışı yol (traversal) → ret. B1
guard denylist'iyle tutarlı savunma refleksi.

**Toplam ≈ 300** (A:180 + B:70 + C:35 + D:15). Denge: her aracın ≥ eşik örneği; anlama+zincir
payı yüksek.

## 7. Authoring stratejisi — Hibrit (kullanıcı onayı)

- **B/C/D (elle, ~120):** `data/sft/tools/asistan_tr.jsonl` (anlama+emit-elle) +
  `asistan_chains_tr.jsonl` (zincir+ret). Gerçek CVE metni, gerçekçi log satırları.
- **A (template, ~180):** yeni küçük jeneratör `data/sft/tools/gen_asistan_emit.py` — yol/URL/
  sorgu havuzlarından çeşitli tekli emit örnekleri üretir → `asistan_emit_tr.jsonl`. `augment_targets`
  IP-odaklı olduğu için YENİDEN KULLANILMAZ; bu jeneratör asistan-parametrelerine özel.
  - Havuzlar: dosya yolları (`/var/log/auth.log`, `./config.py`, `/etc/nginx/nginx.conf`…),
    URL'ler (çeşitli host — audit hostname payını besler), sorgular (CVE/araç/hata sorguları).
  - **Denetim güvencesi:** `web_fetch` `url` alanı `target_audit`'e sayılır → URL host çeşitliliği
    zorunlu (tek host ≤ %6). `yol`/`komut`/`sorgu` audit'e SAYILMAZ (audit yalnız hedef/url/
    hedef_url/domain okur).

## 8. Entegrasyon

1. Üç jsonl `data/sft/tools/` altında → `build_tools.py` glob'u **otomatik toplar**.
2. `uv run python data/sft/tools/build_tools.py` → doğrula + dedup + `tools_dist/
   octopus_tools_tr.jsonl` yeniden üret. Kapsama raporunda **8 asistan aracı görünür**;
   `target_audit` **GEÇTI** kalmalı.
3. `build_catalog.py` DEĞİŞMEZ (asistan araçları zaten explicit). İstenirse çalıştırılıp
   parametreler artık eğitimden de doğrulanır.
4. Retrain YOK — B2 çıktısı A+C+D ile birleşip **tek büyük retrain**e gider.

## 9. Test / doğrulama

Yeni `tests/data/test_assistant_sft.py`:
- 8 aracın her biri ≥ eşik (örn. ≥12) örnekte geçiyor.
- Anlama örnekleri var: en az bir negatif/boş-çıktı örneği ("bulunamadı"), en az bir CVE-okuma.
- Ret örnekleri var: `run_cmd` yıkıcı + `web_fetch` metadata reddi.
- Tüm satırlar `build_tools._valid` geçer.
- Merge sonrası `target_audit` GEÇTI (URL host çeşitliliği).
- Jeneratör deterministik (seed) → reproduce.

Uçtan uca: `build_tools.py` çıktısı + `pytest tests/data/ tests/agent/` yeşil.

## 10. Riskler

- **Template tekdüzeliği → ezber:** jeneratör havuzları geniş + seed çeşitliliği; anlama örnekleri
  elle olduğu için sinyal korunur.
- **Anlama sinyalinin uzun-yorum tokenlarında boğulması** (BalanceSFT): D'de signal-balance;
  B2'de yorumları kısa+spesifik tutarak hafifletilir.
- **CVE metni eskir:** örnekler statik; canlı veri B3'ün işi. B2 metinleri "okuma" becerisini
  öğretmek için yeterli (içerik doğruluğu değil, çıkarım doğruluğu hedef).
