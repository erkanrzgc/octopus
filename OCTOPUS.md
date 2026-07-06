# 🐙 Octópus — Kuzey Yıldızı

> Projenin **vizyonu, hikâyesi ve hedefi**. Yeni bir oturum buraya bakıp "bu proje neyi amaçlıyor"u
> anlasın diye. Güncel strateji: fine-tuning ([ADR 0002](docs/decisions/0002-pivot-to-finetuning.md)).
> Fazlı icra planı: `~/.claude/plans/atomic-jumping-swan.md`. Kurallar: `CLAUDE.md`.

## Tek cümlede
Octópus, **Türkçe konuşan**, siber güvenlikte (red + blue + network) ve **sunucu/sistem yönetiminde**
usta, kendi sunucunda çalışacak otonom bir yapay zekâ. Teori ezberleyen bot değil; bilen, yapan, araç
kullanan bir uzman — **yalnızca sahibinin yetkisi içinde.** Model konuşmada **"Ben Octópus"** der.

## Neden fine-tuning (from-scratch değil)
Önce sıfırdan pretraining seçilmişti ([ADR 0001](docs/decisions/0001-from-scratch-turkish-first.md)); kendi
Türkçe tokenizer + 100M model yerelde ayağa kalktı. Ama **ölçek turu maliyeti** (RunPod $60-150+, milyarlarca
token) ağır bastı. **Karar: güçlü bir tabanı QLoRA ile fine-tune etmek** (~$3-15, birkaç saat, 100-1000×
daha ucuz + çok daha yüksek yetenek tavanı).

**Kural:** DİL tabanda olmalı, BİLGİ sonradan eklenir. Türkçe akıcılığı bir İngilizce tabana LoRA ile
enjekte edilemez; siber bilgiyi Türkçe-native bir tabana QLoRA ile eklemek ise kanıtlı. → **Türkçe-önce
hedef = Qwen3 tabanı.**

## Taban model
- **Birincil:** `Qwen3-8B` — Türkçe-native, Apache 2.0, yerel-önce (Q4 ~5GB uçar), QLoRA ucuz.
- **Yükseltme:** `Qwen3-14B` (pipeline oturunca).
- **Opsiyonel öğretmen:** `fdtn-ai/Foundation-Sec-8B-Reasoning` (İngilizce siber derinliği Türkçe SFT'ye damıt).
- Detay + gerekçe + kanıt: [ADR 0002](docs/decisions/0002-pivot-to-finetuning.md).

## Dört sütun (hedef yetenek)
- 🔴 **Red team** (yetkili): recon/OSINT, tarama, web/AD saldırıları, MITRE ATT&CK doğru ID'yle.
- 🔵 **Blue team**: log/SIEM, tehdit avı, olay müdahale, sertleştirme, Sigma/YARA, D3FEND.
- 🌐 **Network**: TCP/IP, DNS/TLS, paket analizi, firewall/VPN.
- 🖥️ **Sunucu** (ana hedef): Linux, nginx/TLS, Docker, ufw/iptables, fail2ban, journald — uygulanabilir Türkçe.

## Kırmızı çizgi
Tüm saldırı yetenekleri **yalnızca yetkili lab / CTF / eğitim / sahibinin sistemleri** ile sınırlı.
Sahip = yetki. Başkasına ait/izinsiz hedef → net reddet, laba yönlendir. Guardrail system prompt SFT'de işlenir.

## Marka & yol
Model konuşmada **"Ben Octópus"** (noktalı ó). Kod/yol/repo düz ASCII `octopus` (Windows native lib
non-ASCII path'i bozar). Klasör: `Desktop\Octopus`.

## Yol haritası (fine-tuning)
1. **Taban seç** ✅ Qwen3-8B (ADR 0002).
2. **SFT veri** — Fenrir v2.1 + secdata-raw + AlicanKiraz CVE + Türkçe persona/sunucu → `messages` normalize,
   dedup, split (skill `octopus-data`).
3. **QLoRA eğitim** — Unsloth, r=32 başlangıç, seq 1024→2048, lr 2e-4 (skill `octopus-finetune`).
4. **Eval + safety** — ppl + yetkili-yardım/yetkisiz-ret dengesi + brittleness red-team (skill `octopus-eval`).
5. **Merge + deploy** — LoRA merge → GGUF Q4 → yerel (Ollama/llama.cpp); bulut sonra.
6. **(sonra)** RAG grounding (MITRE/CVE/OWASP) + agentic harness portu + çok-dillilik.

## Arşiv (from-scratch denemesi)
Kendi tokenizer (`tokenizer/octopus-tr.*`, fertility -%35), veri pipeline (`data/`), 100M model
(`model/`, `train/`, `checkpoints_web/`) **korunuyor** ama aktif yolda değil. Bilgi kaybı yok; gerekirse
referans/deney. Detay: [ADR 0001](docs/decisions/0001-from-scratch-turkish-first.md).

## Durum (2026-07-03)
Strateji fine-tuning'e döndü; taban Qwen3-8B seçildi; docs hizalandı; proje skill/subagent kurulumu yapılıyor.
Sıradaki: SFT veri hazırlama → yerel duman turu → (💰 checkpoint) → RunPod QLoRA turu.
