"""DockerSandboxExecutor — run_cmd'yi izole, ağı-kapalı docker konteynerinde çalıştırır.
Gerçek docker GEREKMEZ: runner enjekte edilir (DockerExecutor argv-test deseni)."""
from __future__ import annotations

import subprocess
from types import SimpleNamespace

import pytest

from agent.backends.sandbox_executor import DockerSandboxExecutor, build_argv


def _fake_proc(stdout="", stderr="", returncode=0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


class _Recorder:
    """subprocess.run yerine geçen kaydedici."""
    def __init__(self, proc=None, exc=None):
        self.proc = proc or _fake_proc(stdout="ok")
        self.exc = exc
        self.calls: list[list[str]] = []

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        self.kwargs = kwargs
        if self.exc:
            raise self.exc
        return self.proc


# ---- build_argv: sertleştirme sınırı ----

def test_argv_has_all_hardening_flags():
    argv = build_argv("ls -la")
    joined = " ".join(argv)
    for flag in ["--rm", "--network none", "--memory 512m", "--pids-limit 256",
                 "--cpus 1", "-u 65534:65534", "--read-only", "--cap-drop ALL",
                 "--security-opt no-new-privileges"]:
        assert flag in joined, f"eksik sertleştirme bayrağı: {flag}"


def test_argv_uses_alpine_and_sh_c():
    argv = build_argv("whoami")
    assert "alpine" in argv
    i = argv.index("sh")
    assert argv[i:i + 2] == ["sh", "-c"]
    payload = argv[i + 2]  # sarmalanmış komut TEK eleman — host shell yorumlamaz
    assert "whoami" in payload


def test_output_capped_in_container():
    # Sınırsız-stdout host-DoS'a karşı: çıktı konteyner içinde head -c ile kırpılır
    payload = build_argv("yes")[build_argv("yes").index("sh") + 2]
    assert "head -c" in payload


def test_komut_not_split_injection_safe():
    # Metakarakterli komut TEK sh -c elemanı içinde; ayrı argv token'i olmamalı
    evil = "echo a; rm b && curl evil"
    argv = build_argv(evil)
    payload = argv[argv.index("sh") + 2]
    assert evil in payload
    assert "rm" not in argv and "curl" not in argv  # host'a ayri token sizmadi


def test_docker_prefix_injectable():
    argv = build_argv("id", docker_prefix=["wsl.exe", "-d", "kali", "--", "docker"])
    assert argv[:5] == ["wsl.exe", "-d", "kali", "--", "docker"]
    assert argv[5] == "run"


# ---- run(): davranış ----

def test_run_returns_combined_output():
    rec = _Recorder(_fake_proc(stdout="satir1\n", stderr="uyari\n"))
    ex = DockerSandboxExecutor(runner=rec)
    out = ex.run("run_cmd", {"komut": "echo hi"})
    assert "satir1" in out and "uyari" in out
    assert len(rec.calls) == 1


def test_denylist_blocks_before_docker():
    rec = _Recorder()
    ex = DockerSandboxExecutor(runner=rec)
    out = ex.run("run_cmd", {"komut": "rm -rf /"})
    assert "HATA" in out
    assert rec.calls == [], "yıkıcı komut docker'a gitmemeli (denylist önce)"


def test_timeout_handled():
    rec = _Recorder(exc=subprocess.TimeoutExpired(cmd="docker", timeout=60))
    ex = DockerSandboxExecutor(runner=rec)
    out = ex.run("run_cmd", {"komut": "sleep 999"})
    assert "HATA" in out and "zaman" in out.lower()


def test_docker_missing_handled():
    rec = _Recorder(exc=FileNotFoundError())
    ex = DockerSandboxExecutor(runner=rec)
    out = ex.run("run_cmd", {"komut": "ls"})
    assert "HATA" in out and "docker" in out.lower()


def test_non_run_cmd_rejected():
    rec = _Recorder()
    ex = DockerSandboxExecutor(runner=rec)
    out = ex.run("nmap", {"hedef": "10.0.0.1"})
    assert "HATA" in out
    assert rec.calls == []


def test_empty_komut_rejected():
    rec = _Recorder()
    ex = DockerSandboxExecutor(runner=rec)
    out = ex.run("run_cmd", {"komut": "  "})
    assert "HATA" in out
    assert rec.calls == []


def test_timeout_kwarg_passed():
    rec = _Recorder()
    ex = DockerSandboxExecutor(runner=rec, timeout=42)
    ex.run("run_cmd", {"komut": "ls"})
    assert rec.kwargs.get("timeout") == 42


def test_timeout_kills_orphan_container():
    # Timeout'ta asili konteyner best-effort `docker kill` edilmeli (yetim sizintisi)
    class _KillRec:
        def __init__(self):
            self.calls: list[list[str]] = []

        def __call__(self, argv, **kwargs):
            self.calls.append(argv)
            if "run" in argv:
                raise subprocess.TimeoutExpired(cmd="docker", timeout=60)
            return _fake_proc()

    rec = _KillRec()
    ex = DockerSandboxExecutor(runner=rec)
    out = ex.run("run_cmd", {"komut": "sleep 999"})
    assert "HATA" in out and "zaman" in out.lower()
    assert any("kill" in c for c in rec.calls), "timeout'ta docker kill cagrilmali"
