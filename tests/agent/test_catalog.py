from agent.catalog import (
    CATALOG, get_spec, ToolSpec, extension_specs, extension_manifest_text,
)
from data.sft.tools.build_tools import MASTER_TOOLS


def test_all_master_tools_present():
    # Katalog kanonik 117 aracin HEPSINI kapsamali (parser/model eslesmesi).
    missing = [t for t in MASTER_TOOLS if t not in CATALOG]
    assert missing == [], f"katalogda eksik: {missing}"


def test_spec_shape():
    spec = get_spec("nmap")
    assert isinstance(spec, ToolSpec)
    assert spec.domain and spec.risk in {"low", "medium", "high"}
    assert "secenekler" in spec.params  # egitim verisinde nmap secenekler kullaniyor


def test_unknown_tool_is_none():
    assert get_spec("boyle_bir_arac_yok") is None


def test_extension_tools_present():
    for name in ("trufflehog", "magika", "ghunt"):
        spec = get_spec(name)
        assert spec is not None, name
        assert spec.risk in {"low", "medium", "high"}
        assert spec.domain and spec.params


def test_extension_tool_domains():
    assert get_spec("trufflehog").domain == "secrets"
    assert get_spec("magika").domain == "forensic-re"
    assert get_spec("ghunt").domain == "osint"


def test_extension_specs_are_only_the_three():
    """extension_specs SADECE egitim-disi 3 aracı verir (117 egitilmis DAHIL DEGIL)."""
    names = {s.name for s in extension_specs()}
    assert names == {"trufflehog", "magika", "ghunt"}
    assert "nmap" not in names                              # egitilmis arac sizmaz


def test_extension_manifest_lists_tools_with_params():
    """Kesif manifesti her eklenti aracini + parametrelerini icerir; egitilmis arac DOKMEZ."""
    man = extension_manifest_text()
    for name in ("trufflehog", "magika", "ghunt"):
        assert name in man
    assert "kaynak" in man and "hedef" in man               # trufflehog params
    assert "yol" in man                                     # magika param
    assert "modul" in man                                   # ghunt param
    assert "nmap" not in man                                # 117 egitilmis DOKULMEZ
    assert man.count("\n") == 2                             # tam 3 satir (arac basi 1)
