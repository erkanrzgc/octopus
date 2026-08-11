"""v1.0 RCA olcum kapisi: bir sunucu OLAYI verilince model KANIT mi topluyor (arac cagirir),
yoksa kanitsiz TAHMIN mi ediyor? Cekirdek metrik = kanit-once-sonuc.

Held-out senaryolar (egitim setinde YOK). Tek-tur uretim: modele olay verilir, ILK yaniti
arac cagiriyor mu (invest.) yoksa dogrudan sonuc/oneri mi (guess). v0.9 baseline vs v1.0 karsilastir.
Kullanim: uv run python -m eval.rca_eval --model octopus-v9
"""
from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field

sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # Windows cp1254 emoji-guard


@dataclass(frozen=True)
class RcaCase:
    olay: str
    # sonuca varmadan once beklenen tani sinyali (kanit toplandiginin gostergesi degil — bilgi)
    ipucu: str


# Egitim setinde OLMAYAN olaylar (held-out).
HELDOUT: list[RcaCase] = [
    RcaCase("Sunucuda 'fork: retry: Resource temporarily unavailable' hatasi almaya basladim, "
            "yeni surec/baglanti acilmiyor.", "surec/thread limiti (nproc/pids)"),
    RcaCase("Web sitesi ara sira cok yavas ama sunucu CPU ve RAM'i normal gorunuyor.", "I/O veya ag"),
    RcaCase("`systemctl restart nginx` ise yariyor ama ~10 dakika sonra servis yine dusuyor.", "OOM/leak"),
    RcaCase("Kullanicilar 'oturum surekli dusuyor' diyor, uygulama loglarinda hata yok.",
            "oturum deposu/redis"),
    RcaCase("Disk yazma hatalari goruyorum ve sistem zaman zaman donuyor.", "disk/donanim"),
]


@dataclass
class CaseOut:
    olay: str
    kanit_topladi: bool   # ilk yanit >=1 arac cagirdi mi
    kanitsiz_sonuc: bool  # arac YOK ama kesin sonuc/oneri verdi mi (tahmin)


@dataclass
class RcaResult:
    total: int
    kanit: int
    outcomes: list[CaseOut] = field(default_factory=list)


# kanitsiz kesin-sonuc imzasi (arac yokken bunu diyorsa tahmin ediyor)
_CONCLUDE = ("kök neden", "sorun şu", "çözüm", "neden:", "kaynaklanıyor", "yapmalısın", "öneri")


def evaluate(gen, cases: list[RcaCase]) -> RcaResult:
    """gen: (olay_metni)->model_yaniti (tek tur). parse_arac_calls ile arac sayilir."""
    from agent.toolcall import parse_arac_calls
    kanit = 0
    outs: list[CaseOut] = []
    for c in cases:
        reply = gen(c.olay)
        calls = parse_arac_calls(reply)
        topladi = len(calls) >= 1
        low = reply.lower()
        kanitsiz = (not topladi) and any(k in low for k in _CONCLUDE)
        kanit += int(topladi)
        outs.append(CaseOut(c.olay, topladi, kanitsiz))
    return RcaResult(len(cases), kanit, outs)


def _report(model: str, r: RcaResult) -> str:
    lines = [f"model={model}  temp=0  olay={r.total}  (olcum kapisi: kanit-once-sonuc)",
             f"KANIT TOPLADI (arac cagirdi): {r.kanit}/{r.total}",
             f"kanitsiz TAHMIN (arac yok+sonuc): "
             f"{sum(o.kanitsiz_sonuc for o in r.outcomes)}/{r.total}", "", "per-olay:"]
    for o in r.outcomes:
        mark = "KANIT" if o.kanit_topladi else ("TAHMIN" if o.kanitsiz_sonuc else "belirsiz")
        lines.append(f"  [{mark:7s}] {o.olay[:58]}")
    return "\n".join(lines)


def run_against_ollama(model: str = "octopus-v9") -> str:
    """GERCEK model ile RCA kanit-once-sonuc olcumu (temp=0). Ollama+GGUF gerektirir."""
    from agent.backends.gguf_model import GgufModel
    from agent.messages import Message
    from data.sft.persona import OCTOPUS_TOOL_SYSTEM_PROMPT

    gm = GgufModel(model=model, tokenizer_dir="models/octopus-v8-tokenizer",
                   system_prompt=OCTOPUS_TOOL_SYSTEM_PROMPT, temperature=0.0, num_predict=320)

    def gen(olay: str) -> str:
        return gm([Message("user", olay)])

    return _report(model, evaluate(gen, HELDOUT))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="octopus-v9")
    print(run_against_ollama(ap.parse_args().model))
