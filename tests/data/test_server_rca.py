"""v1.0 depth — server-admin/blue-team olay-RCA veri format + kalite dogrulamasi.
Cekirdek ilke: model sonuca varmadan `arac` ile KANIT toplamali (olcum kapisi #1)."""
import json
import re
from pathlib import Path

from agent.catalog import get_spec

P = Path("data/sft/tools/server_rca_tr.jsonl")
DUSUNCE = re.compile(r"```dusunce\s*(.*?)```", re.S)
ARAC_JSON = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)
# red-herring / yaniltici-belirti ogreten isaretler
RED_HERRING = re.compile(r"yanıltıcı|yaniltici|kurban|ilk sinyal|değil, ", re.I)


def _rows():
    return [json.loads(l) for l in P.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_dosya_var_ve_dolu():
    assert P.exists()
    assert len(_rows()) >= 30, "RCA derinlik paketi >= 30 ornek olmali"


def test_rol_yapisi_tutarli():
    # her ornek: system -> user ... + en az bir tool (tani ciktisi) + assistant ile biter
    for o in _rows():
        roles = [m["role"] for m in o["messages"]]
        assert roles[0] == "system" and roles[1] == "user", roles
        assert "tool" in roles, "tani ciktisi (tool) yok"
        assert roles[-1] == "assistant", "kok-neden assistant ile bitmeli"


def test_ilk_assistant_dusunce_ile_baslar():
    # hipotez muhakemesi gizli ```dusunce``` blogunda olmali (v0.9 formati)
    for o in _rows():
        first = next(m["content"] for m in o["messages"] if m["role"] == "assistant")
        assert first.lstrip().startswith("```dusunce"), first[:60]


def test_kanit_once_sonuc_olcum_kapisi():
    # OLCUM KAPISI #1: ilk assistant turu SONUCA varmadan once bir arac cagirmali
    for o in _rows():
        first = next(m["content"] for m in o["messages"] if m["role"] == "assistant")
        assert ARAC_JSON.search(first), "ilk turda kanit-toplama araci yok: " + first[:80]
        assert "Kök neden" not in first, "kanit toplamadan kok-neden ilan edilmis"


def test_arac_bloklari_gecerli_ve_katalogda():
    for o in _rows():
        for m in o["messages"]:
            if m["role"] != "assistant":
                continue
            for blk in ARAC_JSON.findall(m["content"]):
                d = json.loads(blk)  # gecerli JSON
                assert d.get("arac") and "parametreler" in d
                assert get_spec(d["arac"]) is not None, f"katalog-disi arac: {d['arac']}"


def test_her_ornek_kanita_dayali_kok_neden_ile_biter():
    for o in _rows():
        last = o["messages"][-1]["content"]
        assert "Kök neden" in last, "son turda kanita-dayali kok-neden yok"


def test_user_istemleri_benzersiz():
    users = [o["messages"][1]["content"] for o in _rows()]
    assert len(set(users)) == len(users), "yinelenen olay istemi var"


def test_red_herring_kapsami():
    # ilk sinyale yapismamayi ogreten en az birkac ornek (yaniltici-belirti disiplini)
    rh = sum(1 for o in _rows() if RED_HERRING.search(o["messages"][-1]["content"]))
    assert rh >= 3, f"yaniltici-belirti ornegi az: {rh}"
