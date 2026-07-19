"""Harness transcript renderer — Claude Code tarzı okunur tool-aktivite gösterimi.

SUNUM KATMANI (model kusuru/veri değil): model yine ```arac``` basar; burada güzel render edilir.
- ```dusunce``` bloğu GİZLİ (iç muhakeme kullanıcıya gösterilmez — strip_dusunce).
- Her ```arac``` çağrısı bir '⏺ <araç>' tool-aktivite başlığı + soluk parametre satırı olur.
- Ham arac JSON kullanıcıya gösterilmez; tool ÇIKTISI '⎿' ile girintili/gölgeli blok olur (kısaltmalı).

Saf fonksiyon: ANSI renk yalnız color=True'da (TTY); varsayılan düz metin (test edilebilir, Windows).
"""
from __future__ import annotations

import re

from agent.messages import Message
from agent.toolcall import parse_arac_calls, strip_dusunce

_ARAC_BLOCK = re.compile(r"```arac\s*\{.*?\}\s*```", re.S)
_DIM = "\033[2m"
_BOLD = "\033[1m"
_RESET = "\033[0m"
_DEFAULT_MAX_OUTPUT_LINES = 12


def _sty(text: str, code: str, color: bool) -> str:
    return f"{code}{text}{_RESET}" if color else text


def _strip_blocks(text: str) -> str:
    """Assistant prozasından dusunce + arac bloklarını çıkar (geriye düz konuşma kalır)."""
    return _ARAC_BLOCK.sub("", strip_dusunce(text)).strip()


def _params_ozet(params: dict) -> str:
    return ", ".join(f"{k}={v}" for k, v in params.items())


def _render_tool_output(content: str, max_lines: int, color: bool) -> list[str]:
    """Tool çıktısını '⎿' ile girintili, kısaltmalı, soluk blok olarak render et."""
    lines = (content or "").splitlines() or [""]
    shown, hidden = lines[:max_lines], len(lines) - max_lines
    out = [f"  {_sty('⎿ ' + shown[0], _DIM, color)}"]
    out += [f"    {_sty(l, _DIM, color)}" for l in shown[1:]]
    if hidden > 0:
        out.append(f"    {_sty(f'… (+{hidden} satır)', _DIM, color)}")
    return out


def render_transcript(
    messages: list[Message],
    *,
    color: bool = False,
    max_output_lines: int = _DEFAULT_MAX_OUTPUT_LINES,
) -> str:
    """Message listesini Claude Code tarzı okunur transcript'e çevir (saf, yan etkisiz)."""
    out: list[str] = []
    for m in messages:
        if m.role == "user":
            out.append(_sty(f"▸ {m.content}", _BOLD, color))
        elif m.role == "assistant":
            prose = _strip_blocks(m.content)
            if prose:
                out.append(prose)
            for call in parse_arac_calls(m.content):
                out.append(_sty(f"⏺ {call.name}", _BOLD, color)
                           + _sty(f"  ({call.name} kullanılıyor)", _DIM, color))
                if call.params:
                    out.append(f"  {_sty(_params_ozet(call.params), _DIM, color)}")
        elif m.role == "tool":
            out.extend(_render_tool_output(m.content, max_output_lines, color))
    return "\n".join(out)
