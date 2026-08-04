"""Extension-tool DISCOVERY olcumu: egitilmemis araclar (trufflehog/magika/ghunt) sistem-prompt
manifestiyle tanitilinca model onlari CAGIRIYOR mu?

Deney: ayni istek, manifest OFF (taban sistem-prompt) vs ON (manifest ekli). Her ikisinde de
skills=None -> post-call correction'dan IZOLE; olculen tek sey MANIFEST'in kesif etkisi.
Metrik: modelin urettigi arac bloklari beklenen extension aracini iceriyor mu (emisyon).
Beklenti: OFF ~0 (model bu araclari bilmez), ON > OFF = retrain'siz kesif kazanci.
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from agent.loop import run_tool_loop
from agent.messages import Message
from agent.registry import ToolRegistry


@dataclass(frozen=True)
class DiscoveryCase:
    prompt: str
    tool: str   # bu istegin dogru extension araci (EXTENSION_TOOL_NAMES icinde olmali)


@dataclass
class DiscoveryOutcome:
    prompt: str
    tool: str
    off_called: bool   # manifest YOKken beklenen arac emit edildi mi
    on_called: bool    # manifest VARken


@dataclass
class DiscoveryResult:
    total: int
    called_off: int
    called_on: int
    outcomes: list[DiscoveryOutcome] = field(default_factory=list)


# Yetkili/lab cerceveli; her istek TEK bir extension aracina isaret eder (arac adi el VERILMEZ,
# is niyeti Turkce yazilir -> modelin manifestten dogru araci secmesi beklenir).
DISCOVERY_CASES: list[DiscoveryCase] = [
    DiscoveryCase("Yetkili denetimde su git deposunu sizmis parola ve API anahtarlari icin tara: "
                  "https://github.com/ornek/lab-repo", "trufflehog"),
    DiscoveryCase("Adli incelemede /tmp/ornek.bin dosyasinin uzantisi yaniltici; gercek dosya "
                  "turunu tespit et", "magika"),
    DiscoveryCase("Yetkili OSINT kapsaminda su Google hesabi hakkinda acik kaynak bilgi topla: "
                  "hedef@ornek.com", "ghunt"),
]


def _called(res_calls, tool: str) -> bool:
    """Model bu araci emit etti mi (policy reddetse bile executed'e islenir; emisyon metrigi)."""
    return any(c.name == tool for c in res_calls)


def evaluate_discovery(
    gen_off_factory: Callable[[], object],
    gen_on_factory: Callable[[], object],
    cases: list[DiscoveryCase],
    registry_factory: Callable[[], ToolRegistry],
) -> DiscoveryResult:
    """Her case icin OFF ve ON modeli ayri calistir (taze generate + taze registry, durum sizmasin;
    skills=None -> izole). Beklenen arac emit edildi mi say."""
    called_off = called_on = 0
    outcomes: list[DiscoveryOutcome] = []
    for case in cases:
        off_res = run_tool_loop([Message("user", case.prompt)], gen_off_factory(),
                                registry_factory(), skills=None)
        on_res = run_tool_loop([Message("user", case.prompt)], gen_on_factory(),
                               registry_factory(), skills=None)
        off = _called(off_res.calls, case.tool)
        on = _called(on_res.calls, case.tool)
        called_off += int(off)
        called_on += int(on)
        outcomes.append(DiscoveryOutcome(case.prompt, case.tool, off, on))
    return DiscoveryResult(len(cases), called_off, called_on, outcomes)


def _report(model: str, res: DiscoveryResult) -> str:
    lines = [
        f"model={model}  temp=0  cases={res.total}  (manifest OFF vs ON, skills=None izole)",
        f"extension-arac emit (manifest OFF): {res.called_off}/{res.total}",
        f"extension-arac emit (manifest ON):  {res.called_on}/{res.total}",
        f"KESIF KAZANCI (ON - OFF): {res.called_on - res.called_off:+d}",
        "",
        "per-case (arac: OFF -> ON):",
    ]
    for o in res.outcomes:
        off_s = "CAGIRDI" if o.off_called else "yok"
        on_s = "CAGIRDI" if o.on_called else "yok"
        mark = " <== KESIF KAZANCI" if (o.on_called and not o.off_called) else ""
        lines.append(f"  {o.tool:11s} {off_s} -> {on_s}{mark}")
    return "\n".join(lines)


def run_against_ollama(model: str = "octopus-v9", scope: list[str] | None = None) -> str:
    """GERCEK model ile manifest OFF vs ON kesif olcumu (temp=0). Ollama+GGUF gerektirir.
    Kullanim: uv run python -m eval.extension_discovery_eval."""
    from agent.audit import AuditLog
    from agent.executor import MockExecutor
    from agent.policy import LabPolicy
    from agent.backends.gguf_model import GgufModel
    from agent.catalog import extension_augmented_system_prompt
    from data.sft.persona import OCTOPUS_TOOL_SYSTEM_PROMPT

    scope = scope or ["10.10.10.0/24"]
    base = OCTOPUS_TOOL_SYSTEM_PROMPT
    augmented = extension_augmented_system_prompt(base)   # TEK KAYNAK (cli demo ile ayni)

    def reg() -> ToolRegistry:
        return ToolRegistry(LabPolicy(scope=scope), MockExecutor(), AuditLog.default())

    def off_factory():
        return GgufModel(model=model, temperature=0.0, system_prompt=base)

    def on_factory():
        return GgufModel(model=model, temperature=0.0, system_prompt=augmented)

    res = evaluate_discovery(off_factory, on_factory, DISCOVERY_CASES, reg)
    return _report(model, res)


if __name__ == "__main__":
    print(run_against_ollama())
