# Kerberoasting (MITRE ATT&CK T1558.003)

Kerberoasting, Active Directory ortaminda **SPN (ServicePrincipalName) tanimli
servis hesaplarinin** parolalarini cevrimdisi kirmayi hedefleyen bir saldiridir.
T1558 "Steal or Forge Kerberos Tickets" taktiginin alt teknigidir (T1558.003).

## Nasil calisir (dogru mekanizma)
1. Saldirgan, AD'de **kimligi dogrulanmis HERHANGI bir domain kullanicisi** olur
   (ozel yetki GEREKMEZ).
2. SPN'i olan bir servis hesabi icin Kerberos servis bileti ister (TGS-REP).
3. Bu TGS bileti, **servis hesabinin parola turevli anahtariyla (NTLM hash)**
   sifrelenmistir. Eski sistemlerde RC4 (etype 0x17) kullanilir — kirilmasi kolaydir.
4. Saldirgan bileti diskten alir ve **CEVRIMDISI** kirar (ornek: hashcat mod 13100).
   Cevrimdisi oldugu icin hesap kilitlenmesi tetiklenmez, fark edilmesi zordur.
5. Parola bulunursa servis hesabinin yetkileriyle erisim saglanir.

NOT: Kerberoasting TGT degil **TGS** biletini hedefler ve parola tahmini
cevrimdisi yapilir. "100'den fazla TGT" gibi bir esik yoktur.

## Tespit
- **Event ID 4769** (Kerberos servis bileti istendi) — ozellikle RC4 (0x17)
  sifreleme ve kisa surede cok sayida farkli SPN istegi.
- Honeypot SPN hesaplari (decoy) olusturup istek gelirse alarm.
- Tek kullanicidan anormal sayida TGS istegi.

## Azaltma
- Servis hesaplari icin **uzun, karmasik parolalar** (25+ karakter) veya
  **Group Managed Service Accounts (gMSA)** kullan (otomatik 120+ karakter parola).
- RC4 yerine **AES** sifrelemeyi zorunlu kil.
- Gereksiz SPN'leri kaldir, least privilege uygula.
- Servis hesaplarini Protected Users grubuna alma/izleme.
