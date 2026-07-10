"""Dengeli hedef havuzu — ezberi kirmak icin cesitli IP/CIDR/hostname uretir.
stdlib-only, seed'le deterministik (ayni seed -> ayni cikti)."""
from __future__ import annotations

import random
from ipaddress import IPv4Address, IPv4Network, ip_network

PRIVATE_RANGES: tuple[IPv4Network, ...] = (
    ip_network("10.0.0.0/8"),
    ip_network("172.16.0.0/12"),
    ip_network("192.168.0.0/16"),
)
DOC_RANGE: IPv4Network = ip_network("203.0.113.0/24")  # RFC 5737 TEST-NET-3

HOSTNAMES: tuple[str, ...] = (
    "octopus-target", "web01.lab.local", "dc01.corp.local", "app-staging.internal",
    "kali-victim", "db-01.internal", "gitlab.lab.local", "vpn-gw.corp.local",
    "mail.corp.local", "jenkins.lab.local", "fileserver.internal", "portal.kurum.local",
    "wordpress.lab.local", "api-gw.internal", "ad01.corp.local", "backup.lab.local",
    "intranet.lab.local", "staging.internal", "vault.corp.local", "srv-web02.lab.local",
    "ns1.corp.local", "proxy.internal", "ci.lab.local", "erp.kurum.local",
    "shop.magaza.local", "crm.sirket.local", "orneksirket.local", "acme-corp.local",
    "test-hedef.internal", "dmz-web.lab.local", "helpdesk.corp.local", "grafana.lab.local",
)

HOSTNAME_SHARE: float = 0.28  # tek-host hedeflerin ~%28'i hostname olur


def sample_subnet(rng: random.Random, prefix: int = 24, doc_prob: float = 0.08) -> IPv4Network:
    """Ozel araliklardan (nadiren TEST-NET) rastgele bir /prefix blogu."""
    base = DOC_RANGE if rng.random() < doc_prob else rng.choice(PRIVATE_RANGES)
    if base.prefixlen >= prefix:
        return base
    n_blocks = 2 ** (prefix - base.prefixlen)
    net_int = int(base.network_address) + (rng.randrange(n_blocks) << (32 - prefix))
    return ip_network((net_int, prefix))


def sample_host(rng: random.Random, subnet: IPv4Network | None = None) -> IPv4Address:
    """subnet icinde gecerli bir host adresi (network/broadcast disi)."""
    if subnet is None:
        subnet = sample_subnet(rng, prefix=24)
    max_octet = min(254, subnet.num_addresses - 2)
    return IPv4Address(int(subnet.network_address) + rng.randint(1, max_octet))


def sample_hostname(rng: random.Random) -> str:
    return rng.choice(HOSTNAMES)


def use_hostname(rng: random.Random, share: float = HOSTNAME_SHARE) -> bool:
    return rng.random() < share
