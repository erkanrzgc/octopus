from agent.backends.docker_executor import build_argv, DockerExecutor


def test_build_argv_nmap_docker_run():
    argv = build_argv("nmap", {"hedef": "octopus-target", "secenekler": "-Pn -sV -p80"})
    assert argv == [
        "wsl.exe", "-d", "kali-linux", "--", "docker", "run", "--rm", "--network", "octopus-lab",
        "instrumentisto/nmap", "-Pn", "-sV", "-p80", "octopus-target",
    ]


def test_build_argv_unmapped_tool_none():
    # Haritada imaji olmayan arac -> None (run() 'imaj yok' doner).
    assert build_argv("sqlmap", {"url": "http://x"}) is None


def test_build_argv_custom_network():
    argv = build_argv("nmap", {"hedef": "1.2.3.4"}, network="test-net")
    assert "--network" in argv and "test-net" in argv


def test_build_argv_no_shell_injection():
    argv = build_argv("nmap", {"hedef": "t", "secenekler": "; rm -rf /"})
    assert argv[0] == "wsl.exe"  # shell yok
    assert ";" in argv and "rm" in argv  # literal token'lar


def test_run_unknown_tool_rejected():
    assert "bilinmeyen" in DockerExecutor().run("yok_boyle", {}).lower()


def test_run_unmapped_tool_message():
    out = DockerExecutor().run("sqlmap", {"url": "http://x"})
    assert "imaj" in out.lower()
