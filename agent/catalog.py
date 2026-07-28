"""117 guvenlik + 10 asistan + 3 runtime-eklenti araci: TEK GERCEK KAYNAK. catalog_data.py'den ToolSpec yukler.
Yeniden uret:  uv run python -m agent.build_catalog"""
from __future__ import annotations
from dataclasses import dataclass
from agent.catalog_data import CATALOG_DATA


# Kapsam (scope) icin AG hedefi tasiyan parametre anahtarlari — IP/host/URL/domain.
# TEK KAYNAK: hem policy (scope kilidi) hem executor (bu + gorsel ekstralar) buradan okur.
# NOT: arayuz/dosya AG hedefi DEGIL (yerel arayuz/dosya) -> scope anahtari degil.
TARGET_KEYS: tuple[str, ...] = ("hedef", "url", "hedef_url", "domain")


@dataclass(frozen=True)
class ToolSpec:
    name: str
    domain: str
    risk: str
    params: tuple[str, ...]


CATALOG: dict[str, ToolSpec] = {
    d["name"]: ToolSpec(name=d["name"], domain=d["domain"], risk=d["risk"], params=tuple(d["params"]))
    for d in CATALOG_DATA
}


def get_spec(name: str) -> ToolSpec | None:
    return CATALOG.get(name)


def target_value(params: dict) -> str | None:
    """Cagri parametrelerinden AG hedefini (scope-degerlendirilebilir) cikar; yoksa None.
    TEK KAYNAK: policy (scope kilidi) + executor'lar (gercek komut) buradan okur."""
    for k in TARGET_KEYS:
        if params.get(k):
            return str(params[k])
    return None
