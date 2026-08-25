---
name: nikto
description: Web sunucu zafiyet/yapılandırma tarayıcı; bilinen dosyalar, başlıklar, eski yazılım.
tool: nikto
---

## Kanonik kullanım
`{"hedef": "<host/url>", "secenekler": "-h <host> <ek>"}`. Örn: `-h https://hedef -ssl`.

## Ana flag'ler
- `-h` host (zorunlu), `-ssl` HTTPS, `-p` port, `-Tuning <x>` test sınıfı seçimi.
- `-o rapor.html -Format htm` çıktı, `-useproxy` proxy üzerinden.

## Tuzaklar
- Doğası gereği LOUD ve imza tabanlı — WAF/IDS kolayca yakalar; sessiz recon değildir.
- Yüksek yanlış-pozitif; bulguları elle doğrula.

## Güvenlik/kapsam
Aktif tarama. Yalnızca yetkili hedef; sonuçları teyit etmeden "zafiyet var" deme.
