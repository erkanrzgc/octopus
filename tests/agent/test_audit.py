import json
from agent.audit import AuditLog


def test_write_appends_jsonl(tmp_path):
    log = AuditLog(tmp_path / "audit.jsonl")
    log.write("tool.start", "nmap")
    log.write("tool.done", "3 port")
    lines = (tmp_path / "audit.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    rec = json.loads(lines[0])
    assert rec["event"] == "tool.start" and rec["detail"] == "nmap" and "ts" in rec
