# 🐙 Octópus — Kuzey Yıldızı

> Projenin **vizyonu, hikâyesi ve hedefi**. Yeni bir oturum buraya bakıp "bu proje neyi amaçlıyor"u
> anlasın diye. Güncel strateji: fine-tuning ([ADR 0002](docs/decisions/0002-pivot-to-finetuning.md)),
> taban **Turkish-Gemma-9b bf16 LoRA** ([ADR 0003](docs/decisions/0003-pivot-to-turkish-gemma-bf16.md)).
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
enjekte edilemez; siber bilgiyi Türkçe-**native** bir tabana LoRA ile eklemek ise kanıtlı. → **Türkçe-önce
hedef = Türkçe-uzman bir taban** (önce Qwen3-8B denendi, Türkçe pürüzleri yüzünden Turkish-Gemma'ya geçildi).

## Taban model
- **Birincil (güncel):** `ytu-ce-cosmos/Turkish-Gemma-9b-v0.1` — Türkçe continual-pretrain + SFT + DPO, Gemma-2
  mimarisi. Yöntem: **bf16 LoRA** (4-bit NF4 DEĞİL — merge'li ağırlıkları bozup çok-dilli çöp üretiyor).
- **Neden Qwen3-8B değil:** v0.1/v0.2 Qwen3-8B QLoRA ile eğitildi ama Türkçe akıcılık/persona pürüzlüydü
  (`<think>` sızıntısı, "Octópüs" yazımı). Gerekçe + kanıt: [ADR 0003](docs/decisions/0003-pivot-to-turkish-gemma-bf16.md).
- **Opsiyonel öğretmen:** `fdtn-ai/Foundation-Sec-8B-Reasoning` (İngilizce siber derinliği Türkçe SFT'ye damıt).

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
1. **Taban seç** ✅ Turkish-Gemma-9b-v0.1, bf16 LoRA (ADR 0003; Qwen3-8B denendi→bırakıldı).
2. **SFT veri** ✅ Türkçe distill bilgi (1029 Q&A) + 117-araç tool-use (125 örnek) + persona seed → `messages`
   normalize, dedup, split (skill `octopus-data`, `data/sft/build_sft.py`).
3. **bf16 LoRA eğitim** ✅ düz `transformers`+`peft`+TRL (Unsloth DEĞİL), r=32, seq 1024, lr 2e-4, RunPod
   RTX 4090 (skill `octopus-finetune`, `train/sft_bf16.py`).
4. **Eval + safety** ✅ persona/Türkçe/bilgi/ret gen-testi geçti (skill `octopus-eval`); brittleness sürüyor.
5. **Merge + deploy** ⏳ LoRA merge → GGUF Q4 → yerel RTX 5060 8GB (Ollama/llama.cpp); bulut sonra.
6. **(sonra)** yapısal ```arac``` bloğunu güçlendir (v0.7.1) + RAG grounding (MITRE/CVE/OWASP) + agentic harness portu.

## Arşiv (from-scratch denemesi)
Kendi tokenizer (`tokenizer/octopus-tr.*`, fertility -%35), veri pipeline (`data/`), 100M model
(`model/`, `train/`, `checkpoints_web/`) **korunuyor** ama aktif yolda değil. Bilgi kaybı yok; gerekirse
referans/deney. Detay: [ADR 0001](docs/decisions/0001-from-scratch-turkish-first.md).

## Durum (2026-07-07)
Fine-tuning yolu tamamlandı: **v0.6** (akıcı Türkçe + persona, loss 0.22) ✅ · **v0.7** (siber bilgi +
117-araç tool-use, loss 0.048, %98.7) ✅. Adapter HF'de (`erkanrzgcc/octopus-gemma-v0.7`) + yerelde.
Sıradaki: GGUF Q4 (yerel çalıştırma) · v0.7.1 (yapısal ```arac``` bloğu). Tek-gerçek: `docs/v0.7-loop-queue.md`.
