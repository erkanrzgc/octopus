#!/usr/bin/env python
"""Model doğruluk smoke testi: instantiate + forward + param sayısı + tek-batch overfit.

Tek bir rastgele batch'i overfit edebiliyorsa (loss→~0) → mimari + backprop doğru.
    uv run python -m model.smoke_test
"""
from __future__ import annotations

import sys

try:  # Windows konsolu cp1254 → '≈', 'ç', '✓' gibi karakterlerde patlamasın
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import torch

from model.config import OctopusConfig
from model.transformer import OctopusLM


def main() -> None:
    torch.manual_seed(0)
    cfg = OctopusConfig()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = OctopusLM(cfg).to(device)

    print(f"device = {device}")
    if device == "cuda":
        print(f"gpu    = {torch.cuda.get_device_name(0)}")
    print(f"params = {model.num_params() / 1e6:.1f}M  "
          f"(dim {cfg.dim} · {cfg.n_layers} layer · {cfg.n_heads}h/{cfg.n_kv_heads}kv · vocab {cfg.vocab_size})")

    B, T = 2, 64
    idx = torch.randint(0, cfg.vocab_size, (B, T), device=device)
    targets = torch.randint(0, cfg.vocab_size, (B, T), device=device)

    logits, loss = model(idx, targets)
    import math
    print(f"forward OK: logits={tuple(logits.shape)}  loss0={loss.item():.3f} "
          f"(rastgele beklenen ≈ ln(vocab) = {math.log(cfg.vocab_size):.2f})")

    opt = torch.optim.AdamW(model.parameters(), lr=3e-4)
    model.train()
    for step in range(200):
        logits, loss = model(idx, targets)
        opt.zero_grad()
        loss.backward()
        opt.step()
        if step % 40 == 0 or step == 199:
            print(f"  step {step:3d}  loss {loss.item():.4f}")

    ok = loss.item() < 0.5
    print("SONUÇ:", "overfit OK — mimari + backprop doğru ✓" if ok else "overfit zayıf ✗ (incele)")
    raise SystemExit(0 if ok else 1)


if __name__ == "__main__":
    main()
