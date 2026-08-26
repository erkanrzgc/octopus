import json
from pathlib import Path

P = Path("data/sft/distilled/octopus_distill_v12_accuracy.jsonl")


def _rows():
    return [json.loads(l) for l in P.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_dosya_var_ve_dolu():
    assert P.exists() and len(_rows()) >= 25


def test_arac_ve_dusunce_yok():
    # Bilgi-derinligi = saf reasoning Q&A; arac YOK (D1 olcum-orani), dusunce YOK (B3/D2 tutarli).
    for o in _rows():
        for m in o["messages"]:
            assert "```arac" not in m["content"]
            assert "```dusunce" not in m["content"]


def test_hedef_konular():
    # v1.0 eval zayif-noktalarini kapsamali (en az bir ornek her konuda).
    blob = " ".join(m["content"].lower() for o in _rows() for m in o["messages"])
    for konu in ["syn", "-ss", "simetrik", "base64"]:
        assert konu in blob, f"eksik konu: {konu}"
