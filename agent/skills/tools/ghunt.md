---
name: ghunt
description: Google hesap OSINT çerçevesi (email, Gaia ID, Drive, geolocate); pasif hesap keşfi.
tool: ghunt
---

## Kanonik kullanım
`{"modul": "<email|gaia|drive|geolocate|spiderdal>", "hedef": "<eposta/id/url/bssid>"}`.
Örn: `email <adres>`, `gaia <id>`, `drive <url>`. Kimlik doğrulama (Google cookie) gerekir — `ghunt login`.

## Ana modüller
- `email` e-postadan hesap bilgisi, `gaia` Gaia ID'den veri, `drive` Drive dosya/klasör analizi.
- `geolocate` BSSID konumu, `spiderdal` Digital Asset Links üzerinden varlık keşfi.
- `--json` dışa aktarım; asenkron çalışır.

## Tuzaklar
- Önce `ghunt login` (tarayıcı eklentisiyle cookie) yoksa modüller çalışmaz.
- Cookie'ler süresi dolar; hata alırsan yeniden login.

## Güvenlik/kapsam
Gerçek bir kişinin Google hesabına OSINT = kişiyi hedefleme. Yalnızca yetkili/rızalı hedef; kapsam (hedef) kilidi uygulanır.
