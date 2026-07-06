# MITRE ATT&CK — Taktikler ve Onemli Teknikler (Enterprise)

MITRE ATT&CK, gercek saldirgan davranislarini taktik (NEDEN) ve teknik (NASIL)
olarak siniflandiran bir cercevedir. Enterprise matrisi 14 taktik icerir.

## 14 Taktik (dogru ID'ler)
- TA0043 Reconnaissance (Kesif)
- TA0042 Resource Development (Kaynak Gelistirme)
- TA0001 Initial Access (Ilk Erisim)
- TA0002 Execution (Calistirma)
- TA0003 Persistence (Kalicilik)
- TA0004 Privilege Escalation (Yetki Yukseltme)
- TA0005 Defense Evasion (Savunma Atlatma)
- TA0006 Credential Access (Kimlik Bilgisi Erisimi)
- TA0007 Discovery (Kesfetme)
- TA0008 Lateral Movement (Yanal Hareket)
- TA0009 Collection (Toplama)
- TA0011 Command and Control / C2 (Komuta Kontrol)
- TA0010 Exfiltration (Sizdirma)
- TA0040 Impact (Etki)

## Privilege Escalation (TA0004) — onemli teknikler ve savunma
- T1548 Abuse Elevation Control Mechanism: sudo, setuid, Windows UAC bypass.
  Savunma: UAC en yuksek seviye, sudo loglama, least privilege.
- T1068 Exploitation for Privilege Escalation: cekirdek/surucu zafiyeti somurme.
  Savunma: yama yonetimi, exploit korumalari.
- T1055 Process Injection: baska surece kod enjekte etme.
  Savunma: EDR, sysmon ile process izleme.
- T1053 Scheduled Task/Job: zamanlanmis gorevle yuksek yetki.
  Savunma: gorev olusturma denetimi (Event ID 4698).
- T1078 Valid Accounts: mevcut ayricalikli hesaplari kullanma.
  Savunma: MFA, ayricalikli hesap izleme.

## Lateral Movement (TA0008)
- T1021 Remote Services: RDP (T1021.001), SMB/Admin Shares (T1021.002), SSH (T1021.004).
- T1550 Use Alternate Authentication Material: Pass-the-Hash (T1550.002),
  Pass-the-Ticket (T1550.003).
- T1570 Lateral Tool Transfer.
  Savunma: ag segmentasyonu, SMB imzalama, LAPS, MFA.

## Credential Access (TA0006)
- T1003 OS Credential Dumping: LSASS (T1003.001), /etc/shadow, NTDS.dit.
- T1110 Brute Force.
- T1558 Steal or Forge Kerberos Tickets: Kerberoasting (T1558.003),
  AS-REP Roasting (T1558.004), Golden Ticket (T1558.001).
  Savunma: Credential Guard, LSASS koruma, guclu parolalar, gMSA.
