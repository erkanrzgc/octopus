import pytest

from agent.guards import cmd


@pytest.mark.parametrize("komut", [
    "rm -rf /", "rm  -rf   /", "rm -rf ~", "mkfs.ext4 /dev/sda",
    "dd if=/dev/zero of=/dev/sda", ":(){ :|:& };:", "shutdown -h now", "reboot",
    "chmod -R 777 /", "> /dev/sda",
])
def test_denies_destructive(komut):
    assert cmd.guard({"komut": komut}).allowed is False


@pytest.mark.parametrize("komut", [
    "nmap -sV 10.0.0.5", "ls -la", "cat notes.txt", "python3 script.py", "grep -r TODO .",
])
def test_allows_benign(komut):
    assert cmd.guard({"komut": komut}).allowed is True


def test_denies_missing_command():
    assert cmd.guard({}).allowed is False
