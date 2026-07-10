"""web_fetch icin SSRF guard: sadece http(s), host'u coz, private/loopback/link-local/
metadata IP'lerini reddet. web_search sabit backend -> her zaman izinli. Saf + resolver enjekte."""
from __future__ import annotations

import ipaddress
import socket
from collections.abc import Callable
from urllib.parse import urlparse

from agent.policy import Decision


def _default_resolve(host: str) -> str:
    return socket.gethostbyname(host)


def is_blocked_ip(ip_str: str) -> bool:
    """Ic/ozel/metadata adresi mi (SSRF). Guard + executor fetch ayni kurali kullanir."""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # cozulemedi -> fail-closed
    return (ip.is_private or ip.is_loopback or ip.is_link_local
            or ip.is_reserved or ip.is_unspecified or ip.is_multicast)


def guard(params: dict, resolve: Callable[[str], str] = _default_resolve) -> Decision:
    if "sorgu" in params:                       # web_search: sabit backend, SSRF-guvenli
        if not str(params.get("sorgu") or "").strip():
            return Decision(False, False, "'sorgu' parametresi eksik")
        return Decision(True, False, "izinli (arama backend)")
    url = params.get("url")
    if not url:
        return Decision(False, False, "'url' parametresi eksik")
    parsed = urlparse(str(url))
    if parsed.scheme not in ("http", "https"):
        return Decision(False, False, f"sema reddedildi: {parsed.scheme or '(yok)'} (yalniz http/https)")
    host = parsed.hostname
    if not host:
        return Decision(False, False, "url host'u yok")
    try:
        ip = resolve(host)
    except OSError:
        return Decision(False, False, f"host cozulemedi: {host} (fail-closed)")
    if is_blocked_ip(ip):
        return Decision(False, False, f"SSRF: {host} -> {ip} ic/ozel adres reddedildi")
    return Decision(True, False, "izinli")
