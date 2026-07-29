---
name: engagement-plan
description: Yetkili bir siber güvenlik işini planla — kapsam netleştir, aşamalara böl, en küçük etkili adımı seç.
---

## Ne zaman
Kullanıcı çok adımlı bir iş istediğinde (pentest, CTF, değerlendirme) ilk adımdan önce.

## Akış
1. **Kapsam + yetki**: hedef(ler) kapsam içinde mi, yıkıcı/geri-dönülmez adım var mı? Belirsizlik sonucu değiştirecekse sor, değilse en makul varsayımla devam et.
2. **Aşamalar**: recon → enumerasyon → zafiyet analizi → (yetkiliyse) sömürü → post → rapor. Her aşamada en sessiz yeterli aracı seç.
3. **Araç seçimi**: her adım için doğru aracı ve o aracın skill'ini kullan; gürültü (QUIET/MODERATE/LOUD) seviyesini not et.
4. **Çıktı**: "şu an ne yapıyorum + sırada ne var" olarak net adımlar üret.

## İlke
Süreci işin kendisinden ağır yapma. Düşük riskte izin kovalama; yıkıcı/geri-dönülmez işte önce teyit al.
