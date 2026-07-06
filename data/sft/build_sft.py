"""Octopus SFT veri hazirlayici — kaynaklari 'messages' JSONL'e cevirir.

HF + yerel kaynaklari okur, normalize eder (data/sft/normalize.py), Octopus
persona/guardrail'ini system olarak koyar (kaynagin system'ini atar), dedup +
kalite filtresi uygular, train/val/test boler, `data/sft/` altina yazar + manifest.

Hibrit karisim (varsayilan): Ingilizce cyber cekirdek (Fenrir) + Turkce akicilik
(InstrucTurca dilimi) + elle-yazilmis Turkce seed (sunucu/red-blue/persona).

Kullanim:
    uv run python -m data.sft.build_sft --limit 300 --stream    # hizli duman (indirmeden)
    uv run python -m data.sft.build_sft                         # tam hibrit (registry limitleri)
    uv run python -m data.sft.build_sft --source fenrir         # tek kaynak
"""
from __future__ import annotations

import argparse
import glob
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

from data.sft.normalize import apply_octopus_system, ensure_system, fingerprint, is_valid, to_messages
from data.sft.persona import OCTOPUS_SYSTEM_PROMPT

ROOT = Path(__file__).resolve().parent.parent.parent  # .../Octopus
OUT_DIR = ROOT / "data" / "sft"
SEED = 3407
VAL_RATIO = 0.02
TEST_RATIO = 0.02

# Kaynak kayit defteri. field_map: kaynak kolonu -> standart ('user'/'assistant').
# max_rows: 0=hepsi; >0 kaynak-basi tavan (hibrit dengesi icin). --limit hepsini ezer.
SOURCES: dict[str, dict] = {
    "fenrir": {
        "kind": "hf", "hf_id": "AlicanKiraz0/Cybersecurity-Dataset-Fenrir-v2.1",
        "split": "train", "license": "apache-2.0", "lang": "en", "max_rows": 0,
    },
    "instructurca": {
        "kind": "hf", "hf_id": "turkish-nlp-suite/InstrucTurca",
        "split": "train", "license": "apache-2.0", "lang": "tr",
        "field_map": {"user": "Input", "assistant": "Output"}, "max_rows": 10000,
    },
    "seed_tr": {
        "kind": "local", "path": "data/sft/seed_tr", "license": "octopus-authored",
        "lang": "tr", "max_rows": 0,
    },
    "distill": {  # v0.5+v0.7: teacher-uretimi CESITLI Turkce cyber. distilled/ altindaki TUM
        # *.jsonl'i glob'lar -> octopus_distill_tr.jsonl (918) + octopus_distill_v07.jsonl (111) otomatik dahil.
        "kind": "local", "path": "data/sft/distilled", "license": "distilled+octopus-authored",
        "lang": "tr", "max_rows": 0,
    },
    "tools": {  # v0.7: agentic tool-use (```arac``` blok formatiyla arac cagirma). keep_system=True:
        # her ornegin ozel system'i (arac spec) KORUNUR (apply_octopus_system ile EZILMEZ).
        # tools_dist/ = build_tools.py'nin birlesik ciktisi (per-domain dosyalarla cift-sayim olmaz).
        "kind": "local", "path": "data/sft/tools_dist", "license": "octopus-authored",
        "lang": "tr", "max_rows": 0, "keep_system": True,
    },
    "tr_native": {  # v0.6: NATIVE Turkce instruction (makine-cevirisi DEGIL) — akicilik/edebi Turkce
        "kind": "hf", "hf_id": "erenfazlioglu/turkish-instruct-reasoning-dpo-3.4m",
        "config": "sft", "split": "train", "license": "other-mixed", "lang": "tr", "max_rows": 20000,
    },
    # Opsiyonel (sonra): Turkce savunma cyber ama dar JSON-SOC ciktisi:
    # "phishsoc": {"kind":"hf","hf_id":"ErenAta00/turkish-phishsoc-50k", ...}
}
DEFAULT_SOURCES = ["fenrir", "instructurca", "seed_tr"]
# Elle-yazilmis, yuksek-degerli AMA az sayida Octopus kaynaklari: buyuk karisimda iğne
# kalmasin diye train'de upsample edilir (--seed-repeat). tool-use + persona/sunucu seed'i.
UPSAMPLE_SOURCES = {"seed_tr", "tools"}


def _remap(row: dict, field_map: dict | None) -> dict:
    """Kaynak kolonlarini standart isimlere cevir (field_map varsa)."""
    if not field_map:
        return row
    return {std: row.get(src) for std, src in field_map.items()}


def load_rows(name: str, cli_limit: int, stream: bool):
    """Bir kaynaktan (HF ya da yerel) ham satirlari getir, field_map uygula."""
    src = SOURCES[name]
    limit = cli_limit if cli_limit > 0 else src.get("max_rows", 0)
    fmap = src.get("field_map")

    if src["kind"] == "local":
        files = sorted(glob.glob(str(ROOT / src["path"] / "*.jsonl")))
        print(f"[*] Kaynak: {name} (yerel, {len(files)} dosya)")
        count = 0
        for fp in files:
            with open(fp, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    if limit and count >= limit:
                        break
                    yield _remap(json.loads(line), fmap)
                    count += 1
        print(f"[*] {name}: {count:,} yerel satir.")
        return

    try:
        from datasets import load_dataset
    except ImportError:
        sys.exit("[X] 'datasets' kurulu degil. Once: uv sync")
    # Sinirli dilim alirken stream et (tum seti indirme); tam kaynakta cache kullan.
    use_stream = stream or limit > 0
    ds_args = [src["hf_id"]] + ([src["config"]] if src.get("config") else [])
    print(f"[*] Kaynak: {name} ({src['hf_id']}, config={src.get('config')}, split={src['split']}, stream={use_stream}, limit={limit or 'hepsi'})")
    ds = load_dataset(*ds_args, split=src["split"], streaming=use_stream)
    count = 0
    for row in ds:
        if limit and count >= limit:
            break
        yield _remap(row, fmap)
        count += 1
    print(f"[*] {name}: {count:,} ham satir okundu.")


def build(names: list[str], cli_limit: int, stream: bool, out_dir: Path, seed_repeat: int = 1) -> None:
    seen: set[str] = set()
    out: list[dict] = []
    upsample_examples: list[dict] = []   # UPSAMPLING icin: az-sayida Octopus kaynaklarini ayri tut
    per_source: dict[str, int] = {}
    skipped = 0

    for name in names:
        keep_system = SOURCES[name].get("keep_system", False)
        kept = 0
        for row in load_rows(name, cli_limit, stream):
            msgs = to_messages(row)
            if not is_valid(msgs):
                skipped += 1
                continue
            # tool-use kaynagi: ozel system'i (arac spec) KORU; digerleri: persona enjekte et.
            msgs = ensure_system(msgs) if keep_system else apply_octopus_system(msgs)
            fp = fingerprint(msgs)
            if fp in seen:
                skipped += 1
                continue
            seen.add(fp)
            rec = {"messages": msgs}
            out.append(rec)
            if name in UPSAMPLE_SOURCES:
                upsample_examples.append(rec)
            kept += 1
        per_source[name] = kept

    print(f"[*] Gecerli: {len(out):,} | Atlanan (bos/kisa/tekrar): {skipped:,} | kaynak: {per_source}")
    if not out:
        sys.exit("[X] Hic gecerli ornek cikmadi. Kolon yapisini kontrol et.")

    random.seed(SEED)
    random.shuffle(out)
    n_test = max(1, int(len(out) * TEST_RATIO))
    n_val = max(1, int(len(out) * VAL_RATIO))
    test, val, train = out[:n_test], out[n_test:n_test + n_val], out[n_test + n_val:]

    # UPSAMPLING: az-sayidaki Octopus kaynaklarini (seed_tr + tools) train'de N kez tekrarla
    # (persona/kimlik/yetkili-saldiri + arac-kullanim bagini guclendir — buyuk karisimda
    # iğne kalmasin). Sadece TRAIN'de kopyalanan ornekler; val/test etkilenmez (sizinti yok,
    # cunku split kopyalamadan ONCE yapildi -> ayni ornek hem train hem test'te olmaz).
    if seed_repeat > 1 and upsample_examples:
        # split sonrasi train'de kalan upsample orneklerini bul (test/val'e dusenleri tekrarlama)
        train_fps = {fingerprint(r["messages"]) for r in train}
        train_upsample = [r for r in upsample_examples if fingerprint(r["messages"]) in train_fps]
        extra = train_upsample * (seed_repeat - 1)
        train = train + extra
        random.shuffle(train)
        print(f"[*] Upsampling: {sorted(UPSAMPLE_SOURCES)} x{seed_repeat} -> train'e +{len(extra):,} kopya "
              f"(etkin agirlik ~{len(train_upsample)*seed_repeat:,})")

    out_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(out_dir / "train.jsonl", train)
    _write_jsonl(out_dir / "val.jsonl", val)
    _write_jsonl(out_dir / "test.jsonl", test)
    _write_manifest(out_dir / "manifest.json", per_source, len(train), len(val), len(test), cli_limit, stream)

    print("=" * 60)
    print(f"[OK] train={len(train):,}  val={len(val):,}  test={len(test):,}  -> {out_dir}")
    print("Sonraki adim: octopus-finetune skill (yerel duman turu, para-oncesi).")
    print("=" * 60)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _write_manifest(path, per_source, n_train, n_val, n_test, cli_limit, stream) -> None:
    manifest = {
        "created": datetime.now(timezone.utc).isoformat(),
        "seed": SEED,
        "cli_limit": cli_limit or "registry-max_rows",
        "streaming": stream,
        "splits": {"train": n_train, "val": n_val, "test": n_test},
        "per_source_kept": per_source,
        "sources": {n: SOURCES[n] for n in per_source},
        "persona_prompt": OCTOPUS_SYSTEM_PROMPT,
    }
    with path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def main() -> None:
    ap = argparse.ArgumentParser(description="Octopus SFT veri hazirlayici (hibrit)")
    ap.add_argument("--source", nargs="+", default=DEFAULT_SOURCES,
                    choices=list(SOURCES.keys()), help="Kaynak(lar)")
    ap.add_argument("--limit", type=int, default=0,
                    help="0=registry max_rows; >0 kaynak-basi tavani EZER (hizli duman)")
    ap.add_argument("--stream", action="store_true", help="HF stream (indirmeden ilk N)")
    ap.add_argument("--seed-repeat", type=int, default=1,
                    help="Turkce seed'i train'de N kez tekrarla (persona bagini guclendir; gercek tur icin ~20)")
    ap.add_argument("--cap", type=str, default=None,
                    help="Per-source tavan override (oran dengesi): 'fenrir=50000,instructurca=30000'")
    ap.add_argument("--out-dir", default=str(OUT_DIR), help="Cikti dizini")
    args = ap.parse_args()

    # --cap: SOURCES max_rows'u override et (Fenrir baskinligini kirmak icin)
    if args.cap:
        for part in args.cap.split(","):
            name, _, val = part.partition("=")
            name, val = name.strip(), val.strip()
            if name in SOURCES and val.isdigit():
                SOURCES[name]["max_rows"] = int(val)
                print(f"[*] cap: {name} -> max_rows={val}")

    build(args.source, args.limit, args.stream, Path(args.out_dir), args.seed_repeat)


if __name__ == "__main__":
    main()
