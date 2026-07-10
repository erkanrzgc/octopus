"""Konusma-tutarli hedef remapping — her ornekteki TUM IP/CIDR/host'u tutarli
bir haritayla yeni bir sete cevir, K varyant uret. Kor find-replace DEGIL:
ayni ornek icinde tarama-ciktisi <-> takip-hedefi baglantisi korunur."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from ipaddress import IPv4Network, ip_address, ip_network

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
