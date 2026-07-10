"""Konusma-tutarli hedef remapping — her ornekteki TUM IP/CIDR/host'u tutarli
bir haritayla yeni bir sete cevir, K varyant uret. Kor find-replace DEGIL:
ayni ornek icinde tarama-ciktisi <-> takip-hedefi baglantisi korunur."""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field
from ipaddress import IPv4Network, ip_address, ip_network

from data.sft.tools import target_pool as tp

_CIDR_RE = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d{1,3}){3})/(\d{1,2})(?![\d.])")
_IP_RE = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d{1,3}){3})(?![\d.])")
# Lab hostname'leri: bilinen suffiksler (over-match'i onlemek icin dar).
_HOST_RE = re.compile(
    r"\b(?:[a-z0-9][a-z0-9-]*\.)*[a-z0-9][a-z0-9-]*\."
    r"(?:local|internal|kurum\.com)\b"
)
_BARE_HOSTS = ("octopus-target", "kali-victim")


@dataclass
class Entities:
    cidrs: list[str] = field(default_factory=list)
    hosts: list[str] = field(default_factory=list)
    hostnames: list[str] = field(default_factory=list)


def _all_text(example: dict) -> str:
    return "\n".join(m.get("content", "") for m in example.get("messages", []))


def extract_entities(example: dict) -> Entities:
    text = _all_text(example)
    cidrs: list[str] = []
    cidr_nets: list[IPv4Network] = []
    for m in _CIDR_RE.finditer(text):
        c = f"{m.group(1)}/{m.group(2)}"
        if c not in cidrs:
            cidrs.append(c)
            cidr_nets.append(ip_network(c, strict=False))
    hosts: list[str] = []
    for m in _IP_RE.finditer(text):
        ip = m.group(1)
        try:
            addr = ip_address(ip)
        except ValueError:
            continue
        # CIDR agi/broadcast adresini bare-host sayma
        if any(addr == n.network_address or addr == n.broadcast_address for n in cidr_nets):
            continue
        if ip not in hosts:
            hosts.append(ip)
    hostnames: list[str] = []
    for m in _HOST_RE.finditer(text):
        if m.group(0) not in hostnames:
            hostnames.append(m.group(0))
    for bare in _BARE_HOSTS:
        if bare in text and bare not in hostnames:
            hostnames.append(bare)
    return Entities(cidrs=cidrs, hosts=hosts, hostnames=hostnames)


def build_mapping(ent: Entities, rng: random.Random) -> dict[str, str]:
    """Tutarli old->new haritasi: CIDR-ici host'lar eslesmis subnet icine dusar;
    tek basina host bir hostname'e donebilir (kota) -> ezberi kirar."""
    mapping: dict[str, str] = {}
    src_net_to_new: dict[str, IPv4Network] = {}
    for c in ent.cidrs:
        src = ip_network(c, strict=False)
        new = tp.sample_subnet(rng, prefix=src.prefixlen)
        mapping[c] = str(new)
        src_net_to_new[c] = new
    used: set[str] = set()

    def _fresh_host(subnet: IPv4Network | None) -> str:
        h = str(tp.sample_host(rng, subnet))
        for _ in range(64):
            if h not in used:
                break
            h = str(tp.sample_host(rng, subnet))
        used.add(h)
        return h

    lone_standalone = (not ent.cidrs) and len(ent.hosts) == 1
    for ip in ent.hosts:
        addr = ip_address(ip)
        parent = next((c for c in ent.cidrs if addr in ip_network(c, strict=False)), None)
        if parent is not None:
            mapping[ip] = _fresh_host(src_net_to_new[parent])
        elif lone_standalone and tp.use_hostname(rng):
            mapping[ip] = tp.sample_hostname(rng)   # tek-host -> hostname
        else:
            mapping[ip] = _fresh_host(None)
    for hn in ent.hostnames:
        mapping[hn] = tp.sample_hostname(rng)
    return mapping


def _sub_all(text: str, mapping: dict[str, str]) -> str:
    """Sinir-guvenli degistirme: uzun anahtar once (CIDR bare-IP'den once)."""
    for key in sorted(mapping, key=len, reverse=True):
        val = mapping[key]
        if "/" in key:                                # CIDR: literal
            text = text.replace(key, val)
        elif _IP_RE.fullmatch(key):                   # bare IP: rakam/nokta siniri
            text = re.sub(rf"(?<![\d.]){re.escape(key)}(?![\d.])", val, text)
        else:                                         # hostname
            text = re.sub(rf"(?<![\w.-]){re.escape(key)}(?![\w.-])", val, text)
    return text


def apply_mapping(example: dict, mapping: dict[str, str]) -> dict:
    """Haritayi tum mesaj iceriklerine uygula; YENI ornek dondur (mutasyon yok)."""
    msgs = [dict(m) for m in example["messages"]]
    for m in msgs:
        if "content" in m:
            m["content"] = _sub_all(m["content"], mapping)
    return {**example, "messages": msgs}
