"""DockerExecutor: araci lab docker aginda CONTAINER olarak calistirir (Model B).

NEDEN: kali-linux ve docker-desktop AYRI WSL2 distro'lari -> Kali, docker hedef agina
route edemez. Cozum: araci da hedefle AYNI docker aginda container koştur -> DNS adiyla
erisir. (RealExecutor Kali-WSL yolu; bu docker-lab yolu -> erisilebilir savunmasiz hedefler.)

GUVENLIK: Policy kapisi registry.invoke'da ONCE gecer. Komut argv (shell=False); 'secenekler'
shlex ile token -> shell metakarakteri literal arg. Imaj entrypoint'i = arac (instrumentisto/nmap
gibi) -> arg olarak yalniz bayrak+hedef verilir."""
from __future__ import annotations
import shlex
import subprocess
from dataclasses import dataclass, field
from agent.catalog import get_spec, target_value

_DEFAULT_TIMEOUT = 180
_DEFAULT_NETWORK = "octopus-lab"

# Arac -> docker imaji (entrypoint = arac). Genisletilir; haritada olmayan icin
# ileride tek kali-tools imaji (kali-linux-default) fallback'i eklenecek.
TOOL_IMAGES: dict[str, str] = {
    "nmap": "instrumentisto/nmap",
}


def build_argv(tool: str, params: dict, network: str = _DEFAULT_NETWORK,
               distro: str = "kali-linux", images: dict[str, str] | None = None) -> list[str] | None:
    """docker-lab argv: wsl.exe -d <distro> -- docker run --rm --network <net> <image> <flags...> [target].
    Imaj tanimli degilse None (run() 'imaj yok' doner)."""
    images = images if images is not None else TOOL_IMAGES
    image = images.get(tool)
    if image is None:
        return None
    flag_args = shlex.split(str(params.get("secenekler", "") or ""))
    argv = ["wsl.exe", "-d", distro, "--", "docker", "run", "--rm", "--network", network,
            image, *flag_args]
    target = target_value(params)
    if target is not None:
        argv.append(target)
    return argv


@dataclass
class DockerExecutor:
    network: str = _DEFAULT_NETWORK
    distro: str = "kali-linux"
    timeout: int = _DEFAULT_TIMEOUT
    images: dict[str, str] = field(default_factory=lambda: dict(TOOL_IMAGES))

    def run(self, tool: str, params: dict) -> str:
        if get_spec(tool) is None:
            return f"HATA: bilinmeyen arac '{tool}'"
        argv = build_argv(tool, params, self.network, self.distro, self.images)
        if argv is None:
            return f"HATA: '{tool}' icin docker imaji tanimli degil (kali-tools imaji ileride)"
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            return f"HATA: '{tool}' zaman asimi ({self.timeout}s)"
        except FileNotFoundError:
            return "HATA: wsl.exe bulunamadi (WSL kurulu mu?)"
        out = (proc.stdout or "") + (proc.stderr or "")
        return out.strip() or f"({tool} cikti uretmedi, exit={proc.returncode})"
