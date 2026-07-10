from agent.composite_executor import CompositeExecutor


class _Tag:
    def __init__(self, tag):
        self.tag = tag

    def run(self, tool, params):
        return f"{self.tag}:{tool}"


def test_routes_assistant_domain():
    ce = CompositeExecutor(security=_Tag("SEC"), assistant=_Tag("ASST"))
    assert ce.run("read_file", {"yol": "a"}) == "ASST:read_file"


def test_routes_security_domain():
    ce = CompositeExecutor(security=_Tag("SEC"), assistant=_Tag("ASST"))
    assert ce.run("nmap", {"hedef": "10.0.0.5"}) == "SEC:nmap"


def test_unknown_tool_is_error_string():
    ce = CompositeExecutor(security=_Tag("SEC"), assistant=_Tag("ASST"))
    assert "bilinmeyen" in ce.run("yok_boyle_arac", {}).lower()
