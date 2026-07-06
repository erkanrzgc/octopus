# Olay Mudahale (IR) ve SOC Temelleri (blue team)

## IR Yasam Dongusu
- **NIST SP 800-61**: 1) Preparation 2) Detection & Analysis
  3) Containment, Eradication & Recovery 4) Post-Incident Activity.
- **SANS PICERL**: Preparation, Identification, Containment, Eradication,
  Recovery, Lessons Learned.

## Onemli Windows Event ID'leri (Security log)
- 4624 basarili oturum acma · 4625 basarisiz oturum acma · 4634 oturum kapatma.
- 4672 ozel ayricaliklarla oturum (admin) · 4648 explicit credential ile logon.
- 4688 yeni surec olusturma (komut satiri denetimi acik olmali).
- 4720 kullanici olusturuldu · 4728/4732 gruba ekleme.
- 4769 Kerberos servis bileti (Kerberoasting tespiti) · 4768 TGT istegi.
- 4698 zamanlanmis gorev olusturuldu · 7045 yeni servis kuruldu.
- 4104 PowerShell ScriptBlock loglama · 1102 guvenlik logu temizlendi (supheli!).

## Triyaj akisi (supheli oturum/olay)
1. Kapsam: hangi host/kullanici/zaman? Etkilenen varliklari belirle.
2. Dogrula: log korelasyonu (SIEM), kaynak IP/cografya, calisma saati disi mi?
3. Sinifla: gercek pozitif mi, yanlis alarm mi; ciddiyet/etki.
4. Kontrol altina al: hesabi devre disi birak, host'u izole et, oturumlari iptal et.
5. Kanit topla: bellek/disk imaji, log saklama (zaman damgali).
6. Temizle & kurtar: zararliyi kaldir, parola reset, yama; izleyerek geri al.
7. Ders cikar: kok neden, tespit kuralini iyilestir.

## Sigma
- Saglayicidan bagimsiz, YAML tabanli tespit kurali formati; SIEM sorgusuna cevrilir
  (Splunk, Elastic, Sentinel). Ornek: supheli PowerShell (`EncodedCommand`,
  `IEX (New-Object Net.WebClient)`) icin detection deseni.
- MITRE ATT&CK teknikleriyle eslestirilir (ornek T1059.001 PowerShell).
