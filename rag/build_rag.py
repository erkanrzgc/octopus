"""Octopus RAG — Turkce bilgi tabani (MITRE/CVE/OWASP...) -> Chroma vektor DB.

Amac: modelin ezberden UYDURMASINI kesmek. rag/knowledge/*.md (Turkce, dogru ID'ler)
parcalanir -> embedding -> Chroma. Sorguda ilgili parcalar getirilip cevaba baglam olur.
cyberm4fia 06_build_rag.py deseninden uyarlandi (self-contained; cyberm4fia config'e bagli degil).

ONEMLI: embedding icin torch gerekir -> Octopus .venv (3.14) DEGIL, cyberm4fia .venv (3.12) ile kosulur:
    CY=C:/Users/erkanrzgc/Desktop/cyberm4fiaModel/.venv/Scripts/python.exe
    "$CY" -m pip install chromadb sentence-transformers   # bir kez
    "$CY" rag/build_rag.py --build
    "$CY" rag/build_rag.py --query "Kerberoasting MITRE ID"
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent          # .../Octopus
KNOWLEDGE_DIR = ROOT / "rag" / "knowledge"
CHROMA_DIR = ROOT / "rag" / "chroma"
COLLECTION = "octopus_kb"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"  # hafif, hizli, coklu-dil makul


def _chunk(text: str, size: int = 800, overlap: int = 100) -> list[str]:
    """Metni ortusen pencerelere boler (baglam kopmasin)."""
    text = " ".join(text.split())
    if len(text) <= size:
        return [text] if text else []
    chunks, start = [], 0
    while start < len(text):
        chunks.append(text[start:start + size])
        start += size - overlap
    return chunks


def _client():
    import chromadb
    return chromadb.PersistentClient(path=str(CHROMA_DIR))


def _embedder():
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer(EMBED_MODEL)


def build() -> None:
    docs = list(KNOWLEDGE_DIR.rglob("*.txt")) + list(KNOWLEDGE_DIR.rglob("*.md"))
    if not docs:
        sys.exit(f"[X] {KNOWLEDGE_DIR} bos.")
    embedder = _embedder()
    client = _client()
    try:
        client.delete_collection(COLLECTION)
    except Exception:  # noqa: BLE001
        pass
    col = client.create_collection(COLLECTION)

    ids, texts, metas = [], [], []
    for doc in docs:
        content = doc.read_text(encoding="utf-8", errors="ignore")
        rel = doc.relative_to(KNOWLEDGE_DIR).as_posix()
        for j, ch in enumerate(_chunk(content)):
            ids.append(f"{rel.replace('/', '__')}_{j}")
            texts.append(ch)
            metas.append({"source": rel})

    print(f"[*] {len(docs)} dosya -> {len(texts)} parca embedding'leniyor...")
    embs = embedder.encode(texts, show_progress_bar=True, batch_size=64).tolist()
    col.add(ids=ids, documents=texts, embeddings=embs, metadatas=metas)
    print(f"[OK] {len(texts)} parca '{COLLECTION}' -> {CHROMA_DIR}")


def query(q: str, k: int = 4) -> None:
    embedder = _embedder()
    col = _client().get_collection(COLLECTION)
    emb = embedder.encode([q]).tolist()
    res = col.query(query_embeddings=emb, n_results=k)
    print(f"\n[?] Sorgu: {q}\n" + "=" * 56)
    for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
        print(f"\n--- {meta.get('source')} ---\n{doc[:400]}")


def retrieve(q: str, k: int = 4) -> list[dict]:
    """Serving icin: sorguya en yakin k parcayi dondur (prompt'a baglam olarak eklenir)."""
    embedder = _embedder()
    col = _client().get_collection(COLLECTION)
    emb = embedder.encode([q]).tolist()
    res = col.query(query_embeddings=emb, n_results=k)
    return [{"source": m.get("source"), "text": d}
            for d, m in zip(res["documents"][0], res["metadatas"][0])]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("--query", type=str, default=None)
    args = ap.parse_args()
    try:
        import chromadb  # noqa: F401
        import sentence_transformers  # noqa: F401
    except ImportError:
        sys.exit("[X] RAG bagimliliklari yok. Once: pip install chromadb sentence-transformers")
    if args.build:
        build()
    elif args.query:
        query(args.query)
    else:
        print("Kullanim: --build  veya  --query \"...\"")


if __name__ == "__main__":
    main()
