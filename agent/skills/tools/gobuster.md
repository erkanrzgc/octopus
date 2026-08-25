---
name: gobuster
description: Dizin/dosya, DNS subdomain ve vhost brute-force keşif aracı (wordlist tabanlı).
tool: gobuster
---

## Kanonik kullanım
`{"url": "<hedef>", "mod": "dir", "wordlist": "<yol>", "secenekler": "<ek>"}`.
Mod ZORUNLU: `dir` (dizin), `dns` (subdomain), `vhost`. Örn dir: `-x php,txt -t 50`.

## Ana flag'ler
- `dir`: `-u <url> -w <wordlist> -x <uzantilar> -t <thread>`; `-s`/`-b` status kodu allow/deny.
- `dns`: `-d <domain> -w <wordlist>`; `vhost`: `-u <url> -w <wordlist>`.
- Wordlist: `/usr/share/wordlists/dirbuster/...` veya seclists.

## Tuzaklar
- Mod belirtmezsen çalışmaz — `mod` her zaman ver.
- `dns` modunda `-u` değil `-d` kullanılır; karıştırma.
- Çok yüksek `-t` sunucuyu yorar / rate-limit'e takılır.

## Güvenlik/kapsam
Aktif tarama (MODERATE). Hedef URL/domain kapsam içinde olmalı.
