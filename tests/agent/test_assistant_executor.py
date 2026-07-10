from agent.backends.assistant_executor import AssistantExecutor


def test_write_then_read(tmp_path):
    ex = AssistantExecutor(str(tmp_path))
    ex.run("write_file", {"yol": "a.txt", "icerik": "merhaba"})
    assert "merhaba" in ex.run("read_file", {"yol": "a.txt"})


def test_edit_file(tmp_path):
    ex = AssistantExecutor(str(tmp_path))
    ex.run("write_file", {"yol": "a.txt", "icerik": "eski deger"})
    ex.run("edit_file", {"yol": "a.txt", "eski": "eski", "yeni": "yeni"})
    assert "yeni deger" in ex.run("read_file", {"yol": "a.txt"})


def test_list_dir(tmp_path):
    (tmp_path / "x.txt").write_text("1", encoding="utf-8")
    out = AssistantExecutor(str(tmp_path)).run("list_dir", {"yol": "."})
    assert "x.txt" in out


def test_grep(tmp_path):
    (tmp_path / "x.txt").write_text("TODO: fix\nnope", encoding="utf-8")
    out = AssistantExecutor(str(tmp_path)).run("grep", {"desen": "TODO", "yol": "."})
    assert "TODO" in out


def test_run_cmd_delegates_to_sandbox(tmp_path):
    calls = {}

    class FakeSandbox:
        def run(self, tool, params):
            calls["got"] = (tool, params)
            return "SANDBOX_OUT"

    ex = AssistantExecutor(str(tmp_path), sandbox=FakeSandbox())
    out = ex.run("run_cmd", {"komut": "ls"})
    assert out == "SANDBOX_OUT"
    assert calls["got"][1]["komut"] == "ls"   # host'a gitmedi, sandbox'a gitti


def test_web_fetch_uses_injected_client(tmp_path):
    ex = AssistantExecutor(str(tmp_path), http_get=lambda url: f"FETCHED:{url}")
    assert ex.run("web_fetch", {"url": "https://x/"}) == "FETCHED:https://x/"


def test_web_search_uses_injected_backend(tmp_path):
    ex = AssistantExecutor(str(tmp_path), search=lambda q: f"RESULTS:{q}")
    assert ex.run("web_search", {"sorgu": "mac saati"}) == "RESULTS:mac saati"
