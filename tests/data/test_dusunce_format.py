"""D1 — reasoning pilot veri format dogrulamasi (```dusunce``` blogu)."""
import json
import re
from pathlib import Path

P = Path("data/sft/distilled/octopus_distill_d1_reasoning.jsonl")
DUSUNCE = re.compile(r"```dusunce\s*(.*?)```", re.S)
ARAC = re.compile(r"```arac\s*\{.*?\}\s*```", re.S)


def _rows():
    return [json.loads(l) for l in P.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_dosya_var_ve_dolu():
    assert P.exists() and len(_rows()) >= 15


def test_her_ilk_assistant_dusunce_ile_baslar():
    # ilk assistant turu ```dusunce``` ile baslamali (bloklardan once)
    for o in _rows():
        first_asst = next(m["content"] for m in o["messages"] if m["role"] == "assistant")
        assert first_asst.lstrip().startswith("```dusunce"), first_asst[:60]


def test_dusunce_kisa():
    # signal-balance: dusunce govdesi <= 90 kelime
    for o in _rows():
        for m in o["messages"]:
            if m["role"] != "assistant":
                continue
            for body in DUSUNCE.findall(m["content"]):
                n = len(body.split())
                assert n <= 90, f"dusunce cok uzun ({n} kelime): {body[:60]}"


def test_dusunce_ascii_ad():
    # marka disi kontrol token'i ASCII: 'düşünce' fence adi YOK, 'dusunce' VAR
    for o in _rows():
        blob = " ".join(m["content"] for m in o["messages"])
        assert "```düşünce" not in blob and "```dusunce" in blob
