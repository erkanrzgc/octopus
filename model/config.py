"""octopus taban model konfigürasyonu."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OctopusConfig:
    """nanoGPT-tarzı modern Llama konfigürasyonu.

    Varsayılan ≈ 100M param (dim 768 · 12 layer · 12 head · 4 kv-head/GQA · vocab 32k).
    Yerel 8GB'de smoke + ilk eğitim için uygun; ladder ile RunPod'da büyütülür (dim/layer artırılır).
    """
    vocab_size: int = 32000
    dim: int = 768
    n_layers: int = 12
    n_heads: int = 12
    n_kv_heads: int = 4          # GQA: 12 query head, 4 kv head paylaşır → kv cache 3× küçük
    max_seq_len: int = 1024
    rope_theta: float = 10000.0
    norm_eps: float = 1e-5
    ffn_mult: float = 8 / 3      # SwiGLU gizli boyut ≈ 8/3·dim (Llama oranı)
    ffn_multiple_of: int = 256   # gizli boyutu 256'nın katına yuvarla (donanım dostu)
    dropout: float = 0.0
    tie_embeddings: bool = True  # giriş embedding ↔ çıkış lm_head paylaşımlı

    def __post_init__(self) -> None:
        assert self.dim % self.n_heads == 0, "dim, n_heads'e bölünebilmeli"
        assert self.n_heads % self.n_kv_heads == 0, "n_heads, n_kv_heads'e bölünebilmeli (GQA)"
        assert self.head_dim % 2 == 0, "RoPE için head_dim çift olmalı"

    @property
    def head_dim(self) -> int:
        return self.dim // self.n_heads


# Boyut ladder'ı — yerel (≤200M) → RunPod (0.5B-1B). Tümü head_dim 64, GQA.
PRESETS: dict[str, dict] = {
    "octopus-100m": dict(dim=768, n_layers=12, n_heads=12, n_kv_heads=4),    # ~100M (mevcut)
    "octopus-200m": dict(dim=1024, n_layers=16, n_heads=16, n_kv_heads=4),   # ~210M — yerel tavan
    "octopus-500m": dict(dim=1280, n_layers=24, n_heads=20, n_kv_heads=4),   # ~470M — RunPod A5000
    "octopus-1b":   dict(dim=2048, n_layers=22, n_heads=32, n_kv_heads=4),   # ~1.1B — RunPod çok-GPU
}


def config_from_preset(name: str, **overrides) -> "OctopusConfig":
    if name not in PRESETS:
        raise ValueError(f"bilinmeyen preset: {name} (seçenekler: {list(PRESETS)})")
    return OctopusConfig(**{**PRESETS[name], **overrides})
