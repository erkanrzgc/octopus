"""Uctan uca demo/giris. Uc mod, tek dongü:
  (varsayilan) mock  : MockExecutor (sahte cikti, Windows'ta calisir)
  --real             : RealExecutor (Kali WSL'de gercek arac)
  --docker           : DockerExecutor (lab docker aginda container arac -> erisilebilir hedef)
Faz 2'de ScriptedModel yerine gercek GGUF modeli takilir, ayni dongu."""
from __future__ import annotations
import argparse
import re
import sys
from agent.backends.mock_model import ScriptedModel
from agent.loop import run_tool_loop
from agent.messages import Message
from agent.registry import ToolRegistry

# Docker container-adi grameri: harf/rakam ile baslar, ardindan [A-Za-z0-9_.-]. Enjeksiyon
# kapisi — _docker_container_ip'te WSL komutuna yalniz bu deseni gecen ad girer.
_CONTAINER_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")


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


def run_gguf_demo(scope: list[str] | None = None, model: str = "octopus-v7",
                  executor=None, target: str = "10.10.10.5", label: str = "gguf demo bitti") -> str:
    """GERCEK BEYIN: GgufModel (Ollama'da v0.7) dongüyü sürer. executor=None -> MockExecutor eller.
    executor verilirse (ör. DockerExecutor) gercek beyin + gercek eller uctan-uca calisir.
    Ollama yoksa GgufModel net HATA stringi döner -> döngü çökmez, onu nihai cevap alir."""
    from agent.backends.gguf_model import GgufModel
    from agent.policy import LabPolicy
    from agent.audit import AuditLog
    if executor is None:
        from agent.executor import MockExecutor
        executor = MockExecutor()
    scope = scope or ["10.10.10.0/24"]
    registry = ToolRegistry(LabPolicy(scope=scope), executor, AuditLog.default())
    msgs = [Message("user", f"{target} yetkili lab hedefini tara")]
    result = run_tool_loop(msgs, GgufModel(model=model), registry)
    lines = [f"[{m.role}] {m.content}" for m in msgs]
    lines.append(f"(adim={result.steps}, cagri={len(result.calls)}) ({label})")
    return "\n".join(lines)


def _docker_container_ip(container: str, distro: str = "kali-linux") -> str | None:
    """Lab container'inin guncel IP'sini docker inspect ile al (None = bulunamadi).
    NEDEN IP: Docker embedded DNS (isimle cozme) WSL'de flaky olabilir; model zaten
    prompt'taki ACIK IP'yi arac blogunda birebir onurlandirir (hostname'i ise kacirir).
    GUVENLIK: shell YOK — argv listesi (wsl.exe -> docker inspect ...) + container adi
    allowlist ile dogrulanir (enjeksiyon kapali)."""
    import subprocess
    if not _CONTAINER_NAME_RE.match(container):     # gecersiz/kotucul ad -> hic komut kurma
        return None
    try:
        out = subprocess.run(
            ["wsl.exe", "-d", distro, "--", "docker", "inspect", container,
             "--format", "{{json .NetworkSettings.Networks}}"],
            capture_output=True, text=True, timeout=30).stdout
    except (subprocess.SubprocessError, FileNotFoundError):
        return None
    m = re.search(r'"IPAddress":"([0-9.]+)"', out)
    return m.group(1) if m else None


def run_gguf_docker_demo(scope: list[str] | None = None, model: str = "octopus-v7",
                         target: str = "octopus-target", network: str = "octopus-lab") -> str:
    """UCTAN UCA (Model B): GERCEK v0.7 beyni + GERCEK docker-lab eli (container nmap).
    Model arac blogu uretir -> policy -> DockerExecutor lab aginda gercek nmap -> hedef.
    Hedefi IP'ye cevir (DNS-siz): model acik IP'yi onurlandirir, container adini kacirir."""
    from agent.backends.docker_executor import DockerExecutor
    ip = _docker_container_ip(target)
    real_target = ip or target                      # IP alinamazsa isme dus (DNS calisiyorsa olur)
    scope = scope or [real_target, "172.16.0.0/12", "172.30.0.0/24"]
    return run_gguf_demo(scope, model, executor=DockerExecutor(network=network),
                         target=real_target, label="gguf+docker uctan uca bitti")


def run_assistant_demo(workspace: str | None = None) -> str:
    """Asistan araclari demo: gercek jailed dosya islemi + policy reddi (mock guvenlik elleri)."""
    import tempfile
    from agent.audit import AuditLog
    from agent.backends.assistant_executor import AssistantExecutor
    from agent.composite_executor import CompositeExecutor
    from agent.executor import MockExecutor
    from agent.policy import LabPolicy
    from agent.toolcall import ToolCall
    ws = workspace or tempfile.mkdtemp(prefix="octopus-ws-")
    execu = CompositeExecutor(security=MockExecutor(), assistant=AssistantExecutor(ws))
    registry = ToolRegistry(LabPolicy(scope=[], workspace_root=ws), execu, AuditLog.default())
    steps = [
        ToolCall(name="write_file", params={"yol": "not.txt", "icerik": "Octópus lab notu"}),
        ToolCall(name="read_file", params={"yol": "not.txt"}),
        ToolCall(name="write_file", params={"yol": "../kacis.txt", "icerik": "x"}),  # reddedilmeli
    ]
    lines = [f"[workspace] {ws}"]
    for c in steps:
        lines.append(f"[{c.name}] -> {registry.invoke(c)}")
    lines.append("(asistan demo bitti)")
    return "\n".join(lines)


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
    ap.add_argument("--gguf", action="store_true", help="GgufModel: Ollama'da gercek v0.7")
    ap.add_argument("--assistant", action="store_true", help="Asistan araclari demo (jailed file + policy)")
    ap.add_argument("--model", default=None, help="Ollama model adi (varsayilan octopus-v7)")
    ap.add_argument("--target", default=None, help="hedef (mod varsayilanini ezer)")
    ap.add_argument("--port", type=int, default=None, help="taranacak port (mod varsayilani)")
    args = ap.parse_args()
    if args.assistant:
        print(run_assistant_demo())
    elif args.gguf and args.docker:
        print(run_gguf_docker_demo(args.scope, args.model or "octopus-v7",
                                   args.target or "octopus-target"))
    elif args.gguf:
        print(run_gguf_demo(args.scope, args.model or "octopus-v7"))
    elif args.docker:
        print(run_docker_demo(args.target or "octopus-target", args.scope, port=args.port or 80))
    elif args.real:
        print(run_real_demo(args.target or "127.0.0.1", args.scope, port=args.port or 8000))
    else:
        print(run_demo(args.scope or ["10.10.10.0/24"]))


if __name__ == "__main__":
    main()
