# Octópus Skill Layer — Design (2026-07-25)

> **Status:** APPROVED (user, 2026-07-25). Next: spec review → writing-plans → implement (pilot first).
> **Kaynak esin:** agentskills.io açık standardı (Anthropic; Codex/Claude Code/Cursor/Gemini CLI/Hermes benimsemiş) + Hermes agent skills hub. Codex ekran görüntüleri = birebir bu standart.

## Amaç

Octópus'a bir **skill katmanı** kazandırmak: model bir aracı **kullanmadan önce** o aracın "nasıl doğru kullanılır" `.md`'sini okur (v0.9'daki **uydurma-flag** sorununu doğrudan çözer) + genel cyber iş-akışı skilleri. Standartta skill'i **ajan RUNTIME'ı** tüketir (model değil) → doğru yer **`agent/` harness**.

## Kritik ön-bulgu

- `rag/knowledge/methodologies/*.md` (55+) **zaten SKILL.md formatında** (`name` + `description` frontmatter; ör. attack-planner.md). AMA harness bunları **hiç yüklemiyor** (agent/'da methodolog/knowledge/skill referansı yok).
- Yani skill *içeriği* kısmen var; eksik olan **harness'ın skill-farkında olması** + araç-skilleri + runtime bağlama.

## Mimari kararlar (onaylı)

**1. Konum/tüketim = RUNTIME harness** (SFT DEĞİL şimdilik). Progressive disclosure. Retrain yok, bedava, iteratif. İleride kanıtlanan skiller SFT'ye damıtılır ("ikisi de" yolu — sonraki faz).

**2. Üç skill türü:**
| Tür | Yer | Ne | Adet |
|---|---|---|---|
| Araç skilleri | `agent/skills/tools/<araç>.md` | "nmap nasıl doğru kullanılır": kanonik sözdizim, ana flag'ler, tuzaklar, güvenlik notu | 117 (yeni) |
| Metodoloji skilleri | `rag/knowledge/methodologies/*.md` (mevcut) | domain NE: recon, exploit-zincir, IR, detection | 55 (bağla) |
| Meta iş-akışı | `agent/skills/workflows/*.md` | NASIL: engagement-planla, bulgu-sentezle, rapor-yaz, doğrula-önce-iddia | ~4-6 (yeni) |

Hepsi `SKILL.md` standardı: YAML frontmatter `name` + `description` (araç skillerinde ek `tool: <ad>`) + markdown gövde.

**3. Mekanizma = post-call correction (kullanıcı seçti):**
- Discovery: açılışta TÜM skillerin sadece `name`+`description`'ı yüklenir (kompakt manifest, system prompt'a eklenir).
- Araç-skili aktivasyonu: model `arac` bloğu yazar → harness araç adını parse eder → **o araç bu konuşmada henüz gösterilmediyse** tool md'yi `<skill>`/system mesajı olarak enjekte eder → model çağrıyı DÜZELTİR/onaylar → execute. **Cache:** gösterilen araçlar konuşma-state'inde tutulur, tekrar enjekte edilmez (gereksiz round-trip yok).
- Metodoloji/iş-akışı aktivasyonu: istek description'a uyunca (keyword/embedding eşleşme) tam md planlamadan önce enjekte edilir.

**4. Yeni modül `agent/skills.py`:**
- `load_index()` → tüm SKILL.md frontmatter (name+desc) → kompakt manifest
- `get(name)` → tam md
- `match_tool(tool_name)` → araç md'si
- `match(query)` → ilgili metodoloji/iş-akışı (description eşleşmesi)
- `loop.py`'ye bağlanır: toolcall parse SONRASI, execute ÖNCESİ araç-skili enjekte (cache kontrolü ile)

**5. Yazım stratejisi — YAGNI/aşamalı (ÖNEMLİ):**
- Araç md'lerini `agent/catalog_data.py`'den **otomatik taslak üret** (117 starter; ad/param'lar oradan) → değerlileri elle zenginleştir (nmap/sqlmap/metasploit/hydra/nikto/gobuster…).
- **PİLOT ÖNCE:** harness mekanizması + ~8-10 yüksek-değer araç skili + 3-4 iş-akışı → correction-loop çalışıyor mu **ÖLÇ** → sonra 117'ye ölçekle. (Projenin eval-first/ölçüm-kapısı deseni.)

**6. Test/eval:**
- Unit: `agent/skills.py` loader (index/get/match_tool/match)
- Entegrasyon: correction-loop — yanlış araç çağrısı mock'la → tool md enjekte edildi mi + düzeltilmiş çağrı geldi mi assert
- Eval: **uydurma-flag oranı skil öncesi/sonrası** (v0.9 teknik-doğruluk eval'ine bağlı; `eval/verify_correctness_v9.py` yanına)

## İzolasyon/sınırlar

- `agent/skills.py` tek sorumluluk: skill keşif/yükleme/eşleşme. Harness loop'u sadece "enjekte et" çağırır.
- Skill dosyaları veri (md), kod değil → sürüm-kontrollü, güncellemesi retrain gerektirmez.
- Policy gate DEĞİŞMEZ (skill katmanı gate'in üstünde; skil doğru KULLANIMI öğretir, yetkiyi değil).

## Kapsam-dışı (YAGNI)

- SFT'ye damıtma (sonraki faz)
- Model-kontrollü skill açma (SFT gerektirir; şimdilik harness-güdümlü post-call)
- 117'nin tamamının elle yazımı (auto-draft + pilot; ölçekleme sonra)
- Embedding altyapısı zorunlu değil (keyword eşleşme yeterse onunla başla)
