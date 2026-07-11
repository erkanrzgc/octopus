import json
from data.sft.tools.gen_asistan_emit import build, ARACLAR

def test_deterministic():
    assert build(40, 3407) == build(40, 3407)

def test_all_tools_covered():
    rows = build(160, 3407)
    seen = set()
    for o in rows:
        for m in o["messages"]:
            if m["role"] == "assistant" and "```arac" in m["content"]:
                blk = m["content"].split("```arac")[1].split("```")[0].strip()
                seen.add(json.loads(blk)["arac"])
    assert set(ARACLAR) <= seen, f"eksik: {set(ARACLAR) - seen}"

def test_schema_valid():
    for o in build(80, 3407):
        msgs = o["messages"]
        assert msgs[0]["role"] == "system" and len(msgs) >= 3
        assert any("```arac" in m["content"] for m in msgs if m["role"] == "assistant")

def test_web_fetch_url_host_diversity():
    rows = build(160, 3407)
    hosts = []
    for o in rows:
        for m in o["messages"]:
            if m["role"] == "assistant" and '"web_fetch"' in m["content"]:
                blk = m["content"].split("```arac")[1].split("```")[0].strip()
                url = json.loads(blk)["parametreler"]["url"]
                hosts.append(url.split("/")[2])
    assert len(set(hosts)) >= 6, "web_fetch url host cesitliligi dusuk"

def test_each_tool_min_distinct():
    from collections import defaultdict
    rows = build(180, 3407)
    per_tool = defaultdict(set)
    for o in rows:
        t = None
        for m in o["messages"]:
            if m["role"] == "assistant" and "```arac" in m["content"]:
                blk = m["content"].split("```arac")[1].split("```")[0].strip()
                t = json.loads(blk)["arac"]
        per_tool[t].add(json.dumps(o, sort_keys=True, ensure_ascii=False))
    for t, s in per_tool.items():
        assert len(s) >= 12, f"{t}: sadece {len(s)} distinct satir"
