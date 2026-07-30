"""Model<->arac dongusu (Hermes recursive loop deseni, agentic-model'den uyarlandi).
model uret -> arac blogu var mi? yoksa nihai cevap; varsa (skill katmani acikken) yeni
arac icin once skill enjekte et + regenerate, sonra calistir, sonucu tool mesaji olarak
ekle, tekrarla. max_steps sonsuz-dongu korumasi."""
from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass, field
from agent.messages import Message
from agent.registry import ToolRegistry
from agent.skills import SkillLibrary
from agent.toolcall import ToolCall, parse_arac_calls, strip_dusunce

Generate = Callable[[list[Message]], str]


@dataclass
class ToolLoopResult:
    final: str
    steps: int
    calls: list[ToolCall] = field(default_factory=list)


def _inject_tool_skills(
    messages: list[Message], calls: list[ToolCall],
    skills: SkillLibrary, shown: set[str],
) -> bool:
    """Cagrilan araclardan skill'i olan + bu konusmada henuz gosterilmemis olanlar icin
    skill md'sini USER turu olarak ekle (once oku). Cache: her arac en fazla 1 kez.
    En az bir enjeksiyon yapildiysa True (dongu regenerate etsin)."""
    injected = False
    for call in calls:
        if call.name in shown:
            continue
        skill = skills.match_tool(call.name)
        if skill is None:
            continue
        messages.append(Message("user", skills.tool_skill_injection(skill)))
        shown.add(call.name)
        injected = True
    return injected


def run_tool_loop(
    messages: list[Message],
    generate: Generate,
    registry: ToolRegistry,
    *,
    max_steps: int = 10,
    skills: SkillLibrary | None = None,
) -> ToolLoopResult:
    executed: list[ToolCall] = []
    shown: set[str] = set()
    for step in range(max_steps):
        reply = generate(messages)
        messages.append(Message("assistant", reply))
        calls = parse_arac_calls(reply)
        if not calls:
            return ToolLoopResult(final=strip_dusunce(reply), steps=step + 1, calls=executed)
        if skills is not None and _inject_tool_skills(messages, calls, skills, shown):
            continue  # skill eklendi -> model cagriyi duzeltsin diye yeniden uret
        for call in calls:
            result = registry.invoke(call)
            executed.append(call)
            messages.append(Message("tool", result))
    final = generate(messages)
    messages.append(Message("assistant", final))
    return ToolLoopResult(final=strip_dusunce(final), steps=max_steps, calls=executed)
