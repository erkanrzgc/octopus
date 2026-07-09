import json
import urllib.error
import urllib.request

from agent.backends.gguf_model import GgufModel, render_prompt
from agent.messages import Message


class _FakeTok:
    """apply_chat_template'i taklit eder; gordugu argumanlari kaydeder."""
    def __init__(self) -> None:
        self.seen: dict | None = None

    def apply_chat_template(self, msgs, tokenize=False, add_generation_prompt=False, **kw) -> str:
        self.seen = {"msgs": msgs, "tokenize": tokenize, "agp": add_generation_prompt, "kw": kw}
        return "<bos><start_of_turn>user\nU<end_of_turn>\n<start_of_turn>model\n"


def test_render_prompt_strips_bos_and_passes_flags():
    tok = _FakeTok()
    out = render_prompt(
        [{"role": "system", "content": "S"}, {"role": "user", "content": "U"}], tok)
    assert not out.startswith("<bos>")                 # cift-BOS tuzagi: bastaki BOS siyrilir
    assert tok.seen["agp"] is True                     # add_generation_prompt=True
    assert tok.seen["tokenize"] is False
    assert tok.seen["msgs"][0]["role"] == "system"


def test_render_prompt_falls_back_when_enable_thinking_unsupported():
    class _StrictTok:
        def apply_chat_template(self, msgs, tokenize=False, add_generation_prompt=False):
            return "no-bos-here"                        # enable_thinking kwarg'i KABUL ETMEZ
    out = render_prompt([{"role": "user", "content": "U"}], _StrictTok())
    assert out == "no-bos-here"


class _Resp:
    def __init__(self, payload: dict) -> None:
        self._data = json.dumps(payload).encode("utf-8")

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _urlopen_ok(capture: dict, payload: dict):
    def _fake(req, timeout=None):
        capture["url"] = req.full_url
        capture["body"] = json.loads(req.data.decode("utf-8"))
        return _Resp(payload)
    return _fake


def _urlopen_raises(exc):
    def _fake(req, timeout=None):
        raise exc
    return _fake


def test_call_builds_raw_request_and_returns_response(monkeypatch):
    cap: dict = {}
    monkeypatch.setattr(urllib.request, "urlopen",
                        _urlopen_ok(cap, {"response": "Tararim ```arac```"}))
    m = GgufModel(renderer=lambda d: "PROMPT")
    out = m([Message("user", "10.10.10.5 tara")])
    assert out == "Tararim ```arac```"
    assert cap["url"].endswith("/api/generate")
    assert cap["body"]["raw"] is True
    assert cap["body"]["prompt"] == "PROMPT"
    assert cap["body"]["options"]["stop"] == ["<end_of_turn>"]
    assert cap["body"]["options"]["temperature"] == 0.6


def test_call_injects_system_and_flattens_tool(monkeypatch):
    seen: dict = {}
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_ok({}, {"response": "ok"}))
    m = GgufModel(renderer=lambda d: seen.setdefault("dicts", d) or "P")
    m([Message("user", "U"), Message("tool", "nmap ciktisi")])
    roles = [d["role"] for d in seen["dicts"]]
    assert roles[0] == "system"                          # persona basta
    assert "ARAÇ ÇIKTISI:" in seen["dicts"][-1]["content"]  # tool -> user flatten


def test_default_system_prompt_describes_arac_format(monkeypatch):
    """Teşhis (2026-07-09): persona-only prompt -> model arac blogu basmaz (0/3).
    Varsayilan system prompt arac formatini TARIF ETMELI (araç-farkinda, 3/3)."""
    seen: dict = {}
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_ok({}, {"response": "ok"}))
    m = GgufModel(renderer=lambda d: seen.setdefault("dicts", d) or "P")
    m([Message("user", "10.10.10.5 tara")])
    system = seen["dicts"][0]["content"]
    assert "```arac" in system                           # arac format spec system'de
    assert "parametreler" in system
    assert "Octópus" in system                            # persona guardrail da KORUNUR


def test_connection_refused_returns_error_string(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen",
                        _urlopen_raises(urllib.error.URLError("refused")))
    out = GgufModel(renderer=lambda d: "P")([Message("user", "U")])
    assert out.startswith("HATA") and "Ollama" in out


def test_timeout_returns_error_string(monkeypatch):
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_raises(TimeoutError()))
    out = GgufModel(renderer=lambda d: "P")([Message("user", "U")])
    assert out.startswith("HATA") and "zaman" in out.lower()


def test_model_not_found_returns_error_string(monkeypatch):
    err = urllib.error.HTTPError("u", 404, "not found", {}, None)
    monkeypatch.setattr(urllib.request, "urlopen", _urlopen_raises(err))
    out = GgufModel(renderer=lambda d: "P")([Message("user", "U")])
    assert "ollama create" in out
