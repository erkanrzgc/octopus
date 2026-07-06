#!/usr/bin/env python
"""octopus pretraining döngüsü — Faz 4.

bf16 autocast · decay-split AdamW · cosine LR + warmup · grad accumulation · grad clip ·
checkpoint kaydet/resume · periyodik val eval · periyodik Türkçe örnekleme · jsonl log.

Yerel smoke:
    uv run python -m train.pretrain --max-steps 300 --eval-interval 100 --sample-interval 150
Resume:
    uv run python -m train.pretrain --resume --max-steps 3000
"""
from __future__ import annotations

import sys

try:  # Windows konsolu cp1254 → Türkçe/örnek karakterlerde patlamasın
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import argparse
import json
import math
import os
import time
from contextlib import nullcontext

import torch

from model.config import OctopusConfig, config_from_preset
from model.transformer import OctopusLM
from train.dataset import BinDataset, ShardedBinDataset

DTYPES = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}


def get_lr(step: int, warmup: int, max_steps: int, lr: float, min_lr: float) -> float:
    """Lineer warmup → cosine decay → min_lr'de düzleşir."""
    if step < warmup:
        return lr * (step + 1) / warmup
    if step >= max_steps:
        return min_lr
    ratio = (step - warmup) / max(1, max_steps - warmup)
    coeff = 0.5 * (1.0 + math.cos(math.pi * ratio))  # 1→0
    return min_lr + coeff * (lr - min_lr)


def make_optimizer(model: OctopusLM, lr: float, weight_decay: float,
                   betas: tuple[float, float], device: str, use_8bit: bool = False):
    """nanoGPT-tarzı: 2D+ tensörlere (matmul ağırlıkları) weight decay, norm/bias'a yok.

    Tied embedding tek tensör → id ile dedup (aynı param iki kez eklenirse PyTorch hata verir).
    use_8bit: Adam durumlarını 8-bit tutar (bitsandbytes) → büyük modelde ~6 byte/param tasarruf.
    """
    seen: set[int] = set()
    decay, no_decay = [], []
    for p in model.parameters():
        if not p.requires_grad or id(p) in seen:
            continue
        seen.add(id(p))
        (decay if p.dim() >= 2 else no_decay).append(p)
    groups = [
        {"params": decay, "weight_decay": weight_decay},
        {"params": no_decay, "weight_decay": 0.0},
    ]
    if use_8bit:
        try:
            import bitsandbytes as bnb
            print("[optim] bitsandbytes AdamW8bit")
            return bnb.optim.AdamW8bit(groups, lr=lr, betas=betas)
        except Exception as e:  # Windows'ta kurulu olmayabilir → normal AdamW'ye düş
            print(f"[uyarı] 8-bit Adam yok ({type(e).__name__}) → normal AdamW")
    fused = device.startswith("cuda")
    return torch.optim.AdamW(groups, lr=lr, betas=betas, fused=fused)


@torch.no_grad()
def estimate_loss(model: OctopusLM, ds_map: dict[str, BinDataset], eval_iters: int,
                  batch_size: int, device: str, ctx) -> dict[str, float]:
    model.eval()
    out: dict[str, float] = {}
    for name, ds in ds_map.items():
        losses = torch.zeros(eval_iters)
        for k in range(eval_iters):
            x, y = ds.get_batch(batch_size, device)
            with ctx:
                _, loss = model(x, y)
            losses[k] = loss.item()
        out[name] = losses.mean().item()
    model.train()
    return out


@torch.no_grad()
def sample(model: OctopusLM, sp, prompt: str, device: str,
           max_new_tokens: int, top_k: int, temperature: float) -> str:
    model.eval()
    ids = sp.encode(prompt, out_type=int)
    idx = torch.tensor([ids], dtype=torch.long, device=device)
    out = model.generate(idx, max_new_tokens, temperature=temperature, top_k=top_k)
    model.train()
    return sp.decode(out[0].tolist())


def save_ckpt(path: str, model: OctopusLM, opt, step: int, val_loss: float,
              cfg: OctopusConfig, args: argparse.Namespace) -> None:
    torch.save({
        "model": model.state_dict(),
        "optimizer": opt.state_dict(),
        "step": step,
        "val_loss": val_loss,
        "config": vars(cfg) if hasattr(cfg, "__dict__") else cfg.__dict__,
        "args": vars(args),
    }, path)


def load_tokenizer(path: str):
    if not os.path.exists(path):
        print(f"[uyarı] tokenizer yok ({path}) → örnekleme atlanacak")
        return None
    import sentencepiece as spm
    return spm.SentencePieceProcessor(model_file=path)


def setup_ddp(device_pref: str):
    """torchrun ortamını algıla. (ddp, rank, local_rank, world, device, is_master) döner."""
    if int(os.environ.get("RANK", -1)) == -1:
        return False, 0, 0, 1, device_pref, True
    import torch.distributed as dist
    rank = int(os.environ["RANK"])
    local_rank = int(os.environ["LOCAL_RANK"])
    world = int(os.environ["WORLD_SIZE"])
    backend = "nccl" if device_pref.startswith("cuda") else "gloo"
    dist.init_process_group(backend=backend)
    if device_pref.startswith("cuda"):
        torch.cuda.set_device(local_rank)
        device = f"cuda:{local_rank}"
    else:
        device = "cpu"
    return True, rank, local_rank, world, device, rank == 0


def main() -> None:
    p = argparse.ArgumentParser(description="octopus pretraining")
    p.add_argument("--preset", default="", help="model boyutu: octopus-100m/200m/500m/1b (boş=100m default)")
    p.add_argument("--data-dir", default="", help="çok-shard dizini (manifest.json) — verilirse train-bin yerine")
    p.add_argument("--train-bin", default="data/bin/train.bin")
    p.add_argument("--val-bin", default="data/bin/val.bin")
    p.add_argument("--tokenizer", default="tokenizer/octopus-tr.model")
    p.add_argument("--out-dir", default="checkpoints")
    p.add_argument("--max-steps", type=int, default=3000)
    p.add_argument("--batch-size", type=int, default=4, help="micro-batch (8GB-dostu)")
    p.add_argument("--grad-accum", type=int, default=8)
    p.add_argument("--seq-len", type=int, default=1024)
    p.add_argument("--lr", type=float, default=3e-4)
    p.add_argument("--min-lr", type=float, default=3e-5)
    p.add_argument("--warmup", type=int, default=100)
    p.add_argument("--weight-decay", type=float, default=0.1)
    p.add_argument("--grad-clip", type=float, default=1.0)
    p.add_argument("--beta1", type=float, default=0.9)
    p.add_argument("--beta2", type=float, default=0.95)
    p.add_argument("--eval-interval", type=int, default=250)
    p.add_argument("--eval-iters", type=int, default=50)
    p.add_argument("--sample-interval", type=int, default=500)
    p.add_argument("--save-interval", type=int, default=500)
    p.add_argument("--log-interval", type=int, default=10)
    p.add_argument("--dtype", choices=list(DTYPES), default="bf16")
    p.add_argument("--optim", choices=["adamw", "adamw8bit"], default="adamw",
                   help="adamw8bit = bitsandbytes (büyük modelde VRAM tasarrufu)")
    p.add_argument("--grad-checkpoint", action="store_true",
                   help="aktivasyonu backward'da yeniden hesapla (8GB'da büyük model)")
    p.add_argument("--prompt", default="Siber güvenlik, ")
    p.add_argument("--seed", type=int, default=1337)
    p.add_argument("--resume", action="store_true")
    args = p.parse_args()

    device_pref = "cuda" if torch.cuda.is_available() else "cpu"
    ddp, rank, local_rank, world, device, is_master = setup_ddp(device_pref)
    torch.manual_seed(args.seed + rank)  # her rank farklı veri örneklesin
    torch.set_float32_matmul_precision("high")  # tensor core hızlandırma
    if is_master:
        os.makedirs(args.out_dir, exist_ok=True)

    ptdtype = DTYPES[args.dtype]
    use_amp = device.startswith("cuda") and args.dtype != "fp32"
    ctx = torch.autocast(device_type="cuda", dtype=ptdtype) if use_amp else nullcontext()
    scaler = torch.amp.GradScaler(enabled=(args.dtype == "fp16"))

    base = config_from_preset(args.preset, max_seq_len=max(1024, args.seq_len)) if args.preset \
        else OctopusConfig(max_seq_len=max(1024, args.seq_len))
    if args.seq_len > base.max_seq_len:
        raise SystemExit(f"seq_len {args.seq_len} > max_seq_len {base.max_seq_len}")
    cfg = base
    raw_model = OctopusLM(cfg).to(device)
    raw_model.set_grad_checkpoint(args.grad_checkpoint)
    opt = make_optimizer(raw_model, args.lr, args.weight_decay, (args.beta1, args.beta2), device,
                         use_8bit=(args.optim == "adamw8bit"))

    start_step = 0
    best_val = float("inf")
    ckpt_path = os.path.join(args.out_dir, "ckpt.pt")
    if args.resume and os.path.exists(ckpt_path):
        state = torch.load(ckpt_path, map_location=device, weights_only=True)
        raw_model.load_state_dict(state["model"])
        opt.load_state_dict(state["optimizer"])
        start_step = state["step"] + 1
        best_val = state.get("val_loss", float("inf"))
        if is_master:
            print(f"[resume] {ckpt_path} → step {start_step}, best_val {best_val:.4f}")

    model = raw_model
    if ddp:
        from torch.nn.parallel import DistributedDataParallel as DDP
        model = DDP(raw_model, device_ids=[local_rank] if device.startswith("cuda") else None)

    if args.data_dir:
        train_ds = ShardedBinDataset(args.data_dir, args.seq_len)
        val_ds = BinDataset(os.path.join(args.data_dir, "val.bin"), args.seq_len)
    else:
        train_ds = BinDataset(args.train_bin, args.seq_len)
        val_ds = BinDataset(args.val_bin, args.seq_len)
    ds_map = {"train": train_ds, "val": val_ds}
    sp = load_tokenizer(args.tokenizer) if is_master else None

    tok_per_step = args.batch_size * args.grad_accum * args.seq_len * world
    if is_master:
        print(f"device={device}  ddp={ddp}(world={world})  params={raw_model.num_params()/1e6:.1f}M  "
              f"dtype={args.dtype}  preset={args.preset or 'default-100m'}")
        print(f"micro={args.batch_size} × accum={args.grad_accum} × seq={args.seq_len} × world={world} "
              f"→ {tok_per_step:,} token/step  (toplam ≤ {tok_per_step*args.max_steps/1e9:.2f}B)")

    logf = open(os.path.join(args.out_dir, "log.jsonl"), "a", encoding="utf-8") if is_master else None
    model.train()
    t0 = time.time()

    for step in range(start_step, args.max_steps):
        lr = get_lr(step, args.warmup, args.max_steps, args.lr, args.min_lr)
        for g in opt.param_groups:
            g["lr"] = lr

        opt.zero_grad(set_to_none=True)
        accum_loss = 0.0
        for micro in range(args.grad_accum):
            x, y = train_ds.get_batch(args.batch_size, device)
            # DDP: son micro-step hariç grad sync'i ertele (no_sync) → daha az iletişim
            sync_ctx = model.no_sync() if (ddp and micro < args.grad_accum - 1) else nullcontext()
            with sync_ctx:
                with ctx:
                    _, loss = model(x, y)
                    loss = loss / args.grad_accum
                scaler.scale(loss).backward()
            accum_loss += loss.item()

        if args.grad_clip > 0:
            scaler.unscale_(opt)
            torch.nn.utils.clip_grad_norm_(model.parameters(), args.grad_clip)
        scaler.step(opt)
        scaler.update()

        if is_master and step % args.log_interval == 0:
            dt = time.time() - t0
            tps = tok_per_step * args.log_interval / dt if step > start_step else 0
            print(f"step {step:5d}  loss {accum_loss:.4f}  lr {lr:.2e}  {tps/1e3:.1f}k tok/s")
            logf.write(json.dumps({"step": step, "loss": accum_loss, "lr": lr,
                                   "tok_per_s": tps}) + "\n")
            logf.flush()
            t0 = time.time()

        if is_master and step > start_step and step % args.eval_interval == 0:
            ev = estimate_loss(raw_model, ds_map, args.eval_iters, args.batch_size, device, ctx)
            print(f"  ↳ eval  train {ev['train']:.4f}  val {ev['val']:.4f}  "
                  f"(ppl≈{math.exp(min(ev['val'], 20)):.1f})")
            logf.write(json.dumps({"step": step, "eval_train": ev["train"],
                                   "eval_val": ev["val"]}) + "\n")
            logf.flush()
            if ev["val"] < best_val:
                best_val = ev["val"]
                save_ckpt(os.path.join(args.out_dir, "ckpt_best.pt"),
                          raw_model, opt, step, best_val, cfg, args)
            t0 = time.time()

        if is_master and sp is not None and step > start_step and step % args.sample_interval == 0:
            txt = sample(raw_model, sp, args.prompt, device, 60, top_k=50, temperature=0.8)
            print(f"  ↳ örnek: {txt!r}")
            t0 = time.time()

        if is_master and step > start_step and step % args.save_interval == 0:
            save_ckpt(ckpt_path, raw_model, opt, step, best_val, cfg, args)
            t0 = time.time()

    if is_master:
        save_ckpt(ckpt_path, raw_model, opt, args.max_steps - 1, best_val, cfg, args)
        logf.close()
        print(f"bitti — son checkpoint: {ckpt_path}  best_val {best_val:.4f}")
    if ddp:
        import torch.distributed as dist
        dist.destroy_process_group()


if __name__ == "__main__":
    main()
