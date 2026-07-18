"""D1 — harness strip_dusunce: ic muhakeme blogunu kullanicidan gizle."""
from agent.toolcall import strip_dusunce


def test_dusunce_blogu_sokulur():
    t = "```dusunce\nSMB surumu lazim.\n```\nSonuc: port 445 acik."
    assert strip_dusunce(t) == "Sonuc: port 445 acik."


def test_blok_yoksa_ayni_metin():
    t = "Duz cevap, dusunce yok."
    assert strip_dusunce(t) == t


def test_arac_blogu_korunur():
    # dusunce sokulur AMA arac blogu dokunulmaz (harness onu ayri parse eder)
    t = "```dusunce\nAraci sec.\n```\n```arac\n{\"arac\": \"nmap\"}\n```"
    out = strip_dusunce(t)
    assert "dusunce" not in out
    assert "```arac" in out and "nmap" in out


def test_bos_string_cokmez():
    assert strip_dusunce("") == ""
