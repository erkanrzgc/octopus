---
name: octopus-data
description: Use when preparing SFT (instruction) data for Octópus fine-tuning — normalizing Türkçe + cyber datasets into chat-format `messages`, injecting the "Ben Octópus" persona/guardrail, dedup, and train/val/test split. Triggers on "SFT veri", "veri hazırla", "dataset", "instruction verisi", "Fenrir".
---

# Octópus SFT Veri Hazırlama

Fine-tuning **ham korpus değil, talimat (SFT) verisi** ister: `system/user/assistant` üçlüleri. Amaç: Türkçe +
siber kaynakları tek `messages` şemasına normalize etmek, Octópus persona/guardrail'ini gömmek, temizlemek.
Çalışan referans: `Desktop\cyberm4fiaModel\scripts\01_prepare_data.py` + `cyberm4fia/config.py` (desen, kopya değil).

## Kaynaklar (lisans doğrulanmış)
| Kaynak | İçerik | Not |
|---|---|---|
| `AlicanKiraz0/Cybersecurity-Dataset-Fenrir-v2.1` | ~100k siber system/user/assistant, savunma-hizalı | çekirdek |
| `deardaniel/secdata-raw` | CWE/CVE/ExploitDB/güvenlik-kodu (cc-by-sa) | template'e sar |
| AlicanKiraz CVE (apache) | CVE analiz çiftleri | `{User}\n\n{Assistant}` |
| Türkçe persona/sunucu | "Ben Octópus" + Linux/nginx/Docker/fw senaryoları | elle/damıtma ile üret |

> ⚠️ Türkçe siber SFT verisi kıt. Fenrir çoğunlukla İngilizce → **Türkçe kapsama için**: (a) bir kısmını
> Türkçeye çevir/damıt (Foundation-Sec-Reasoning öğretmen + `distill_teacher_tr.py`), (b) sunucu/Türkçe
> persona örneklerini elle üret. Dengeyi ölç, tek dile boğma.

## Normalize kuralları
1. Her örnek → `{"messages":[{"role":"system","content":PERSONA},{"role":"user",...},{"role":"assistant",...}]}`.
2. **Persona/guardrail system prompt** başa eklenir (aşağıdaki). Model kendini **"Ben Octópus"** tanıtır.
3. **Dedup:** user+assistant içeriği üzerinde exact dedup (çift satırları at).
4. **Kalite filtresi:** boş/çok kısa/bozuk-encoding at; Türkçe-i (İ/ı) ve diakritik korunur (NFC, casefold YOK).
5. **Split:** %96 train / %2 val / %2 test (held-out). Kaynak/lisans/risk etiketini manifest'te tut.

## Persona / guardrail system prompt (başlangıç)
```
Sen Octópus'sun: yetkili siber güvenlik ve sunucu yönetimi için uzman bir asistansın. Kendini "Ben Octópus"
diye tanıtırsın. Hem savunma (blue) hem saldırı (red) + ağ + Linux sunucu yönetiminde derinlemesine, ana dili
gibi akıcı Türkçe yardım edersin (komut/kod/CVE-ID verbatim kalır). Yardımın laboratuvar, CTF, eğitim ve
SAHİBİNİN AÇIKÇA İZİN VERDİĞİ sistemlerle sınırlıdır. Yetkisiz gerçek hedeflere saldırı adımı/komutu VERME
(başkasının WiFi/hesap/ağ/sistemi, kimlik avı, zarar amaçlı zararlı yazılım). Böyle istekte NET reddet,
sebebini kısaca söyle, yetkili/etik/savunma alternatifi sun. Yetki belirsizse önce izin/kapsam sor.
```

## Çıktı
`data/sft/train.jsonl` · `val.jsonl` · `test.jsonl` (+ kaynak manifest). Örnek decode okunur Türkçe/İngilizce
karışımı olmalı; persona her örnekte var. Bu hazır olunca `octopus-finetune` skill'ine geç.
