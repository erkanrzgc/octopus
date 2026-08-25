---
name: magika
description: Google'ın ML tabanlı dosya-tipi tespiti; içerikten ~%99 doğrulukla 200+ format, forensics/triyaj.
tool: magika
---

## Kanonik kullanım
`{"yol": "<dosya/dizin>"}`. Bilinmeyen dosyanın gerçek türünü içerikten belirler (uzantıya güvenmeden).
Örn: şüpheli örnek/DFIR artefaktı türünü hızlı tanı.

## Ana flag'ler
- `-r` özyinelemeli dizin, `--json` makine-okur, `--mime-type` MIME çıktısı, `-s` güven skoru.
- Girdi tek dosya veya dizin; ikili/metin ayrımı ve gerçek format (ör. uzantısız PE, gizlenmiş script).

## Tuzaklar
- Uzantı yanıltıcıysa magika içeriğe bakar — bu güçlü yanı; yine de düşük-güven skorlarını elle teyit et.
- Şifreli/paketlenmiş dosyada tür "generic" dönebilir; binwalk/strings ile derinleştir.

## Güvenlik/kapsam
Pasif, yerel içerik analizi (ağ hedefi yok). Şüpheli örneği izole/lab ortamında incele.
