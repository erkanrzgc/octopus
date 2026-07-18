"""Model<->arac dongusu (Hermes recursive loop deseni, agentic-model'den uyarlandi).
model uret -> arac blogu var mi? yoksa nihai cevap; varsa calistir, sonucu tool mesaji
olarak ekle, tekrarla. max_steps sonsuz-dongu korumasi."""
from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass, field
from agent.messages import Message
from agent.registry import ToolRegistry
from agent.toolcall import ToolCall, parse_arac_calls, strip_dusunce

Generate = Callable[[list[Message]], str]


@dataclass
class ToolLoopResult:
    final: str
    steps: int
    calls: list[ToolCall] = field(default_factory=list)


def run_tool_loop(
    messages: list[Message],
    generate: Generate,
    registry: ToolRegistry,
    *,
    max_steps: int = 10,
) -> ToolLoopResult:
    executed: list[ToolCall] = []
    for step in range(max_steps):
        reply = generate(messages)
        messages.append(Message("assistant", reply))
        calls = parse_arac_calls(reply)
        if not calls:
            return ToolLoopResult(final=strip_dusunce(reply), steps=step + 1, calls=executed)
        for call in calls:
            result = registry.invoke(call)
            executed.append(call)
            messages.append(Message("tool", result))
    final = generate(messages)
    messages.append(Message("assistant", final))
    return ToolLoopResult(final=strip_dusunce(final), steps=max_steps, calls=executed)
