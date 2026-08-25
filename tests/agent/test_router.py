"""Deterministik gorev->rol yonlendirme; eslesme yoksa general."""
from agent.router import route


def test_wireless():
    assert route("komsu wifi agini test et, WPA handshake yakala") == "wireless"


def test_password():
    assert route("bu hash listesini hashcat ile kir") == "password"


def test_web():
    assert route("hedef sitede SQL injection dene, sqlmap kullan") == "web"


def test_exploit_ad():
    assert route("SMB paylasimina netexec ile baglan, lateral hareket") == "exploit-ad"


def test_recon():
    assert route("10.0.0.0/24 aginda canli hostlari ve portlari tara (nmap)") == "recon-scan"


def test_blue_server():
    assert route("sunucuda fail2ban ve firewall ile sertlestirme yap") == "blue-server"


def test_empty_and_unknown_go_general():
    assert route("") == "general"
    assert route("bugun hava nasil") == "general"
