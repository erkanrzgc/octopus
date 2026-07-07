"""Uctan uca demo/giris. run_demo: scripted modelle tam tur (Windows'ta calisir).
Faz 2'de ScriptedModel yerine gercek GGUF modeli takilir, ayni dongu."""
from __future__ import annotations
import argparse
import sys
from agent.backends.mock_model import ScriptedModel
from agent.loop import run_tool_loop
from agent.messages import Message
from agent.registry import ToolRegistry


def run_demo(scope: list[str]) -> str:
    from agent.policy import LabPolicy
    from agent.executor import MockExecutor
    from agent.audit import AuditLog
    registry = ToolRegistry(LabPolicy(scope=scope), MockExecutor(), AuditLog.default())
    model = ScriptedModel([
        'Yetkili testte tararim.\n```arac\n{"arac":"nmap","parametreler":'
        '{"hedef":"10.10.10.5","secenekler":"-sV"}}\n```',
        "Tarama tamam: SSH/HTTP/SMB acik. Sirada web yuzeyini inceleyebilirim.",
    ])
    msgs = [Message("user", "10.10.10.5 hedefini yetkili testte tara")]
    result = run_tool_loop(msgs, model, registry)
    lines = [f"[{m.role}] {m.content}" for m in msgs]
    lines.append(f"(adim={result.steps}, cagri={len(result.calls)}) (demo bitti)")
    return "\n".join(lines)


def main() -> None:
    # Windows konsolu (cp1254) ó/Ç basamaz -> UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Octópus agent harness demo (Faz 1, mock)")
    ap.add_argument("--scope", nargs="*", default=["10.10.10.0/24"], help="izinli IP/CIDR")
    args = ap.parse_args()
    print(run_demo(args.scope))


if __name__ == "__main__":
    main()
