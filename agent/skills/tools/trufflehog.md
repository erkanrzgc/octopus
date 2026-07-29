---
name: trufflehog
description: Sızmış sır/credential tarayıcı (git, GitHub, S3, dosya sistemi, Docker); 800+ tip, canlı doğrulama.
tool: trufflehog
---

## Kanonik kullanım
`{"kaynak": "<git|github|s3|filesystem|docker>", "hedef": "<uri/org/bucket/yol>"}`.
Örn: `git https://github.com/org/repo`, `github --org=<org>`, `filesystem <yol>`, `docker --image <imaj>`.

## Ana flag'ler
- Alt-komut (kaynak) ZORUNLU: `git`, `github`, `s3`, `filesystem`, `docker`.
- `--results=verified,unknown` çıktı filtresi (yalnız doğrulanmış sırlar için `verified`).
- `--json` makine-okur çıktı, `--fail` sır bulununca exit 183 (CI gate).
- `--only-verified` gürültüyü keser (canlı doğrulanan credential'lar).

## Tuzaklar
- Kaynağı (git/github/...) belirtmezsen çalışmaz.
- `--only-verified` olmadan yüksek yanlış-pozitif; triage için önce doğrulanmışlara bak.
- GitHub org taraması API rate-limit'e takılabilir; token ver.

## Güvenlik/kapsam
Çoğunlukla defansif/pasif (kendi repolarında sır avı). Başkasının özel kaynağına erişim yetki ister; hedef kapsam içinde olmalı.
