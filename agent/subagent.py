"""Rol-scoped subagent: scoped ToolRegistry + DEGISMEYEN run_tool_loop. route()->SubAgent = 'backend'.
Cikti kalitesini artirmaz; arac UZAYINI daraltir (rol-disi cagri reddedilir, model kendini duzeltir)."""
from __future__ import annotations
from collections.abc import Callable
from dataclasses import dataclass, field
from agent.loop import ToolLoopResult, run_tool_loop
from agent.messages import Message
from agent.registry import ToolRegistry
from agent.roles import GENERAL
from agent.router import route
from agent.skills import SkillLibrary

Generate = Callable[[list[Message]], str]


@dataclass
class SubAgent:
    role: str
    registry: ToolRegistry = field(default=None)  # type: ignore[assignment]

    def __post_init__(self) -> None:
        if self.registry is None:
            self.registry = (ToolRegistry.default() if self.role == GENERAL
                             else ToolRegistry.scoped(self.role))

    def run(self, gorev: str, generate: Generate, *,
            skills: SkillLibrary | None = None, max_steps: int = 10) -> ToolLoopResult:
        return run_tool_loop([Message("user", gorev)], generate, self.registry,
                             max_steps=max_steps, skills=skills)


@dataclass(frozen=True)
class SubAgentRun:
    role: str
    result: ToolLoopResult


def run_task(gorev: str, generate: Generate, *,
             skills: SkillLibrary | None = None, max_steps: int = 10) -> SubAgentRun:
    """Backend girisi: gorevi rota -> rol-scoped subagent -> calistir. Rolu de dondurur (gozlem)."""
    role = route(gorev)
    result = SubAgent(role).run(gorev, generate, skills=skills, max_steps=max_steps)
    return SubAgentRun(role=role, result=result)
