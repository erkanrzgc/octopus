#!/usr/bin/env python
"""Tokenizer fertility (kelime başına token) ölç ve baseline'larla karşılaştır.

Fertility düşük = Türkçeyi daha az parçaya bölüyor = aynı context'e daha çok bilgi,
daha hızlı/ucuz eğitim. Octopus tokenizer'ını mevcut tokenizer'lara (örn. Qwen2.5)
karşı ölçeriz. Hedef: Qwen'in Türkçe fertility'sinin ALTINA inmek.

Kullanım:
    uv run python eval/fertility.py --text data/corpus/eval_tr.txt
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import sentencepiece as spm

# Windows konsolu cp1254 olabilir → Türkçe çıktı için stdout'u UTF-8'e zorla
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def count_words(text: str) -> int:
    return sum(len(line.split()) for line in text.splitlines())


def measure_spm(model_path: str, text: str) -> int:
    sp = spm.SentencePieceProcessor(model_file=model_path)
    return len(sp.encode(text, out_type=int))


def measure_hf(name: str, text: str) -> int | None:
    try:
        from transformers import AutoTokenizer
        tok = AutoTokenizer.from_pretrained(name)
        return len(tok.encode(text, add_special_tokens=False))
    except Exception as e:  # ağ yok / gated / kurulu değil → atla
        print(f"  [skip] {name}: {type(e).__name__}: {e}")
        return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--text", type=Path, required=True, help="değerlendirme metni (held-out TR)")
    ap.add_argument("--spm", default="tokenizer/octopus-tr.model")
    ap.add_argument("--baselines", nargs="*", default=["Qwen/Qwen2.5-0.5B"])
    args = ap.parse_args()

    if not args.text.exists():
        raise SystemExit(f"[!] eval metni yok: {args.text}")

    text = args.text.read_text(encoding="utf-8")
    n_words = max(count_words(text), 1)
    n_chars = max(len(text), 1)
    print(f"eval metni: {n_words} kelime · {n_chars} karakter\n")
    print(f"{'tokenizer':32s} {'tokens':>9s}  {'fertility':>9s}  {'tok/char':>8s}")
    print("-" * 64)

    def report(label: str, n_tokens: int | None) -> None:
        if n_tokens is None:
            return
        print(f"{label:32s} {n_tokens:9d}  {n_tokens / n_words:9.3f}  {n_tokens / n_chars:8.3f}")

    if Path(args.spm).exists():
        report("octopus-tr (bizim)", measure_spm(args.spm, text))
    else:
        print(f"[!] {args.spm} yok — önce tokenizer/train_tokenizer.py çalıştır")
    for name in args.baselines:
        report(name, measure_hf(name, text))


if __name__ == "__main__":
    main()
