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


def run_real_demo(target: str = "127.0.0.1", scope: list[str] | None = None,
                  distro: str = "kali-linux", port: int = 8000) -> str:
    """GERCEK tur: scripted model -> RealExecutor Kali WSL'de gercek nmap -> gercek hedef.
    Policy kapisi scope-ici hedefi gecirir. (Faz 2 uctan uca dogrulama.)"""
    from agent.policy import LabPolicy
    from agent.backends.real_executor import RealExecutor
    from agent.audit import AuditLog
    scope = scope or ["127.0.0.0/8"]
    registry = ToolRegistry(LabPolicy(scope=scope), RealExecutor(distro=distro), AuditLog.default())
    model = ScriptedModel([
        f'Yetkili lab hedefini tararim.\n```arac\n'
        f'{{"arac":"nmap","parametreler":{{"hedef":"{target}","secenekler":"-Pn -sV -p{port}"}}}}\n```',
        "Tarama tamamlandi, sonucu yukarida yorumladim.",
    ])
    msgs = [Message("user", f"{target} yetkili lab hedefini tara")]
    result = run_tool_loop(msgs, model, registry)
    lines = [f"[{m.role}] {m.content}" for m in msgs]
    lines.append(f"(adim={result.steps}, cagri={len(result.calls)}) (gercek demo bitti)")
    return "\n".join(lines)


def main() -> None:
    # Windows konsolu (cp1254) ó/Ç basamaz -> UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Octópus agent harness demo")
    ap.add_argument("--scope", nargs="*", default=None, help="izinli IP/CIDR")
    ap.add_argument("--real", action="store_true", help="RealExecutor ile GERCEK nmap (Kali WSL)")
    ap.add_argument("--target", default="127.0.0.1", help="gercek demo hedefi (lab)")
    ap.add_argument("--port", type=int, default=8000, help="taranacak port")
    args = ap.parse_args()
    if args.real:
        print(run_real_demo(args.target, args.scope, port=args.port))
    else:
        print(run_demo(args.scope or ["10.10.10.0/24"]))


if __name__ == "__main__":
    main()
