---
name: sqlmap
description: SQL injection tespit ve sömürü otomasyonu; DB dump, dosya okuma, OS shell.
tool: sqlmap
---

## Kanonik kullanım
`{"url": "<enjekte-edilebilir-url>", "secenekler": "<ek>"}`.
Tespitle başla: `-u "<url>" --batch`. Sonra kademeli: `--dbs` → `-D <db> --tables` → `-T <t> --dump`.

## Ana flag'ler
- `--batch` etkileşimsiz (varsayılan cevaplar), `--level 1-5`/`--risk 1-3` derinlik.
- `-r <istek.txt>` ham HTTP isteği (POST/başlık enjeksiyonu için ideal), `-p <param>` hedef parametre.
- `--dbs --tables --columns --dump`, `--current-user --is-dba`, `--os-shell` (yüksek risk).

## Tuzaklar
- `--os-shell`/`--dump-all` yüksek etkili ve gürültülü — önce tespiti doğrula.
- `--level/--risk` yükseltmek yavaşlatır ve LOUD yapar; 1'den başla.
- POST/JSON için `-r` ile ham istek ver; URL'ye sıkıştırma.

## Güvenlik/kapsam
Yüksek etki (veri sömürüsü). Yalnızca yetkili hedef; dump/os-shell öncesi kapsamı ve gereği teyit et.
