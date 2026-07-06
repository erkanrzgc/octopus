#!/usr/bin/env python
"""octopus-tr tokenizer round-trip + Türkçe sağlık testi.

Kontrol eder:
  1. encode→decode kayıpsız mı (diakritik, Türkçe-i İ/ı, sayı, komut korunuyor mu)
  2. özel tokenlar (<|im_start|> vb.) vocab'da mı
  3. örnek Türkçe kelimelerin morfolojik bölünmesi makul mü

Kullanım:
    uv run python tokenizer/roundtrip_test.py
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import sentencepiece as spm

# Windows konsolu cp1254 olabilir → Türkçe + ▁ (U+2581) için stdout'u UTF-8'e zorla
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

SAMPLES = [
    "İstanbul'da bir güvenlik açığı bulundu: 443 portu açık ve TLS 1.0 kullanılıyor.",
    "Türkçe-i testi: Iıİi — IŞIK ışık İLGİ ilgi.",
    "Komut: sudo nmap -sV -p- 10.0.0.1 && echo 'bitti'",
    "Şifreleme, ağ güvenliği ve sistem yönetiminde uzmanlaşmıştır.",
    "<|im_start|>kullanıcı\nSelam<|im_end|>",
]
SPECIALS = [
    "<|im_start|>", "<|im_end|>",
    "<tool_call>", "</tool_call>",
    "<tool_response>", "</tool_response>",
]
MORPH = ["evlerimizden", "güvenliğini", "kitaplarındaki", "çalıştırabilirsiniz", "bilgisayarlarımız"]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--spm", default="tokenizer/octopus-tr.model")
    args = ap.parse_args()

    if not Path(args.spm).exists():
        raise SystemExit(f"[!] {args.spm} yok — önce tokenizer/train_tokenizer.py çalıştır")

    sp = spm.SentencePieceProcessor(model_file=args.spm)
    print(f"vocab boyutu: {sp.get_piece_size()}\n")

    # 1) round-trip
    all_ok = True
    print("round-trip:")
    for s in SAMPLES:
        ids = sp.encode(s, out_type=int)
        back = sp.decode(ids)
        same = back == s
        all_ok = all_ok and same
        print(f"  [{'OK ' if same else 'FARK'}] {len(ids):3d} tok  {s!r}")
        if not same:
            print(f"         decode: {back!r}")
    print()

    # 2) özel tokenlar
    print("özel tokenlar:")
    unk = sp.unk_id()
    for t in SPECIALS:
        pid = sp.piece_to_id(t)
        print(f"  {t:22s} id={pid:<6d} {'VAR' if pid != unk else 'YOK (unk!)'}")
    print()

    # 3) morfolojik bölme
    print("morfolojik bölme (Türkçe sondan eklemeli):")
    for w in MORPH:
        print(f"  {w:22s} -> {sp.encode(w, out_type=str)}")
    print()

    print("SONUÇ:", "round-trip KAYIPSIZ ✓" if all_ok else "round-trip FARK VAR ✗")
    raise SystemExit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
