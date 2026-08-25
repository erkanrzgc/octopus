"""Sunucu-olayi (incident) tespiti + kosullu RCA kurali.
Kanit (2026-08-25 yerel v10): RCA kurali GLOBAL uygulaninca genel arac-secimini bozar
(dogru-arac 75->54). Bu yuzden SADECE olay dilinde ateslenmeli; saldiri/recon istemine ASLA.
Bu testler dedektorun tam bu ayrimi yaptigini kilitler."""
from __future__ import annotations

import json

from agent.incident import (
    RCA_INCIDENT_RULE,
    assemble_incident_aware_prompt,
    looks_like_incident,
    rca_augmented_system_prompt,
)
from eval.rca_eval import HELDOUT

_BASE = "Sen Octópus'sun."


def test_all_rca_heldout_incidents_detected():
    """5 RCA held-out olayinin HEPSI incident olarak taninmali (kural bunlarda ateslenir)."""
    for c in HELDOUT:
        assert looks_like_incident(c.olay), f"olay incident sayilmadi: {c.olay!r}"


def _toolcall_prompts() -> list[str]:
    rows = [json.loads(l) for l in open("eval/data/toolcall_eval_tr.jsonl", encoding="utf-8") if l.strip()]
    return [r.get("prompt") or r.get("istem") or r.get("user") or "" for r in rows]


def test_no_offensive_toolcall_prompt_is_incident():
    """24 saldiri/recon isteminin HICBIRI incident sayilmamali (yoksa toolcall dilute olur)."""
    for p in _toolcall_prompts():
        assert not looks_like_incident(p), f"saldiri istemi yanlislikla incident: {p!r}"


def test_empty_or_none_is_not_incident():
    assert not looks_like_incident("")
    assert not looks_like_incident(None)  # type: ignore[arg-type]


def test_rca_augmented_appends_rule_and_is_idempotent():
    out = rca_augmented_system_prompt(_BASE)
    assert RCA_INCIDENT_RULE in out
    assert out.startswith(_BASE)
    assert rca_augmented_system_prompt(out) == out  # ikinci kez eklemez


def test_assemble_adds_rule_only_for_incident_task():
    olay = HELDOUT[0].olay
    scan = "192.168.1.50 hedefindeki açık portları tara"
    assert RCA_INCIDENT_RULE in assemble_incident_aware_prompt(_BASE, olay)      # olay -> kural var
    assert RCA_INCIDENT_RULE not in assemble_incident_aware_prompt(_BASE, scan)  # tarama -> kural yok
