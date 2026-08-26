"""Octópus kalite + safety/balance + brittleness eval — yerel Ollama RAW üretimi.

`octopus-eval` skill'in 3 ekseninin (kalite / safety-denge / brittleness) ÜRETİM adımı.
Yargı içerik-tabanlıdır ve insan/Claude tarafından ham çıktılar üzerinden yapılır — bu betik
YALNIZ deterministik (temp=0) üretimi toplar, kelime-eşleşmesiyle puan VERMEZ.

Batarya: `eval/data/quality_safety_tr.jsonl` (15 istem: kalite×4, yetkili×4, yetkisiz×4,
brittle-obf×1, brittle-reframe×2) — v0.8 raporundan çıkarılan kanonik set, sürümler-arası
paired karşılaştırma için sabittir.

Kullanım:
    uv run python -m eval.quality_safety_eval --model octopus-v10 \
        --out eval/reports/v1.0_quality_safety_raw.json

Sistem promptu = OCTOPUS_TOOL_SYSTEM_PROMPT (araç-farkında dağıtım varsayılanı: model
```arac``` bloğu basabilir — v0.8'in "reddederken araç emit etme" glitch'i bu modda görünür).
Template = octopus-v8-tokenizer (v8/v9/v10 aynı Gemma tabanı+template'i paylaşır).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from agent.backends.gguf_model import GgufModel
from agent.messages import Message
from data.sft.persona import OCTOPUS_TOOL_SYSTEM_PROMPT

DEFAULT_BATTERY = "eval/data/quality_safety_tr.jsonl"


def load_battery(path: str) -> list[dict]:
    items: list[dict] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                items.append(json.loads(line))
    return items


def run(model: str, tokenizer_dir: str, temperature: float, num_predict: int,
        battery_path: str) -> list[dict]:
    battery = load_battery(battery_path)
    gm = GgufModel(
        model=model,
        tokenizer_dir=tokenizer_dir,
        system_prompt=OCTOPUS_TOOL_SYSTEM_PROMPT,
        temperature=temperature,
        num_predict=num_predict,
    )
    results: list[dict] = []
    for it in battery:
        out = gm([Message("user", it["soru"])])
        results.append({"id": it["id"], "kategori": it["kategori"],
                        "soru": it["soru"], "yanit": out})
        print(f"[{it['id']:>2} {it['kategori']:<14}] {it['soru'][:60]}")
        print("   >>", out[:200].replace("\n", " ") + ("…" if len(out) > 200 else ""))
    return results


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="octopus-v10")
    ap.add_argument("--tokenizer-dir", default="models/octopus-v8-tokenizer")
    ap.add_argument("--temp", type=float, default=0.0)
    ap.add_argument("--num-predict", type=int, default=512)
    ap.add_argument("--battery", default=DEFAULT_BATTERY)
    ap.add_argument("--out", default="eval/reports/quality_safety_raw.json")
    args = ap.parse_args()

    results = run(args.model, args.tokenizer_dir, args.temp, args.num_predict, args.battery)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\nWROTE {out_path} ({len(results)} yanıt, model={args.model}, temp={args.temp})")


if __name__ == "__main__":
    main()
