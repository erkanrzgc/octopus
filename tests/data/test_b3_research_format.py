"""B3 — deep-research grounding zincirleri format + grounding dogrulamasi."""
import json
import re
from pathlib import Path

P = Path("data/sft/distilled/octopus_distill_b3_research.jsonl")
ARAC_JSON = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)
WEB = {"web_search", "web_fetch"}


def _rows():
    return [json.loads(l) for l in P.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_dosya_var_ve_dolu():
    assert P.exists() and len(_rows()) >= 18


def test_hepsi_cok_turlu_arastirma_zinciri():
    # her kayit tool rolu icermeli (ara -> oku dongusu)
    for o in _rows():
        assert "tool" in [m["role"] for m in o["messages"]], "arastirma zinciri tool cikti icermeli"


def test_web_araclari_kullaniliyor_ve_katalogda():
    from agent.catalog import get_spec
    for o in _rows():
        araclar = [json.loads(j)["arac"]
                   for m in o["messages"] for j in ARAC_JSON.findall(m["content"])]
        assert any(a in WEB for a in araclar), "web_search/web_fetch yok"
        for a in araclar:
            assert get_spec(a) is not None, f"katalogda olmayan arac: {a}"


def test_dusunce_yok():
    # B3 reasoning-siz (D1 olcum-oranini kirletmesin)
    for o in _rows():
        assert all("```dusunce" not in m["content"] for m in o["messages"])


def test_grounding_sinyali():
    # final assistant kaynaga atif yapmali (grounding): kaynak/göre/sonuc/site adi vb.
    SIG = ("kaynak", "göre", "sonuc", "sonuç", "belirtiyor", "doğrula", "dogrula",
           "iki kaynak", "siteye göre", "raporuna", "resmi")
    hits = 0
    for o in _rows():
        last = o["messages"][-1]["content"].lower()
        if any(s in last for s in SIG):
            hits += 1
    assert hits >= 15, f"grounding-atifli sentez az: {hits}"


def test_durustluk_ornekleri_var():
    # en az birkac: kaynak bulunamadi/celiskili -> uydurmuyorum
    HON = ("bulamadım", "bulamadim", "doğrulayamadım", "dogrulayamadim", "çelişki", "celiski",
           "uydurmuyorum", "kesin değil", "kesin degil", "teyit edemedim",
           "kesinleştirmiyorum", "kesin bir şey söyleyemem", "uydurmak", "uydurma",
           "doğrulanmış bilgi yok", "spekülatif", "tek kaynağa dayanıp", "veremem")
    hits = sum(1 for o in _rows()
               if any(h in o["messages"][-1]["content"].lower() for h in HON))
    assert hits >= 3, f"durustluk/celiski ornegi az: {hits}"
