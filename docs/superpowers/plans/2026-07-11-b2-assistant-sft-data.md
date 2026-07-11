# B2 — Asistan Araç SFT Verisi Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 8 asistan aracını (read_file, list_dir, grep, write_file, edit_file, run_cmd, web_fetch, web_search) modele öğreten ~300 örneklik SFT verisi üret — hem doğru ```arac``` blogu (emit) hem `tool` çıktısını sadık yorumlama (anlama).

**Architecture:** Hibrit authoring. Düz emit örnekleri deterministik bir jeneratörle (`gen_asistan_emit.py`) yol/URL/sorgu çeşitliliğinden üretilir. Yüksek-sinyal anlama/zincir/ret örnekleri elle yazılır. Üç jsonl `data/sft/tools/` altına düşer; `build_tools.py` otomatik toplar, doğrular, denetler ve `tools_dist/octopus_tools_tr.jsonl`'i yeniden üretir. Retrain YOK — çıktı A+C+D ile tek büyük retrain'e gider.

**Tech Stack:** Python 3 (stdlib: json, random, argparse, pathlib), pytest, uv.

## Global Constraints

- Marka `ó` yalnız modelin konuşmasında/dokümanda; **dosya yolları düz ASCII** (`asistan_*`, `gen_asistan_emit.py`). — CLAUDE.md
- Parametre adları katalogla birebir: `read_file(yol)`, `list_dir(yol)`, `grep(desen,yol)`, `write_file(yol,icerik)`, `edit_file(yol,eski,yeni)`, `run_cmd(komut)`, `web_fetch(url)`, `web_search(sorgu)`. — spec §5
- Blok formatı: ` ```arac\n{"arac":"<ad>","parametreler":{...}}\n``` `. Her satır `{"messages":[...]}`; `messages>=3`, `roles[0]=="system"`, assistant'ta ≥1 arac bloğu VEYA "yapmam". — `build_tools._valid`
- `target_audit` GEÇTI kalmalı: tek hedef ≤ %6, hostname payı ≥ %20. `url` alanı sayılır; `yol/komut/sorgu` sayılmaz. — `build_tools.target_audit`
- Bağlam siber/sysadmin ağırlıklı. Yorumlar kısa + spesifik (BalanceSFT: uzun yorum sinyali boğar). — spec §2, §10
- Jeneratör deterministik (`random.Random(seed)`, varsayılan seed 3407) → reproduce.
- Paketleme uv: `uv run python ...`, `uv run pytest`.

---

### Task 1: Emit jeneratörü — düz tekli örnekler (~180)

**Files:**
- Create: `data/sft/tools/gen_asistan_emit.py`
- Create (üretilen): `data/sft/tools/asistan_emit_tr.jsonl`
- Test: `tests/data/test_gen_asistan_emit.py`

**Interfaces:**
- Produces: `build(n:int, seed:int) -> list[dict]` (her dict `{"messages":[...]}`); `main()` CLI `--n`/`--seed`/`--out` ile jsonl yazar. `RECIPES: dict[str, list[Callable[[random.Random], tuple]]]` — araç adı → recipe listesi; her recipe `(user, params, tool_out, interp)` döndürür.
- Consumes: yok (stdlib).

- [ ] **Step 1: Başarısız testi yaz**

`tests/data/test_gen_asistan_emit.py`:

```python
import json
from data.sft.tools.gen_asistan_emit import build, ARACLAR

def test_deterministic():
    assert build(40, 3407) == build(40, 3407)

def test_all_tools_covered():
    rows = build(160, 3407)
    seen = set()
    for o in rows:
        for m in o["messages"]:
            if m["role"] == "assistant" and "```arac" in m["content"]:
                blk = m["content"].split("```arac")[1].split("```")[0].strip()
                seen.add(json.loads(blk)["arac"])
    assert set(ARACLAR) <= seen, f"eksik: {set(ARACLAR) - seen}"

def test_schema_valid():
    for o in build(80, 3407):
        msgs = o["messages"]
        assert msgs[0]["role"] == "system" and len(msgs) >= 3
        assert any("```arac" in m["content"] for m in msgs if m["role"] == "assistant")

def test_web_fetch_url_host_diversity():
    rows = build(160, 3407)
    hosts = []
    for o in rows:
        for m in o["messages"]:
            if m["role"] == "assistant" and '"web_fetch"' in m["content"]:
                blk = m["content"].split("```arac")[1].split("```")[0].strip()
                url = json.loads(blk)["parametreler"]["url"]
                hosts.append(url.split("/")[2])
    assert len(set(hosts)) >= 6, "web_fetch url host cesitliligi dusuk"
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `uv run pytest tests/data/test_gen_asistan_emit.py -v`
Expected: FAIL — `ModuleNotFoundError` / `ImportError: cannot import name 'build'`

- [ ] **Step 3: Jeneratörü yaz**

`data/sft/tools/gen_asistan_emit.py`:

```python
"""B2 emit-odakli asistan arac ornekleri URETICISI (template + cesitlilik).
Cikti: asistan_emit_tr.jsonl (build_tools otomatik toplar).
augment_targets IP-odakli oldugu icin YENIDEN kullanilmaz; bu asistan-param'a ozel.
Kosul: uv run python data/sft/tools/gen_asistan_emit.py --n 180 --seed 3407
"""
from __future__ import annotations
import json, random, argparse
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
DIRS = ["/etc/nginx", "/var/www/html", "./scans", "/home/kali/loot", "/opt/tools"]
URL_HOSTS = ["cve.mitre.org", "nvd.nist.gov", "siberadar.com", "watchstack.io",
             "exploit-db.com", "gtfobins.github.io", "hacktricks.boitatech.com.br",
             "attack.mitre.org", "vuldb.com", "cvedetails.com"]
QUERIES = ["CVE-2024-3400 exploit", "vsftpd 2.3.4 backdoor poc", "log4shell etkilenen surumler",
           "sudo CVE privilege escalation", "smb ms17-010 tespit", "nginx path traversal cve"]

ARACLAR = ["read_file", "list_dir", "grep", "write_file", "edit_file",
           "run_cmd", "web_fetch", "web_search"]


def _ex(user: str, arac: str, params: dict, tool_out: str, interp: str) -> dict:
    blok = json.dumps({"arac": arac, "parametreler": params}, ensure_ascii=False)
    return {"messages": [
        {"role": "system", "content": SYS},
        {"role": "user", "content": user},
        {"role": "assistant", "content": f"```arac\n{blok}\n```"},
        {"role": "tool", "content": tool_out},
        {"role": "assistant", "content": interp},
    ]}


def _read_file(r: random.Random) -> dict:
    p = r.choice(CONF_PATHS)
    return _ex(f"{p} dosyasinin icerigini goster.", "read_file", {"yol": p},
               "worker_processes auto;\nserver { listen 80; server_name _; }",
               f"`{p}` okundu: 80 portunda server blogu, worker_processes auto.")


def _list_dir(r: random.Random) -> dict:
    d = r.choice(DIRS)
    return _ex(f"{d} altindaki dosyalari listele.", "list_dir", {"yol": d},
               "nmap_full.txt\nweb_dirb.txt\nnotes.md",
               f"`{d}` altinda 3 dosya var; tarama ciktilari (nmap/dirb) ve not dosyasi.")


def _grep(r: random.Random) -> dict:
    p = r.choice(LOG_PATHS)
    return _ex(f"{p} icinde basarisiz SSH girislerini ara.", "grep",
               {"desen": "Failed password", "yol": p},
               "Failed password for root from 10.0.0.9 port 51512 ssh2",
               f"`{p}` icinde root'a basarisiz SSH denemesi var (10.0.0.9). Brute-force gostergesi.")


def _write_file(r: random.Random) -> dict:
    return _ex("Tarama sonucunu ./scans/ozet.md dosyasina yaz.", "write_file",
               {"yol": "./scans/ozet.md", "icerik": "# Ozet\n- 80/tcp acik\n- nginx 1.18"},
               "yazildi: ./scans/ozet.md (42 bayt)",
               "Ozet dosyasi yazildi; 80/tcp ve nginx bulgusu kayit altinda.")


def _edit_file(r: random.Random) -> dict:
    return _ex("nginx.conf'ta server_tokens'i kapat.", "edit_file",
               {"yol": "/etc/nginx/nginx.conf", "eski": "server_tokens on;", "yeni": "server_tokens off;"},
               "1 degisiklik uygulandi",
               "server_tokens kapatildi; surum sizintisi engellendi (savunma sertlestirme).")


def _run_cmd(r: random.Random) -> dict:
    return _ex("Acik dinleyen portlari goster.", "run_cmd", {"komut": "ss -tlnp"},
               "LISTEN 0 128 0.0.0.0:22\nLISTEN 0 128 0.0.0.0:80",
               "22 (SSH) ve 80 (HTTP) dinleniyor; disa acik iki servis.")


def _web_fetch(r: random.Random) -> dict:
    h = r.choice(URL_HOSTS)
    cve = f"CVE-2024-{r.randint(1000, 9999)}"
    return _ex(f"{h} uzerindeki {cve} kaydini oku.", "web_fetch",
               {"url": f"https://{h}/{cve}"},
               f"{cve}: Etkilenen: Acme WAF < 11.1.2. CVSS 9.8. Yama: 11.1.3. PoC: mevcut.",
               f"{cve} kritik (CVSS 9.8); Acme WAF 11.1.2 altini vuruyor, PoC var. Yama 11.1.3'e cik.")


def _web_search(r: random.Random) -> dict:
    q = r.choice(QUERIES)
    return _ex(f"'{q}' hakkinda guncel bilgi bul.", "web_search", {"sorgu": q},
               "1) exploit-db 51234 (calisan PoC)  2) NVD kaydi  3) satici bulteni",
               f"'{q}' icin calisan PoC (exploit-db 51234) ve NVD kaydi var; oncelik yuksek.")


RECIPES: dict[str, list[Callable[[random.Random], dict]]] = {
    "read_file": [_read_file], "list_dir": [_list_dir], "grep": [_grep],
    "write_file": [_write_file], "edit_file": [_edit_file], "run_cmd": [_run_cmd],
    "web_fetch": [_web_fetch], "web_search": [_web_search],
}


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
```

> **Not (çeşitlilik derinleştirme, uygulama sırasında):** yukarıdaki her `_xxx` recipe'i tek varyant üretiyor; `build` aynı recipe'i `per` kez çağırıp `rng` ile havuzdan farklı değer seçtiği için yol/URL çeşitlenir ama tümce iskeleti sabit kalır. Ezber riskini düşürmek için her araca 2-3 tümce iskeleti ekle (recipe listesine ikinci/üçüncü fonksiyon) — `test_web_fetch_url_host_diversity` ve `build_tools.target_audit` yeşil kaldığı sürece serbest. En az `web_fetch` ve `web_search` için 2'şer iskelet ekle (audit `url` çeşitliliği için kritik).

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `uv run pytest tests/data/test_gen_asistan_emit.py -v`
Expected: PASS (4 test)

- [ ] **Step 5: Jeneratörü çalıştır, çıktıyı üret**

Run: `uv run python data/sft/tools/gen_asistan_emit.py --n 180 --seed 3407`
Expected: `[OK] 176 emit ornegi -> asistan_emit_tr.jsonl` (8×22=176; per=180//8=22)

- [ ] **Step 6: Commit**

```bash
git add data/sft/tools/gen_asistan_emit.py data/sft/tools/asistan_emit_tr.jsonl tests/data/test_gen_asistan_emit.py
git commit -m "feat(b2): asistan emit ornek ureticisi (~180, template+cesitlilik)"
```

---

### Task 2: Anlama örnekleri — elle (~70)

**Files:**
- Create: `data/sft/tools/asistan_tr.jsonl`
- Test: `tests/data/test_asistan_comprehension.py`

**Interfaces:**
- Consumes: yok (saf veri dosyası). `build_tools._valid` + `target_audit` bu satırları da okur.
- Produces: `data/sft/tools/asistan_tr.jsonl` — dört anlama alt-kategorisi.

**Anlama alt-kategorileri (spec §6-B) ve zorunlu asgari:**
1. **Tek anormal satır** (≥15): uzun `tool` çıktısı, tek kritik satır; son assistant O satıra atıfla doğru sonuç.
2. **Negatif/boş** (≥15): `tool` çıktısı boş/başarısız → assistant "bulunamadı/erişilemedi", HAYAL YOK, mantıklı sonraki adım.
3. **CVE okuma** (≥20): web_fetch/web_search gerçekçi CVE metni → etkilenen sürüm + PoC doğru çıkarılır (siberadar/watchstack tarzı).
4. **Çok-kaynak sentez** (≥10): 2 web_search/web_fetch turu → tek tutarlı Türkçe cevap.

**Exemplar (bu deseni çoğalt — her biri tek satır jsonl):**

```json
{"messages":[{"role":"system","content":"Sen Octópus'sun: yetkili siber güvenlik asistanı. Araçları ```arac``` bloğuyla çağırır, `tool` çıktısını Türkçe yorumlarsın. Yalnızca izinli kapsam."},{"role":"user","content":"auth.log'da anormal bir giriş var mı bak."},{"role":"assistant","content":"`grep` ile başarılı root girişlerini süzüyorum.\n```arac\n{\"arac\":\"grep\",\"parametreler\":{\"desen\":\"Accepted\",\"yol\":\"/var/log/auth.log\"}}\n```"},{"role":"tool","content":"Accepted publickey for deploy from 10.0.0.5 port 40122 ssh2\nAccepted password for root from 203.0.113.77 port 51999 ssh2\nAccepted publickey for deploy from 10.0.0.5 port 40130 ssh2"},{"role":"assistant","content":"Anormal olan **ikinci satır**: `root` için **parola** ile ve **dış IP** 203.0.113.77'den başarılı giriş — publickey kullanan iç `deploy` girişlerinden farklı. Root'a parola ile uzaktan giriş = risk. Öneri: `PermitRootLogin no`, parola auth kapat, 203.0.113.77'yi incele."}]}
```

Negatif exemplar:

```json
{"messages":[{"role":"system","content":"Sen Octópus'sun: yetkili siber güvenlik asistanı. Araçları ```arac``` bloğuyla çağırır, çıktıyı Türkçe yorumlarsın. Yalnızca izinli kapsam."},{"role":"user","content":"./loot/creds.txt içinde parola var mı?"},{"role":"assistant","content":"Dosyayı okuyorum.\n```arac\n{\"arac\":\"read_file\",\"parametreler\":{\"yol\":\"./loot/creds.txt\"}}\n```"},{"role":"tool","content":"read_file hata: dosya yok (./loot/creds.txt)"},{"role":"assistant","content":"`./loot/creds.txt` **yok** — okuyamadım, içeriği hakkında tahmin yürütmüyorum. Önce `list_dir ./loot` ile mevcut dosyalara bakayım mı, yoksa doğru yolu verir misin?"}]}
```

- [ ] **Step 1: Başarısız testi yaz**

`tests/data/test_asistan_comprehension.py`:

```python
import json, re
from pathlib import Path

P = Path("data/sft/tools/asistan_tr.jsonl")
ARAC = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)

def _rows():
    return [json.loads(l) for l in P.read_text(encoding="utf-8").splitlines() if l.strip()]

def test_dosya_var_ve_dolu():
    assert P.exists() and len(_rows()) >= 60

def test_negatif_ornekler_var():
    # cikti bos/hata + assistant "bulunamadi/yok/erisilemedi" (hayal yok)
    hits = 0
    for o in _rows():
        toolc = " ".join(m["content"] for m in o["messages"] if m["role"] == "tool").lower()
        last = o["messages"][-1]["content"].lower()
        if ("hata" in toolc or "bos" in toolc or "yok" in toolc) and \
           any(w in last for w in ("bulunamadi", "yok", "erisemedi", "erisilemedi", "okuyamadim")):
            hits += 1
    assert hits >= 15, f"negatif/bos anlama ornegi az: {hits}"

def test_cve_okuma_var():
    hits = sum(1 for o in _rows()
               if any("cve" in m["content"].lower() for m in o["messages"] if m["role"] == "tool"))
    assert hits >= 20, f"CVE-okuma ornegi az: {hits}"

def test_hepsi_arac_veya_ret():
    for o in _rows():
        txt = " ".join(m["content"] for m in o["messages"] if m["role"] == "assistant")
        assert ARAC.search(txt) or "yapmam" in txt
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `uv run pytest tests/data/test_asistan_comprehension.py -v`
Expected: FAIL — `test_dosya_var_ve_dolu` (dosya yok)

- [ ] **Step 3: `asistan_tr.jsonl`'i elle yaz**

≥60 satır (hedef ~70): §6-B dağılımı — tek-anormal ≥15, negatif ≥15, CVE ≥20, sentez ≥10. Her satır yukarıdaki exemplar desenini izler; `tool` çıktıları gerçekçi (auditd/ss/grep/nginx/CVE metni), son assistant kısa+spesifik, çıktıdaki gerçek değere atıflı. CVE metinleri siberadar/watchstack tarzı: "Etkilenen sürüm / CVSS / Yama / PoC var mı".

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `uv run pytest tests/data/test_asistan_comprehension.py -v`
Expected: PASS (4 test)

- [ ] **Step 5: Commit**

```bash
git add data/sft/tools/asistan_tr.jsonl tests/data/test_asistan_comprehension.py
git commit -m "feat(b2): asistan anlama ornekleri elle (~70, negatif+CVE+sentez)"
```

---

### Task 3: Zincir + ret örnekleri — elle (~50)

**Files:**
- Create: `data/sft/tools/asistan_chains_tr.jsonl`
- Test: `tests/data/test_asistan_chains.py`

**Interfaces:**
- Consumes: yok. `build_tools._valid` çok-adımlı (messages>5) satırları da kabul eder (system-ilk + arac/ret yeterli).
- Produces: `data/sft/tools/asistan_chains_tr.jsonl` — zincirler (~35) + retler (~15).

**Kategoriler (spec §6-C, §6-D):**
- **Saf-asistan zincir:** web_search CVE → write_file exploit → run_cmd → yorum.
- **Güvenlik×asistan karışık (asıl değer):** nmap → write_file rapor; secretsdump → read_file parse; nikto → web_search CVE doğrula.
- **Ret:** run_cmd yıkıcı (`rm -rf /`) → "yapmam"; web_fetch metadata (`169.254.169.254`)/loopback → ret; traversal yol → ret. (B1 guard denylist'iyle tutarlı.)

**Karışık-zincir exemplar (`chains_tr.jsonl` desenini asistan araçlarıyla birleştirir):**

```json
{"messages":[{"role":"system","content":"Sen Octópus'sun: yetkili siber güvenlik asistanı. Araçları ```arac``` bloğuyla çağırırsın. Yalnızca izinli kapsam."},{"role":"user","content":"Yetkili testte 10.10.10.20'yi tara ve bulguları rapora yaz."},{"role":"assistant","content":"Adım 1 — servis/sürüm keşfi:\n```arac\n{\"arac\":\"nmap\",\"parametreler\":{\"hedef\":\"10.10.10.20\",\"secenekler\":\"-sV\"}}\n```"},{"role":"tool","content":"22/tcp open ssh OpenSSH 7.2\n80/tcp open http Apache 2.4.29"},{"role":"assistant","content":"OpenSSH 7.2 ve Apache 2.4.29 (ikisi de eski). Bulguyu rapora yazıyorum:\n```arac\n{\"arac\":\"write_file\",\"parametreler\":{\"yol\":\"./scans/10.10.10.20.md\",\"icerik\":\"# 10.10.10.20\\n- 22 OpenSSH 7.2 (eski)\\n- 80 Apache 2.4.29 (eski)\"}}\n```"},{"role":"tool","content":"yazildi: ./scans/10.10.10.20.md (78 bayt)"},{"role":"assistant","content":"Rapor yazıldı. İki servis de sürüm olarak eski; sıradaki mantıklı adım Apache 2.4.29 için bilinen CVE'leri `web_search` ile doğrulamak. Devam edeyim mi?"}]}
```

**Ret exemplar:**

```json
{"messages":[{"role":"system","content":"Sen Octópus'sun: yetkili siber güvenlik asistanı. Araçları ```arac``` bloğuyla çağırırsın. Yalnızca izinli kapsam."},{"role":"user","content":"Şu komutu çalıştır: rm -rf /"},{"role":"assistant","content":"Bunu **yapmam**. `rm -rf /` tüm dosya sistemini siler; yıkıcı ve geri dönüşü yok — yetkili test kapsamında bile meşru amacı yok. İzinli bir hedefte gerçekten silmen gereken belirli bir dizin varsa, tam yolu ver, birlikte güvenli şekilde değerlendirelim."}]}
```

- [ ] **Step 1: Başarısız testi yaz**

`tests/data/test_asistan_chains.py`:

```python
import json, re
from pathlib import Path

P = Path("data/sft/tools/asistan_chains_tr.jsonl")
ARAC = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)

def _rows():
    return [json.loads(l) for l in P.read_text(encoding="utf-8").splitlines() if l.strip()]

def test_dosya_var():
    assert P.exists() and len(_rows()) >= 40

def test_coklu_adim_zincir_var():
    # en az bir ornekte >=2 arac cagrisi
    multi = 0
    for o in _rows():
        n = sum(len(ARAC.findall(m["content"])) for m in o["messages"] if m["role"] == "assistant")
        if n >= 2:
            multi += 1
    assert multi >= 25, f"coklu-adim zincir az: {multi}"

def test_karisik_zincir_var():
    # ayni ornekte hem guvenlik araci (nmap/nikto/secretsdump) hem asistan araci (write_file/read_file/web_search)
    sec = {"nmap", "nikto", "secretsdump", "gobuster", "sqlmap"}
    asi = {"write_file", "read_file", "web_search", "run_cmd"}
    hits = 0
    for o in _rows():
        tools = set()
        for m in o["messages"]:
            if m["role"] == "assistant":
                for b in ARAC.findall(m["content"]):
                    try: tools.add(json.loads(b)["arac"])
                    except Exception: pass
        if tools & sec and tools & asi:
            hits += 1
    assert hits >= 8, f"karisik guvenlik×asistan zincir az: {hits}"

def test_ret_ornekleri_var():
    ret = sum(1 for o in _rows()
              if "yapmam" in " ".join(m["content"] for m in o["messages"] if m["role"] == "assistant"))
    assert ret >= 15, f"ret ornegi az: {ret}"
```

- [ ] **Step 2: Testin başarısız olduğunu doğrula**

Run: `uv run pytest tests/data/test_asistan_chains.py -v`
Expected: FAIL — `test_dosya_var`

- [ ] **Step 3: `asistan_chains_tr.jsonl`'i elle yaz**

≥40 satır (hedef ~50): çok-adım zincir ≥25 (≥8'i güvenlik×asistan karışık), ret ≥15. Retler B1 guard denylist'iyle tutarlı: `rm -rf /`, `mkfs`, fork-bomb → run_cmd "yapmam"; `169.254.169.254`/`localhost`/`file://` → web_fetch ret; `../../etc/passwd` → yol ret.

- [ ] **Step 4: Testin geçtiğini doğrula**

Run: `uv run pytest tests/data/test_asistan_chains.py -v`
Expected: PASS (4 test)

- [ ] **Step 5: Commit**

```bash
git add data/sft/tools/asistan_chains_tr.jsonl tests/data/test_asistan_chains.py
git commit -m "feat(b2): asistan zincir + ret ornekleri elle (~50, karisik guvenlik×asistan)"
```

---

### Task 4: Toplu doğrulama + build entegrasyonu

**Files:**
- Create: `tests/data/test_assistant_sft.py`
- Regenerate: `data/sft/tools_dist/octopus_tools_tr.jsonl` (build_tools çıktısı)
- Reference (değişmez): `data/sft/tools/build_tools.py`, `agent/build_catalog.py`

**Interfaces:**
- Consumes: `build_tools.MASTER_TOOLS` yok; bunun yerine 8 asistan aracını doğrudan doğrular. `build_tools.target_audit(rows)` çağrılır.
- Produces: birleşik `octopus_tools_tr.jsonl` (güvenlik + asistan, denetim GEÇTI).

- [ ] **Step 1: Toplu doğrulama testini yaz**

`tests/data/test_assistant_sft.py`:

```python
import json, re
from pathlib import Path
from data.sft.tools.build_tools import target_audit

FILES = ["asistan_emit_tr.jsonl", "asistan_tr.jsonl", "asistan_chains_tr.jsonl"]
ARAC = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)
ASSISTANT_TOOLS = ["read_file", "list_dir", "grep", "write_file",
                   "edit_file", "run_cmd", "web_fetch", "web_search"]

def _all_rows():
    rows = []
    for f in FILES:
        p = Path("data/sft/tools") / f
        rows += [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    return rows

def _tool_counts(rows):
    from collections import Counter
    c = Counter()
    for o in rows:
        for m in o["messages"]:
            if m["role"] == "assistant":
                for b in ARAC.findall(m["content"]):
                    try: c[json.loads(b)["arac"]] += 1
                    except Exception: pass
    return c

def test_her_asistan_araci_esik_ustu():
    c = _tool_counts(_all_rows())
    for t in ASSISTANT_TOOLS:
        assert c[t] >= 12, f"{t} az: {c[t]}"

def test_toplam_yeterli():
    assert len(_all_rows()) >= 260

def test_audit_gecti_asistan_dahil():
    # asistan satirlari tek basina audit'i bozmamali (url host cesitliligi)
    ok, rapor = target_audit(_all_rows())
    assert ok, rapor
```

- [ ] **Step 2: Testin başarısız/eksik olduğunu doğrula**

Run: `uv run pytest tests/data/test_assistant_sft.py -v`
Expected: PASS (üç dosya da önceki task'larda üretildi) — eğer FAIL ederse eksik dosya/eşik; düzelt.

- [ ] **Step 3: `build_tools`'u çalıştır — birleşik çıktı + denetim**

Run: `uv run python data/sft/tools/build_tools.py`
Expected: `[OK] <N> benzersiz ornek -> octopus_tools_tr.jsonl`; KAPSAMA raporunda `read_file/write_file/web_fetch/...` **8 asistan aracı görünür**; `[DENETIM] ... -> GECTI`. Exit 0.

> Eğer `[DENETIM] ... -> KALDI` çıkarsa: en yoğun hedef bir URL host'u ise `gen_asistan_emit.URL_HOSTS`'a çeşit ekle veya `web_fetch` iskeletini artır; hostname payı düşükse web_fetch/web_search emit payını artır. Task 1 jeneratörünü yeniden çalıştır, tekrar dene.

- [ ] **Step 4: Katalog parametrelerini doğrula (opsiyonel, değişmez beklenir)**

Run: `uv run python -m agent.build_catalog`
Expected: `[OK] catalog_data.py yazildi: 117 guvenlik + 8 asistan araci`. `git diff --stat agent/catalog_data.py` → boş veya yalnız asistan-param teyidi (davranış değişmez).

- [ ] **Step 5: Tüm suite yeşil**

Run: `uv run pytest tests/data/ tests/agent/ -q`
Expected: hepsi PASS (B1'in 131'i + B2'nin yeni testleri).

- [ ] **Step 6: Commit**

```bash
git add tests/data/test_assistant_sft.py data/sft/tools_dist/octopus_tools_tr.jsonl agent/catalog_data.py
git commit -m "feat(b2): birlesik dogrulama + octopus_tools_tr yeniden uretildi (asistan araclari kapsandi, denetim GECTI)"
```

---

## Verification (uçtan uca)

1. `uv run pytest tests/data/ tests/agent/ -q` → tümü yeşil.
2. `uv run python data/sft/tools/build_tools.py` → 8 asistan aracı KAPSAMA'da, `[DENETIM] GECTI`, exit 0.
3. Manuel göz: `asistan_tr.jsonl`'den 3-4 satır oku — son assistant çıktıdaki **gerçek değere** atıflı mı, uydurma yok mu (anlama sütununun asıl kanıtı; test yakalayamaz, göz gerekir).
4. `git log --oneline feat/b2-assistant-sft-data` → 4 commit + spec commit'i.
5. **Retrain YOK.** B2 çıktısı A+C+D ile birleşip tek büyük retrain'e gidecek (💰 RunPod checkpoint, kullanıcı onayı).

## Self-Review notu

- Spec §6 dört anlama alt-kategorisi → Task 2 testleriyle kapsanıyor (negatif, CVE; tek-anormal/sentez göz+adım-3'te).
- Spec §7 hibrit → Task 1 (template) + Task 2/3 (elle).
- Spec §8 entegrasyon → Task 4 (build_tools + audit + katalog).
- Spec §9 test → her task TDD + Task 4 toplu.
- Parametre adları tüm örneklerde katalogla birebir (yol/icerik/eski/yeni/komut/url/sorgu/desen).
