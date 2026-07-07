from agent.catalog import CATALOG, get_spec, ToolSpec
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
