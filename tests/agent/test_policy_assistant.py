from agent.catalog import get_spec
from agent.policy import LabPolicy


def test_write_file_traversal_denied(tmp_path):
    pol = LabPolicy(scope=[], workspace_root=str(tmp_path))
    d = pol.decide(get_spec("write_file"), {"yol": "../escape.txt", "icerik": "x"})
    assert d.allowed is False


def test_read_file_in_workspace_allowed(tmp_path):
    pol = LabPolicy(scope=[], workspace_root=str(tmp_path))
    d = pol.decide(get_spec("read_file"), {"yol": "notes.txt"})
    assert d.allowed is True


def test_web_fetch_metadata_denied_not_scope_checked():
    # url bir TARGET_KEY ama asistan araci -> ag-scope'a DEGIL web guard'a gider
    pol = LabPolicy(scope=[])
    d = pol.decide(get_spec("web_fetch"), {"url": "http://x/"})  # cozumsuz/ozel -> ret
    assert d.allowed is False


def test_run_cmd_requires_approval(tmp_path):
    pol = LabPolicy(scope=[], workspace_root=str(tmp_path), allow_high=False)
    d = pol.decide(get_spec("run_cmd"), {"komut": "ls -la"})
    assert d.allowed is False and d.requires_approval is True


def test_run_cmd_destructive_denied_before_approval(tmp_path):
    pol = LabPolicy(scope=[], workspace_root=str(tmp_path), allow_high=True)
    d = pol.decide(get_spec("run_cmd"), {"komut": "rm -rf /"})
    assert d.allowed is False and d.requires_approval is False


def test_network_tool_unchanged():
    pol = LabPolicy(scope=["10.0.0.0/24"])
    d = pol.decide(get_spec("nmap"), {"hedef": "10.0.0.5", "secenekler": "-sV"})
    assert d.allowed is True
