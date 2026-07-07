from agent.backends.real_executor import build_argv, RealExecutor


def test_build_argv_nmap_flags_then_target():
    argv = build_argv("nmap", {"hedef": "172.30.0.10", "secenekler": "-sV -p80"})
    assert argv == ["wsl.exe", "-d", "kali-linux", "--", "nmap", "-sV", "-p80", "172.30.0.10"]


def test_build_argv_no_target_not_appended():
    argv = build_argv("msfvenom", {"secenekler": "-p windows/x"})
    assert argv == ["wsl.exe", "-d", "kali-linux", "--", "msfvenom", "-p", "windows/x"]


def test_build_argv_no_shell_injection():
    # secenekler icindeki ; | && LITERAL token olur (argv), shell metakarakteri DEGIL.
    argv = build_argv("nmap", {"hedef": "1.2.3.4", "secenekler": "; rm -rf /"})
    assert argv[0] == "wsl.exe"  # shell yok, dogrudan exe
    assert ";" in argv and "rm" in argv and "/" in argv  # ayri literal token'lar


def test_run_unknown_tool_rejected():
    # Katalog-disi arac calistirilmaz (subprocess'e hic gitmez).
    assert "bilinmeyen" in RealExecutor().run("boyle_arac_yok", {}).lower()


def test_custom_distro():
    argv = build_argv("nmap", {"hedef": "1.2.3.4"}, distro="Ubuntu")
    assert argv[:3] == ["wsl.exe", "-d", "Ubuntu"]
