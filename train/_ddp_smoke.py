"""DDP mantığını Windows'ta torchrun launcher'ına takılmadan doğrula (mp.spawn, CPU/gloo).
Geçici test — silinebilir. RunPod'da gerçek komut: torchrun --nproc_per_node=N -m train.pretrain ...
"""
import os

os.environ["CUDA_VISIBLE_DEVICES"] = "-1"  # GPU'yu tamamen gizle → CPU/gloo yolu
os.environ["USE_LIBUV"] = "0"              # Windows c10d quirk

import sys

import torch.multiprocessing as mp

ARGV = [
    "pretrain", "--data-dir", "data/bin/fineweb2_tr", "--out-dir", "checkpoints_ddptest",
    "--max-steps", "4", "--warmup", "1", "--batch-size", "2", "--grad-accum", "2",
    "--seq-len", "64", "--eval-interval", "2", "--eval-iters", "2", "--log-interval", "1",
    "--sample-interval", "100", "--save-interval", "100",
]


def worker(rank: int) -> None:
    os.environ.update(
        RANK=str(rank), LOCAL_RANK=str(rank), WORLD_SIZE="2",
        MASTER_ADDR="127.0.0.1", MASTER_PORT="29577",
        USE_LIBUV="0", CUDA_VISIBLE_DEVICES="",
    )
    sys.argv = list(ARGV)
    from train.pretrain import main
    main()
    print(f"[rank {rank}] tamam")


if __name__ == "__main__":
    mp.set_start_method("spawn")
    mp.spawn(worker, nprocs=2, join=True)
    print("DDP smoke OK")
