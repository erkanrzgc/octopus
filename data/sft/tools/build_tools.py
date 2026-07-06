"""Octopus v0.7 tool-use SFT — birlestir + dogrula + kapsama raporu (uretim pipeline).

Ne yapar:
  1. data/sft/tools/*.jsonl (bu script + cikti haric) tum el-uretimi ornekleri toplar.
  2. Her ornegi dogrular: messages yapisi, en az 1 ```arac``` cagrisi VEYA ret ("yapmam").
  3. Icerik-hash ile tekrari eler.
  4. Birlestirilmis -> octopus_tools_tr.jsonl (build_sft.py bunu 'tools' kaynagi olarak alir).
  5. KAPSAMA RAPORU: katalogdaki ~90 aracin her biri icin ornek sayisi + BOSLUK (0 ornekli araclar) =
     bir sonraki uretim dalgasinin hedef listesi.

Kosul:  python data/sft/tools/build_tools.py
"""
from __future__ import annotations
import sys, json, glob, re, hashlib
from pathlib import Path
from collections import Counter

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

HERE = Path(__file__).resolve().parent
# Birlesik cikti AYRI klasore (tools_dist/) — build_sft.py bunu 'tools' kaynagi olarak okur.
# Boylece per-domain dosyalar (tools/*.jsonl) ile cift-sayim olmaz.
OUT_DIR = HERE.parent / "tools_dist"
OUT_DIR.mkdir(exist_ok=True)
OUT = OUT_DIR / "octopus_tools_tr.jsonl"
ARAC_RE = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)

# Katalog araclari (docs/v0.7-tools-catalog.md ile senkron) — kapsama boslugu icin hedef liste.
MASTER_TOOLS = [
    # ag/tarama
    "nmap","rustscan","masscan","netdiscover","arp-scan","fping",
    # trafik/mitm
    "wireshark","tshark","tcpdump","bettercap","ettercap","mitmproxy","responder",
    # osint
    "theHarvester","maltego","amass","subfinder","spiderfoot","recon-ng","sherlock","shodan",
    "dnsrecon","dnsenum","fierce","whois","dig","host",
    # web
    "burpsuite","zap","nuclei","gobuster","ffuf","feroxbuster","dirsearch","dirb","nikto",
    "sqlmap","wpscan","wfuzz","arjun","paramspider","dalfox","xsstrike","httpx","katana","whatweb",
    # exploit/ad
    "metasploit","msfvenom","searchsploit","sliver","netexec","bloodhound-python","impacket",
    "secretsdump","evil-winrm","mimikatz","rubeus","routersploit","beef","enum4linux-ng","smbclient","smbmap",
    # parola
    "hydra","john","hashcat","medusa","hashid",
    # kablosuz
    "aircrack-ng","airodump-ng","aireplay-ng","wifite","hcxdumptool","kismet","reaver","mdk4",
    # forensic/re
    "volatility3","autopsy","sleuthkit","binwalk","foremost","ghidra","radare2","gdb","strings","yara","capa",
    # privesc / genel
    "linpeas","winpeas","shell",
    # blue-team/sunucu (sonraki dalga)
    "fail2ban","iptables","nftables","ufw","auditd","osquery","wazuh","suricata","snort","clamav",
    "lynis","rkhunter","chkrootkit","aide","ss",
    # bulut/konteyner
    "trivy","prowler","scoutsuite","kube-hunter","kube-bench","docker-bench","checkov","tfsec",
    # mobil/api/sosyal
    "apktool","jadx","mobsf","gophish","setoolkit",
]


def _valid(o: dict) -> tuple[bool, str]:
    msgs = o.get("messages")
    if not isinstance(msgs, list) or len(msgs) < 3:
        return False, "messages<3"
    roles = [m.get("role") for m in msgs]
    if roles[0] != "system":
        return False, "system yok"
    txt = " ".join(m.get("content", "") for m in msgs if m.get("role") == "assistant")
    if not ARAC_RE.search(txt) and "yapmam" not in txt:
        return False, "ne arac-cagrisi ne ret"
    return True, "ok"


def _tools_of(o: dict) -> set[str]:
    t = set()
    for m in o["messages"]:
        if m.get("role") == "assistant":
            for blk in ARAC_RE.findall(m["content"]):
                try:
                    t.add(json.loads(blk)["arac"])
                except Exception:
                    pass
    return t


def main() -> None:
    files = [f for f in sorted(glob.glob(str(HERE / "*.jsonl"))) if Path(f).name != OUT.name]
    seen: set[str] = set()
    rows: list[dict] = []
    per_tool: Counter = Counter()
    refusals = 0
    bad = 0
    for f in files:
        for i, line in enumerate(open(f, encoding="utf-8"), 1):
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception as e:
                print(f"[X] {Path(f).name}:{i} JSON hatasi: {e}")
                bad += 1
                continue
            ok, why = _valid(o)
            if not ok:
                print(f"[!] {Path(f).name}:{i} atlandi ({why})")
                bad += 1
                continue
            h = hashlib.sha256(json.dumps(o, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
            if h in seen:
                continue
            seen.add(h)
            rows.append(o)
            ts = _tools_of(o)
            for t in ts:
                per_tool[t] += 1
            if not ts:
                refusals += 1

    with open(OUT, "w", encoding="utf-8") as w:
        for o in rows:
            w.write(json.dumps(o, ensure_ascii=False) + "\n")

    covered = {t for t in per_tool}
    gaps = [t for t in MASTER_TOOLS if t not in covered]
    print("=" * 64)
    print(f"[OK] {len(rows)} benzersiz ornek -> {OUT.name}  ({bad} atlandi/hatali)")
    print(f"     {len(covered)}/{len(MASTER_TOOLS)} katalog araci kapsandi | {refusals} saf-ret ornegi")
    print(f"\n[KAPSAMA] ornek sayisi (az->cok):")
    for t, c in sorted(per_tool.items(), key=lambda x: x[1]):
        print(f"   {c:>2}  {t}")
    print(f"\n[BOSLUK] henuz 0 ornekli {len(gaps)} arac (sonraki dalga hedefi):")
    print("   " + ", ".join(gaps))
    print("=" * 64)


if __name__ == "__main__":
    main()
