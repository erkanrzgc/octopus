"""Konusma-tutarli hedef remapping — her ornekteki TUM IP/CIDR/host'u tutarli
bir haritayla yeni bir sete cevir, K varyant uret. Kor find-replace DEGIL:
ayni ornek icinde tarama-ciktisi <-> takip-hedefi baglantisi korunur."""
from __future__ import annotations

import argparse
import glob
import json
import random
import re
import sys
from dataclasses import dataclass, field
from ipaddress import IPv4Network, ip_address, ip_network
from pathlib import Path

from data.sft.tools import target_pool as tp

_HERE = Path(__file__).resolve().parent
_SKIP = {"octopus_tools_tr.jsonl"}  # build ciktisi — kaynak degil
# asistan_* dosyalari (B2): semantik ornekler (ret'lerde 169.254.169.254/127.0.0.1 gibi
# ANLAMLI IP'ler var) — hedef remap ETME, verbatim kopyala. Boylece tools_aug'a girer
# ama SSRF/loopback/metadata anlatilari bozulmaz.
_NOAUG = ("asistan_",)

_CIDR_RE = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d{1,3}){3})/(\d{1,2})(?![\d.])")
_IP_RE = re.compile(r"(?<![\d.])(\d{1,3}(?:\.\d{1,3}){3})(?![\d.])")
# Hostname/domain hedefleri: cok-etiketli ad + bilinen TLD (dosya adi/surum degil).
_HOST_RE = re.compile(
    r"\b(?:[a-z0-9][a-z0-9-]*\.)+"
    r"(?:local|internal|com|net|org|io|dev|tr|gov|edu|co)\b"
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
        # public domain (OSINT hedefi) -> public havuz; lab host (.local/.internal) -> lab havuz.
        mapping[hn] = tp.sample_public_domain(rng) if tp.is_public_domain(hn) else tp.sample_hostname(rng)
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


def augment_example(example: dict, k: int, rng: random.Random) -> list[dict]:
    """Orijinal + k tutarli varyant."""
    out = [example]
    for _ in range(k):
        ent = extract_entities(example)
        out.append(apply_mapping(example, build_mapping(ent, rng)))
    return out


def main(argv: list[str] | None = None) -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Hedef dengeleme augmentasyonu")
    ap.add_argument("--src", default=str(_HERE), help="kaynak *.jsonl klasoru")
    ap.add_argument("--out", default=str(_HERE.parent / "tools_aug"))
    ap.add_argument("--k", type=int, default=3)
    ap.add_argument("--seed", type=int, default=3407)
    args = ap.parse_args(argv)
    out_dir = Path(args.out)
    out_dir.mkdir(exist_ok=True)
    rng = random.Random(args.seed)
    total_in = total_out = 0
    for f in sorted(glob.glob(str(Path(args.src) / "*.jsonl"))):
        name = Path(f).name
        if name in _SKIP:
            continue
        noaug = name.startswith(_NOAUG)  # asistan_* -> remap YOK, verbatim kopyala
        rows_out: list[dict] = []
        for line in open(f, encoding="utf-8"):
            line = line.strip()
            if not line:
                continue
            ex = json.loads(line)
            total_in += 1
            rows_out.extend([ex] if noaug else augment_example(ex, args.k, rng))
        with open(out_dir / name, "w", encoding="utf-8") as w:
            for r in rows_out:
                w.write(json.dumps(r, ensure_ascii=False) + "\n")
        total_out += len(rows_out)
        print(f"   {name}: {len(rows_out)} satir")
    print(f"[OK] {total_in} kaynak -> {total_out} augmented ({out_dir})")


if __name__ == "__main__":
    main()
