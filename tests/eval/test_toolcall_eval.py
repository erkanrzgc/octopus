"""Araç-çağrı eval skorer testleri — D1 ölçüm kapısı enstrümanı."""
from eval.toolcall_eval import EvalCase, evaluate, score_reply


def test_dogru_arac_tam_puan():
    # nmap bekleniyor, model gecerli nmap arac blogu bastı
    reply = '```dusunce\nPort taramasi.\n```\n```arac\n{"arac": "nmap", "parametreler": {"hedef": "10.0.0.1", "secenekler": "-sV"}}\n```'
    s = score_reply(reply, ["nmap", "rustscan"])
    assert s["emitted"] and s["valid_call"] and s["in_catalog"] and s["expected_tool"]


def test_arac_yok_sifir():
    reply = "Merhaba, size nasil yardimci olabilirim?"
    s = score_reply(reply, ["nmap"])
    assert not s["emitted"] and not s["valid_call"]
    assert not s["in_catalog"] and not s["expected_tool"]


def test_bozuk_json_emitted_ama_gecersiz():
    # arac fence var ama JSON bozuk -> emitted True, valid_call False
    reply = '```arac\n{"arac": "nmap", bozuk}\n```'
    s = score_reply(reply, ["nmap"])
    assert s["emitted"] and not s["valid_call"]


def test_katalogda_olmayan_arac():
    reply = '```arac\n{"arac": "hayaletcanavar", "parametreler": {}}\n```'
    s = score_reply(reply, ["nmap"])
    assert s["valid_call"] and not s["in_catalog"] and not s["expected_tool"]


def test_gecerli_ama_yanlis_arac_secimi():
    # gecerli katalog araci ama beklenen degil -> in_catalog True, expected_tool False
    reply = '```arac\n{"arac": "sqlmap", "parametreler": {"hedef": "x"}}\n```'
    s = score_reply(reply, ["nmap", "rustscan"])
    assert s["in_catalog"] and not s["expected_tool"]


def test_evaluate_agrega():
    cases = [EvalCase("port tara", ["nmap"]), EvalCase("web dizin", ["gobuster"])]

    def fake_gen(prompt):
        if "port" in prompt:
            return '```arac\n{"arac": "nmap", "parametreler": {"hedef": "x"}}\n```'
        return "arac yok duz cevap"

    rep = evaluate(cases, fake_gen)
    assert rep["toplam"] == 2
    assert rep["oranlar"]["emitted"] == 0.5
    assert rep["oranlar"]["expected_tool"] == 0.5
