#!/usr/bin/env python
"""FineWeb-2 Türkçe'yi streaming çek → temizle → octopus-tr ile tokenize → uint16 shard'lar.

Ölçek pipeline'ı: `clean.py` + `tokenize_corpus.py`'nin bellek-içi sürümünün yerine geçer.
Tüm korpusu RAM'e/diske yığmadan akıtır; token tamponu `--shard-tokens`'a ulaşınca
`shard_NNNNN.bin`'e boşaltılır → RAM sabit kalır (1B de 50B de aynı).

Tasarım:
- EOS **belge sonunda** (satır başına değil): tokenizer `identity` → belge-içi newline korunur,
  model uzun-menzilli yapıyı öğrenir. Belge ayırıcı = EOS.
- Kalite filtresi belge düzeyinde (`is_quality`, clean.py'dan). FineWeb-2 zaten dedup+filtreli →
  ağır exact-dedup'a gerek yok (zaten milyarlarca token RAM'e sığmaz).
- İlk `--val-tokens` token held-out `val.bin`'e; gerisi train shard'larına.

Kullanım (önce küçük dry-run, sonra büyük tur):
    uv run python data/build_pretrain_data.py --max-tokens 5_000_000          # doğrulama
    uv run python data/build_pretrain_data.py --max-tokens 3_000_000_000      # ~3B token tur
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import unicodedata
from array import array
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import numpy as np
import sentencepiece as spm
from datasets import load_dataset

from data.clean import is_quality

ENC_CHUNK = 200_000  # çok uzun belgeleri parça parça encode et (SentencePiece dostu)


def encode_doc(sp: spm.SentencePieceProcessor, text: str) -> list[int]:
    """Belgeyi NFC normalize edip token'lara çevir (uzunsa parçalayarak)."""
    text = unicodedata.normalize("NFC", text)
    if len(text) <= ENC_CHUNK:
        return sp.encode(text, out_type=int)
    out: list[int] = []
    for i in range(0, len(text), ENC_CHUNK):
        out.extend(sp.encode(text[i:i + ENC_CHUNK], out_type=int))
    return out


def flush_shard(buf: array, out_dir: Path, idx: int) -> dict:
    path = out_dir / f"shard_{idx:05d}.bin"
    np.frombuffer(buf, dtype=np.uint16).tofile(path)
    return {"file": path.name, "tokens": len(buf)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dataset", default="HuggingFaceFW/fineweb-2")
    ap.add_argument("--config", default="tur_Latn")
    ap.add_argument("--split", default="train")
    ap.add_argument("--spm", default="tokenizer/octopus-tr.model")
    ap.add_argument("--out-dir", type=Path, default=Path("data/bin/fineweb2_tr"))
    ap.add_argument("--max-tokens", type=int, default=0, help="0 = sınırsız (tüm split)")
    ap.add_argument("--shard-tokens", type=int, default=100_000_000, help="shard başına token")
    ap.add_argument("--val-tokens", type=int, default=5_000_000, help="held-out val token")
    ap.add_argument("--min-chars", type=int, default=200)
    ap.add_argument("--min-letter-ratio", type=float, default=0.5)
    ap.add_argument("--log-every", type=int, default=2000, help="kaç belgede bir log")
    ap.add_argument("--overwrite", action="store_true")
    args = ap.parse_args()

    if not Path(args.spm).exists():
        raise SystemExit(f"[!] tokenizer yok: {args.spm}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    existing = list(args.out_dir.glob("shard_*.bin")) + list(args.out_dir.glob("val.bin"))
    if existing and not args.overwrite:
        raise SystemExit(f"[!] {args.out_dir} dolu ({len(existing)} dosya) — --overwrite ver veya temizle")
    for p in existing:
        p.unlink()

    sp = spm.SentencePieceProcessor(model_file=args.spm)
    eos = sp.eos_id()

    print(f"[stream] {args.dataset}:{args.config} ({args.split}) → {args.out_dir}")
    ds = load_dataset(args.dataset, name=args.config, split=args.split, streaming=True)

    val_buf = array("H")
    buf = array("H")
    shards: list[dict] = []
    shard_idx = 0
    n_docs = n_kept = total_tokens = 0
    t0 = time.time()

    for ex in ds:
        n_docs += 1
        text = (ex.get("text") or "").strip()
        if not is_quality(text, args.min_chars, args.min_letter_ratio):
            continue
        toks = encode_doc(sp, text)
        toks.append(eos)
        n_kept += 1
        total_tokens += len(toks)

        # önce val tamponunu doldur, sonra train shard'larına geç
        if len(val_buf) < args.val_tokens:
            val_buf.extend(toks)
        else:
            buf.extend(toks)
            if len(buf) >= args.shard_tokens:
                shards.append(flush_shard(buf, args.out_dir, shard_idx))
                _write_manifest(args, shards, val_buf, total_tokens, n_docs, n_kept)
                print(f"  [shard {shard_idx:05d}] {len(buf):,} tok  "
                      f"toplam {total_tokens/1e6:.1f}M  {n_kept:,}/{n_docs:,} belge  "
                      f"{total_tokens/max(1,time.time()-t0)/1e3:.1f}k tok/s")
                shard_idx += 1
                buf = array("H")

        if n_docs % args.log_every == 0:
            print(f"  …{n_docs:,} belge tarandı  {total_tokens/1e6:.1f}M tok  "
                  f"({total_tokens/max(1,time.time()-t0)/1e3:.1f}k tok/s)")
        if args.max_tokens and total_tokens >= args.max_tokens:
            break

    if len(buf):
        shards.append(flush_shard(buf, args.out_dir, shard_idx))
    np.frombuffer(val_buf, dtype=np.uint16).tofile(args.out_dir / "val.bin")
    _write_manifest(args, shards, val_buf, total_tokens, n_docs, n_kept)

    train_tok = sum(s["tokens"] for s in shards)
    print(f"\n[ok] {n_kept:,}/{n_docs:,} belge tutuldu  →  {total_tokens/1e6:.1f}M token")
    print(f"     train {train_tok/1e6:.1f}M tok ({len(shards)} shard) + val {len(val_buf)/1e6:.2f}M tok")
    print(f"     → {args.out_dir}/  (manifest.json)")


def _write_manifest(args, shards, val_buf, total_tokens, n_docs, n_kept) -> None:
    manifest = {
        "dataset": args.dataset, "config": args.config, "split": args.split,
        "spm": args.spm, "n_docs_scanned": n_docs, "n_docs_kept": n_kept,
        "total_tokens": total_tokens, "val_tokens": len(val_buf),
        "train_shards": shards, "shard_tokens": args.shard_tokens,
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
