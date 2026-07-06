"""data/sft/normalize.py saf fonksiyon testleri (AAA pattern)."""
from __future__ import annotations

from data.sft.normalize import (
    apply_octopus_system,
    ensure_system,
    fingerprint,
    is_valid,
    nfc,
    norm_role,
    strip_system,
    to_messages,
)
from data.sft.persona import OCTOPUS_SYSTEM_PROMPT


def test_norm_role_maps_aliases_to_standard_roles():
    assert norm_role("human") == "user"
    assert norm_role("instruction") == "user"
    assert norm_role("gpt") == "assistant"
    assert norm_role("output") == "assistant"
    assert norm_role("System") == "system"


def test_nfc_preserves_turkish_dotted_and_dotless_i():
    # NFC bozmamali; casefold OLMAMALI (İ -> i'ye donmemeli)
    text = "İstanbul ılık"
    assert nfc(text) == "İstanbul ılık"


def test_to_messages_from_separate_columns():
    row = {"instruction": "Log4Shell nedir?", "output": "CVE-2021-44228 bir RCE zafiyetidir."}
    msgs = to_messages(row)
    assert msgs is not None
    assert [m["role"] for m in msgs] == ["user", "assistant"]
    assert "Log4Shell" in msgs[0]["content"]


def test_to_messages_from_message_list_with_from_value_schema():
    row = {"conversations": [
        {"from": "human", "value": "SQL injection?"},
        {"from": "gpt", "value": "Parametreli sorgu kullan."},
    ]}
    msgs = to_messages(row)
    assert [m["role"] for m in msgs] == ["user", "assistant"]


def test_to_messages_alpaca_input_is_merged_into_user():
    row = {"instruction": "Bu CVE'yi acikla", "input": "CVE-2021-44228", "output": "Log4Shell RCE."}
    msgs = to_messages(row)
    assert "CVE-2021-44228" in msgs[0]["content"]  # user, input birlesmis


def test_to_messages_returns_none_when_no_answer():
    assert to_messages({"instruction": "sadece soru"}) is None


def test_ensure_system_prepends_octopus_persona_when_absent():
    msgs = [{"role": "user", "content": "selam"}, {"role": "assistant", "content": "Ben Octópus."}]
    out = ensure_system(msgs)
    assert out[0]["role"] == "system"
    assert out[0]["content"] == OCTOPUS_SYSTEM_PROMPT


def test_ensure_system_keeps_existing_source_system_message():
    msgs = [{"role": "system", "content": "kaynak talimati"}, {"role": "user", "content": "x"}]
    out = ensure_system(msgs)
    assert out[0]["content"] == "kaynak talimati"  # ustune yazma


def test_apply_octopus_system_replaces_source_system_with_persona():
    # Fenrir gibi kendi (Ingilizce/jenerik) system'i olan kaynak -> Octopus persona kazanir
    msgs = [
        {"role": "system", "content": "You are an advanced cybersecurity AI."},
        {"role": "user", "content": "Log4Shell?"},
        {"role": "assistant", "content": "CVE-2021-44228 bir RCE zafiyetidir, uzun cevap."},
    ]
    out = apply_octopus_system(msgs)
    assert out[0]["role"] == "system"
    assert out[0]["content"] == OCTOPUS_SYSTEM_PROMPT       # kaynak system'i atildi
    assert [m["role"] for m in out[1:]] == ["user", "assistant"]
    assert all("advanced cybersecurity AI" not in m["content"] for m in out)


def test_strip_system_removes_all_system_messages():
    msgs = [{"role": "system", "content": "x"}, {"role": "user", "content": "q"}]
    assert all(m["role"] != "system" for m in strip_system(msgs))


def test_is_valid_rejects_too_short_assistant():
    short = [{"role": "user", "content": "soru?"}, {"role": "assistant", "content": "ok"}]
    assert is_valid(short) is False


def test_is_valid_accepts_proper_pair():
    ok = [{"role": "user", "content": "Nmap taramasi nasil?"},
          {"role": "assistant", "content": "nmap -sV hedef (yalnizca yetkili hedeflerde)."}]
    assert is_valid(ok) is True


def test_fingerprint_ignores_system_and_is_stable():
    a = [{"role": "system", "content": "A"}, {"role": "user", "content": "q"}, {"role": "assistant", "content": "yeterince uzun cevap"}]
    b = [{"role": "system", "content": "B"}, {"role": "user", "content": "q"}, {"role": "assistant", "content": "yeterince uzun cevap"}]
    # Ayni user+assistant -> ayni fingerprint (system farki dedup'u etkilemez)
    assert fingerprint(a) == fingerprint(b)
