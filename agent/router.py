"""Deterministik gorev->rol yonlendirici (KOD, model degil). Turkce anahtar + arac-adi ipuclari.
Ilk eslesen rol kazanir (oncelik = tuple sirasi); eslesme yoksa GENERAL (bugunku tam-katalog)."""
from __future__ import annotations
from agent.roles import GENERAL

# (rol, anahtar-kelimeler). SIRA = oncelik: daha ozgul roller once.
_ROUTES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("wireless", ("wifi", "kablosuz", "wpa", "wpa2", "handshake", "aircrack", "deauth", "reaver")),
    ("password", ("parola kir", "sifre kir", "hash", "hashcat", "hydra", "john", "brute")),
    ("exploit-ad", ("active directory", "kerberos", "smb", "mimikatz", "ntlm", "lateral",
                    "impacket", "netexec", "metasploit", "meterpreter", "payload", "reverse shell")),
    ("web", ("sql injection", "sqlmap", "xss", "web uygulama", "http", "url", "dizin tara",
             "wordpress", "burp", "gobuster", "ffuf", "nikto")),
    ("traffic-mitm", ("sniff", "mitm", "ortadaki adam", "pcap", "trafik yakala", "wireshark",
                      "tcpdump", "arp spoof", "responder")),
    ("osint", ("osint", "whois", "dns kaydi", "subdomain", "email topla", "shodan",
               "theharvester", "amass", "sherlock")),
    ("recon-scan", ("port tara", "port taramasi", "nmap", "canli host", "ag kesf", "masscan", "rustscan")),
    ("privesc", ("yetki yuksel", "privesc", "linpeas", "winpeas", "root ol")),
    ("forensic-re", ("adli", "forensic", "bellek dump", "memory dump", "tersine muhendis",
                     "malware analiz", "ghidra", "volatility", "radare2")),
    ("blue-server", ("firewall", "fail2ban", "ids", "ips", "sertlestir", "hardening",
                     "rootkit", "suricata", "sunucu guvenlik", "log analiz", "iptables")),
    ("cloud", ("kubernetes", "k8s", "docker imaj", "terraform", "iac tara", "trivy", "prowler")),
    ("mobile-social", ("apk", "android uygulama", "mobil uygulama", "phishing", "oltalama",
                       "gophish", "setoolkit")),
    ("secrets", ("secret tara", "sizinti tara", "api key sizint", "trufflehog", "gizli anahtar")),
)


def route(gorev: str) -> str:
    low = (gorev or "").lower()
    for role, keys in _ROUTES:
        if any(k in low for k in keys):
            return role
    return GENERAL
