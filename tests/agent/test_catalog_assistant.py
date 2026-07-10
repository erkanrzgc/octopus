from agent.catalog import get_spec

_EXPECTED = {
    "read_file": ("low", ("yol",)),
    "list_dir": ("low", ("yol",)),
    "grep": ("low", ("desen", "yol")),
    "write_file": ("medium", ("yol", "icerik")),
    "edit_file": ("medium", ("yol", "eski", "yeni")),
    "run_cmd": ("high", ("komut",)),
    "web_fetch": ("low", ("url",)),
    "web_search": ("low", ("sorgu",)),
}


def test_assistant_tools_registered():
    for name, (risk, params) in _EXPECTED.items():
        spec = get_spec(name)
        assert spec is not None, f"{name} katalogda yok"
        assert spec.domain == "asistan"
        assert spec.risk == risk
        assert spec.params == params
