---
name: ffuf
description: Hızlı web fuzzer; dizin, parametre, vhost ve POST verisi fuzzing için FUZZ anahtar kelimesi.
tool: ffuf
---

## Kanonik kullanım
`{"url": "<url-FUZZ>", "wordlist": "<yol>", "secenekler": "<ek>"}`.
`FUZZ` yer tutucusu URL/başlık/gövdede nereye konursa oraya wordlist basılır. Örn: `-u https://h/FUZZ -w list.txt`.

## Ana flag'ler
- `-w <wordlist>` (`-w a.txt:W1 -w b.txt:W2` çoklu), `-u` URL, `-X POST -d "FUZZ"` gövde fuzzing.
- `-mc 200,301` status eşle, `-fc 404` filtrele, `-fs <boyut>` boyuta göre ele, `-t` thread.
- `-H "Header: FUZZ"` başlık fuzzing.

## Tuzaklar
- `FUZZ` anahtarını koymayı unutma — yoksa hiçbir yere basmaz.
- Filtresiz çıktı 404 gürültüsüyle dolar; `-fc 404` veya `-fs` ile ele.

## Güvenlik/kapsam
Aktif (MODERATE). Yalnızca yetkili hedef; agresif thread rate-limit/WAF tetikler.
