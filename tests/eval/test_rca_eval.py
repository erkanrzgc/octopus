"""rca_eval olcer mantigi (modelsiz, scripted gen)."""
from eval.rca_eval import RcaCase, evaluate, HELDOUT, _report, RcaResult, CaseOut

ARAC = '```arac\n{"arac":"run_cmd","parametreler":{"komut":"dmesg -T | tail"}}\n```'
CASES = [RcaCase("disk doldu", "disk"), RcaCase("servis dusuyor", "oom")]


def test_arac_cagiran_kanit_toplar_sayilir():
    r = evaluate(lambda olay: "Once kontrol edelim:\n" + ARAC, CASES)
    assert r.kanit == 2
    assert all(o.kanit_topladi for o in r.outcomes)
    assert not any(o.kanitsiz_sonuc for o in r.outcomes)


def test_kanitsiz_kesin_sonuc_tahmin_sayilir():
    # arac YOK ama 'kök neden ... çözüm ...' -> tahmin
    r = evaluate(lambda olay: "Kök neden bellek; çözüm servisi restart et.", CASES)
    assert r.kanit == 0
    assert all(o.kanitsiz_sonuc for o in r.outcomes)


def test_heldout_egitim_disi_ve_dolu():
    assert len(HELDOUT) >= 5
    # held-out olaylar egitim dosyasindaki istemlerle birebir CAKISMAMALI
    import json
    from pathlib import Path
    p = Path("data/sft/tools/server_rca_tr.jsonl")
    train_users = {json.loads(l)["messages"][1]["content"]
                   for l in p.read_text(encoding="utf-8").splitlines() if l.strip()}
    for c in HELDOUT:
        assert c.olay not in train_users, "held-out olay egitimde var!"


def test_rapor_kanit_oranini_yazar():
    r = RcaResult(total=2, kanit=1, outcomes=[
        CaseOut("a", True, False), CaseOut("b", False, True)])
    out = _report("m", r)
    assert "KANIT TOPLADI (arac cagirdi): 1/2" in out
