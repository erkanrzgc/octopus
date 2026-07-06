"""uint16 .bin token dosyalarından rastgele seq_len pencereler örnekler (memmap).

memmap → milyarlarca token diske kalır, RAM'e yüklenmez; 8GB makinede sorunsuz.
İki loader: tek-dosya `BinDataset` ve çok-shard `ShardedBinDataset` (manifest.json).
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import torch


def _to_device(x: torch.Tensor, y: torch.Tensor, device: str) -> tuple[torch.Tensor, torch.Tensor]:
    if device.startswith("cuda"):
        return x.pin_memory().to(device, non_blocking=True), y.pin_memory().to(device, non_blocking=True)
    return x.to(device), y.to(device)


def _window(data: np.memmap, i: int, seq_len: int) -> tuple[torch.Tensor, torch.Tensor]:
    x = torch.from_numpy(data[i:i + seq_len].astype(np.int64))
    y = torch.from_numpy(data[i + 1:i + 1 + seq_len].astype(np.int64))
    return x, y


class BinDataset:
    """Tek .bin dosyası."""

    def __init__(self, path: str, seq_len: int) -> None:
        self.data = np.memmap(path, dtype=np.uint16, mode="r")
        self.seq_len = seq_len
        if len(self.data) <= seq_len + 1:
            raise ValueError(f"{path}: token sayısı ({len(self.data)}) seq_len+1'den küçük")

    def get_batch(self, batch_size: int, device: str) -> tuple[torch.Tensor, torch.Tensor]:
        ix = torch.randint(len(self.data) - self.seq_len - 1, (batch_size,))
        xs, ys = zip(*(_window(self.data, int(i), self.seq_len) for i in ix))
        return _to_device(torch.stack(xs), torch.stack(ys), device)


class ShardedBinDataset:
    """manifest.json'daki tüm shard'ları memmap'ler; token-ağırlıklı örnekler.

    Shard seçimi (shard_len - seq_len) ile ağırlıklı → tüm pozisyonlar üniform.
    Pencere tek shard içinde kalır (shard sınırını aşmaz → belge bütünlüğü bozulmaz).
    """

    def __init__(self, data_dir: str, seq_len: int) -> None:
        d = Path(data_dir)
        manifest = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
        self.seq_len = seq_len
        self.shards: list[np.memmap] = []
        weights: list[int] = []
        for s in manifest["train_shards"]:
            mm = np.memmap(d / s["file"], dtype=np.uint16, mode="r")
            if len(mm) <= seq_len + 1:
                continue
            self.shards.append(mm)
            weights.append(len(mm) - seq_len - 1)
        if not self.shards:
            raise ValueError(f"{data_dir}: seq_len {seq_len} için uygun shard yok")
        self.total_tokens = sum(len(m) for m in self.shards)
        w = np.asarray(weights, dtype=np.float64)
        self.probs = w / w.sum()

    def get_batch(self, batch_size: int, device: str) -> tuple[torch.Tensor, torch.Tensor]:
        sids = np.random.choice(len(self.shards), size=batch_size, p=self.probs)
        xs, ys = [], []
        for sid in sids:
            data = self.shards[sid]
            i = int(torch.randint(len(data) - self.seq_len - 1, (1,)))
            x, y = _window(data, i, self.seq_len)
            xs.append(x)
            ys.append(y)
        return _to_device(torch.stack(xs), torch.stack(ys), device)
