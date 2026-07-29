---
name: masscan
description: Internet ölçeğinde çok hızlı asenkron port tarayıcı; geniş aralıkta ilk süpürme için.
tool: masscan
---

## Kanonik kullanım
`{"hedef": "<cidr>", "secenekler": "-p<portlar> --rate <pps>"}`. Örn: `-p1-65535 --rate 1000`.
Geniş aralığı masscan ile süpür, açık portları sonra nmap `-sV` ile derinleştir.

## Ana flag'ler
- `-p80,443` veya `-p1-65535` port aralığı, `--rate` saniyedeki paket (dikkat: yüksek = LOUD/ağ yükü).
- `-oL/-oJ/-oX` çıktı, `--banners` basit banner (nmap kadar güvenilir değil).

## Tuzaklar
- root/raw-socket gerekir. `--rate` çok yüksek ağı boğar ve tespit edilir — lab'da bile makul tut.
- Tek host için abartı; orada doğrudan nmap kullan.

## Güvenlik/kapsam
Yüksek hız = yüksek gürültü + yanlışlıkla DoS riski. Yalnızca yetkili geniş kapsamda, sınırlı `--rate` ile.
