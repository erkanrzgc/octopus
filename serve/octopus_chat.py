"""Octopus serving — adapter + RAG grounding + tuned generation ile yerel sohbet.

'Ship' yolu: eğitilmiş LoRA adapter'i (v0.2/v0.5) tabana bindir, faktüel sorularda RAG
bilgi tabanindan (rag/chroma) baglam ekle, iyi generation ayariyla (thinking-off,
no-repeat) Turkce cevap ver. cyberm4fia venv (3.12+unsloth) ile kosulur.

Kosum:
    CY=C:/Users/erkanrzgc/Desktop/cyberm4fiaModel/.venv/Scripts/python.exe
    "$CY" serve/octopus_chat.py --adapter checkpoints_sft/octopus-8b-adapter --ask "Log4Shell nedir" --rag
    "$CY" serve/octopus_chat.py --adapter checkpoints_sft/octopus-8b-adapter        # interaktif
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

from unsloth import FastLanguageModel  # noqa: E402
import torch  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from data.sft.persona import OCTOPUS_SYSTEM_PROMPT  # noqa: E402

BASE = "unsloth/Qwen3-8B"


def _rag_context(question: str, k: int = 3) -> str:
    """rag/build_rag.retrieve ile ilgili dogrulanmis bilgi parcalarini getir."""
    try:
        from rag.build_rag import retrieve
        hits = retrieve(question, k=k)
        if not hits:
            return ""
        blocks = "\n".join(f"[{h['source']}] {h['text'][:500]}" for h in hits)
        return ("\n\nAşağıdaki DOĞRULANMIŞ bilgiye dayan (ID/terimleri buradan al, uydurma):\n" + blocks)
    except Exception as e:  # noqa: BLE001
        print(f"[!] RAG atlandi: {e}")
        return ""


def _generate(model, tok, question: str, use_rag: bool) -> str:
    system = OCTOPUS_SYSTEM_PROMPT + (_rag_context(question) if use_rag else "")
    msgs = [{"role": "system", "content": system}, {"role": "user", "content": question}]
    enc = tok.apply_chat_template(msgs, tokenize=True, add_generation_prompt=True,
                                  enable_thinking=False, return_dict=True,
                                  return_tensors="pt").to(model.device)
    out = model.generate(**enc, max_new_tokens=400, do_sample=True, temperature=0.6,
                         top_p=0.9, repetition_penalty=1.15, no_repeat_ngram_size=4,
                         pad_token_id=tok.eos_token_id)
    return tok.decode(out[0][enc["input_ids"].shape[1]:], skip_special_tokens=True).strip()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--adapter", default=str(ROOT / "checkpoints_sft" / "octopus-8b-adapter"))
    ap.add_argument("--base", default=BASE)
    ap.add_argument("--ask", default=None, help="Tek soru sor ve cik (test icin)")
    ap.add_argument("--rag", action="store_true", help="RAG grounding ekle")
    args = ap.parse_args()

    # adapter dizininden yukle: unsloth adapter_config.json'daki tabani otomatik indirir+bindirir.
    print(f"[*] Adapter (+taban) yukleniyor: {args.adapter}")
    model, tok = FastLanguageModel.from_pretrained(
        model_name=args.adapter, max_seq_length=4096, load_in_4bit=True, dtype=None)
    FastLanguageModel.for_inference(model)
    print(f"[*] Hazir. RAG={'acik' if args.rag else 'kapali'}\n")

    if args.ask:
        print(f"### SEN: {args.ask}\n### OCTOPUS: {_generate(model, tok, args.ask, args.rag)}")
        return

    print("Octopus'la sohbet (cikis: bos satir / Ctrl+C)")
    while True:
        try:
            q = input("### SEN: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not q:
            break
        print(f"### OCTOPUS: {_generate(model, tok, q, args.rag)}\n")


if __name__ == "__main__":
    main()
