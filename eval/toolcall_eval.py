"""Araç-çağrı güvenilirliği eval'i — D1 ölçüm kapısının enstrümanı.

NEDEN: D1 reasoning pilotu, ```dusunce``` bloğunun v0.7'nin taç mücevheri olan araç-çağrı
güvenilirliğini BOĞUP boğmadığını ölçmek için var (BalanceSFT riski). Bu modül, tutulmuş
(held-out) araç-çağrı istemlerinde modelin geçerli ```arac``` bloğu üretme davranışını skorlar.
Retrain ÖNCESİ v0.7 baseline'ı yakalanır; retrain SONRASI v0.8-pilot ile kıyaslanır.

Skor, harness'in modeli gerçekte nasıl yorumladığıyla BİREBİR aynı primitiflerle hesaplanır
(parse_arac_calls = JSON geçerliliği, get_spec = katalog geçerliliği) — DRY + tutarlılık.

Metrikler (istem başına):
- emitted:       yanıtta ```arac``` bloğu (fence) VAR mı
- valid_call:    blok geçerli JSON'a çözülüp ToolCall verdi mi (parse_arac_calls)
- in_catalog:    araç adı gerçek katalogda mı (get_spec)
- expected_tool: araç, o istem için uygun araç kümesinde mi (araç SEÇİMİ doğruluğu)
"""
from __future__ import annotations

import json
import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from agent.catalog import get_spec
from agent.toolcall import parse_arac_calls

_ARAC_FENCE = re.compile(r"```arac", re.I)
_METRICS = ("emitted", "valid_call", "in_catalog", "expected_tool")


@dataclass(frozen=True)
class EvalCase:
    """Tutulmuş bir araç-çağrı istemi + kabul edilebilir araç kümesi (seçim tekil değildir)."""
    prompt: str
    expected: list[str]


def score_reply(reply: str, expected: list[str]) -> dict[str, bool]:
    """Tek yanıtı 4 metrikte skorla. Harness primitiflerini kullanır (parse_arac_calls, get_spec)."""
    emitted = bool(_ARAC_FENCE.search(reply or ""))
    calls = parse_arac_calls(reply or "")
    valid_call = bool(calls)
    in_catalog = valid_call and get_spec(calls[0].name) is not None
    expected_tool = valid_call and calls[0].name in set(expected)
    return {"emitted": emitted, "valid_call": valid_call,
            "in_catalog": in_catalog, "expected_tool": expected_tool}


def evaluate(cases: list[EvalCase], generate: Callable[[str], str]) -> dict:
    """Her istemi modele (generate) ver, skorla, agrega oranları döndür.

    generate: prompt metnini alıp modelin ham yanıtını döndüren callable (mock veya GgufModel sarmalı).
    """
    rows = []
    for c in cases:
        reply = generate(c.prompt)
        s = score_reply(reply, c.expected)
        rows.append({"prompt": c.prompt, "expected": c.expected,
                     "arac": (parse_arac_calls(reply or "")[:1] or [None])[0].__str__() if s["valid_call"] else None,
                     **s})
    n = len(cases) or 1
    oranlar = {m: sum(r[m] for r in rows) / n for m in _METRICS}
    return {"toplam": len(cases), "oranlar": oranlar, "satirlar": rows}


def format_report(report: dict, model_label: str) -> str:
    """Agrega raporu kısa Markdown'a çevir (eval/reports/ altına yazmak için)."""
    o = report["oranlar"]
    lines = [
        f"# Araç-çağrı eval — {model_label}",
        f"_Tarih: {date.today().isoformat()} · toplam istem: {report['toplam']}_",
        "",
        "| Metrik | Oran |",
        "|---|---|",
        f"| ```arac``` üretti (emitted) | {o['emitted']:.1%} |",
        f"| Geçerli JSON çağrı (valid_call) | {o['valid_call']:.1%} |",
        f"| Katalogda geçerli (in_catalog) | {o['in_catalog']:.1%} |",
        f"| Doğru araç seçimi (expected_tool) | {o['expected_tool']:.1%} |",
        "",
        "## İstem bazında",
        "| İstem | beklenen | üretilen | doğru? |",
        "|---|---|---|---|",
    ]
    for r in report["satirlar"]:
        arac = r["arac"] or "—"
        ok = "✅" if r["expected_tool"] else ("⚠️kat." if r["in_catalog"] else ("⚠️JSON" if r["emitted"] else "❌yok"))
        lines.append(f"| {r['prompt'][:50]} | {','.join(r['expected'])} | {arac[:40]} | {ok} |")
    return "\n".join(lines) + "\n"


def load_cases(path: str | Path) -> list[EvalCase]:
    """JSONL'den EvalCase listesi yükle: {\"prompt\":.., \"expected\":[..]}."""
    rows = [json.loads(l) for l in Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]
    return [EvalCase(prompt=r["prompt"], expected=list(r["expected"])) for r in rows]
