"""B2 Task 2 — asistan anlama (comprehension) ornekleri dogrulamasi."""
import json
import re
from pathlib import Path

P = Path("data/sft/tools/asistan_tr.jsonl")
ARAC = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)


def _rows():
    return [json.loads(l) for l in P.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_dosya_var_ve_dolu():
    assert P.exists() and len(_rows()) >= 60


def test_negatif_ornekler_var():
    # Negatif/bos tool ciktisi + assistant'in HAYAL KURMADAN kabulu.
    NEG_TOOL = ("hata", "bos", "yok", "0 ", "refused", "reddedildi", "denied",
                "fail", "404", "401", "no entries", "packet loss", "eslesme yok")
    HONEST = ("bulunamadi", "yok", "erisemedi", "erisilemedi", "okuyamadim", "goremedim",
              "uydurmuyorum", "uydurmiyorum", "varsaymiyorum", "varsayim yapmiyorum",
              "iddia etmiyorum", "soyleyemem", "alamadim")
    hits = 0
    for o in _rows():
        toolc = " ".join(m["content"] for m in o["messages"] if m["role"] == "tool").lower()
        last = o["messages"][-1]["content"].lower()
        if any(w in toolc for w in NEG_TOOL) and any(w in last for w in HONEST):
            hits += 1
    assert hits >= 15, f"negatif/bos anlama ornegi az: {hits}"


def test_cve_okuma_var():
    hits = sum(1 for o in _rows()
               if any("cve" in m["content"].lower() for m in o["messages"] if m["role"] == "tool"))
    assert hits >= 20, f"CVE-okuma ornegi az: {hits}"


def test_hepsi_arac_veya_ret():
    for o in _rows():
        txt = " ".join(m["content"] for m in o["messages"] if m["role"] == "assistant")
        assert ARAC.search(txt) or "yapmam" in txt
