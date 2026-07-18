"""arac blok parse + modele render. Format: ```arac {"arac":..,"parametreler":{..}} ```.
Geri-besleme egitimle birebir: normalize.flatten_tool_messages reuse (tool->user 'ARAC CIKTISI')."""
from __future__ import annotations
from dataclasses import dataclass
import json
import re
from agent.messages import Message
from data.sft.normalize import flatten_tool_messages

_ARAC_RE = re.compile(r"```arac\s*(\{.*?\})\s*```", re.S)
_DUSUNCE_RE = re.compile(r"```dusunce\s*.*?```", re.S)


def strip_dusunce(text: str) -> str:
    """Kullaniciya giden metinden ```dusunce``` bloklarini sok (ic muhakeme gizli).

    Blok yoksa metni aynen dondurur; asla cokmez. arac blogu KORUNUR (ayri parse edilir).
    """
    return _DUSUNCE_RE.sub("", text or "").strip()


@dataclass(frozen=True)
class ToolCall:
    name: str
    params: dict


def parse_arac_calls(text: str) -> list[ToolCall]:
    """Metindeki her ```arac``` blogunu ToolCall'a cevir; bozuk/eksik blogu atla (asla cokme)."""
    calls: list[ToolCall] = []
    for m in _ARAC_RE.finditer(text or ""):
        try:
            d = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        if not isinstance(d, dict) or "arac" not in d:
            continue
        calls.append(ToolCall(name=str(d["arac"]), params=dict(d.get("parametreler") or {})))
    return calls


def render_for_model(messages: list[Message]) -> list[dict]:
    """Message listesini modele verilecek dict listesine cevir (tool rolu flatten'lanir)."""
    return flatten_tool_messages([m.to_dict() for m in messages])
