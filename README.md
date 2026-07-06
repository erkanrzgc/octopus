<div align="center">

# 🐙 Octópus

### Türkçe-önce siber güvenlik ve sunucu yönetimi için uzman bir dil modeli
##### _A Turkish-first cybersecurity & server-management large language model — red + blue + network + Linux._

<br/>

[![Version](https://img.shields.io/badge/sürüm-v0.7-orange?style=for-the-badge)](https://github.com/erkanrzgc/octopus)
[![Base Model](https://img.shields.io/badge/taban-Turkish--Gemma--9B-4285F4?style=for-the-badge&logo=google)](https://huggingface.co/ytu-ce-cosmos/Turkish-Gemma-9b-v0.1)
[![Language](https://img.shields.io/badge/dil-Türkçe--önce-E30A17?style=for-the-badge)](#)
[![Domain](https://img.shields.io/badge/alan-siber%20güvenlik-000000?style=for-the-badge)](#)

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=flat-square&logo=python&logoColor=white)](#)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.4-EE4C2C?style=flat-square&logo=pytorch&logoColor=white)](#)
[![Transformers](https://img.shields.io/badge/🤗%20Transformers-4.49-FFD21E?style=flat-square)](#)
[![PEFT](https://img.shields.io/badge/PEFT-LoRA%20bf16-00A98F?style=flat-square)](#)
[![RunPod](https://img.shields.io/badge/eğitim-RunPod%20RTX%204090-673AB7?style=flat-square)](#)
[![Lisans](https://img.shields.io/badge/kod-MIT-green?style=flat-square)](#-lisans--license)
[![Kullanım](https://img.shields.io/badge/kullanım-yetkili%2Flab--only-critical?style=flat-square)](#-etik-kullanım--responsible-use)

<em>“Ben Octópus.” — Türkçe konuşan, savunan ve saldıran; ama yalnızca izinli.</em>

</div>

---

## 📖 Hakkında · About

**Octópus**, güçlü bir Türkçe-uzman taban model (**`ytu-ce-cosmos/Turkish-Gemma-9b-v0.1`**) üzerine, siber güvenlik ve sunucu yönetimi bilgisiyle **fine-tune** edilmiş bir dil modelidir. Model kendini **“Ben Octópus”** diye tanıtır (noktalı `ó` yalnızca markadadır; dosya yolları düz ASCII `octopus`).

Amaç; İngilizce-ağırlıklı siber güvenlik asistanlarının aksine, **akıcı, edebî Türkçe** konuşan; hem **kırmızı takım** (sızma testi, keşif, sömürü) hem **mavi takım** (tespit, olay müdahale, sertleştirme) hem de **ağ + Linux sunucu yönetimi** derinliğine sahip, **yetki-bilinçli** bir asistan üretmektir.

> **Dil tabanda, bilgi sonradan.** Türkçe akıcılık LoRA ile enjekte edilemez → bu yüzden Türkçe-uzman bir taban seçilip, siber bilgi SFT + RAG ile eklenir.

---

## ✨ Özellikler · Features

- 🇹🇷 **Türkçe-önce** — ana dili gibi akıcı; komut / kod / CVE-ID `verbatim` korunur.
- 🔴🔵 **Red + Blue** — sızma testinden olay müdahaleye, tek modelde saldırı ve savunma bakışı.
- 🖥️ **Sunucu yönetimi** — SSH/systemd/nginx/nftables/SELinux sertleştirme, konteyner & bulut güvenliği.
- 🛠️ **Agentic araç kullanımı** — `nmap`, `wireshark`, `sqlmap`, `metasploit`, `bloodhound` dahil **117 aracın** kataloğu ve yapılandırılmış çağrı formatı (`arac` blok'u).
- 🛡️ **Yetki kalibrasyonu** — yalnızca lab / CTF / sahibinin izinli sistemleri; yetkisiz istekleri **net reddeder**, etik alternatif sunar.
- 📚 **Şeffaf pipeline** — veri hazırlama → SFT → değerlendirme → GGUF; her adım izlenebilir ve tekrar-üretilebilir.

---

## 🏗️ Mimari · Pipeline

```text
                    ┌──────────────────────────────────────────────┐
   Veri Kaynakları  │  distilled Q&A (teacher)   tool-use (arac)     │
   (Türkçe)         │  + seed persona/guardrail  + red/blue/sunucu   │
                    └───────────────────────┬──────────────────────┘
                                            │  build_sft.py (normalize + persona + dedup + split)
                                            ▼
                    ┌──────────────────────────────────────────────┐
   Taban Model  ──▶ │  Turkish-Gemma-9B  ──(bf16 LoRA, r=32)──▶ SFT  │
                    └───────────────────────┬──────────────────────┘
                                            │  eval (kalite + safety + brittleness)
                                            ▼
                    ┌──────────────────────────────────────────────┐
   Dağıtım      ◀── │  merge → GGUF (Q4) → yerel 8GB | 🤗 HF (adapter)│
                    └──────────────────────────────────────────────┘
```

**Ana bileşenler**

| Dizin / Dosya | Görev |
|---|---|
| `data/sft/build_sft.py` | Kaynakları tek `messages` formatına indirger, persona ekler, dedup + train/val/test böler. |
| `data/sft/tools/` | Elle üretilmiş **agentic tool-use** örnekleri (117 araç, çok-adımlı zincirler, ret örnekleri). |
| `data/sft/distilled/` | Teacher-üretimi Türkçe siber **bilgi** Q&A (CVE, web, AD, DFIR, sunucu, kripto). |
| `train/sft_bf16.py` | `unsloth`-suz **bf16 LoRA** eğitim (Turkish-Gemma'yı bozan 4-bit kuantizasyonundan kaçınır). |
| `data/sft/normalize.py` | Saf/test-edilebilir normalize çekirdeği (+ Gemma-2 `tool` rolü uyarlaması). |
| `cloud/` | RunPod runbook + eğitim / GGUF / değerlendirme script'leri. |
| `docs/` | Kararlar (ADR), veri kataloğu, faz planları. |

---

## 🧠 Model & Eğitim · Training

| | |
|---|---|
| **Taban** | `ytu-ce-cosmos/Turkish-Gemma-9b-v0.1` (Gemma-2 mimarisi, Türkçede güçlü) |
| **Yöntem** | bf16 LoRA (`r=32`, `α=32`, 7 hedef modül) — **4-bit YOK** (merge'li tabanı korur) |
| **Donanım** | RunPod · RTX 4090 (24 GB) · torch 2.4 · pinned `transformers/trl/peft` |
| **Veri (v0.7)** | 1.029 Türkçe bilgi Q&A + 125 tool-use örneği (117 araç) + persona seed |
| **Sonuç (v0.7)** | son loss **0.048** · token doğruluğu **%98.7** · ~3 epoch |

**Neden bf16 LoRA?** Turkish-Gemma continual-pretrain + SFT + DPO + **merge** geçmişi taşır; yaygın 4-bit (NF4) kuantizasyonu bu merge'li ağırlıkları bozup çok-dilli çöp üretir. Kanıt: aynı model düz `bf16`'da kusursuz Türkçe üretir → çözüm, tabanı bf16 yükleyip üzerine LoRA eğitmektir.

---

## 🗺️ Yol Haritası · Roadmap

- [x] **v0.2** — Qwen QLoRA temel hattı (deney / yedek)
- [x] **v0.6** — Turkish-Gemma bf16 LoRA · akıcı Türkçe + persona + yetki kalibrasyonu ✅
- [x] **v0.7** — siber **bilgi derinliği** + **agentic tool-use** (117 araç kataloğu) ✅
- [ ] **v0.7.1** — yapısal `arac` blok formatını güçlendir · tam-veri eğitimi
- [ ] **GGUF Q4** — yerel 8 GB'da çalıştırma (offline-first)
- [ ] **RAG + Lab Mode** — bilgi tabanı + izole laboratuvar entegrasyonu

---

## ⚙️ Teknoloji · Tech Stack

`Python 3.11` · `PyTorch 2.4` · `Transformers 4.49` · `PEFT (LoRA)` · `TRL` · `Datasets` · `SentencePiece` · `llama.cpp (GGUF)` · `uv` (paket) · `RunPod` (eğitim) · `Hugging Face Hub`

---

## 🔒 Etik Kullanım · Responsible Use

> **⚠️ Yalnızca yetkili, yasal ve laboratuvar/CTF/eğitim amaçlı kullanım.**

Octópus, offansif teknikleri **savunmayı güçlendirmek** ve **yetkili sızma testi / güvenlik araştırması** için öğretir. Model, tasarımı gereği:

- Yalnızca **sahibinin açıkça izin verdiği** sistemlerde yardımcı olur.
- Yetkisiz gerçek hedeflere saldırı adımı/komutu **vermez** (başkasının Wi-Fi/hesap/ağ/sistemi, kimlik avı, zarar amaçlı zararlı yazılım).
- Böyle bir istekte **net reddeder**, sebebini söyler ve etik/savunma alternatifi sunar.

Bu depo ve model; suç faaliyeti, izinsiz erişim veya zarar için **kullanılamaz**. Sorumluluk tamamen kullanıcıya aittir.

---

## 👤 Yazar · About the Author

**Erkan** ([@erkanrzgc](https://github.com/erkanrzgc)) — etik (white/grey-hat) güvenlik meraklısı, yerel-öncelikli (local-first) yapay zekâ üzerine çalışıyor. Octópus; Türkçe bir siber güvenlik asistanını sıfırdan tasarlama, veri üretme, fine-tune etme ve değerlendirme sürecinin uçtan uca, şeffaf bir kaydıdır.

> Bir soru, öneri veya işbirliği için Issues bölümü açık. 🐙

---

## 📜 Lisans · License

- **Kod:** MIT (bu depodaki script'ler, pipeline, dokümanlar).
- **Taban model:** [Gemma kullanım koşulları](https://ai.google.dev/gemma/terms) geçerlidir (`ytu-ce-cosmos/Turkish-Gemma-9b-v0.1` üzerinden).
- **Türetilmiş ağırlıklar/adapter:** tabanın lisans koşullarına tabidir; yalnızca yetkili/etik kullanım.

<div align="center">
<sub>Türkçe düşünen, savunan ve — yalnızca izinliyse — saldıran bir model. 🐙</sub>
</div>
