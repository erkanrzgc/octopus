"""E2 — DPI (blue-agirlik arac+kural) format dogrulamasi.

Tasarim: docs/superpowers/specs/2026-07-22-v0.9-technical-correctness-dpi-design.md
Ilke: yalniz DPI araclari (suricata/snort/tshark/tcpdump/wireshark); verbatim dogru
kural/filtre sozdizimi; IDS cikti yorumu (cok-turlu); evasion savunma cercevesinde;
dusunce YOK; arac'tan once tanima prose.
"""
import json
import re
from pathlib import Path

P = Path("data/sft/tools/dpi_tr.jsonl")
ARAC_JSON = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)
DPI_TOOLS = {"suricata", "snort", "tshark", "tcpdump", "wireshark"}
SURICATA_RULE = re.compile(r"alert\s+\w+\s+.*\(.*sid:\s*\d+.*\)", re.S)   # kural sozdizimi
TSHARK_DPI = re.compile(r"tshark\s+-r\s+\S+.*-Y\s+.*-T\s+fields", re.S)   # DPI filtre


def _rows():
    return [json.loads(l) for l in P.read_text(encoding="utf-8").splitlines() if l.strip()]


def _assistant_text(o):
    return "\n".join(m["content"] for m in o["messages"] if m["role"] == "assistant")


def _araclar(o):
    # Yalnizca assistant turlarini tara: arac cagrisi sadece assistant'tan gelir.
    # Sistem promptu (server_blueteam_tr.jsonl'den birebir) ornek-amacli bir
    # yer-tutucu arac blogu icerir ({"arac":"<ad>","parametreler":{...}}) -- bu
    # gecerli JSON DEGIL ve tarama disi birakilmali (E1/D3 testiyle ayni yaklasim).
    return [json.loads(j)["arac"] for m in o["messages"] if m["role"] == "assistant"
            for j in ARAC_JSON.findall(m["content"])]


def test_dosya_var_ve_dolu():
    assert P.exists() and len(_rows()) >= 42


def test_dusunce_yok():
    for o in _rows():
        assert all("```dusunce" not in m["content"] for m in o["messages"])


def test_yalniz_dpi_araclari_ve_katalog_gecerli():
    from agent.catalog import get_spec
    for o in _rows():
        for a in _araclar(o):
            assert get_spec(a) is not None, f"katalog-disi arac: {a}"
            assert a in DPI_TOOLS, f"DPI-disi arac E2'de olmamali: {a}"


def test_arac_once_tanima_prose():
    for o in _rows():
        for m in o["messages"]:
            if m["role"] == "assistant" and "```arac" in m["content"]:
                assert not m["content"].lstrip().startswith("```arac")


def test_suricata_snort_kural_yeterli():
    n = sum(1 for o in _rows() if SURICATA_RULE.search(_assistant_text(o)))
    assert n >= 8, f"kural-yazma ornegi az: {n}"


def test_tshark_dpi_filtre_yeterli():
    n = sum(1 for o in _rows() if TSHARK_DPI.search(_assistant_text(o)))
    assert n >= 5, f"tshark DPI filtre az: {n}"


def test_ids_cikti_yorumu_cok_turlu():
    # eve.json/fast.log besleyen cok-turlu (tool rolu) triyaj ornekleri
    turns = sum(1 for o in _rows() if any(m["role"] == "tool" for m in o["messages"]))
    assert turns >= 10, f"cok-turlu IDS-yorum az: {turns}"


def test_evasion_savunma_cercevesinde():
    # evasion gecen ornek MUTLAKA tespit/savunma da anlatmali (salt saldiri talimati degil)
    ev = [o for o in _rows() if re.search(r"evasion|atlat|parçala|fragment|obfs|tünel|tunnel",
                                          _assistant_text(o).lower())]
    for o in ev:
        t = _assistant_text(o).lower()
        assert re.search(r"tespit|yakala|alert|kural|savun|dedect|signature", t), \
            f"evasion ornegi savunma cercevesi yok: {t[:80]}"
