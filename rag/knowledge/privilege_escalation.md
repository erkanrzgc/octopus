# Privilege Escalation Kontrol Listeleri (yetkili pentest/CTF)

## Linux yetki yukseltme
- `sudo -l` : parolasiz/izinli sudo komutlari (GTFOBins ile somurulebilir).
- SUID binary'ler: `find / -perm -4000 -type f 2>/dev/null` (sonra GTFOBins'e bak).
- Capabilities: `getcap -r / 2>/dev/null` (ornek cap_setuid).
- Cron isleri: `/etc/crontab`, yazilabilir script cagiran root cron.
- Yazilabilir `/etc/passwd` veya `/etc/shadow`.
- Cekirdek somurusu: eski kernel (`uname -a`) -> bilinen exploit.
- Otomasyon: `linpeas.sh`, `linenum.sh`.

## Windows yetki yukseltme
- `whoami /priv` : token ayricaliklari. **SeImpersonatePrivilege / SeAssignPrimaryToken**
  -> "Potato" saldirilari (JuicyPotato, PrintSpoofer) ile SYSTEM.
- Unquoted service path: bosluk iceren tirnaksiz servis yolu.
- Zayif servis izinleri: `accesschk.exe` ile degistirilebilir servis -> binPath degistir.
- AlwaysInstallElevated: HKLM+HKCU registry 1 ise .msi ile SYSTEM.
- Saklanmis kimlik bilgileri: `cmdkey /list`, kayitli RDP/Group Policy parolalari (GPP cPassword).
- Otomasyon: `winPEAS.exe`, PowerUp (`Invoke-AllChecks`).

## Savunma (her iki taraf)
- Least privilege, gereksiz SUID/servis kaldir, yama yonetimi.
- EDR + process olusturma denetimi (Windows Event ID 4688, Sysmon).
- LAPS (yerel admin parola rotasyonu), uygulama beyaz listesi (AppLocker/WDAC).
