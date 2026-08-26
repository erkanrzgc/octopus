import json
import re
from pathlib import Path

P = Path("data/sft/tools/gapfill_recon_v12_tr.jsonl")
ARAC = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)


def _rows():
    return [json.loads(l) for l in P.read_text(encoding="utf-8").splitlines() if l.strip()]


def _araclar(o):
    return [json.loads(j)["arac"] for m in o["messages"] for j in ARAC.findall(m["content"])]


def test_dosya_var_ve_dolu():
    assert P.exists() and len(_rows()) >= 26


def test_arac_adlari_katalogda_gecerli():
    from agent.catalog import get_spec
    for o in _rows():
        araclar = _araclar(o)
        assert araclar, "arac-call ornegi olmali (offensive gap-fill)"
        for a in araclar:
            assert get_spec(a) is not None, f"katalogda olmayan arac: {a}"


def test_gecerli_arac_json():
    for o in _rows():
        for m in o["messages"]:
            for j in ARAC.findall(m["content"]):
                d = json.loads(j)  # bozuk JSON -> hata
                assert "arac" in d and "parametreler" in d
