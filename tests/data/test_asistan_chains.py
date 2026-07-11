"""B2 Task 3 — asistan zincir + ret ornekleri dogrulamasi."""
import json
import re
from pathlib import Path

P = Path("data/sft/tools/asistan_chains_tr.jsonl")
ARAC = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)


def _rows():
    return [json.loads(l) for l in P.read_text(encoding="utf-8").splitlines() if l.strip()]


def _tools(o):
    t = set()
    for m in o["messages"]:
        if m["role"] == "assistant":
            for b in ARAC.findall(m["content"]):
                try:
                    t.add(json.loads(b)["arac"])
                except Exception:
                    pass
    return t


def test_dosya_var():
    assert P.exists() and len(_rows()) >= 40


def test_coklu_adim_zincir_var():
    multi = sum(1 for o in _rows()
                if sum(len(ARAC.findall(m["content"])) for m in o["messages"]
                       if m["role"] == "assistant") >= 2)
    assert multi >= 25, f"coklu-adim zincir az: {multi}"


def test_karisik_zincir_var():
    sec = {"nmap", "nikto", "secretsdump", "gobuster", "sqlmap", "wpscan", "smb-vuln", "hydra"}
    asi = {"write_file", "read_file", "web_search", "web_fetch", "run_cmd", "edit_file"}
    hits = sum(1 for o in _rows() if (_tools(o) & sec) and (_tools(o) & asi))
    assert hits >= 8, f"karisik guvenlik×asistan zincir az: {hits}"


def test_ret_ornekleri_var():
    ret = sum(1 for o in _rows()
              if "yapmam" in " ".join(m["content"] for m in o["messages"] if m["role"] == "assistant"))
    assert ret >= 15, f"ret ornegi az: {ret}"


def test_git_is_akisi_var():
    hits = sum(1 for o in _rows()
               if re.search(r'"komut"\s*:\s*"git ',
                            " ".join(m["content"] for m in o["messages"] if m["role"] == "assistant")))
    assert hits >= 3, f"git is-akisi ornegi az: {hits}"
