"""Harness transcript renderer — Claude Code tarzı tool-aktivite gösterimi."""
from agent.display import render_transcript
from agent.messages import Message


def _sample():
    return [
        Message("user", "10.10.10.5 yetkili lab hedefini tara"),
        Message("assistant",
                "```dusunce\nPort taramasi gerek.\n```\n"
                "Yetkili hedefi tariyorum.\n"
                '```arac\n{"arac": "nmap", "parametreler": {"hedef": "10.10.10.5", "secenekler": "-sV"}}\n```'),
        Message("tool", "22/tcp open ssh\n80/tcp open http"),
        Message("assistant", "Tarama bitti: SSH ve HTTP açık."),
    ]


def test_dusunce_gizli():
    out = render_transcript(_sample())
    assert "dusunce" not in out and "Port taramasi gerek" not in out


def test_arac_basligi_ve_arac_adi():
    out = render_transcript(_sample())
    assert "⏺" in out and "nmap" in out  # tool-aktivite basligi + arac adi


def test_ham_arac_json_gosterilmez():
    # cikti kutulu render; ham ```arac {json}``` bloğu kullaniciya gösterilmez
    out = render_transcript(_sample())
    assert '{"arac"' not in out and "```arac" not in out


def test_tool_ciktisi_golgeli_blok():
    out = render_transcript(_sample())
    assert "⎿" in out and "22/tcp open ssh" in out


def test_prose_ve_final_gorunur():
    out = render_transcript(_sample())
    assert "Yetkili hedefi tariyorum." in out
    assert "Tarama bitti: SSH ve HTTP açık." in out


def test_kullanici_satiri():
    out = render_transcript(_sample())
    assert "▸" in out and "yetkili lab hedefini tara" in out


def test_uzun_cikti_kisaltilir():
    msgs = [Message("tool", "\n".join(f"satir {i}" for i in range(50)))]
    out = render_transcript(msgs, max_output_lines=5)
    assert "satir 0" in out and "satir 49" not in out
    assert "satır" in out.lower() or "…" in out  # kisaltma isareti


def test_bos_liste_cokmez():
    assert render_transcript([]) == ""
