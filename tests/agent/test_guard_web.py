from agent.guards import web


def _fake_resolve(mapping):
    return lambda host: mapping.get(host, "203.0.113.10")  # varsayilan public


def test_web_search_always_allowed():
    assert web.guard({"sorgu": "ispanya belcika mac saati"}).allowed is True


def test_fetch_public_allowed():
    d = web.guard({"url": "https://example.com/x"}, resolve=_fake_resolve({"example.com": "93.184.216.34"}))
    assert d.allowed is True


def test_fetch_denies_metadata_ip():
    d = web.guard({"url": "http://metadata.internal/latest"},
                  resolve=_fake_resolve({"metadata.internal": "169.254.169.254"}))
    assert d.allowed is False


def test_fetch_denies_loopback_and_private():
    assert web.guard({"url": "http://localhost/"}, resolve=_fake_resolve({"localhost": "127.0.0.1"})).allowed is False
    assert web.guard({"url": "http://x/"}, resolve=_fake_resolve({"x": "10.1.2.3"})).allowed is False


def test_fetch_denies_non_http_scheme():
    assert web.guard({"url": "file:///etc/passwd"}).allowed is False


def test_fetch_denies_missing_url():
    assert web.guard({}).allowed is False
