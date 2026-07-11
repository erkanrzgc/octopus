"""B2 Task 4 — toplu dogrulama: asistan araci kapsamasi + merged denetim.

Not: B2-tek denetim degil, MERGED committed artifact (tools_dist/octopus_tools_tr.jsonl)
denetlenir — asil gate odur (augment'lenmis guvenlik ornekleri hedef havuzunu buyutur,
CVE-DB host kumelenmesini seyreltir). B2 uretim zinciri:
  augment_targets --k 3 --seed 3407  (asistan_* passthrough)  ->  tools_aug/
  build_tools.py --src data/sft/tools_aug                      ->  tools_dist/octopus_tools_tr.jsonl
"""
import json
import re
from collections import Counter
from pathlib import Path

from data.sft.tools.build_tools import target_audit

SRC = Path("data/sft/tools")
B2_FILES = ["asistan_emit_tr.jsonl", "asistan_tr.jsonl", "asistan_chains_tr.jsonl"]
MERGED = Path("data/sft/tools_dist/octopus_tools_tr.jsonl")
ARAC = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)
ASSISTANT_TOOLS = ["read_file", "list_dir", "grep", "write_file",
                   "edit_file", "run_cmd", "web_fetch", "web_search"]


def _rows(paths):
    out = []
    for p in paths:
        out += [json.loads(l) for l in Path(p).read_text(encoding="utf-8").splitlines() if l.strip()]
    return out


def _tool_counts(rows):
    c: Counter = Counter()
    for o in rows:
        for m in o["messages"]:
            if m["role"] == "assistant":
                for b in ARAC.findall(m["content"]):
                    try:
                        c[json.loads(b)["arac"]] += 1
                    except Exception:
                        pass
    return c


def test_b2_toplam_yeterli():
    assert len(_rows(SRC / f for f in B2_FILES)) >= 260


def test_her_asistan_araci_esik_ustu():
    c = _tool_counts(_rows(SRC / f for f in B2_FILES))
    for t in ASSISTANT_TOOLS:
        assert c[t] >= 12, f"{t} az: {c[t]}"


def test_merged_artifact_asistan_iceriyor():
    """Committed merged set 8 asistan aracini da icermeli (pipeline calistirilmis)."""
    assert MERGED.exists(), "octopus_tools_tr.jsonl yok — build_tools --src tools_aug calistir"
    c = _tool_counts(_rows([MERGED]))
    for t in ASSISTANT_TOOLS:
        assert c[t] >= 12, f"merged'de {t} az: {c[t]} (pipeline'i yeniden calistir)"


def test_merged_denetim_gecti():
    """Asil gate: merged committed artifact hedef-dengeli olmali."""
    ok, rapor = target_audit(_rows([MERGED]))
    assert ok, rapor


def test_ret_ssrf_ip_passthrough_korundu():
    """augment asistan_* dosyalarini remap ETMEMELI: SSRF metadata IP merged sette aynen durmali."""
    text = MERGED.read_text(encoding="utf-8")
    assert "169.254.169.254" in text, \
        "SSRF metadata IP kaybolmus — augment asistan_'i remap etmis olabilir (passthrough kirik)"
