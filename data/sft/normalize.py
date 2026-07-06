"""SFT normalize cekirdegi — SAF fonksiyonlar (ag/IO yok, test edilebilir).

Farkli veri seti semalarini tek 'messages' formatina cevirir, persona system
prompt'unu basa ekler, NFC normalize eder, kalite filtresi ve dedup fingerprint
uretir. cyberm4fia 01_prepare_data.py deseninden turetildi (kopya degil, uyarlama).
"""
from __future__ import annotations

import hashlib
import unicodedata

from data.sft.persona import OCTOPUS_SYSTEM_PROMPT

# Cok kisa cevap = dusuk sinyal; ele. (karakter)
MIN_ASSISTANT_CHARS = 16
MIN_USER_CHARS = 3


def norm_role(role: str) -> str:
    """Degisik veri setlerindeki rol adlarini standartlastir."""
    r = (role or "").strip().lower()
    if r == "system":
        return "system"
    if r in ("user", "human", "prompt", "instruction", "question"):
        return "user"
    if r in ("assistant", "gpt", "model", "response", "output", "answer"):
        return "assistant"
    return r or "user"


def nfc(text: str) -> str:
    """Unicode NFC normalize. casefold YOK -> Turkce-i (İ/ı) korunur."""
    return unicodedata.normalize("NFC", text or "").strip()


def to_messages(row: dict) -> list[dict] | None:
    """Bilinen semalari birlesik 'messages' listesine cevir.

    Destek: messages/conversations listesi VEYA ayri kolonlar
    (system/user/assistant, instruction/input/output, prompt/response...).
    Basarisizsa None.
    """
    # 1) Zaten mesaj listesi
    for key in ("messages", "conversations", "conversation"):
        val = row.get(key)
        if isinstance(val, list) and val:
            msgs: list[dict] = []
            for m in val:
                if not isinstance(m, dict):
                    return None
                role = norm_role(m.get("role") or m.get("from") or "")
                content = nfc(m.get("content") or m.get("value") or "")
                if content:
                    msgs.append({"role": role, "content": content})
            return msgs or None

    # 2) Ayri kolonlar
    user_txt = row.get("user") or row.get("instruction") or row.get("prompt") or row.get("question")
    asst_txt = row.get("assistant") or row.get("output") or row.get("response") or row.get("answer")
    if user_txt and asst_txt:
        msgs = []
        if row.get("system"):
            msgs.append({"role": "system", "content": nfc(str(row["system"]))})
        if row.get("input"):  # Alpaca tarzi instruction + input
            user_txt = f"{user_txt}\n\n{row['input']}"
        msgs.append({"role": "user", "content": nfc(str(user_txt))})
        msgs.append({"role": "assistant", "content": nfc(str(asst_txt))})
        return msgs
    return None


def ensure_system(msgs: list[dict], system_prompt: str = OCTOPUS_SYSTEM_PROMPT) -> list[dict]:
    """Ilk mesaj system degilse verilen system prompt'u basa ekle (varsa KORUR)."""
    if msgs and msgs[0]["role"] == "system":
        return msgs
    return [{"role": "system", "content": system_prompt}, *msgs]


def strip_system(msgs: list[dict]) -> list[dict]:
    """Tum system mesajlarini cikar (kaynak-ozel system'i atmak icin)."""
    return [m for m in msgs if m["role"] != "system"]


def apply_octopus_system(msgs: list[dict], system_prompt: str = OCTOPUS_SYSTEM_PROMPT) -> list[dict]:
    """Kaynagin system'ini AT, Octopus persona/guardrail'ini system olarak koy.

    Persona tutarliligi icin: model 'system = Ben Octopus + guardrail' baglar.
    Kaynagin jenerik/Ingilizce system'i (or. Fenrir) korunmaz.
    """
    return ensure_system(strip_system(msgs), system_prompt)


def flatten_tool_messages(msgs: list[dict], tool_prefix: str = "ARAÇ ÇIKTISI:\n") -> list[dict]:
    """Gemma-2 chat template'i 'tool' rolunu tanimaz (yalniz system/user/model).

    'tool' rollu mesajlari, icerigin basina bir belirtec ekleyerek 'user' rolune cevirir.
    Boylece arac ciktisi modele bir sonraki 'user' turu gibi verilir (agentic loop davranisiyla
    ayni: harness arac ciktisini geri besler) ve Gemma'nin istedigi user/model alternasyonu korunur.
    Donusum sonrasi ardisik ayni-rol olusursa (or. assistant-arac-call sonrasi degil ama guvenlik icin)
    birlestirir; system asla birlestirilmez. JSONL dosyalari SADIK 4-rollu kalir; bu yalniz render-zamani.
    """
    out: list[dict] = []
    for m in msgs:
        role = m.get("role", "")
        content = m.get("content", "")
        if role == "tool":
            role = "user"
            content = tool_prefix + content
        if out and out[-1]["role"] == role and role != "system":
            out[-1] = {"role": role, "content": out[-1]["content"] + "\n\n" + content}
        else:
            out.append({"role": role, "content": content})
    return out


def is_valid(msgs: list[dict] | None) -> bool:
    """En az bir user + bir yeterli-uzunlukta assistant mesaji var mi?"""
    if not msgs:
        return False
    has_user = any(m["role"] == "user" and len(m["content"]) >= MIN_USER_CHARS for m in msgs)
    has_asst = any(m["role"] == "assistant" and len(m["content"]) >= MIN_ASSISTANT_CHARS for m in msgs)
    return has_user and has_asst


def fingerprint(msgs: list[dict]) -> str:
    """Dedup icin user+assistant icerigine dayali sha256."""
    key = "".join(m["content"] for m in msgs if m["role"] in ("user", "assistant"))
    return hashlib.sha256(key.encode("utf-8", "ignore")).hexdigest()
