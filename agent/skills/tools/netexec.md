---
name: netexec
description: Ağ protokol sömürü/enum (SMB/WinRM/LDAP/MSSQL...); credential doğrulama ve lateral hareket. (eski adı crackmapexec)
tool: netexec
---

## Kanonik kullanım
`{"hedef": "<ip/cidr>", "protokol": "<smb|winrm|ldap|mssql|ssh>", "secenekler": "<ek>"}`.
Örn: `-u <kullanici> -p <parola>` veya `-H <ntlm-hash>` (pass-the-hash).

## Ana flag'ler
- Protokol ilk argüman (`smb`, `winrm`, ...). `-u`/`-p` veya `-H` hash, `--local-auth` yerel hesap.
- SMB: `--shares`, `--sam`, `--lsa`, `-x <komut>`; `--continue-on-success` spray.

## Tuzaklar
- Protokolü belirtmezsen çalışmaz — `protokol` her zaman ver.
- Parola spray hesap kilitler; `--continue-on-success` + kilitleme politikasına dikkat.
- `-x`/`--sam`/`--lsa` LOUD ve EDR tetikler.

## Güvenlik/kapsam
Aktif/intrusive (kimlik doğrulama, kod çalıştırma). Yalnızca yetkili domain/hedef; spray öncesi kilit riskini değerlendir.
