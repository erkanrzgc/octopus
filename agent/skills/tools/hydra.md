---
name: hydra
description: Ağ servisi online parola brute-force (SSH/FTP/HTTP-form/RDP...). Yüksek gürültü/kilit riski.
tool: hydra
---

## Kanonik kullanım
`{"hedef": "<ip/host>", "secenekler": "-l <kullanici> -P <parola-listesi> <servis>"}`.
Örn SSH: `-l admin -P rockyou.txt ssh://10.10.10.5`. HTTP form: `http-post-form "<path>:<body>:<fail-string>"`.

## Ana flag'ler
- `-l <tek-kullanici>` / `-L <liste>`, `-p <tek-parola>` / `-P <liste>`, `-t <paralel>` (varsayılan 16).
- Servis URL biçimi: `ssh://`, `ftp://`, `rdp://`, `http-post-form`/`http-get-form`.
- `-f` ilk bulunanda dur, `-o` çıktı, `-s <port>` özel port.

## Tuzaklar
- HTTP form'da `fail-string` yanlışsa her denemeyi "başarılı" sanar — geçersiz login'in dönüş metnini doğru ver.
- Yüksek `-t` hesap kilitler ve servisi boğar; kilitleme politikası olan hedefte düşür.
- Büyük listeler çok LOUD; hedefli küçük listeyle başla.

## Güvenlik/kapsam
Intrusive (kilit + DoS riski). Yalnızca yetkili hedef; başkasının hesabına brute-force = red çizgisi.
