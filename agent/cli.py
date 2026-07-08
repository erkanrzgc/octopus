"""Uctan uca demo/giris. Uc mod, tek dongü:
  (varsayilan) mock  : MockExecutor (sahte cikti, Windows'ta calisir)
  --real             : RealExecutor (Kali WSL'de gercek arac)
  --docker           : DockerExecutor (lab docker aginda container arac -> erisilebilir hedef)
Faz 2'de ScriptedModel yerine gercek GGUF modeli takilir, ayni dongu."""
from __future__ import annotations
import argparse
import sys
from agent.backends.mock_model import ScriptedModel
from agent.loop import run_tool_loop
from agent.messages import Message
from agent.registry import ToolRegistry


def _scan_demo(executor, target: str, scope: list[str], secenekler: str, label: str) -> str:
    """Tek scripted nmap turu: model arac blogu -> policy -> executor -> geri-besleme -> cevap."""
    from agent.policy import LabPolicy
    from agent.audit import AuditLog
    registry = ToolRegistry(LabPolicy(scope=scope), executor, AuditLog.default())
    model = ScriptedModel([
        f'Yetkili lab hedefini tararim.\n```arac\n'
        f'{{"arac":"nmap","parametreler":{{"hedef":"{target}","secenekler":"{secenekler}"}}}}\n```',
        "Tarama tamamlandi, sonucu yukarida yorumladim.",
    ])
    msgs = [Message("user", f"{target} yetkili lab hedefini tara")]
    result = run_tool_loop(msgs, model, registry)
    lines = [f"[{m.role}] {m.content}" for m in msgs]
    lines.append(f"(adim={result.steps}, cagri={len(result.calls)}) ({label})")
    return "\n".join(lines)


def run_demo(scope: list[str]) -> str:
    """Mock: gercek arac calistirmadan dongu (Windows'ta calisir)."""
    from agent.executor import MockExecutor
    return _scan_demo(MockExecutor(), "10.10.10.5", scope, "-sV", "demo bitti")


def run_real_demo(target: str = "127.0.0.1", scope: list[str] | None = None,
                  distro: str = "kali-linux", port: int = 8000) -> str:
    """GERCEK: RealExecutor Kali WSL'de gercek nmap (hedef Kali'den erisilebilir olmali)."""
    from agent.backends.real_executor import RealExecutor
    scope = scope or ["127.0.0.0/8"]
    return _scan_demo(RealExecutor(distro=distro), target, scope, f"-Pn -sV -p{port}", "gercek demo bitti")


def run_docker_demo(target: str = "octopus-target", scope: list[str] | None = None,
                    network: str = "octopus-lab", port: int = 80) -> str:
    """DOCKER LAB (Model B): arac lab aginda container -> hedefe DNS adiyla erisir."""
    from agent.backends.docker_executor import DockerExecutor
    scope = scope or [target, "172.30.0.0/24"]
    return _scan_demo(DockerExecutor(network=network), target, scope, f"-Pn -sV -p{port}", "docker demo bitti")


def main() -> None:
    # Windows konsolu (cp1254) ó/Ç basamaz -> UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="Octópus agent harness demo")
    ap.add_argument("--scope", nargs="*", default=None, help="izinli IP/CIDR (mod varsayilanini ezer)")
    ap.add_argument("--real", action="store_true", help="RealExecutor: Kali WSL'de gercek nmap")
    ap.add_argument("--docker", action="store_true", help="DockerExecutor: lab docker aginda gercek nmap")
    ap.add_argument("--target", default=None, help="hedef (mod varsayilanini ezer)")
    ap.add_argument("--port", type=int, default=None, help="taranacak port (mod varsayilani)")
    args = ap.parse_args()
    if args.docker:
        print(run_docker_demo(args.target or "octopus-target", args.scope, port=args.port or 80))
    elif args.real:
        print(run_real_demo(args.target or "127.0.0.1", args.scope, port=args.port or 8000))
    else:
        print(run_demo(args.scope or ["10.10.10.0/24"]))


if __name__ == "__main__":
    main()
