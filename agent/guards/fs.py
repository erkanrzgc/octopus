"""Dosya araclari icin workspace hapishane guard'i. workspace_root disina cikis
(traversal/absolute/symlink) fail-closed reddedilir. Saf fonksiyon -> test kolay."""
from __future__ import annotations

from pathlib import Path

from agent.policy import Decision


def guard(params: dict, workspace_root: str | None) -> Decision:
    if not workspace_root:
        return Decision(False, False, "workspace_root tanimsiz (fail-closed)")
    yol = params.get("yol")
    if not yol:
        return Decision(False, False, "'yol' parametresi eksik")
    root = Path(workspace_root).resolve()
    candidate = Path(yol)
    target = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    if target == root or root in target.parents:
        return Decision(True, False, "izinli")
    return Decision(False, False, f"workspace disina cikis reddedildi: {yol}")
