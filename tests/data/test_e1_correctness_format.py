"""E1 — teknik-doguruluk (payload/komut verbatim) format + dogruluk dogrulamasi.

Tasarim: docs/superpowers/specs/2026-07-22-v0.9-technical-correctness-dpi-design.md
Ilke: kanonik DOGRU sozdizimli komut/payload; cok-ifadeli (acik-uclu + spesifik) ayni
komuta esler; persona degismez; gercek-kurban reddi korunur; dusunce YOK.
"""
import json
import re
from pathlib import Path

# E1 paketi IKI dosyaya bolundu (boru-hatti dersi): prose komut ornekleri seed_tr'ye
# (persona promptu + upsample, arac-kapisi YOK); gercek arac-cagrisi ornekleri tools/'da
# (tool-aware prompt, build_tools arac-kapisini gecer). Test ikisinin BIRLESIMINI dogrular.
PATHS = [
    Path("data/sft/seed_tr/e1_correctness_tr.jsonl"),   # prose komut (cogunluk)
    Path("data/sft/tools/payload_correctness_tr.jsonl"),  # arac-cagrisi (msfvenom/metasploit)
]
ARAC_JSON = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)
# Dogru msfvenom reverse_tcp kanonik kalibi: -p <os>/.../reverse_tcp LHOST=.. LPORT=.. -f .. -o ..
MSFVENOM_OK = re.compile(
    r"msfvenom\s+-p\s+\S+/(meterpreter|shell)/reverse_tcp\s+LHOST=\S+\s+LPORT=\d+\s+-f\s+\w+")
# Uydurma kaliplari (v0.8.1 hatasi) YASAK:
FABRICATED = re.compile(r"payload\.py|\|\s*read\s+-p")


def _rows():
    rows = []
    for p in PATHS:
        rows += [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]
    return rows


def _assistant_text(o):
    return "\n".join(m["content"] for m in o["messages"] if m["role"] == "assistant")


def _araclar(o):
    # Yalnizca assistant turlarini tara: arac cagrisi sadece assistant'tan gelir.
    # Sistem promptu (her satirda ayni, exploit_tr.jsonl'den birebir) ornek-amacli
    # bir yer-tutucu arac blogu icerir ({"arac":"<ad>","parametreler":{...}}) --
    # bu gecerli JSON DEGIL ve tarama disi birakilmali (D3 testiyle ayni yaklasim).
    return [json.loads(j)["arac"] for m in o["messages"] if m["role"] == "assistant"
            for j in ARAC_JSON.findall(m["content"])]


def test_dosya_var_ve_dolu():
    assert all(p.exists() for p in PATHS) and len(_rows()) >= 65


def test_dusunce_yok():
    for o in _rows():
        assert all("```dusunce" not in m["content"] for m in o["messages"])


def test_arac_adlari_katalogda_gecerli():
    from agent.catalog import get_spec
    for o in _rows():
        for a in _araclar(o):
            assert get_spec(a) is not None, f"katalogda olmayan arac: {a}"


def test_uydurma_sozdizimi_yok():
    # v0.8.1 hatasinin (payload.py / | read -p '') tekrari YASAK
    for o in _rows():
        t = _assistant_text(o)
        assert not FABRICATED.search(t), f"uydurma kalip: {t[:80]}"


def test_msfvenom_reverse_tcp_kanonik_yeterli():
    # en az 8 ornek DOGRU msfvenom reverse_tcp kalibini ogretmeli
    n = sum(1 for o in _rows() if MSFVENOM_OK.search(_assistant_text(o)))
    assert n >= 8, f"kanonik msfvenom az: {n}"


def test_dinleyici_esligi():
    # reverse shell ureten ornek dinleyiciyi de vermeli (nc -lvnp VEYA multi/handler)
    rev = [o for o in _rows() if "reverse" in _assistant_text(o).lower()
           or "reverse" in json.dumps(o, ensure_ascii=False).lower()]
    with_listener = [o for o in rev if re.search(r"nc\s+-l\S*\s*-?\S*\s*\d+|multi/handler|-lvnp",
                                                 _assistant_text(o))]
    assert len(with_listener) >= 6, f"dinleyici esligi az: {len(with_listener)}/{len(rev)}"


def test_cok_ifadeli_ayni_komuta():
    # Ayni kanonik komut EN AZ 2 farkli kullanici-ifadesiyle gorunmeli (genelleme).
    # Kaba olcut: 'reverse shell' isteyen >=2 acik-uclu + >=2 spesifik ifade var.
    users = [m["content"].lower() for o in _rows() for m in o["messages"] if m["role"] == "user"]
    acik = sum(1 for u in users if "payload ver" in u or "shell al" in u or "kabuk al" in u)
    spesifik = sum(1 for u in users if "meterpreter" in u or "x64" in u or "reverse_tcp" in u)
    assert acik >= 2 and spesifik >= 2, f"ifade cesitliligi az: acik={acik} spesifik={spesifik}"


def test_hicbir_satir_sessizce_dusmez():
    # BORU-HATTI DERSI (v0.9): E1 prose komut satirlari `tools` kaynagina konunca
    # build_tools._valid (arac-cagrisi VEYA ret sart) 58/69'u SESSIZCE dusurmustu.
    # Cozum: prose -> seed_tr (arac-kapisi YOK, is_valid yeter); arac -> tools/ (kapiyi gecer).
    # Bu test o yonlendirmeyi kalici garanti eder (build kosmadan drop-mantigini dogrular).
    from data.sft.tools.build_tools import _valid as tools_valid
    from data.sft.normalize import is_valid, to_messages

    seed_p, tools_p = PATHS[0], PATHS[1]
    # seed_tr E1 satirlari: build_sft is_valid'i gecmeli (arac gerekmez)
    for line in seed_p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            o = json.loads(line)
            assert is_valid(to_messages(o)), f"seed_tr E1 satiri is_valid'den duser: {line[:60]}"
    # tools/ E1 satirlari (arac-cagrisi): build_tools kapisini gecmeli
    for line in tools_p.read_text(encoding="utf-8").splitlines():
        if line.strip():
            ok, sebep = tools_valid(json.loads(line))
            assert ok, f"tools/ E1 satiri build_tools'ta duser ({sebep}): {line[:60]}"


def test_persona_dosyasi_degismedi():
    # E1 salt yetenek: persona.py'ye dokunulmaz (guardrail sabit).
    import subprocess
    r = subprocess.run(["git", "diff", "--name-only", "HEAD", "--", "data/sft/persona.py"],
                       capture_output=True, text=True)
    assert r.stdout.strip() == "", "persona.py degismis olmamali (E1 salt yetenek)"
