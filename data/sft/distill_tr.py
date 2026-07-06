"""v0.4 distillation — güçlü teacher (Qwen3-14B) RAG bilgi tabanından ÇEŞİTLİ Türkçe cyber Q&A üretir.

Neden: v0.3'te öğrendik ki el-yazımı 87 seed'i ×20 tekrarlamak ÇEŞİTLİLİK vermiyor (model ezberliyor,
Türkçe genellemiyor). Kök sebep: %91 İngilizce Fenrir baskın + Türkçe çeşitlilik az. Çözüm: teacher
model, rag/knowledge/ (18 Türkçe dosya, doğru ID'ler) her parçasından FARKLI Türkçe soru-cevaplar üretsin
→ binlerce ÇEŞİTLİ, faktüel-doğru Türkçe cyber örneği. cyberm4fia/agentic distill deseninden.

ÇALIŞTIRMA (pod'da — torch/unsloth gerekir):
    python data/sft/distill_tr.py --teacher unsloth/Qwen3-14B --per-chunk 3 --out data/sft/seed_tr/octopus_distill_tr.jsonl

Çıktı: seed_tr/*.jsonl -> build_sft otomatik toplar (seed_tr kaynağı). Çıktı 'messages' formatında.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

ROOT = Path(__file__).resolve().parent.parent.parent
KNOWLEDGE_DIR = ROOT / "rag" / "knowledge"

# Teacher'a farkli acilar sordurup cesitlilik yaratan yonergeler.
ANGLES = [
    "bir sistem yoneticisinin sunucu tarafi",
    "yetkili bir kirmizi takim (red team) uzmaninin saldiri tarafi (kendi lab/CTF/izinli kapsam)",
    "bir mavi takim (blue team) analistinin tespit/savunma tarafi",
    "kavramin ne oldugunu ve dogru ID/terimleri soran bir ogrenci",
]

PROMPT_TMPL = (
    "Aşağıdaki doğrulanmış siber güvenlik bilgisine dayanarak, {angle} perspektifinden "
    "{n} farklı, gerçekçi Türkçe SORU ve her birine bu bilgiye dayalı DOĞRU, teknik, uygulanabilir "
    "Türkçe CEVAP üret. Komut/kod/CVE-ID'leri verbatim koru. Cevaplar akıcı ve doğal Türkçe olsun. "
    "SADECE şu JSON formatında dön (başka açıklama yok):\n"
    '[{{"soru": "...", "cevap": "..."}}]\n\n'
    "BİLGİ:\n{chunk}"
)


def _chunks(text: str, size: int = 1100, overlap: int = 120):
    text = text.strip()
    if len(text) <= size:
        return [text] if text else []
    out, start = [], 0
    while start < len(text):
        out.append(text[start:start + size])
        start += size - overlap
    return out


def _extract_pairs(raw: str) -> list[dict]:
    """Teacher ciktisindan [{soru,cevap}] cikar (JSON, degilse regex fallback)."""
    m = re.search(r"\[\s*\{.*\}\s*\]", raw, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            return [{"soru": d["soru"], "cevap": d["cevap"]}
                    for d in data if d.get("soru") and d.get("cevap")]
        except Exception:  # noqa: BLE001
            pass
    return []


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--teacher", default="unsloth/Qwen3-14B")
    ap.add_argument("--per-chunk", type=int, default=3, help="parca basi Q&A (her biri farkli acidan)")
    ap.add_argument("--max-chunks", type=int, default=0, help="0=hepsi; test icin sinirla")
    ap.add_argument("--out", default=str(ROOT / "data" / "sft" / "distilled" / "octopus_distill_tr.jsonl"))
    args = ap.parse_args()
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)  # ayri klasor (seed_tr degil -> upsample edilmez)

    from unsloth import FastLanguageModel
    import torch  # noqa: F401

    print(f"[*] Teacher yukleniyor (4-bit): {args.teacher}")
    model, tok = FastLanguageModel.from_pretrained(
        model_name=args.teacher, max_seq_length=4096, load_in_4bit=True, dtype=None)
    FastLanguageModel.for_inference(model)

    docs = sorted(list(KNOWLEDGE_DIR.rglob("*.md")))
    chunks = []
    for d in docs:
        for ch in _chunks(d.read_text(encoding="utf-8", errors="ignore")):
            chunks.append((d.name, ch))
    if args.max_chunks:
        chunks = chunks[:args.max_chunks]
    print(f"[*] {len(docs)} dosya -> {len(chunks)} parca; her parca {args.per_chunk} Q&A")

    out_path = Path(args.out)
    seen: set[str] = set()
    n = 0
    with out_path.open("w", encoding="utf-8") as f:
        for i, (src, chunk) in enumerate(chunks):
            angle = ANGLES[i % len(ANGLES)]
            prompt = PROMPT_TMPL.format(angle=angle, n=args.per_chunk, chunk=chunk)
            msgs = [{"role": "user", "content": prompt}]
            enc = tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True,
                                          enable_thinking=False, return_dict=True,
                                          return_tensors="pt").to(model.device)
            out = model.generate(**enc, max_new_tokens=1200, do_sample=True, temperature=0.7,
                                 top_p=0.9, repetition_penalty=1.1, pad_token_id=tok.eos_token_id)
            raw = tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True)
            for pair in _extract_pairs(raw):
                key = pair["soru"][:80]
                if key in seen or len(pair["cevap"]) < 40:
                    continue
                seen.add(key)
                rec = {"messages": [
                    {"role": "user", "content": pair["soru"].strip()},
                    {"role": "assistant", "content": pair["cevap"].strip()},
                ]}
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1
            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{len(chunks)}] toplam {n} Q&A")

    print(f"[OK] {n} cesitli Turkce cyber Q&A -> {out_path}")


if __name__ == "__main__":
    main()
