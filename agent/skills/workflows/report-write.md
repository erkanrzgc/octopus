---
name: report-write
description: Bir bulguyu triage-hazır rapora çevir — başlık, etki, tekrar-üretim, kanıt, düzeltme.
---

## Ne zaman
Bir zafiyet/bulgu doğrulandıktan sonra, teslim edilebilir çıktı üretirken.

## Şablon
- **Başlık**: kısa, etki odaklı.
- **Önem**: CVSS/severity + iş etkisi (bir cümle).
- **Etkilenen**: host/endpoint/parametre.
- **Tekrar-üretim**: adım adım komut/istek (verbatim).
- **Kanıt**: çıktı/ekran/loglar (uydurma yok — yalnızca gerçekten gözlemleneni yaz).
- **Düzeltme**: somut, uygulanabilir öneri.
- **Tespit (blue)**: savunmanın nerede yakalayabileceği.

## İlke
Kanıtsız iddia yok. Doğrulamadıysan "muhtemel" de, "doğrulandı" deme.
