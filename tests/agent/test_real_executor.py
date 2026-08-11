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


# --- BUG FIX: build_argv secenekler+hedef DISINDAKI parametreleri DUSURUYORDU ---
# (discovery kanitlandi ama keşfedilen arac RealExecutor'a giderse yanlis cagriliyordu).

def test_build_argv_extension_trufflehog_renders_kaynak_subcommand():
    # 'kaynak' (git/filesystem/github) alt-komutu DUSURULMEMELI; hedef en sona.
    argv = build_argv("trufflehog", {"kaynak": "git", "hedef": "https://github.com/x/y"})
    assert argv == ["wsl.exe", "-d", "kali-linux", "--",
                    "trufflehog", "git", "https://github.com/x/y"]


def test_build_argv_extension_magika_renders_yol_positional():
    # 'yol' AG-hedefi DEGIL -> eskiden HIC arg gelmiyordu (magika arg'siz calisirdi).
    argv = build_argv("magika", {"yol": "/tmp/ornek.bin"})
    assert argv == ["wsl.exe", "-d", "kali-linux", "--", "magika", "/tmp/ornek.bin"]


def test_build_argv_extension_ghunt_renders_modul_subcommand():
    argv = build_argv("ghunt", {"modul": "email", "hedef": "hedef@ornek.com"})
    assert argv == ["wsl.exe", "-d", "kali-linux", "--",
                    "ghunt", "email", "hedef@ornek.com"]


def test_build_argv_subcommand_param_not_dropped_and_before_target():
    # netexec: 'protokol' alt-komutu DUSURULMEMELI ve ag-hedefinden ONCE gelmeli.
    argv = build_argv("netexec", {"hedef": "10.10.10.15", "protokol": "smb",
                                  "secenekler": "-u a -p b"})
    assert "smb" in argv                      # protokol artik dusmuyor
    assert argv.index("smb") < argv.index("10.10.10.15")  # alt-komut hedeften once
