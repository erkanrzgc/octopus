"""GgufModel: gercek Octópus v0.7'yi Ollama uzerinden harness'e baglar (mock yerine).

Prompt EGITIMLE BIREBIR: kaydedilmis tokenizer'in kendi chat template'i (system rolu +
enable_thinking'i destekler) uygulanir, bastaki cift <bos> siyrilir (ADR 0003 tuzagi),
Ollama'ya RAW modda gonderilir. Ollama'nin kendi gemma2 template'ine GUVENILMEZ."""
from __future__ import annotations


def load_tokenizer(tokenizer_dir: str):
    """transformers'i LAZY import et (yalniz --gguf yolu; torch weights yuklenmez)."""
    from transformers import AutoTokenizer
    return AutoTokenizer.from_pretrained(tokenizer_dir)


def render_prompt(dicts: list[dict], tokenizer, *, bos_token: str = "<bos>") -> str:
    """dict listesi -> egitim-birebir prompt metni (tokenize=False, add_generation_prompt=True)."""
    try:
        t = tokenizer.apply_chat_template(
            dicts, tokenize=False, add_generation_prompt=True, enable_thinking=False)
    except TypeError:  # bazi template'ler enable_thinking kwarg'ini tanimaz
        t = tokenizer.apply_chat_template(dicts, tokenize=False, add_generation_prompt=True)
    # Gemma template metne literal <bos> basar; Ollama raw'da tek BOS yeter -> bastakini siyir.
    if bos_token and t.startswith(bos_token):
        t = t[len(bos_token):]
    return t
