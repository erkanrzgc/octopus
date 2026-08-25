"""Flat vs scoped-B araç-seçim kıyası. Aynı tutulmuş istemler, aynı model; scoped = route->subagent.

Rol-scoped subagent backend'in ASIL hipotezini ölçer: araç uzayını rol dilimine daraltmak +
rol-dışını reddedip self-correct ettirmek, araç-seçim doğruluğunu (flat baseline %62-79) yükseltiyor mu?

- flat:      tek-tur generate, İLK ```arac``` çağrısı (mevcut toolcall eval metriği).
- scoped-B:  run_task(prompt) -> route -> rol-scoped subagent; İLK ÇALIŞAN çağrı (scope-deny
             self-correction SONRASI) skorlanır. Prompt DEĞİŞMEZ (on-distribution).

Kullanım (pod ya da yerel GGUF):
  uv run python -m eval.run_subagent_eval --model octopus-v10 --tokenizer-dir models/octopus-v8-tokenizer
"""
from __future__ import annotations

import argparse
from datetime import date
from pathlib import Path

from agent.backends.gguf_model import GgufModel
from agent.messages import Message
from agent.subagent import run_task
from agent.toolcall import parse_arac_calls
from eval.toolcall_eval import load_cases

REPORTS = Path("eval/reports")
CASES = "eval/data/toolcall_eval_tr.jsonl"


def _first_tool(reply: str) -> str | None:
    calls = parse_arac_calls(reply or "")
    return calls[0].name if calls else None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="octopus-v10")
    ap.add_argument("--tokenizer-dir", default="models/octopus-v8-tokenizer")
    ap.add_argument("--cases", default=CASES)
    ap.add_argument("--label", default="octopus-v10")
    args = ap.parse_args()

    cases = load_cases(args.cases)
    gm = GgufModel(model=args.model, tokenizer_dir=args.tokenizer_dir)
    print(f"[*] {len(cases)} istem — flat vs scoped-B, model={args.model}")

    rows = []
    flat_ok = scoped_ok = 0
    for c in cases:
        exp = set(c.expected)
        flat_tool = _first_tool(gm([Message("user", c.prompt)]))       # tek-tur ilk cagri
        run = run_task(c.prompt, lambda msgs: gm(msgs))                # route->scoped subagent
        exec_tool = run.result.calls[0].name if run.result.calls else None
        f_ok, s_ok = int(flat_tool in exp), int(exec_tool in exp)
        flat_ok += f_ok
        scoped_ok += s_ok
        rows.append((run.role, c.prompt, sorted(exp), flat_tool, exec_tool, f_ok, s_ok))
        print(f"  [{run.role:12s}] flat={flat_tool} ({'✓' if f_ok else '✗'}) "
              f"scoped={exec_tool} ({'✓' if s_ok else '✗'})")

    n = len(cases) or 1
    print(f"\nflat   doğru-araç: {flat_ok}/{len(cases)} = {flat_ok/n:.0%}")
    print(f"scoped doğru-araç: {scoped_ok}/{len(cases)} = {scoped_ok/n:.0%}")

    REPORTS.mkdir(parents=True, exist_ok=True)
    out = REPORTS / f"subagent_scoping_{args.label}_{date.today().isoformat()}.md"
    lines = [
        f"# Subagent scoping ölçümü — {args.label}",
        f"_Tarih: {date.today().isoformat()} · {len(cases)} istem · flat vs scoped-B_",
        "",
        f"- **flat doğru-araç:** {flat_ok}/{len(cases)} = {flat_ok/n:.0%}",
        f"- **scoped-B doğru-araç:** {scoped_ok}/{len(cases)} = {scoped_ok/n:.0%}",
        f"- **Δ:** {(scoped_ok-flat_ok)/n:+.0%}",
        "",
        "| rol | istem | beklenen | flat | scoped |",
        "|---|---|---|---|---|",
    ]
    for role, prompt, exp, ft, st, f_ok, s_ok in rows:
        lines.append(f"| {role} | {prompt[:44]} | {','.join(exp)} | "
                     f"{ft or '—'}{'✓' if f_ok else '✗'} | {st or '—'}{'✓' if s_ok else '✗'} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[OK] rapor -> {out}")


if __name__ == "__main__":
    main()
