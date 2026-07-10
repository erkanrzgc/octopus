import json
import re
from pathlib import Path

_PATH = Path("data/sft/tools/hostname_tr.jsonl")
_ARAC = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)


def _rows():
    return [json.loads(l) for l in _PATH.read_text(encoding="utf-8").splitlines() if l.strip()]


def test_at_least_15_examples():
    assert len(_rows()) >= 15


def test_user_hostname_appears_verbatim_in_arac_hedef():
    host_re = re.compile(r"[a-z0-9][a-z0-9.-]*\.(?:local|internal)|octopus-target")
    for row in _rows():
        user = next(m["content"] for m in row["messages"] if m["role"] == "user")
        hosts = set(host_re.findall(user))
        assert hosts, f"kullanici mesajinda hostname yok: {user[:60]}"
        arac_txt = " ".join(m["content"] for m in row["messages"] if m["role"] == "assistant")
        hedefs = " ".join(json.loads(b).get("parametreler", {}).get("hedef", "")
                          for b in _ARAC.findall(arac_txt))
        assert any(h in hedefs for h in hosts), f"hostname arac hedefinde yok: {hosts}"
