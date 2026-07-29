---
name: finding-synthesis
description: Birden çok araç çıktısını korele et, bulguları önem sırasına koy, saldırı zincirine bağla.
---

## Ne zaman
Elde birden çok tarama/enum çıktısı olunca; ham çıktı yerine karar üretmek için.

## Akış
1. **Normalize**: her bulguyu (host, port, servis, zafiyet, güven) tek biçime getir.
2. **İlişkilendir**: aynı subnet/domain, ortak kimlik bilgisi, pivot noktaları.
3. **Önceliklendir**: etki × olasılık × gürültü. Tek başına orta bir bulgu, bir zincirin ilk halkasıysa kritiktir.
4. **Zincirle**: initial access → execution → privesc → lateral → impact olarak anlatıya bağla.

## İlke
Güven seviyesini dürüst işaretle (Confirmed/High/Moderate/Speculative). Doğrulanmamış halkayı doğrulanmış gibi sunma.
