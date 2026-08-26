from pathlib import Path


def test_v12_recipe_archives_adapter():
    """v12 GGUF recipe, bf16 adapter'ı indirme dizinine (OUT) stage etmeli.

    v10 dersi (octopus-adapter-archival): adapter yalnız pod'da kaldı, pod silinince
    kayboldu (yalnız Q4 GGUF scp'lendi) → v1.0 bf16 perplexity/yeniden-nicemleme imkânsız.
    Düzeltme, mevcut güvenlik tasarımına UYUMLU: pod'dan HF-push YOK (token komut-metnine
    girmesin) — adapter OUT'a kopyalanır, GGUF ile scp'lenir, HF upload YERELDEN + promote
    sonrası yapılır.
    """
    p = Path("cloud/pod_gguf_v12.sh")
    assert p.exists(), "v12 GGUF recipe yok"
    lines = p.read_text(encoding="utf-8").splitlines()
    staged = any(
        ("adapter" in ln.lower()) and ("$OUT" in ln)
        and any(cmd in ln for cmd in ("cp", "tar", "rsync"))
        for ln in lines
    )
    assert staged, "adapter indirme dizinine (OUT) stage eden satir yok"
