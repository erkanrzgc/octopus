"""Rol-scoped ToolRegistry: rol-disi arac reddedilir; asistan cross-cutting; default scope YOK."""
from agent.registry import ToolRegistry
from agent.roles import role_tools
from agent.toolcall import ToolCall


def test_default_is_unscoped():
    assert ToolRegistry.default().allowed is None


def test_scoped_tool_names_match_role():
    reg = ToolRegistry.scoped("recon-scan")
    assert set(reg.tool_names()) == set(role_tools("recon-scan"))


def test_scoped_rejects_out_of_role():
    reg = ToolRegistry.scoped("recon-scan")            # sqlmap 'web', recon degil
    out = reg.invoke(ToolCall("sqlmap", {"url": "http://x"}))
    assert "BU ROL İÇİN DEĞİL" in out
    assert "sqlmap" in out


def test_scoped_allows_in_role_tool():
    reg = ToolRegistry.scoped("recon-scan")
    out = reg.invoke(ToolCall("nmap", {"hedef": "10.0.0.1"}))
    assert "BU ROL İÇİN DEĞİL" not in out               # policy/executor'a ulasir


def test_scoped_allows_asistan_tool():
    reg = ToolRegistry.scoped("recon-scan")             # read_file asistan (cross-cutting)
    out = reg.invoke(ToolCall("read_file", {"yol": "lab/x.txt"}))
    assert "BU ROL İÇİN DEĞİL" not in out
