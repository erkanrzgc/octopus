"""GgufModel: gercek Octópus v0.7'yi Ollama uzerinden harness'e baglar (mock yerine).

Prompt EGITIMLE BIREBIR: kaydedilmis tokenizer'in kendi chat template'i (system rolu +
enable_thinking'i destekler) uygulanir, bastaki cift <bos> siyrilir (ADR 0003 tuzagi),
Ollama'ya RAW modda gonderilir. Ollama'nin kendi gemma2 template'ine GUVENILMEZ."""
from __future__ import annotations

import json
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass, field

from agent.messages import Message
from agent.toolcall import render_for_model
from data.sft.normalize import ensure_system
from data.sft.persona import OCTOPUS_TOOL_SYSTEM_PROMPT

_EOT = "<end_of_turn>"


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


@dataclass
class GgufModel:
    """Ollama uzerinden gercek v0.7. __call__ mock ScriptedModel ile ayni arayuz."""
    model: str = "octopus-v7"
    host: str = "http://localhost:11434"
    tokenizer_dir: str = "models/octopus-v7-tokenizer"
    system_prompt: str = OCTOPUS_TOOL_SYSTEM_PROMPT  # araç-farkında: model ```arac``` bloğu basar
    temperature: float = 0.6
    top_p: float = 0.95
    top_k: int = 20
    repeat_penalty: float = 1.15
    num_predict: int = 512
    timeout: int = 180
    renderer: Callable[[list[dict]], str] | None = None  # test enjeksiyonu (transformers'i atlar)
    _tokenizer: object = field(default=None, init=False, repr=False)

    def __call__(self, messages: list[Message]) -> str:
        dicts = ensure_system(render_for_model(messages), self.system_prompt)
        try:
            prompt = self._render(dicts)
        except Exception as e:  # noqa: BLE001 -- dongu asla cokmemeli
            return f"HATA: prompt/tokenizer hazirlanamadi ({type(e).__name__}: {e})"
        return self._generate(prompt)

    def _render(self, dicts: list[dict]) -> str:
        if self.renderer is not None:
            return self.renderer(dicts)
        if self._tokenizer is None:
            self._tokenizer = load_tokenizer(self.tokenizer_dir)
        return render_prompt(dicts, self._tokenizer)

    def _generate(self, prompt: str) -> str:
        body = json.dumps({
            "model": self.model, "prompt": prompt, "raw": True, "stream": False,
            "options": {
                "temperature": self.temperature, "top_p": self.top_p, "top_k": self.top_k,
                "repeat_penalty": self.repeat_penalty, "num_predict": self.num_predict,
                "stop": [_EOT],
            },
        }).encode("utf-8")
        req = urllib.request.Request(
            f"{self.host}/api/generate", data=body,
            headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:  # URLError alt-sinifi -> ONCE yakala
            if e.code == 404:
                return (f"HATA: '{self.model}' Ollama'da yok "
                        f"(once: ollama create {self.model} -f models/Modelfile)")
            return f"HATA: Ollama HTTP {e.code}"
        except TimeoutError:
            return f"HATA: Ollama zaman asimi ({self.timeout}s)"
        except (urllib.error.URLError, OSError) as e:
            return (f"HATA: Ollama'ya baglanilamadi ({e}); "
                    f"'ollama serve' calisiyor mu?")
        return (data.get("response") or "").strip()
