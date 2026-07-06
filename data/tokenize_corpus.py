#!/usr/bin/env python
"""Temiz korpusu octopus-tr ile tokenize edip uint16 .bin'e yaz (nanoGPT-tarzı).

Her satır sonuna EOS eklenir. Eğitim loader'ı .bin'i memory-map'leyip rastgele
seq_len pencereler örnekler. vocab 32k < 65536 → uint16 yeterli.

Not: tüm token'lar bellekte `array('H')` olarak tutulur; mevcut korpus için yeterli.
Çok-GB korpusta shard'lı/streaming yazıma geçilecek.

Kullanım:
    uv run python data/tokenize_corpus.py --input data/corpus/tr_wiki.clean.txt
"""
from __future__ import annotations

import argparse
from array import array
from pathlib import Path

import numpy as np
import sentencepiece as spm


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=Path("data/corpus/tr_wiki.clean.txt"))
    ap.add_argument("--spm", default="tokenizer/octopus-tr.model")
    ap.add_argument("--out", type=Path, default=Path("data/bin/train.bin"))
    ap.add_argument("--val-out", type=Path, default=Path("data/bin/val.bin"))
    ap.add_argument("--val-fraction", type=float, default=0.005)
    args = ap.parse_args()

    if not args.input.exists():
        raise SystemExit(f"[!] korpus yok: {args.input} — önce data/clean.py")
    if not Path(args.spm).exists():
        raise SystemExit(f"[!] tokenizer yok: {args.spm}")

    sp = spm.SentencePieceProcessor(model_file=args.spm)
    eos = sp.eos_id()
    args.out.parent.mkdir(parents=True, exist_ok=True)

    ids = array("H")  # uint16
    n_lines = 0
    with args.input.open(encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line:
                continue
            toks = sp.encode(line, out_type=int)
            toks.append(eos)
            ids.extend(toks)
            n_lines += 1

    arr = np.frombuffer(ids, dtype=np.uint16)
    n_val = int(len(arr) * args.val_fraction)
    val, train = arr[:n_val], arr[n_val:]
    train.tofile(args.out)
    val.tofile(args.val_out)

    print(f"[ok] {n_lines:,} satır → {len(arr):,} token")
    print(f"     train {len(train):,} tok ({train.nbytes / 1e6:.1f} MB) -> {args.out}")
    print(f"     val   {len(val):,} tok ({val.nbytes / 1e6:.1f} MB) -> {args.val_out}")


if __name__ == "__main__":
    main()
