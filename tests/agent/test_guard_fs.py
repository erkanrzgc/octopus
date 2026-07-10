from agent.guards import fs


def test_denies_when_root_unset():
    assert fs.guard({"yol": "a.txt"}, None).allowed is False


def test_denies_missing_path():
    assert fs.guard({}, "/tmp/ws").allowed is False


def test_allows_path_inside_root(tmp_path):
    (tmp_path / "sub").mkdir()
    d = fs.guard({"yol": "sub/a.txt"}, str(tmp_path))
    assert d.allowed is True


def test_denies_traversal(tmp_path):
    assert fs.guard({"yol": "../../etc/passwd"}, str(tmp_path)).allowed is False


def test_denies_absolute_escape(tmp_path):
    assert fs.guard({"yol": "/etc/passwd"}, str(tmp_path)).allowed is False


def test_denies_symlink_escape(tmp_path):
    outside = tmp_path.parent / "outside_secret"
    outside.mkdir(exist_ok=True)
    link = tmp_path / "link"
    try:
        link.symlink_to(outside)
    except (OSError, NotImplementedError):
        import pytest
        pytest.skip("symlink olusturulamiyor (izin/OS)")
    assert fs.guard({"yol": "link/x.txt"}, str(tmp_path)).allowed is False
