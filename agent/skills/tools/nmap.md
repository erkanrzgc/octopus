---
name: nmap
description: TCP/UDP port ve servis tarayıcı; recon'un ilk adımı. Versiyon/OS tespiti ve NSE scriptleri.
tool: nmap
---

## Kanonik kullanım
`arac`: `nmap`, `parametreler`: `{"hedef": "<ip/cidr/host>", "secenekler": "<flag'ler>"}`.
Tipik: `-sV -sC -Pn -p-` (tüm portlar + servis + varsayılan scriptler). Hedef parametreye ayrı yaz, `secenekler` içine gömme.

## Ana flag'ler
- `-sV` servis/versiyon, `-O` OS tespiti, `-sC` varsayılan NSE scriptleri, `-A` agresif (hepsi).
- `-p-` tüm 65535 port, `-p 80,443` seçili, `--top-ports 100` hızlı.
- `-Pn` ping'i atla (host ping'e cevap vermiyorsa şart), `-T4` hız, `-oN/-oX` çıktı dosyası.
- `-sU` UDP (yavaş), `-sS` SYN (root gerekir).

## Tuzaklar
- `-sS`/`-O` root ister; yetki yoksa `-sT` (connect) kullan.
- `--script vuln` LOUD'dur, IDS tetikler; varsayılan `-sC`'den başla.
- `masscan` çok geniş aralıkta daha hızlı — sonra nmap ile derinleştir.

## Güvenlik/kapsam
Yalnızca yetkili/lab hedefi. Hedef IP/host kapsam (scope) içinde olmalı; policy scope dışını reddeder.
