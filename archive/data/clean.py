#!/usr/bin/env python
"""Ham korpusu temizle: NFC normalize + kalite filtresi + satır dedup.

NFC normalizasyonu BURADA yapılır (tokenizer `identity` olduğu için normalizasyon
veri tarafına taşındı). Çıktı sonra `tokenize_corpus.py` ile .bin'e çevrilir.

Not: dedup şu an exact-line (bellekte hash set) — mevcut korpus için yeterli.
Çok-GB korpusta MinHash / streaming dedup gerekecek.

Kullanım:
    uv run python data/clean.py --input data/corpus/tr_wiki.txt --out data/corpus/tr_wiki.clean.txt
"""
from __future__ import annotations

import argparse
import sys
import unicodedata
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


def is_quality(line: str, min_chars: int, min_letter_ratio: float) -> bool:
    """Çok kısa veya çoğu sembol/sayı olan satırları ele."""
    if len(line) < min_chars:
        return False
    letters = sum(ch.isalpha() for ch in line)
    return letters / len(line) >= min_letter_ratio


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=Path("data/corpus/tr_wiki.txt"))
    ap.add_argument("--out", type=Path, default=Path("data/corpus/tr_wiki.clean.txt"))
    ap.add_argument("--min-chars", type=int, default=40)
    ap.add_argument("--min-letter-ratio", type=float, default=0.5,
                    help="satırın en az bu oranı harf olmalı (sembol/sayı spam'ini eler)")
    args = ap.parse_args()

    if not args.input.exists():
        raise SystemExit(f"[!] korpus yok: {args.input}")
    args.out.parent.mkdir(parents=True, exist_ok=True)

    seen: set[int] = set()
    n_in = n_out = n_dup = n_lowq = 0
    with args.input.open(encoding="utf-8") as f, args.out.open("w", encoding="utf-8") as g:
        for raw in f:
            n_in += 1
            line = unicodedata.normalize("NFC", raw.strip())
            if not line:
                continue
            if not is_quality(line, args.min_chars, args.min_letter_ratio):
                n_lowq += 1
                continue
            key = hash(line)
            if key in seen:
                n_dup += 1
                continue
            seen.add(key)
            g.write(line + "\n")
            n_out += 1

    print(f"[ok] in={n_in:,}  out={n_out:,}  (dedup atılan={n_dup:,}, düşük-kalite={n_lowq:,})")
    print(f"     -> {args.out}")


if __name__ == "__main__":
    main()
