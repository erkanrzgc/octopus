# Active Directory Saldirilari (yetkili red team / savunma)

## Kesif (Recon)
- **BloodHound / SharpHound**: AD'deki saldiri yollarini (kim kime nasil ulasir) graf olarak cikarir.
- LDAP/SMB enum: kullanicilar, gruplar, SPN'ler, GPO'lar, trust'lar.

## Kimlik Bilgisi Erisimi (Credential Access)
- **Kerberoasting** (T1558.003): SPN'li servis hesaplarinin TGS biletini alip cevrimdisi kir (hashcat 13100). Bkz. kerberoasting.md.
- **AS-REP Roasting** (T1558.004): "Do not require Kerberos preauth" acik hesaplarda AS-REP'i alip kir (hashcat 18200).
- **LLMNR/NBT-NS/mDNS zehirleme**: `Responder` ile ag yayinlarina sahte cevap -> NetNTLM hash yakala.
- **NTLM Relay**: yakalanan kimlik dogrulamayi baska hosta relay et (`ntlmrelayx`); SMB imzasi kapaliysa etkili.

## Yanal Hareket (Lateral Movement)
- **Pass-the-Hash (PtH)** (T1550.002): NTLM hash ile parola olmadan kimlik dogrula.
- **Pass-the-Ticket (PtT)** (T1550.003): calinan Kerberos biletini kullan.
- **Overpass-the-Hash**: NTLM hash'ten Kerberos TGT al.

## Yetki Yukseltme / Domain Ele Gecirme
- **DCSync** (T1003.006): replication hakkiyla DC'den tum hash'leri cek (Mimikatz / `secretsdump.py`).
- **Golden Ticket**: `krbtgt` hash'i ile sahte TGT uret -> tum domain. **Silver Ticket**: servis hesabi hash'i ile sahte TGS.
- **ADCS (Certified Pre-Owned)**: zayif sertifika sablonlari (ESC1-ESC8) -> domain admin.

## Savunma
- Tiered admin modeli, **LAPS** (yerel admin parola rotasyonu), Protected Users grubu.
- **krbtgt** parolasini periyodik (2x) rotasyon; servis hesaplarinda gMSA + AES.
- NTLM'i mumkun oldukca kapat, SMB imzalama zorunlu, Credential Guard.
- Izleme: Event ID 4769 (RC4 anomalileri), 4624/4625, 4662 (DCSync), 4768.
- ADCS sablonlarini sertlestir; BloodHound ile kendi saldiri yollarini periyodik denetle.
