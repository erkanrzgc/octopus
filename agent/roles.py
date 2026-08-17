"""Rol = katalog domain'i (TEK KAYNAK: CATALOG.domain). asistan araclari cross-cutting
(her role dahil), routable rol DEGIL. general = tum katalog (router fallback = bugunku davranis)."""
from __future__ import annotations
from agent.catalog import CATALOG

ASISTAN = "asistan"
GENERAL = "general"
# routable roller = asistan HARIC tum domain'ler, sirali (deterministik)
ROLES: tuple[str, ...] = tuple(sorted({s.domain for s in CATALOG.values()} - {ASISTAN}))
_ASISTAN_TOOLS = frozenset(n for n, s in CATALOG.items() if s.domain == ASISTAN)


def role_tools(role: str) -> frozenset[str]:
    """role icin izinli arac adlari. general -> tum katalog; domain -> o dilim + asistan.
    Bilinmeyen role -> ValueError (router yalniz gecerli rol veya general dondurur)."""
    if role == GENERAL:
        return frozenset(CATALOG)
    if role not in ROLES:
        raise ValueError(f"bilinmeyen rol: {role!r}")
    return frozenset(n for n, s in CATALOG.items() if s.domain == role) | _ASISTAN_TOOLS
