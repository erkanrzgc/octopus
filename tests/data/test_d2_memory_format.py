"""D2 — hafıza (save/recall) zincirleri format + davranış doğrulaması.

Yapı: çoğu satır çok-turlu hafıza zinciri (kaydet/getir); hassas-veri satırları
bilinçli olarak tek-turlu KAYDETME-REDDİ (arac yok — doğru davranış saklamamak).
"""
import json
import re
from pathlib import Path

P = Path("data/sft/distilled/octopus_distill_d2_memory.jsonl")
ARAC_JSON = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)
HAFIZA = {"hafiza_kaydet", "hafiza_getir"}


def _rows():
    return [json.loads(l) for l in P.read_text(encoding="utf-8").splitlines() if l.strip()]


def _araclar(o):
    return [json.loads(j)["arac"] for m in o["messages"] for j in ARAC_JSON.findall(m["content"])]


def test_dosya_var_ve_dolu():
    assert P.exists() and len(_rows()) >= 18


def test_zincir_satirlari_cok_turlu_hafiza_katalog():
    # arac içeren satırlar: çok-turlu (tool rolü) + hafıza aracı kullanır + hepsi katalog-geçerli
    from agent.catalog import get_spec
    for o in _rows():
        araclar = _araclar(o)
        if not araclar:
            continue  # kaydetme-reddi satırı (ayrı testte)
        assert "tool" in [m["role"] for m in o["messages"]], "zincir tool cikti icermeli"
        assert any(a in HAFIZA for a in araclar), "zincirde hafiza araci yok"
        for a in araclar:
            assert get_spec(a) is not None, f"katalogda olmayan arac: {a}"


def test_aracsiz_satirlar_kaydetme_reddi():
    # arac içermeyen satırlar hassas-veri KAYDETME-REDDİ olmalı (hayal değil, güvenlik kararı)
    RED = ("kaydetmem", "saklamam", "kaydetmeyeceğim", "tutmam", "kalıcı olarak saklamam")
    for o in _rows():
        if _araclar(o):
            continue
        last = o["messages"][-1]["content"].lower()
        assert any(r in last for r in RED), f"arac'siz satir ret degil: {last[:60]}"


def test_dusunce_yok():
    for o in _rows():
        assert all("```dusunce" not in m["content"] for m in o["messages"])


def test_kaydet_ve_getir_ikisi_de_var():
    saves = sum(1 for o in _rows() if "hafiza_kaydet" in _araclar(o))
    gets = sum(1 for o in _rows() if "hafiza_getir" in _araclar(o))
    assert saves >= 8 and gets >= 8, f"kaydet={saves} getir={gets}"


def test_negatif_yok_uydurmam():
    # getir BOŞ/yok dönünce assistant hayal kurmadan kabul etmeli
    HON = ("kayıtlı değil", "kayitli degil", "kaydım yok", "kaydim yok", "hatırlamıyorum",
           "hatirlamiyorum", "uydurmuyorum", "bir kaydım bulunmuyor", "kaydım bulunmuyor",
           "kaydetmemişsin", "böyle bir kaydım yok")
    hits = sum(1 for o in _rows()
               if any(h in o["messages"][-1]["content"].lower() for h in HON))
    assert hits >= 3, f"negatif/uydurma-yok ornegi az: {hits}"


def test_hassas_veri_kaydetme_ornegi():
    # parola/sır/kart/özel-anahtar gibi hassas veriyi kalıcı kaydetmeyi reddeden örnekler
    SENS = ("parola", "kart numara", "özel anahtar", "api anahtar", "sır")
    hits = sum(1 for o in _rows()
               if not _araclar(o)
               and any(s in " ".join(m["content"] for m in o["messages"]).lower() for s in SENS))
    assert hits >= 2, f"hassas-veri-kaydetme-reddi ornegi az: {hits}"
