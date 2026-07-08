"""RealExecutor: araci Kali WSL'de GERCEKTEN calistirir (Faz 2).

GUVENLIK:
- Policy kapisi registry.invoke'da ONCEDEN gecer (scope + risk). Burada ek koruma:
  katalog-disi arac reddi + timeout.
- Komut **argv listesi** olarak kurulur (shell=False). Model'in 'secenekler' dizisi
  shlex ile token'lara ayrilir -> shell metakarakteri (;, |, &&) LITERAL arg olur,
  shell yorumlamaz. Enjeksiyon yuzeyi kapali.
- Yalnizca Kali WSL icinde calisir (yerel Windows'ta degil)."""
from __future__ import annotations
import shlex
import subprocess
from dataclasses import dataclass
from agent.catalog import get_spec, target_value

_DEFAULT_TIMEOUT = 120


def build_argv(tool: str, params: dict, distro: str = "kali-linux") -> list[str]:
    """Kali WSL argv: wsl.exe -d <distro> -- <tool> <flags...> [target].
    'secenekler' shlex ile ayrilir (shell YOK -> literal token)."""
    flag_args = shlex.split(str(params.get("secenekler", "") or ""))
    argv = ["wsl.exe", "-d", distro, "--", tool, *flag_args]
    target = target_value(params)
    if target is not None:
        argv.append(target)
    return argv


@dataclass
class RealExecutor:
    distro: str = "kali-linux"
    timeout: int = _DEFAULT_TIMEOUT

    def run(self, tool: str, params: dict) -> str:
        if get_spec(tool) is None:
            return f"HATA: bilinmeyen arac '{tool}'"
        argv = build_argv(tool, params, self.distro)
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            return f"HATA: '{tool}' zaman asimi ({self.timeout}s)"
        except FileNotFoundError:
            return "HATA: wsl.exe bulunamadi (WSL kurulu mu?)"
        out = (proc.stdout or "") + (proc.stderr or "")
        return out.strip() or f"({tool} cikti uretmedi, exit={proc.returncode})"
