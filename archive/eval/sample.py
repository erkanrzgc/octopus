#!/usr/bin/env python
"""Eğitilmiş checkpoint'ten metin üret — tek-atış veya interaktif sohbet.

Bu bir TABAN dil modeli: prompt'u DEVAM ETTİRİR (soru-cevap değil). Bir cümle başı
ver, gerisini getirir.

Tek-atış:
    uv run python -m eval.sample --prompt "Siber güvenlik" --max-new-tokens 100
İnteraktif (kendi terminalinde):
    uv run python -m eval.sample --interactive
"""
from __future__ import annotations

import sys

try:  # Windows konsolu cp1254 → Türkçe çıktı patlamasın
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import argparse

import torch

from model.config import OctopusConfig
from model.transformer import OctopusLM


def load_model(ckpt_path: str, device: str) -> tuple[OctopusLM, dict]:
    state = torch.load(ckpt_path, map_location=device, weights_only=True)
    cfg = OctopusConfig(**state["config"])
    model = OctopusLM(cfg).to(device)
    model.load_state_dict(state["model"])
    model.eval()
    return model, state


def generate(model: OctopusLM, sp, prompt: str, device: str,
             max_new_tokens: int, temperature: float, top_k: int) -> str:
    ids = sp.encode(prompt, out_type=int)
    idx = torch.tensor([ids], dtype=torch.long, device=device)
    out = model.generate(idx, max_new_tokens, temperature=temperature, top_k=top_k)
    return sp.decode(out[0].tolist())


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--ckpt", default="checkpoints/ckpt_best.pt")
    p.add_argument("--spm", default="tokenizer/octopus-tr.model")
    p.add_argument("--prompt", default="Siber güvenlik")
    p.add_argument("--max-new-tokens", type=int, default=100)
    p.add_argument("--temperature", type=float, default=0.8)
    p.add_argument("--top-k", type=int, default=40)
    p.add_argument("--interactive", action="store_true", help="REPL: her satır bir prompt")
    args = p.parse_args()

    import os
    if not os.path.exists(args.ckpt):
        raise SystemExit(f"[!] checkpoint yok: {args.ckpt}")
    import sentencepiece as spm
    sp = spm.SentencePieceProcessor(model_file=args.spm)

    device = "cuda" if torch.cuda.is_available() else "cpu"
    model, state = load_model(args.ckpt, device)
    n = model.num_params() / 1e6
    print(f"[octopus] {args.ckpt}  ({n:.0f}M param, step {state.get('step','?')}, "
          f"val {state.get('val_loss', float('nan')):.3f})  device={device}")
    print(f"[ayar] temp={args.temperature} top_k={args.top_k} max_new={args.max_new_tokens}\n")

    if not args.interactive:
        txt = generate(model, sp, args.prompt, device, args.max_new_tokens,
                       args.temperature, args.top_k)
        print(f">>> {args.prompt}")
        print(txt)
        return

    print("İnteraktif mod — prompt yaz, Enter. Çıkış: boş satır veya Ctrl+C.\n")
    while True:
        try:
            prompt = input("sen> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\ngörüşürüz.")
            break
        if not prompt:
            break
        txt = generate(model, sp, prompt, device, args.max_new_tokens,
                       args.temperature, args.top_k)
        print(f"octópus> {txt}\n")


if __name__ == "__main__":
    main()
