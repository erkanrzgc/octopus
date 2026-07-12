"""B2 emit-odaklı asistan araç örnekleri ÜRETİCİSİ (template + kombinatoryal entropi).

Çıktı: asistan_emit_tr.jsonl (build_tools otomatik toplar, içerik-hash ile DEDUP eder).
Her recipe bir havuz slotu SEÇER + `r` ile grounded bir sayı (IP/port/bayt/satır/sayı)
GÖMER; bu sayı hem `tool` çıktısında hem son assistant yorumunda geçer. Böylece:
  (1) her satır neredeyse benzersiz -> dedup sonrası araç başına bol distinct örnek kalır,
  (2) grounding korunur -> model "çıktıdaki gerçek değeri oku" sinyali alır, uydurmaz.
Türkçe: kullanıcı + asistan metni diakritikli (Türkçe-first korpusla tutarlı); `tool`
çıktısı teknik-ASCII kalır (log/komut satırları). augment_targets IP-odaklı olduğu için
YENİDEN kullanılmaz; bu asistan-parametrelerine özeldir.
Koşul: uv run python data/sft/tools/gen_asistan_emit.py --n 180 --seed 3407
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
QUERIES = ["CVE-2024-3400 exploit", "vsftpd 2.3.4 backdoor poc", "log4shell etkilenen sürümler",
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
    return _ex(f"{p} dosyasının içeriğini göster.", "read_file", {"yol": p},
               f"worker_processes auto;\nserver {{ listen {port}; server_name _; }}",
               f"`{p}` okundu: {port} portunda server bloğu tanımlı, worker_processes auto.")


def _read_file_v2(r: random.Random) -> dict:
    p = r.choice(LOG_PATHS)
    lat = r.randint(120, 950)
    return _ex(f"{p} dosyasının son satırlarını oku.", "read_file", {"yol": p},
               f"09:12:03 INFO servis baslatildi\n09:14:41 WARN yuksek gecikme {lat}ms",
               f"`{p}` okundu: başlangıç kaydı ve {lat}ms gecikme uyarısı (WARN) var; gecikme yüksek.")


# --- list_dir ----------------------------------------------------------------
def _list_dir(r: random.Random) -> dict:
    d = r.choice(DIRS)
    n = r.randint(2, 6)
    names = r.sample(FILE_NAMES, n)
    return _ex(f"{d} altındaki dosyaları listele.", "list_dir", {"yol": d},
               "\n".join(names),
               f"`{d}` altında {n} dosya var: {', '.join(names)}.")


def _list_dir_v2(r: random.Random) -> dict:
    d = r.choice(DIRS)
    sz = r.randint(3, 900)
    return _ex(f"{d} klasörünün içeriği ne?", "list_dir", {"yol": d},
               f"backup_{sz}M.tar.gz\nid_rsa\nid_rsa.pub",
               f"`{d}` altında {sz}M yedek arşivi ve bir SSH anahtar çifti var; id_rsa izinlerini kontrol et.")


# --- grep --------------------------------------------------------------------
def _grep(r: random.Random) -> dict:
    p = r.choice(LOG_PATHS)
    ip, port = _ip(r), _port(r)
    return _ex(f"{p} içinde başarısız SSH girişlerini ara.", "grep",
               {"desen": "Failed password", "yol": p},
               f"Failed password for root from {ip} port {port} ssh2",
               f"`{p}` içinde {ip} adresinden root'a başarısız SSH denemesi var; brute-force göstergesi.")


def _grep_v2(r: random.Random) -> dict:
    p = r.choice(LOG_PATHS)
    n = r.randint(1, 40)
    return _ex(f"{p} içinde 'error' geçen satırları say.", "grep",
               {"desen": "error", "yol": p},
               f"toplam {n} eslesme\n[error] upstream timed out",
               f"`{p}` içinde {n} hata satırı; upstream zaman aşımı var, backend servisini kontrol et.")


# --- write_file --------------------------------------------------------------
def _write_file(r: random.Random) -> dict:
    sid = r.randint(100, 999)
    ip = _ip(r)
    yol = f"./scans/tarama-{sid}.md"
    icerik = f"# {ip}\n- 80/tcp acik\n- nginx 1.18"
    return _ex(f"Tarama sonucunu {yol} dosyasına yaz.", "write_file",
               {"yol": yol, "icerik": icerik},
               f"yazildi: {yol} ({len(icerik)} bayt)",
               f"Rapor yazıldı ({yol}, {len(icerik)} bayt); {ip} için 80/tcp + nginx bulgusu kayıtlı.")


def _write_file_v2(r: random.Random) -> dict:
    port = _port(r)
    yol = f"./loot/port-{port}.txt"
    icerik = f"{port}/tcp open unknown"
    return _ex(f"Bulunan portu {yol} dosyasına kaydet.", "write_file",
               {"yol": yol, "icerik": icerik},
               f"yazildi: {yol} ({len(icerik)} bayt)",
               f"{port}/tcp bulgusu {yol} dosyasına kaydedildi; servis tespiti için sonraki adım -sV.")


# --- edit_file ---------------------------------------------------------------
def _edit_file(r: random.Random) -> dict:
    port = _port(r)
    return _ex("SSH portunu değiştir.", "edit_file",
               {"yol": "/etc/ssh/sshd_config", "eski": "Port 22", "yeni": f"Port {port}"},
               "1 degisiklik uygulandi",
               f"SSH portu 22'den {port}'e alındı; varsayılan-port taramalarını zorlaştırır (savunma).")


def _edit_file_v2(r: random.Random) -> dict:
    n = r.randint(2, 5)
    return _ex("fail2ban deneme sınırını sertleştir.", "edit_file",
               {"yol": "/etc/fail2ban/jail.local", "eski": "maxretry = 10", "yeni": f"maxretry = {n}"},
               "1 degisiklik uygulandi",
               f"Deneme sınırı 10'dan {n}'e düşürüldü; brute-force'a karşı sertleştirme.")


# --- run_cmd (git dahil) -----------------------------------------------------
def _run_cmd_ss(r: random.Random) -> dict:
    p1, p2 = r.choice([22, 2222]), r.choice([80, 443, 8080, 8443])
    return _ex("Açık dinleyen portları göster.", "run_cmd", {"komut": "ss -tlnp"},
               f"LISTEN 0 128 0.0.0.0:{p1}\nLISTEN 0 128 0.0.0.0:{p2}",
               f"{p1} (SSH) ve {p2} (HTTP/S) dinleniyor; dışa açık iki servis.")


def _run_cmd_df(r: random.Random) -> dict:
    pct = r.randint(60, 99)
    return _ex("Disk kullanımını göster.", "run_cmd", {"komut": "df -h"},
               f"/dev/sda1 40G {pct*0.4:.0f}G ... {pct}% /",
               f"Kök bölüm %{pct} dolu; {'kritik, temizlik gerek' if pct >= 90 else 'takip et'}.")


def _run_cmd_id(r: random.Random) -> dict:
    uid = r.randint(1000, 1010)
    return _ex("Hangi kullanıcıyız, yetkiler ne?", "run_cmd", {"komut": "whoami && id"},
               f"kali\nuid={uid}(kali) gid={uid}(kali) groups={uid}(kali),27(sudo)",
               f"kali (uid={uid}) sudo grubunda; yükseltilmiş işlem yapılabilir.")


def _run_cmd_git_status(r: random.Random) -> dict:
    f = r.choice(["core/engine.py", "modules/sqli.py", "utils/http.py", "core/scope.py"])
    return _ex("Depoda hangi değişiklikler var?", "run_cmd", {"komut": "git status --short"},
               f" M {f}\n?? scans/yeni-{r.randint(10,99)}.md",
               f"{f} değişmiş, yeni bir tarama notu izlenmiyor; commit öncesi ikisini gözden geçir.")


def _run_cmd_git_log(r: random.Random) -> dict:
    sha = f"{r.randint(0x100000, 0xffffff):06x}"
    return _ex("Son commit'leri göster.", "run_cmd", {"komut": "git log --oneline -3"},
               f"{sha} fix: ssrf sertlestir\n9f8e7d6 feat: web_fetch guard\n1122334 docs: b1 spec",
               f"En yeni commit {sha} 'ssrf sertleştir'; dal SSRF/guard üstüne aktif çalışılıyor.")


def _run_cmd_git_diff(r: random.Random) -> dict:
    a, b = r.choice([(5, 30), (10, 60), (3, 15)])
    return _ex("Sahnelenmemiş değişiklikleri göster.", "run_cmd", {"komut": "git diff"},
               f"-    timeout = {a}\n+    timeout = {b}",
               f"Tek değişiklik: timeout {a}->{b} sn (yavaş hedefler için mantıklı). Commit'e hazır.")


# --- web_fetch ---------------------------------------------------------------
def _sev(cvss: float) -> str:
    return "kritik" if cvss >= 9.0 else "yüksek önem"


def _web_fetch(r: random.Random) -> dict:
    h = r.choice(URL_HOSTS)
    cve = f"CVE-2024-{r.randint(1000, 9999)}"
    cvss = round(r.uniform(7.5, 10.0), 1)
    return _ex(f"{h} üzerindeki {cve} kaydını oku.", "web_fetch",
               {"url": f"https://{h}/{cve}"},
               f"{cve}: Etkilenen: Acme WAF < 11.1.2. CVSS {cvss}. Yama: 11.1.3. PoC: mevcut.",
               f"{cve} {_sev(cvss)} (CVSS {cvss}); Acme WAF 11.1.2 altını vuruyor, PoC var. Yama 11.1.3'e çık.")


def _web_fetch_v2(r: random.Random) -> dict:
    h = r.choice(URL_HOSTS)
    cve = f"CVE-2023-{r.randint(1000, 9999)}"
    cvss = round(r.uniform(6.0, 8.9), 1)
    return _ex(f"{h}/{cve} sayfasını getir, özetle.", "web_fetch",
               {"url": f"https://{h}/{cve}"},
               f"{cve}: Etkilenen: OpenGate VPN < 4.2.0. CVSS {cvss}. Yama: 4.2.1. PoC: yok.",
               f"{cve} {_sev(cvss)} (CVSS {cvss}); OpenGate VPN 4.2.0 altını etkiliyor, PoC yok. Yamayı takip et.")


# --- web_search --------------------------------------------------------------
def _web_search(r: random.Random) -> dict:
    q = r.choice(QUERIES)
    edb = r.randint(10000, 99999)
    return _ex(f"'{q}' hakkında güncel bilgi bul.", "web_search", {"sorgu": q},
               f"1) exploit-db {edb} (calisan PoC)  2) NVD kaydi  3) satici bulteni",
               f"'{q}' için çalışan PoC (exploit-db {edb}) ve NVD kaydı var; öncelik yüksek.")


def _web_search_v2(r: random.Random) -> dict:
    q = r.choice(QUERIES)
    n = r.randint(3, 12)
    return _ex(f"'{q}' konusunda arama yap.", "web_search", {"sorgu": q},
               f"{n} sonuc: resmi bulten, teknik blog, github PoC deposu",
               f"'{q}' için {n} sonuç; resmi bülten ve github PoC deposu öne çıkıyor, ikisini doğrula.")


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
# NOT: git AYRI araç DEĞİL — run_cmd üzerinden geçer (git status/log/diff). Model'in git
# bilmesi = run_cmd'de git komutlarını doğru üretmesi + çıktısını (durum/diff/log) yorumlaması.


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
    ap = argparse.ArgumentParser(description="B2 emit örnek üreticisi")
    ap.add_argument("--n", type=int, default=180)
    ap.add_argument("--seed", type=int, default=3407)
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    rows = build(a.n, a.seed)
    with open(a.out, "w", encoding="utf-8") as w:
        for o in rows:
            w.write(json.dumps(o, ensure_ascii=False) + "\n")
    print(f"[OK] {len(rows)} emit örneği -> {Path(a.out).name}")


if __name__ == "__main__":
    main()
