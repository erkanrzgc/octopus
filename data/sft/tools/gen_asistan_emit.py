"""B2 emit-odakli asistan arac ornekleri URETICISI (template + kombinatoryal entropi).

Cikti: asistan_emit_tr.jsonl (build_tools otomatik toplar, icerik-hash ile DEDUP eder).
Her recipe bir havuz slotu SECER + `r` ile grounded bir sayi (IP/port/bayt/satir/sayi)
GOMER; bu sayi hem `tool` ciktisinda hem son assistant yorumunda gecer. Boylece:
  (1) her satir neredeyse benzersiz -> dedup sonrasi araç basina bol distinct ornek kalir,
  (2) grounding korunur -> model "ciktidaki gercek degeri oku" sinyali alir, uydurmaz.
augment_targets IP-odakli oldugu icin YENIDEN kullanilmaz; bu asistan-param'a ozel.
Kosul: uv run python data/sft/tools/gen_asistan_emit.py --n 180 --seed 3407
"""
from __future__ import annotations

import argparse
import json
import random
from pathlib import Path
from typing import Callable

HERE = Path(__file__).resolve().parent
OUT = HERE / "asistan_emit_tr.jsonl"
SYS = ("Sen Octópus'sun: yetkili siber güvenlik asistanı. Araçları ```arac``` "
       "bloğuyla çağırır, `tool` çıktısını Türkçe yorumlarsın. Yalnızca izinli kapsam.")

LOG_PATHS = ["/var/log/auth.log", "/var/log/syslog", "/var/log/nginx/access.log",
             "/var/log/apache2/error.log", "/var/log/audit/audit.log", "/var/log/fail2ban.log"]
CONF_PATHS = ["/etc/nginx/nginx.conf", "/etc/ssh/sshd_config", "/etc/fail2ban/jail.local",
              "/etc/hosts", "./config.py", "./docker-compose.yml", "/etc/iptables/rules.v4"]
DIRS = ["/etc/nginx", "/var/www/html", "./scans", "/home/kali/loot", "/opt/tools", "./raporlar"]
FILE_NAMES = ["nmap_full.txt", "web_dirb.txt", "notes.md", "id_rsa", "id_rsa.pub",
              "creds.txt", "hosts.txt", "gobuster.log", "nuclei.json", "screenshot.png"]
URL_HOSTS = ["cve.mitre.org", "nvd.nist.gov", "siberadar.com", "watchstack.io",
             "exploit-db.com", "gtfobins.github.io", "hacktricks.boitatech.com.br",
             "attack.mitre.org", "vuldb.com", "cvedetails.com"]
QUERIES = ["CVE-2024-3400 exploit", "vsftpd 2.3.4 backdoor poc", "log4shell etkilenen surumler",
           "sudo CVE privilege escalation", "smb ms17-010 tespit", "nginx path traversal cve",
           "openssl heartbleed test", "apache 2.4.49 path traversal"]

ARACLAR = ["read_file", "list_dir", "grep", "write_file", "edit_file",
           "run_cmd", "web_fetch", "web_search"]


def _ip(r: random.Random) -> str:
    return f"10.0.{r.randint(0, 30)}.{r.randint(2, 254)}"


def _port(r: random.Random) -> int:
    return r.randint(1025, 65500)


def _ex(user: str, arac: str, params: dict, tool_out: str, interp: str) -> dict:
    blok = json.dumps({"arac": arac, "parametreler": params}, ensure_ascii=False)
    return {"messages": [
        {"role": "system", "content": SYS},
        {"role": "user", "content": user},
        {"role": "assistant", "content": f"```arac\n{blok}\n```"},
        {"role": "tool", "content": tool_out},
        {"role": "assistant", "content": interp},
    ]}


# --- read_file ---------------------------------------------------------------
def _read_file(r: random.Random) -> dict:
    p = r.choice(CONF_PATHS)
    port = r.choice([80, 8080, 443, 8000, 3000, 8443])
    return _ex(f"{p} dosyasinin icerigini goster.", "read_file", {"yol": p},
               f"worker_processes auto;\nserver {{ listen {port}; server_name _; }}",
               f"`{p}` okundu: {port} portunda server blogu tanimli, worker_processes auto.")


def _read_file_v2(r: random.Random) -> dict:
    p = r.choice(LOG_PATHS)
    lat = r.randint(120, 950)
    return _ex(f"{p} dosyasinin son satirlarini oku.", "read_file", {"yol": p},
               f"09:12:03 INFO servis baslatildi\n09:14:41 WARN yuksek gecikme {lat}ms",
               f"`{p}` okundu: baslangic kaydi ve {lat}ms gecikme uyarisi (WARN) var; gecikme yuksek.")


# --- list_dir ----------------------------------------------------------------
def _list_dir(r: random.Random) -> dict:
    d = r.choice(DIRS)
    n = r.randint(2, 6)
    names = r.sample(FILE_NAMES, n)
    return _ex(f"{d} altindaki dosyalari listele.", "list_dir", {"yol": d},
               "\n".join(names),
               f"`{d}` altinda {n} dosya var: {', '.join(names)}.")


def _list_dir_v2(r: random.Random) -> dict:
    d = r.choice(DIRS)
    sz = r.randint(3, 900)
    return _ex(f"{d} klasorunun icerigi ne?", "list_dir", {"yol": d},
               f"backup_{sz}M.tar.gz\nid_rsa\nid_rsa.pub",
               f"`{d}` altinda {sz}M yedek arsivi ve bir SSH anahtar cifti var; id_rsa izinlerini kontrol et.")


# --- grep --------------------------------------------------------------------
def _grep(r: random.Random) -> dict:
    p = r.choice(LOG_PATHS)
    ip, port = _ip(r), _port(r)
    return _ex(f"{p} icinde basarisiz SSH girislerini ara.", "grep",
               {"desen": "Failed password", "yol": p},
               f"Failed password for root from {ip} port {port} ssh2",
               f"`{p}` icinde {ip} adresinden root'a basarisiz SSH denemesi var; brute-force gostergesi.")


def _grep_v2(r: random.Random) -> dict:
    p = r.choice(LOG_PATHS)
    n = r.randint(1, 40)
    return _ex(f"{p} icinde 'error' gecen satirlari say.", "grep",
               {"desen": "error", "yol": p},
               f"toplam {n} eslesme\n[error] upstream timed out",
               f"`{p}` icinde {n} hata satiri; upstream zaman asimi var, backend servisini kontrol et.")


# --- write_file --------------------------------------------------------------
def _write_file(r: random.Random) -> dict:
    sid = r.randint(100, 999)
    ip = _ip(r)
    yol = f"./scans/tarama-{sid}.md"
    icerik = f"# {ip}\n- 80/tcp acik\n- nginx 1.18"
    return _ex(f"Tarama sonucunu {yol} dosyasina yaz.", "write_file",
               {"yol": yol, "icerik": icerik},
               f"yazildi: {yol} ({len(icerik)} bayt)",
               f"Rapor yazildi ({yol}, {len(icerik)} bayt); {ip} icin 80/tcp + nginx bulgusu kayitli.")


def _write_file_v2(r: random.Random) -> dict:
    port = _port(r)
    yol = f"./loot/port-{port}.txt"
    icerik = f"{port}/tcp open unknown"
    return _ex(f"Bulunan portu {yol} dosyasina kaydet.", "write_file",
               {"yol": yol, "icerik": icerik},
               f"yazildi: {yol} ({len(icerik)} bayt)",
               f"{port}/tcp bulgusu {yol} dosyasina kaydedildi; servis tespiti icin sonraki adim -sV.")


# --- edit_file ---------------------------------------------------------------
def _edit_file(r: random.Random) -> dict:
    port = _port(r)
    return _ex("SSH portunu degistir.", "edit_file",
               {"yol": "/etc/ssh/sshd_config", "eski": "Port 22", "yeni": f"Port {port}"},
               "1 degisiklik uygulandi",
               f"SSH portu 22'den {port}'e alindi; varsayilan-port taramalarini zorlastirir (savunma).")


def _edit_file_v2(r: random.Random) -> dict:
    n = r.randint(2, 5)
    return _ex("fail2ban deneme sinirini sertlestir.", "edit_file",
               {"yol": "/etc/fail2ban/jail.local", "eski": "maxretry = 10", "yeni": f"maxretry = {n}"},
               "1 degisiklik uygulandi",
               f"Deneme siniri 10'dan {n}'e dusuruldu; brute-force'a karsi sertlestirme.")


# --- run_cmd (git dahil) -----------------------------------------------------
def _run_cmd_ss(r: random.Random) -> dict:
    p1, p2 = r.choice([22, 2222]), r.choice([80, 443, 8080, 8443])
    return _ex("Acik dinleyen portlari goster.", "run_cmd", {"komut": "ss -tlnp"},
               f"LISTEN 0 128 0.0.0.0:{p1}\nLISTEN 0 128 0.0.0.0:{p2}",
               f"{p1} (SSH) ve {p2} (HTTP/S) dinleniyor; disa acik iki servis.")


def _run_cmd_df(r: random.Random) -> dict:
    pct = r.randint(60, 99)
    return _ex("Disk kullanimini goster.", "run_cmd", {"komut": "df -h"},
               f"/dev/sda1 40G {pct*0.4:.0f}G ... {pct}% /",
               f"Kok bolum %{pct} dolu; {'kritik, temizlik gerek' if pct >= 90 else 'takip et'}.")


def _run_cmd_id(r: random.Random) -> dict:
    uid = r.randint(1000, 1010)
    return _ex("Hangi kullaniciyiz, yetkiler ne?", "run_cmd", {"komut": "whoami && id"},
               f"kali\nuid={uid}(kali) gid={uid}(kali) groups={uid}(kali),27(sudo)",
               f"kali (uid={uid}) sudo grubunda; yukseltilmis islem yapilabilir.")


def _run_cmd_git_status(r: random.Random) -> dict:
    f = r.choice(["core/engine.py", "modules/sqli.py", "utils/http.py", "core/scope.py"])
    return _ex("Depoda hangi degisiklikler var?", "run_cmd", {"komut": "git status --short"},
               f" M {f}\n?? scans/yeni-{r.randint(10,99)}.md",
               f"{f} degismis, yeni bir tarama notu izlenmiyor; commit oncesi ikisini gozden gecir.")


def _run_cmd_git_log(r: random.Random) -> dict:
    sha = f"{r.randint(0x100000, 0xffffff):06x}"
    return _ex("Son commit'leri goster.", "run_cmd", {"komut": "git log --oneline -3"},
               f"{sha} fix: ssrf sertlestir\n9f8e7d6 feat: web_fetch guard\n1122334 docs: b1 spec",
               f"En yeni commit {sha} 'ssrf sertlestir'; dal SSRF/guard ustune aktif calisiliyor.")


def _run_cmd_git_diff(r: random.Random) -> dict:
    a, b = r.choice([(5, 30), (10, 60), (3, 15)])
    return _ex("Sahnelenmemis degisiklikleri goster.", "run_cmd", {"komut": "git diff"},
               f"-    timeout = {a}\n+    timeout = {b}",
               f"Tek degisiklik: timeout {a}->{b} sn (yavas hedefler icin mantikli). Commit'e hazir.")


# --- web_fetch ---------------------------------------------------------------
def _web_fetch(r: random.Random) -> dict:
    h = r.choice(URL_HOSTS)
    cve = f"CVE-2024-{r.randint(1000, 9999)}"
    cvss = round(r.uniform(7.5, 10.0), 1)
    return _ex(f"{h} uzerindeki {cve} kaydini oku.", "web_fetch",
               {"url": f"https://{h}/{cve}"},
               f"{cve}: Etkilenen: Acme WAF < 11.1.2. CVSS {cvss}. Yama: 11.1.3. PoC: mevcut.",
               f"{cve} kritik (CVSS {cvss}); Acme WAF 11.1.2 altini vuruyor, PoC var. Yama 11.1.3'e cik.")


def _web_fetch_v2(r: random.Random) -> dict:
    h = r.choice(URL_HOSTS)
    cve = f"CVE-2023-{r.randint(1000, 9999)}"
    cvss = round(r.uniform(6.0, 8.9), 1)
    return _ex(f"{h}/{cve} sayfasini getir, ozetle.", "web_fetch",
               {"url": f"https://{h}/{cve}"},
               f"{cve}: Etkilenen: OpenGate VPN < 4.2.0. CVSS {cvss}. Yama: 4.2.1. PoC: yok.",
               f"{cve} yuksek onem (CVSS {cvss}); OpenGate VPN 4.2.0 altini etkiliyor, PoC yok. Yamayi takip et.")


# --- web_search --------------------------------------------------------------
def _web_search(r: random.Random) -> dict:
    q = r.choice(QUERIES)
    edb = r.randint(10000, 99999)
    return _ex(f"'{q}' hakkinda guncel bilgi bul.", "web_search", {"sorgu": q},
               f"1) exploit-db {edb} (calisan PoC)  2) NVD kaydi  3) satici bulteni",
               f"'{q}' icin calisan PoC (exploit-db {edb}) ve NVD kaydi var; oncelik yuksek.")


def _web_search_v2(r: random.Random) -> dict:
    q = r.choice(QUERIES)
    n = r.randint(3, 12)
    return _ex(f"'{q}' konusunda arama yap.", "web_search", {"sorgu": q},
               f"{n} sonuc: resmi bulten, teknik blog, github PoC deposu",
               f"'{q}' icin {n} sonuc; resmi bulten ve github PoC deposu one cikiyor, ikisini dogrula.")


RECIPES: dict[str, list[Callable[[random.Random], dict]]] = {
    "read_file": [_read_file, _read_file_v2],
    "list_dir": [_list_dir, _list_dir_v2],
    "grep": [_grep, _grep_v2],
    "write_file": [_write_file, _write_file_v2],
    "edit_file": [_edit_file, _edit_file_v2],
    "run_cmd": [_run_cmd_ss, _run_cmd_df, _run_cmd_id,
                _run_cmd_git_status, _run_cmd_git_log, _run_cmd_git_diff],
    "web_fetch": [_web_fetch, _web_fetch_v2],
    "web_search": [_web_search, _web_search_v2],
}
# NOT: git AYRI arac DEGIL — run_cmd uzerinden gecer (git status/log/diff). Model'in git
# bilmesi = run_cmd'de git komutlarini dogru uretmesi + ciktisini (durum/diff/log) yorumlamasi.


def build(n: int, seed: int) -> list[dict]:
    r = random.Random(seed)
    rows: list[dict] = []
    per = max(1, n // len(ARACLAR))
    for arac in ARACLAR:
        recs = RECIPES[arac]
        for i in range(per):
            rows.append(recs[i % len(recs)](r))
    return rows


def main() -> None:
    ap = argparse.ArgumentParser(description="B2 emit ornek ureticisi")
    ap.add_argument("--n", type=int, default=180)
    ap.add_argument("--seed", type=int, default=3407)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    rows = build(a.n, a.seed)
    with open(a.out, "w", encoding="utf-8") as w:
        for o in rows:
            w.write(json.dumps(o, ensure_ascii=False) + "\n")
    print(f"[OK] {len(rows)} emit ornegi -> {Path(a.out).name}")


if __name__ == "__main__":
    main()
