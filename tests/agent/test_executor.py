from agent.executor import MockExecutor


def test_scan_domain_returns_ports():
    out = MockExecutor().run("nmap", {"hedef": "10.10.10.5", "secenekler": "-sV"})
    assert "10.10.10.5" in out and "/" in out  # port listesi gibi


def test_unknown_tool_message():
    out = MockExecutor().run("boyle_arac_yok", {})
    assert "bilinmeyen" in out.lower()


def test_output_is_str():
    assert isinstance(MockExecutor().run("whois", {"hedef": "ornek.com"}), str)
