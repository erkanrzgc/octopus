#!/usr/bin/env python
"""Türkçe korpus indir (tokenizer + ileride pretraining için ham metin).

Varsayılan kaynak: Türkçe Wikipedia (temiz, diakritikli). Tokenizer eğitimi için
birkaç yüz MB fazlasıyla yeter; pretraining için sonra OSCAR/mC4-tr eklenir.

Çıktı: düz metin, satır başına bir paragraf (tokenizer için iyi granülerlik).
Ayrıca held-out bir eval dosyası ayırır (fertility ölçümü için).

Kullanım:
    uv run python data/download_corpus.py --max-docs 50000
"""
from __future__ import annotations

import argparse
from pathlib import Path

from datasets import load_dataset
from tqdm import tqdm


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default="wikimedia/wikipedia")
    ap.add_argument("--config", default="20231101.tr")
    ap.add_argument("--split", default="train")
    ap.add_argument("--out", type=Path, default=Path("data/corpus/tr_wiki.txt"))
    ap.add_argument("--eval-out", type=Path, default=Path("data/corpus/eval_tr.txt"))
    ap.add_argument("--max-docs", type=int, default=0, help="0 = tüm split")
    ap.add_argument("--eval-docs", type=int, default=300, help="held-out eval belge sayısı")
    ap.add_argument("--min-chars", type=int, default=200, help="bundan kısa belgeleri atla")
    args = ap.parse_args()

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.eval_out.parent.mkdir(parents=True, exist_ok=True)

    # streaming → tüm dataset'i RAM'e almadan akıt
    ds = load_dataset(args.dataset, args.config, split=args.split, streaming=True)

    n_docs = n_chars = 0
    with args.out.open("w", encoding="utf-8") as train_f, \
         args.eval_out.open("w", encoding="utf-8") as eval_f:
        for ex in tqdm(ds, desc="indiriliyor"):
            text = (ex.get("text") or "").strip()
            if len(text) < args.min_chars:
                continue
            # ilk N belge held-out eval'e, gerisi train'e
            target = eval_f if n_docs < args.eval_docs else train_f
            for para in text.split("\n"):
                para = para.strip()
                if para:
                    target.write(para + "\n")
            n_docs += 1
            n_chars += len(text)
            if args.max_docs and n_docs >= args.max_docs:
                break

    print(f"[ok] {n_docs} belge · ~{n_chars / 1e6:.1f}M karakter")
    print(f"     train -> {args.out}")
    print(f"     eval  -> {args.eval_out} (ilk {min(args.eval_docs, n_docs)} belge)")


if __name__ == "__main__":
    main()
