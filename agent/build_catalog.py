"""catalog_data.py'yi URET: MASTER_TOOLS (alan) + egitim verisi (parametreler) + alan->risk.
Kosul:  uv run python -m agent.build_catalog
Cikti sadece uretim; catalog.py runtime'da catalog_data.py'yi okur."""
from __future__ import annotations
import json, glob, re
from pathlib import Path
from collections import defaultdict
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from data.sft.tools.build_tools import MASTER_TOOLS

ROOT = Path(__file__).resolve().parent.parent
ARAC_RE = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)

# MASTER_TOOLS'taki alan yorumlarindan alan haritasi (build_tools.py ile senkron).
DOMAINS: dict[str, list[str]] = {
    "recon-scan": ["nmap", "rustscan", "masscan", "netdiscover", "arp-scan", "fping", "ss"],
    "traffic-mitm": ["wireshark", "tshark", "tcpdump", "bettercap", "ettercap", "mitmproxy", "responder"],
    "osint": ["theHarvester", "maltego", "amass", "subfinder", "spiderfoot", "recon-ng", "sherlock", "shodan",
              "dnsrecon", "dnsenum", "fierce", "whois", "dig", "host"],
    "web": ["burpsuite", "zap", "nuclei", "gobuster", "ffuf", "feroxbuster", "dirsearch", "dirb", "nikto",
            "sqlmap", "wpscan", "wfuzz", "arjun", "paramspider", "dalfox", "xsstrike", "httpx", "katana", "whatweb"],
    "exploit-ad": ["metasploit", "msfvenom", "searchsploit", "sliver", "netexec", "bloodhound-python", "impacket",
                   "secretsdump", "evil-winrm", "mimikatz", "rubeus", "routersploit", "beef", "enum4linux-ng",
                   "smbclient", "smbmap"],
    "password": ["hydra", "john", "hashcat", "medusa", "hashid"],
    "wireless": ["aircrack-ng", "airodump-ng", "aireplay-ng", "wifite", "hcxdumptool", "kismet", "reaver", "mdk4"],
    "forensic-re": ["volatility3", "autopsy", "sleuthkit", "binwalk", "foremost", "ghidra", "radare2", "gdb",
                    "strings", "yara", "capa"],
    "privesc": ["linpeas", "winpeas", "shell"],
    "blue-server": ["fail2ban", "iptables", "nftables", "ufw", "auditd", "osquery", "wazuh", "suricata", "snort",
                    "clamav", "lynis", "rkhunter", "chkrootkit", "aide"],
    "cloud": ["trivy", "prowler", "scoutsuite", "kube-hunter", "kube-bench", "docker-bench", "checkov", "tfsec"],
    "mobile-social": ["apktool", "jadx", "mobsf", "gophish", "setoolkit"],
}
# Alan -> varsayilan risk. Offansif=high, recon/pasif=low, savunma=low, degisiklik=medium.
DOMAIN_RISK = {
    "recon-scan": "low", "osint": "low", "blue-server": "low", "privesc": "high",
    "traffic-mitm": "high", "web": "medium", "exploit-ad": "high", "password": "high",
    "wireless": "high", "forensic-re": "low", "cloud": "low", "mobile-social": "medium",
}


# Asistan araclari: egitim verisinde YOK + per-tool risk -> explicit tanim (domain='asistan').
ASSISTANT_TOOLS: list[dict] = [
    {"name": "read_file",  "risk": "low",    "params": ("yol",)},
    {"name": "list_dir",   "risk": "low",    "params": ("yol",)},
    {"name": "grep",       "risk": "low",    "params": ("desen", "yol")},
    {"name": "write_file", "risk": "medium", "params": ("yol", "icerik")},
    {"name": "edit_file",  "risk": "medium", "params": ("yol", "eski", "yeni")},
    {"name": "run_cmd",    "risk": "high",   "params": ("komut",)},
    {"name": "web_fetch",  "risk": "low",    "params": ("url",)},
    {"name": "web_search", "risk": "low",    "params": ("sorgu",)},
    {"name": "hafiza_kaydet", "risk": "medium", "params": ("anahtar", "deger")},
    {"name": "hafiza_getir",  "risk": "low",    "params": ("anahtar",)},
]


# Runtime-eklenen araclar (egitim evreninde YOK; skill katmani modele tanitir).
# MASTER_TOOLS'u KIRLETME — bu 3'u ayri, explicit domain/risk/param ile ekle.
EXTENSION_TOOLS: list[dict] = [
    {"name": "trufflehog", "domain": "secrets",     "risk": "low", "params": ("kaynak", "hedef")},
    {"name": "magika",     "domain": "forensic-re", "risk": "low", "params": ("yol",)},
    {"name": "ghunt",      "domain": "osint",       "risk": "low", "params": ("modul", "hedef")},
]


def _domain_of(tool: str) -> str:
    for dom, tools in DOMAINS.items():
        if tool in tools:
            return dom
    return "other"


def _params_from_training() -> dict[str, list[str]]:
    tp: dict[str, set] = defaultdict(set)
    for f in glob.glob(str(ROOT / "data" / "sft" / "tools" / "*.jsonl")):
        if "build_tools" in f:
            continue
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            try:
                o = json.loads(line)
            except Exception:
                continue
            for m in o.get("messages", []):
                if m.get("role") != "assistant":
                    continue
                for blk in ARAC_RE.findall(m["content"]):
                    try:
                        d = json.loads(blk)
                    except Exception:
                        continue
                    t = d.get("arac")
                    if t:
                        tp[t].update((d.get("parametreler") or {}).keys())
    return {k: sorted(v) for k, v in tp.items()}


def main() -> None:
    params = _params_from_training()
    lines = ['"""URETILDI: agent/build_catalog.py. Elle duzenleme; yeniden uret."""', "CATALOG_DATA = ["]
    for t in MASTER_TOOLS:
        dom = _domain_of(t)
        risk = DOMAIN_RISK.get(dom, "medium")
        prm = params.get(t, ["secenekler"])  # egitimde yoksa makul varsayilan
        lines.append(f"    {{'name': {t!r}, 'domain': {dom!r}, 'risk': {risk!r}, 'params': {tuple(prm)!r}}},")
    for a in ASSISTANT_TOOLS:
        lines.append(f"    {{'name': {a['name']!r}, 'domain': 'asistan', "
                     f"'risk': {a['risk']!r}, 'params': {tuple(a['params'])!r}}},")
    for e in EXTENSION_TOOLS:
        lines.append(f"    {{'name': {e['name']!r}, 'domain': {e['domain']!r}, "
                     f"'risk': {e['risk']!r}, 'params': {tuple(e['params'])!r}}},")
    lines.append("]")
    # Egitim-disi eklenti arac adlari (kesif manifesti icin; catalog.py bunu okur).
    ext_names = [e["name"] for e in EXTENSION_TOOLS]
    lines.append("")
    lines.append(f"EXTENSION_TOOL_NAMES = {ext_names!r}")
    (ROOT / "agent" / "catalog_data.py").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] catalog_data.py yazildi: {len(MASTER_TOOLS)} guvenlik + "
          f"{len(ASSISTANT_TOOLS)} asistan + {len(EXTENSION_TOOLS)} eklenti araci")


if __name__ == "__main__":
    main()
