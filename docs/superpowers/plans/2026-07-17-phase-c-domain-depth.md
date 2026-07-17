# Faz C — Domain Derinliği (ince alanları doldur)

> Büyük hamle veri genişletme: A(hedef dengeleme)✅ → B(araç temeli+asistan verisi)✅ →
> **C(domain derinliği)** → D(reasoning+hafıza) → tek retrain (v0.8).
> Bu faz PARA HARCAMAZ (oturum-içi teacher). Retrain (v0.8) ayrı para-checkpoint.

## Amaç
Mevcut distill (1029) domain dağılımı dengesiz. Kapsama analizi (2026-07-17):

| Domain | Mevcut | Durum |
|---|---|---|
| web | 136 | derin ✅ |
| AD/ağ | 118 | derin ✅ |
| CVE/exploit | 110 | derin ✅ |
| kripto/sertifika | 110 | derin ✅ |
| malware/RE | 82 | iyi ✅ |
| bulut/konteyner | 76 | iyi ✅ |
| **blue/DFIR** | 55 | orta → takviye |
| **sunucu/linux** | 55 | orta → takviye |
| **mobil** | 10 | **ince → doldur** |
| **OSINT** | 9 | **ince → doldur** |
| **kablosuz** | 2 | **ince → doldur** |
| **sosyal müh.** | 2 | **ince → doldur** |

Karar (kullanıcı, 2026-07-17): **ince domainleri doldur** — dengeleme, en düşük risk.

## Kapsam (~120 yoğun Türkçe örnek, kendine-yeten)
Format: `{"messages":[{"role":"user"},{"role":"assistant"}]}` (system YOK — mevcut distill deseni).
Cevaplar 200+ karakter, dış-referanssız, teknik olarak DOĞRU (uydurma yok). Octópus çekirdeği =
kırmızı **ve mavi**: her saldırı konusuna savunma perspektifi ekle.

- **kablosuz (+~22):** WPA2/3 el sıkışma, PMKID, evil twin, deauth + 802.11w/PMF, WPS/Reaver, WEP
  (legacy), handshake yakala/kır, WPA3 SAE + Dragonblood, kurumsal 802.1X/EAP, rogue AP, KRACK,
  MAC filtre baypas, beacon flood, wardriving, BLE/Bluetooth, jamming, RF temel, deauth savunma.
- **sosyal müh. (+~18):** phishing türleri, spear/whaling, vishing, smishing, quishing, pretexting,
  baiting, tailgating, BEC, MFA-fatigue, watering hole, USB-drop, deepfake-vishing, OSINT-güdümlü,
  impersonation, senaryo tasarımı, farkındalık eğitimi, teknik+insan savunma katmanları.
- **OSINT (+~18):** Google dorking, Shodan/Censys, subdomain enum, cert transparency, WHOIS/RDAP,
  pasif DNS, EXIF/metadata, sosyal medya OSINT, ihlal verisi/HIBP, GitHub secret sızıntısı, Wayback,
  Maltego, theHarvester, ASN/BGP, e-posta enum, geolocation, karşı-OSINT/OPSEC, aktif vs pasif.
- **mobil (+~18):** Android mimari, APK yapısı, statik (jadx/apktool), dinamik (Frida/Objection),
  MobSF, OWASP MASVS, güvensiz depolama, cert pinning baypas, root/jailbreak tespit baypas,
  deeplink/intent, iOS IPA/keychain, WebView riskleri, SSL kill switch, biyometrik baypas, mobil C2.
- **blue/DFIR takviye (+~15):** Volatility bellek analizi, plaso/timeline, Windows artefaktları
  (prefetch/amcache/shimcache), registry forensics, disk imaging, ağ forensiği (Zeek), LOLBins
  tespiti, persistence avı, YARA yazma, Sigma yazma, MISP threat-intel, DFIR playbook, konteyner forensiği.
- **sunucu/linux takviye (+~15):** kernel hardening (sysctl detay), namespaces/cgroups, seccomp/
  AppArmor profil yazma, PAM, LUKS, SSH CA/sertifika, WireGuard, nftables gelişmiş, systemd sandbox
  detay, konteyner kaçış önleme, CIS benchmark, yama otomasyonu, secrets vault, TPM/HSM.

## Dosya & doğrulama
- Çıktı: `data/sft/distilled/octopus_distill_c.jsonl` (build_sft `distilled/*.jsonl` glob'lar → otomatik dahil).
- Her batch sonrası: `uv run python -m data.sft.build_sft --source distill seed_tr tools --seed-repeat 3`
  → geçerli sayısı artmalı, 0 dup/0 kısa. `uv run pytest -q` yeşil.
- Kalite: teknik doğruluk elle gözden geçir; komut/parametre gerçek olsun.

## Sıra (batch)
1. kablosuz (en ince, en yüksek marjinal değer) → 2. sosyal müh. → 3. OSINT → 4. mobil →
   5. blue/DFIR takviye → 6. sunucu/linux takviye. Her batch ayrı commit + doğrulama.

## Bitince
Faz D (reasoning+hafıza+skill katmanı) → tek retrain v0.8 (💰 para-checkpoint, kullanıcı onayı).
