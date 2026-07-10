"""run_cmd icin yikici-desen denylist'i. NOT sinir DEGIL (asil sinir sandbox);
savunma-derinligi. Saf fonksiyon."""
from __future__ import annotations

import re

from agent.policy import Decision

# Yikici desenler (bosluga toleransli). Eslesme -> fail-closed ret.
_DENY = [
    re.compile(r"\brm\s+-[a-z]*r[a-z]*f[a-z]*\s+(/|~)(\s|$)"),   # rm -rf / veya ~
    re.compile(r"\bmkfs(\.[a-z0-9]+)?\b"),                        # mkfs...
    re.compile(r"\bdd\b.*\bof=/dev/"),                            # dd of=/dev/...
    re.compile(r":\(\)\s*\{\s*:\s*\|\s*:\s*&\s*\}\s*;\s*:"),      # fork bomb
    re.compile(r"\b(shutdown|reboot|halt|poweroff)\b"),
    re.compile(r"\bchmod\s+-[a-z]*R[a-z]*\s+777\s+/"),
    re.compile(r">\s*/dev/(sd|nvme|hd)"),                          # cihaza yazma
]


def guard(params: dict) -> Decision:
    komut = params.get("komut")
    if not komut or not str(komut).strip():
        return Decision(False, False, "'komut' parametresi eksik")
    text = str(komut)
    for rx in _DENY:
        if rx.search(text):
            return Decision(False, False, f"yikici komut deseni reddedildi: {rx.pattern}")
    return Decision(True, False, "izinli")
