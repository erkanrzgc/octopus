from agent.backends.gguf_model import render_prompt


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
