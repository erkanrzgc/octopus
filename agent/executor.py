"""Araci calistiran katman. Faz 1: MockExecutor (alan-bazli gercekci sahte cikti) —
gercek binary YOK, Windows'ta calisir. Faz 2: RealExecutor (WSL2/Kali subprocess)."""
from __future__ import annotations
from typing import Protocol
from agent.catalog import get_spec, TARGET_KEYS

# Mock ciktida gorunecek etiket icin: scope hedef anahtarlari + yerel gorsel ekstralar.
# (arayuz/dosya scope hedefi DEGIL; yalniz mock cikti etiketi icin.)
_DISPLAY_KEYS: tuple[str, ...] = TARGET_KEYS + ("arayuz", "dosya")


class Executor(Protocol):
    def run(self, tool: str, params: dict) -> str: ...


def _target(params: dict) -> str:
    for k in _DISPLAY_KEYS:
        if params.get(k):
            return str(params[k])
    return "hedef"


class MockExecutor:
    """Alan-bazli gercekci sahte cikti (egitim verisi tarzinda). Gercekten calistirmaz."""

    def run(self, tool: str, params: dict) -> str:
        spec = get_spec(tool)
        if spec is None:
            return f"HATA: bilinmeyen arac '{tool}'"
        t = _target(params)
        dom = spec.domain
        if dom in {"recon-scan"}:
            return f"{t} -> 22/ssh 80/http 443/https 445/smb  (mock tarama)"
        if dom == "web":
            return f"{t}: olasi zafiyet — /admin (200), SQLi parametre id (mock)"
        if dom in {"exploit-ad", "password"}:
            return f"{tool}: mock sonuc — kimlik/oturum elde edildi (lab)"
        if dom == "osint":
            return f"{t}: 3 alt alan, 2 e-posta, 1 acik port (mock OSINT)"
        return f"{tool} calisti (mock, alan={dom}), hedef={t}"
