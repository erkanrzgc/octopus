---
name: nuclei
description: Şablon (template) tabanlı hızlı zafiyet tarayıcı; CVE/misconfig/exposure tespiti.
tool: nuclei
---

## Kanonik kullanım
`{"url": "<hedef>", "secenekler": "<ek>"}` veya toplu `-l <hosts.txt>`. Örn: `-u https://h -severity high,critical`.

## Ana flag'ler
- `-u` tek hedef / `-l` liste, `-t <template/dizin>` seçili şablon, `-tags cve,exposure`.
- `-severity low..critical` filtre, `-rl <rate>` istek hızı, `-o` çıktı.
- `-update-templates` şablonları güncelle.

## Tuzaklar
- Eski şablonlar = eksik/yanlış sonuç; gerekirse `-update-templates`.
- Tüm şablonları çalıştırmak çok LOUD; `-tags`/`-severity` ile daralt.

## Güvenlik/kapsam
Aktif tarama. Kapsam içi hedef; kritik bulguları elle doğrula (nuclei eşleşmesi = ipucu, kanıt değil).
