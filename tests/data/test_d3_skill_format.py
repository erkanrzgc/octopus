"""D3 — skill/metodoloji katmani format + davranis dogrulamasi.

Tasarim: docs/superpowers/specs/2026-07-20-d3-skill-methodology-design.md
Ilke: YENI ARAC/FORMAT YOK, dusunce YOK. Model gorev-sinifini tanir (arac'tan ONCE prose),
icsellestirilmis metodoloji iskeletini uygular, bulguya UYARLAR; negatiflerde toren/cerceve
dayatmaz veya yetkisizi reddeder. Her arac katalog-gecerli olmali (D1 'bilinmeyen arac' dersi).
"""
import json
import re
from pathlib import Path

P = Path("data/sft/distilled/octopus_distill_d3_skill.jsonl")
ARAC_JSON = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)


def _rows():
    return [json.loads(l) for l in P.read_text(encoding="utf-8").splitlines() if l.strip()]


def _araclar(o):
    return [json.loads(j)["arac"] for m in o["messages"] for j in ARAC_JSON.findall(m["content"])]


def test_dosya_var_ve_dolu():
    assert P.exists() and len(_rows()) >= 24


def test_dusunce_yok():
    # D1 olcum-oranini kirletmemek icin D3'te dusunce blogu OLMAMALI (B3/D2 ile tutarli)
    for o in _rows():
        assert all("```dusunce" not in m["content"] for m in o["messages"])


def test_arac_adlari_katalogda_gecerli():
    # KRITIK (D1 dersi): katalog-disi arac adi -> model 'bilinmeyen arac' ogrenir
    from agent.catalog import get_spec
    for o in _rows():
        for a in _araclar(o):
            assert get_spec(a) is not None, f"katalogda olmayan arac: {a}"


def test_cok_turlu_zincirler_yeterli():
    # agentic Tip B: tool-cikti besleyen cok-turlu zincirler (metodoloji yurutumu)
    turns = sum(1 for o in _rows() if any(m["role"] == "tool" for m in o["messages"]))
    assert turns >= 8, f"cok-turlu zincir az: {turns}"


def test_tanima_prose_aractan_once():
    # Tanima disiplini: arac iceren asistan turu HAM arac ile BASLAMAZ; onunde prose (tanima) olur
    for o in _rows():
        for m in o["messages"]:
            if m["role"] == "assistant" and "```arac" in m["content"]:
                assert not m["content"].lstrip().startswith("```arac"), \
                    f"arac'tan once tanima prose yok: {m['content'][:60]}"


def test_uyarlama_ornekleri():
    # Iskeletten bulguya gore SAPMA (robotik degil) — en az 3 acik uyarlama
    hits = sum(1 for o in _rows()
               if any("uyarl" in m["content"].lower() for m in o["messages"]))
    assert hits >= 3, f"uyarlama ornegi az: {hits}"


def test_negatif_ornekleri():
    # Toren-yok (basit tek-atis) / cerceve-dayatma-yok / yetkisiz-ret — en az 3
    NEG = ("gereksiz", "aşırı olur", "gerek yok", "töreni gerekmez", "yapmam", "hayır")
    hits = sum(1 for o in _rows()
               if any(n in o["messages"][-1]["content"].lower() for n in NEG))
    assert hits >= 3, f"negatif ornek az: {hits}"
