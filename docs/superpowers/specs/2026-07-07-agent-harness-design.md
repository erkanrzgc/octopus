# Octópus Agent Harness — Tasarım (Spec)

- **Tarih:** 2026-07-07
- **Durum:** Onaylandı (kullanıcı brainstorming'de bölüm bölüm onayladı)
- **Amaç:** v0.7 modelinin ürettiği ```arac``` bloklarını parse edip araçları çalıştıran, sonucu modele
  geri besleyen **agentic runtime**. Model = beyin (metin üretir); harness = eller (araçları koşturur).

## Bağlam

Octópus v0.7 (Turkish-Gemma-9b bf16 LoRA) 117-araç kataloğuyla tool-use öğrenmiş durumda. Model araç
çağrısını şu formatta **metin olarak** üretir:

```arac
{"arac":"nmap","parametreler":{"hedef":"10.10.10.5","secenekler":"-sV"}}
```

Ama repoda bu bloğu parse edip **gerçekten çalıştıran** bir runtime YOK. Bu spec o runtime'ı tanımlar.
Referans (port/uyarlama, kopya değil): `Desktop\agentic-model\src\octopus\agent` (Hermes tool-loop deseni,
`ToolRegistry`, `LabPolicy`, `AuditLog`).

## Kapsam (iki faz, kademeli)

- **Faz 1 (bu spec'in ana teslimi) — ÇALIŞAN İSKELET, Windows'ta bugün çalışır:** parser + döngü + katalog +
  registry + **MockExecutor** (gerçekçi sahte çıktı) + mock/gerçek model backend + CLI + testler. Gerçek
  binary çalıştırma YOK → sıfır güvenlik riski. Modelin ```arac``` bloğunu güvenilir üretip üretmediğini
  uçtan uca doğrular.
- **Faz 2 (sonra):** gerçek model backend (GGUF Q4, yerel RTX 5060 8GB) + **RealExecutor** (WSL2/Kali
  subprocess) + policy sertleştirme. İskelet pluggable olduğu için sadece backend'ler değişir.

## Mimari

Küçük, tek-sorumluluklu modüller (yeni `agent/` paketi):

```
agent/
  messages.py     Message(role, content) — sade veri tipi
  catalog.py      117-araç KATALOG (TEK GERÇEK KAYNAK, eğitim verisinden türetilir)
  toolcall.py     ```arac``` blok parse + araç-sonucu geri-besleme
  registry.py     katalog → tool-spec + invoke(çağrı) → executor'a yönlendir
  executor.py     Executor protokolü + MockExecutor (Faz 1)
  policy.py       LabPolicy — kapsam allow-list, risk kapısı, dry-run
  audit.py        AuditLog — her araç çağrısı jsonl'e
  loop.py         run_tool_loop — model↔araç döngüsü
  backends/
    mock_model.py scripted/mock `üret` (test + demo)
    (Faz 2) gguf_model.py
  cli.py          `python -m agent.cli` — sohbet girişi
tests/agent/      parser, katalog-bütünlük, döngü, policy, executor testleri
```

### Bileşen sözleşmeleri

- **catalog.py** — 117 girdi, her biri: `{isim, alan, risk(low/med/high), parametreler(anahtar listesi),
  komut_sablonu}`. İsimler + parametre anahtarları **eğitim verisinden türetilir** (garantili model-eşleşmesi).
  Kanıt: 117/117 araç `arac` bloğunda mevcut, 38 benzersiz parametre anahtarı, çoğu `secenekler` (ham bayrak).
- **toolcall.py** — `parse_arac_calls(text) -> list[ToolCall]` (regex ```arac``` blok, bozuk JSON'ı atlar,
  asla çökmez). Geri-besleme: `data/sft/normalize.py::flatten_tool_messages` **aynen yeniden kullanılır**
  (araç sonucu → "ARAÇ ÇIKTISI:\n…" `user` turu; Gemma-2 tool rolü desteklemez).
- **registry.py** — katalogtan tool-spec üretir (system-prompt için), `invoke(call)` çağrısını policy +
  executor'a yönlendirir. Bilinmeyen araç → hata (modele geri döner, döngü ölmez).
- **executor.py** — `Executor` protokolü: `run(tool, params) -> str`. `MockExecutor` alan-bazlı gerçekçi
  çıktı üretir (nmap→port listesi, sqlmap→enjeksiyon bulgusu). Faz 2: `RealExecutor` subprocess+policy.
- **policy.py** — `decide(tool, params) -> Decision(allowed, requires_approval, reason)`. Varsayılan lab-only;
  risk `low` recon kapsam içinde geçer, `high` onay/dry-run ister. Kapsam dışı hedef → reddet.
- **loop.py** — `run_tool_loop(messages, generate, registry, max_steps=10)`: model üret → `arac` var mı?
  yoksa nihai cevap; varsa her çağrıyı invoke et, sonucu `tool` mesajı ekle, tekrarla. `max_steps` koruması.
  Backend-bağımsız (`generate: list[Message] -> str`).

## Veri akışı (bir tur)

```
USER "10.10.10.5 tara" → generate() → ASSISTANT (akıl + ```arac nmap```)
  → parse_arac_calls → [nmap çağrısı]
  → policy.decide (kapsam+risk) → izin
  → executor.run("nmap", {...}) → çıktı (Faz1 mock / Faz2 gerçek)
  → flatten ile "ARAÇ ÇIKTISI:\n…" TOOL mesajı → generate() → ASSISTANT (yorum / sıradaki araç)
  → arac yoksa → nihai cevap, döngü biter
```

## Hata yönetimi

- Bozuk/eksik `arac` bloğu → parser atlar (döngü sürer).
- Bilinmeyen araç / executor hatası → `ERROR: …` metni modele geri döner (asla exception ile çökme).
- `max_steps` → sonsuz döngü koruması, son bir düz cevap alınır.
- Kapsam-dışı/risk → policy reddi, sebep modele döner.

## Test stratejisi (TDD, %80+)

- **parser:** geçerli/bozuk/çoklu `arac` blokları, ret örnekleri.
- **catalog-bütünlük:** 117 aracın hepsi var mı, isimler eğitim verisiyle eşleşiyor mu (kanonik test).
- **loop:** scripted `generate` + `MockExecutor` ile tam tur (tek-araç, çok-adımlı zincir, nihai cevap).
- **policy:** kapsam içi/dışı hedef, low/high risk, dry-run kararları.
- **executor:** MockExecutor alan-bazlı çıktı biçimi.

## Kararlar (brainstorming'de onaylı)

1. Hedef: önce iskelet (mock), sonra gerçek çalıştırma (WSL2/Kali) üstüne takılır — **1 temel, 2 üstüne**.
2. Registry = **veri-güdümlü tek katalog** (117 araç, eğitim verisinden türetilir). 117 elle-handler DEĞİL.
3. Geri-besleme formatı eğitimle **birebir aynı** olmalı (`flatten_tool_messages` reuse) — en kritik doğruluk noktası.
4. Backend soyutlaması: model (mock→GGUF) ve executor (mock→gerçek) ayrı ayrı takılabilir.

## İlgili

- `data/sft/tools/build_tools.py` (MASTER_TOOLS = kanonik 117 liste) · `data/sft/normalize.py` (flatten reuse)
- `docs/v0.7-tools-catalog.md` · `Desktop\agentic-model\src\octopus\agent\*` (referans desen)
