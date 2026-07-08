#!/usr/bin/env python
"""Türkçe-önce SentencePiece (Unigram) tokenizer eğit.

Neden Unigram: Türkçe sondan eklemeli (agglutinative). Unigram LM, BPE'den daha
iyi morfolojik bölme ve daha düşük fertility verir (Llama/Gemma/T5 yaklaşımı).

Türkçe-kritik ayarlar:
  - normalization=identity            → \n + birebir bytes korunur (kod/komut/chat); NFC veri-temizlemede yapılır
  - byte_fallback=True                → nadir karakter / komut / kod / emoji / diakritik (ç/ğ/ı/ş/İ) güvenli
  - split_digits=True                 → port/IP/CVE sayıları tutarlı parçalanır
  - remove_extra_whitespaces=False    → kod/komut girintisi + boş satır korunur

Kullanım:
    uv run python tokenizer/train_tokenizer.py --vocab-size 32000
"""
from __future__ import annotations

import argparse
from pathlib import Path

import sentencepiece as spm

# chat/agent formatı için vocab'da yer ayrılan özel tokenlar (model fazında kullanılacak)
SPECIAL_TOKENS = [
    "<|im_start|>", "<|im_end|>",
    "<tool_call>", "</tool_call>",
    "<tool_response>", "</tool_response>",
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--input", type=Path, default=Path("data/corpus/tr_wiki.txt"))
    ap.add_argument("--model-prefix", default="tokenizer/octopus-tr")
    ap.add_argument("--vocab-size", type=int, default=32000)
    ap.add_argument("--character-coverage", type=float, default=0.9999)
    ap.add_argument("--input-sentence-size", type=int, default=5_000_000,
                    help="eğitim için örneklenecek max satır (0 = hepsi)")
    ap.add_argument("--normalization", default="identity",
                    help="normalization_rule_name: identity (newline korunur, önerilen) | nmt_nfkc (NFKC)")
    args = ap.parse_args()

    if not args.input.exists():
        raise SystemExit(f"[!] korpus yok: {args.input} — önce data/download_corpus.py çalıştır")

    Path(args.model_prefix).parent.mkdir(parents=True, exist_ok=True)

    spm.SentencePieceTrainer.train(
        input=str(args.input),
        model_prefix=args.model_prefix,
        model_type="unigram",
        vocab_size=args.vocab_size,
        character_coverage=args.character_coverage,
        normalization_rule_name=args.normalization,   # identity=newline korunur (kod/komut/chat); NFC veri tarafında
        byte_fallback=True,
        split_digits=True,
        remove_extra_whitespaces=False,
        allow_whitespace_only_pieces=True,
        input_sentence_size=args.input_sentence_size,
        shuffle_input_sentence=True,
        unk_id=0, bos_id=1, eos_id=2, pad_id=3,
        unk_piece="<unk>", bos_piece="<s>", eos_piece="</s>", pad_piece="<pad>",
        user_defined_symbols=SPECIAL_TOKENS,
    )

    print(f"[ok] tokenizer -> {args.model_prefix}.model / {args.model_prefix}.vocab")
    print("     sonraki: uv run python eval/fertility.py --text data/corpus/eval_tr.txt")


if __name__ == "__main__":
    main()
