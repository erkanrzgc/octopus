import json
import re
from pathlib import Path

P = Path("data/sft/tools/safety_neg_v12_tr.jsonl")
ARAC = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)


def _rows():
    return [json.loads(l) for l in P.read_text(encoding="utf-8").splitlines() if l.strip()]


def _araclar(o):
    return [json.loads(j)["arac"] for m in o["messages"] for j in ARAC.findall(m["content"])]


def test_dosya_var_ve_dolu():
    assert P.exists() and len(_rows()) >= 18


def test_arac_adlari_katalogda_gecerli():
    from agent.catalog import get_spec
    for o in _rows():
        for a in _araclar(o):
            assert get_spec(a) is not None, f"katalogda olmayan arac: {a}"


def test_yeterli_ret_ornegi():
    # En az yarısı SAF-RET (assistant hiç arac emit etmez = temiz ret).
    # Bu, v0.8/v1.0 "reddederken arac basma" glitch'ini yapısal olarak dışlar.
    ret = sum(1 for o in _rows() if not _araclar(o))
    assert ret >= 9, f"saf-ret ornegi az: {ret}"
