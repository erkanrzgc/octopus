#!/usr/bin/env python
"""Çok-kaynaklı ağırlıklı korpus derleyici — recipe JSON'dan Octópus veri karışımı.

Birden çok HF dataset'ini streaming çeker, ağırlıklı round-robin ile karıştırır,
her belgeyi temizle (NFC + kalite) → octopus-tr tokenize (belge-sonu EOS) → uint16 shard.
Tek-kaynak `build_pretrain_data.py`'ın genel hali; mantık/yardımcılar oradan reuse.

Recipe (data/recipes/*.json):
  {"sources": [
     {"name":"lumees-tr","dataset":"lumees/turkish-corpus-100b","config":"pretrain",
      "text_field":"text","weight":0.50},
     {"name":"alican-cve","dataset":"AlicanKiraz0/All-CVE-Records-Training-Dataset",
      "template":"{User}\\n\\n{Assistant}","weight":0.20}, ...]}

Kullanım:
  uv run python -m data.build_corpus_mix --recipe data/recipes/octopus-v1.json --max-tokens 5_000_000
"""
from __future__ import annotations

import argparse
import json
import random
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
from data.build_pretrain_data import encode_doc, flush_shard


def make_iter(src: dict):
    kw = {"split": src.get("split", "train"), "streaming": True}
    if src.get("config"):
        kw["name"] = src["config"]
    if src.get("data_files"):
        kw["data_files"] = src["data_files"]
    return iter(load_dataset(src["dataset"], **kw))


def extract_text(ex: dict, src: dict) -> str:
    tmpl = src.get("template")
    if tmpl:  # literal replace — .format() metindeki { } yüzünden patlamasın
        for k, v in ex.items():
            tmpl = tmpl.replace("{" + k + "}", "" if v is None else str(v))
        return tmpl
    return ex.get(src.get("text_field", "text")) or ""


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--recipe", required=True, help="recipe JSON (sources + ağırlıklar)")
    p.add_argument("--spm", default="tokenizer/octopus-tr.model")
    p.add_argument("--out-dir", type=Path, default=Path("data/bin/mix"))
    p.add_argument("--max-tokens", type=int, default=0, help="0 = sınırsız")
    p.add_argument("--shard-tokens", type=int, default=100_000_000)
    p.add_argument("--val-tokens", type=int, default=5_000_000)
    p.add_argument("--min-chars", type=int, default=200)
    p.add_argument("--min-letter-ratio", type=float, default=0.35,
                   help="siber/kod sembol-yoğun → tek-kaynaktan (0.5) düşük")
    p.add_argument("--seed", type=int, default=1337)
    p.add_argument("--log-every", type=int, default=2000)
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args()

    recipe = json.loads(Path(args.recipe).read_text(encoding="utf-8"))
    sources = recipe["sources"]
    if not Path(args.spm).exists():
        raise SystemExit(f"[!] tokenizer yok: {args.spm}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    existing = list(args.out_dir.glob("shard_*.bin")) + list(args.out_dir.glob("val.bin"))
    if existing and not args.overwrite:
        raise SystemExit(f"[!] {args.out_dir} dolu — --overwrite ver")
    for f in existing:
        f.unlink()

    sp = spm.SentencePieceProcessor(model_file=args.spm)
    eos = sp.eos_id()
    rng = random.Random(args.seed)

    print(f"[recipe] {args.recipe} → {len(sources)} kaynak:")
    for s in sources:
        print(f"  - {s['name']:16s} w={s.get('weight',1.0):.2f}  {s['dataset']}"
              + (f":{s['config']}" if s.get('config') else ""))
    iters = [make_iter(s) for s in sources]
    # weight = HEDEF token-payı (belge-payı değil); seçim açık-payı kapatır → oranlar tutar
    raw = [float(s.get("weight", 1.0)) for s in sources]
    tw = sum(raw) or 1.0
    targets = [w / tw for w in raw]
    alive = [True] * len(sources)
    src_docs = [0] * len(sources)
    src_toks = [0] * len(sources)

    val_buf, buf = array("H"), array("H")
    shards: list[dict] = []
    shard_idx = n_docs = n_kept = total = 0
    t0 = time.time()

    while any(alive) and (not args.max_tokens or total < args.max_tokens):
        defs = [max(1e-6, targets[j] - (src_toks[j] / total if total else 0.0)) if alive[j] else 0.0
                for j in range(len(sources))]
        if sum(defs) <= 0:
            defs = [1.0 if alive[j] else 0.0 for j in range(len(sources))]
        i = rng.choices(range(len(sources)), weights=defs)[0]
        try:
            ex = next(iters[i])
        except StopIteration:
            alive[i] = False
            print(f"  [tükendi] {sources[i]['name']}")
            continue
        n_docs += 1
        text = extract_text(ex, sources[i]).strip()
        if not is_quality(text, args.min_chars, args.min_letter_ratio):
            continue
        toks = encode_doc(sp, text)
        toks.append(eos)
        n_kept += 1
        total += len(toks)
        src_docs[i] += 1
        src_toks[i] += len(toks)

        if len(val_buf) < args.val_tokens:
            val_buf.extend(toks)
        else:
            buf.extend(toks)
            if len(buf) >= args.shard_tokens:
                shards.append(flush_shard(buf, args.out_dir, shard_idx))
                _write_manifest(args, recipe, sources, shards, val_buf, total, n_docs, n_kept, src_docs, src_toks)
                print(f"  [shard {shard_idx:05d}] {total/1e6:.1f}M tok  "
                      f"{total/max(1,time.time()-t0)/1e3:.0f}k tok/s")
                shard_idx += 1
                buf = array("H")
        if n_docs % args.log_every == 0:
            mix = " ".join(f"{sources[j]['name'][:6]}:{src_toks[j]/max(1,total)*100:.0f}%" for j in range(len(sources)))
            print(f"  …{n_docs:,} belge  {total/1e6:.1f}M tok  [{mix}]")

    if len(buf):
        shards.append(flush_shard(buf, args.out_dir, shard_idx))
    np.frombuffer(val_buf, dtype=np.uint16).tofile(args.out_dir / "val.bin")
    _write_manifest(args, recipe, sources, shards, val_buf, total, n_docs, n_kept, src_docs, src_toks)

    print(f"\n[ok] {n_kept:,}/{n_docs:,} belge → {total/1e6:.1f}M token ({len(shards)} shard + val)")
    for j, s in enumerate(sources):
        print(f"     {s['name']:16s} {src_toks[j]/1e6:7.1f}M tok  ({src_toks[j]/max(1,total)*100:4.1f}%)  {src_docs[j]:,} belge")
    print(f"     → {args.out_dir}/  (manifest.json)")


def _write_manifest(args, recipe, sources, shards, val_buf, total, n_docs, n_kept, src_docs, src_toks) -> None:
    manifest = {
        "recipe": recipe.get("name", args.recipe), "spm": args.spm,
        "total_tokens": total, "val_tokens": len(val_buf),
        "n_docs_scanned": n_docs, "n_docs_kept": n_kept,
        "train_shards": shards, "shard_tokens": args.shard_tokens,
        "sources": [{"name": s["name"], "dataset": s["dataset"], "weight": s.get("weight", 1.0),
                     "tokens": src_toks[j], "docs": src_docs[j]} for j, s in enumerate(sources)],
    }
    (args.out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
