# Tehdit Istihbarati (Threat Intelligence)

## IOC vs TTP — Pyramid of Pain
Saldirgan icin degistirmesi en kolaydan en zora:
1. Hash (cok kolay) · 2. IP · 3. Domain · 4. Network/host artifact ·
5. Tool · 6. **TTP (en zor)** — davranisa odaklanmak en degerli savunma.

## Cerceveler
- **MITRE ATT&CK**: TTP haritalama (taktik/teknik). Detection engineering temeli.
- **Cyber Kill Chain** (Lockheed): recon -> weaponize -> deliver -> exploit -> install -> C2 -> actions.
- **Diamond Model**: adversary / capability / infrastructure / victim.
- Paylasim: **STIX/TAXII** formati, threat feed'ler (MISP, OTX, abuse.ch).

## Kullanim
- IOC'leri SIEM/EDR'ye besle (tespit + engelleme).
- TTP'leri ATT&CK'e esle -> Sigma kurallari -> tespit kapsami (coverage) olc.
- Onceliklendirme: sektorune/varligina uygun aktorler (CTI).

## Dikkat
- **Attribution zordur**: false flag, paylasilan altyapi. Kesin atfetmede ihtiyatli ol.
- IOC'ler hizla eskir; TTP-tabanli tespit daha dayaniklidir.
