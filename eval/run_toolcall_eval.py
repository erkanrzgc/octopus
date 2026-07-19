"""Araç-çağrı eval koşucusu (CLI). Tutulmuş istemleri gerçek modele verir, rapor yazar.

Kullanım:
  uv run python -m eval.run_toolcall_eval --model octopus-v7 --label v0.7-baseline
  uv run python -m eval.run_toolcall_eval --model octopus-v8 --label v0.8-pilot

Model, Ollama üzerinden GgufModel ile çağrılır (eğitim-birebir template). Rapor:
  eval/reports/toolcall_<label>_<tarih>.md  +  .json (ham skorlar, kıyas için).
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from agent.backends.gguf_model import GgufModel
from agent.messages import Message
from eval.toolcall_eval import evaluate, format_report, load_cases

REPORTS = Path("eval/reports")
CASES = "eval/data/toolcall_eval_tr.jsonl"


def _make_generate(model: str, tokenizer_dir: str):
    """GgufModel'i tek-tur (prompt->yanit) bir generate callable'ina sar."""
    gm = GgufModel(model=model, tokenizer_dir=tokenizer_dir)

    def generate(prompt: str) -> str:
        return gm([Message("user", prompt)])

    return generate


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="octopus-v7", help="Ollama model adı")
    ap.add_argument("--label", default="v0.7-baseline", help="rapor etiketi")
    ap.add_argument("--tokenizer-dir", default="models/octopus-v7-tokenizer")
    ap.add_argument("--cases", default=CASES)
    args = ap.parse_args()

    cases = load_cases(args.cases)
    print(f"[*] {len(cases)} istem, model={args.model} ({args.label}) — Ollama'ya gidiyor...")
    generate = _make_generate(args.model, args.tokenizer_dir)
    report = evaluate(cases, generate)

    REPORTS.mkdir(parents=True, exist_ok=True)
    stem = f"toolcall_{args.label}_{date.today().isoformat()}"
    (REPORTS / f"{stem}.md").write_text(format_report(report, args.label), encoding="utf-8")
    (REPORTS / f"{stem}.json").write_text(
        json.dumps({"label": args.label, "model": args.model, **report}, ensure_ascii=False, indent=2),
        encoding="utf-8")

    o = report["oranlar"]
    print(f"[OK] emitted={o['emitted']:.0%} valid={o['valid_call']:.0%} "
          f"katalog={o['in_catalog']:.0%} dogru-arac={o['expected_tool']:.0%}")
    print(f"[OK] rapor -> {REPORTS / stem}.md")


if __name__ == "__main__":
    main()
