---
name: metasploit
description: Sömürü/post-exploit framework; modül seçimi, payload, oturum yönetimi. Yüksek risk.
tool: metasploit
---

## Kanonik kullanım
`{"komutlar": "<msfconsole komut dizisi>"}`. Komutları ayrı ver (resource script mantığı):
`use <modul>; set RHOSTS <ip>; set LHOST <ip>; set PAYLOAD <p>; run`.

## Ana komutlar
- `search <cve/urun>`, `use <exploit/...>`, `show options`, `set <OPT> <val>`, `check` (varsa non-exploit doğrulama).
- `set PAYLOAD`, `exploit`/`run`, `sessions -l`, `background`.
- Post: `use post/...`, `set SESSION <id>`.

## Tuzaklar
- `RHOSTS/LHOST/PAYLOAD` set etmeden `run` = başarısız; `show options` ile eksikleri gör.
- `check` destekleyen modülde önce doğrula (gürültü/çökme riskini azaltır).
- Yanlış payload/arch hedefi çökertebilir.

## Güvenlik/kapsam
Aktif sömürü (yüksek etki, geri-dönülmez olabilir). Yalnızca yetkili hedef; exploit öncesi kapsamı teyit et.
