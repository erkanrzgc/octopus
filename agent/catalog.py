"""117 guvenlik + 10 asistan + 3 runtime-eklenti araci: TEK GERCEK KAYNAK. catalog_data.py'den ToolSpec yukler.
Yeniden uret:  uv run python -m agent.build_catalog"""
from __future__ import annotations
from dataclasses import dataclass
from agent.catalog_data import CATALOG_DATA, EXTENSION_TOOL_NAMES


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


def positional_args(spec: ToolSpec | None, params: dict) -> list[str]:
    """Model'in verdigi parametreleri argv POSITIONAL token'larina cevir. 'secenekler' (flag
    bag) ve AG-hedefi (TARGET_KEYS) HARIC — onlar executor'da ayri islenir (flag'ler ortada,
    ag-hedefi target_value ile EN SONA). Kalan parametreler (alt-komut/mod/dosya: kaynak, modul,
    protokol, yol, ...) spec.params SIRASINDA lider pozisyonel olur -> eskiden SESSIZCE DUSUYORDU
    (or. trufflehog 'kaynak', ghunt 'modul', magika 'yol').
    NOT: gobuster/subfinder gibi FLAG-DEGERLI parametreli araclarda (url/-u, wordlist/-w) CLI-birebir
    haritalama per-arac sablonu ister (ileride, Kali testli); burada parametreler artik TAM (dusmuyor)
    ama flag-esleme kaba. Eklenti araclari (trufflehog/magika/ghunt) bu kaba kuralda DOGRU cikar."""
    if spec is None:
        return []
    out: list[str] = []
    for p in spec.params:
        if p == "secenekler" or p in TARGET_KEYS:
            continue
        v = params.get(p)
        if v:
            out.append(str(v))
    return out


def extension_specs() -> list[ToolSpec]:
    """Egitim evreni DISI runtime-eklenti araclarinin ToolSpec'leri (skill katmani tanitir).
    117 egitilmis arac DAHIL DEGIL — yalniz EXTENSION_TOOL_NAMES."""
    return [CATALOG[n] for n in EXTENSION_TOOL_NAMES if n in CATALOG]


def extension_manifest_text() -> str:
    """Modelin egitim-disi araclari KESFETMESI icin kompakt manifest (arac + parametreler).
    Her arac tek satir: '- <ad> (<domain>); parametreler: <p1>, <p2>'. Sistem-prompt ekidir;
    detayli kullanim ```arac``` sonrasi skill enjeksiyonuyla (post-call correction) gelir."""
    lines = [
        f"- {s.name} ({s.domain}); parametreler: {', '.join(s.params)}"
        for s in extension_specs()
    ]
    return "\n".join(lines)


# Manifest, taban sistem-promptun SONUNA eklenen sabit baslik. TEK KAYNAK: cli demo + discovery eval
# ayni metni uretsin (drift olmasin) diye burada.
_EXTENSION_MANIFEST_HEADER = "\n\nEk araçlar (eğitim sonrası eklendi; aynı ```arac``` bloğuyla çağrılır):\n"


def extension_augmented_system_prompt(base: str) -> str:
    """base sistem-promptun SONUNA extension-kesif manifestini ekle (egitim-birebir taban KORUNUR —
    basa degil SONA). Eklenti yoksa base AYNEN doner. TEK KAYNAK (cli demo + discovery eval)."""
    ext = extension_manifest_text()
    if not ext:
        return base
    return base + _EXTENSION_MANIFEST_HEADER + ext
