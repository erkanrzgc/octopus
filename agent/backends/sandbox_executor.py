"""DockerSandboxExecutor: run_cmd'nin serbest-form shell komutunu İZOLE, AĞI-KAPALI,
atılabilir bir docker konteynerinde GERÇEKTEN çalıştırır (MockExecutor'ın gerçek karşılığı).

GÜVENLİK (asıl sınır = konteyner):
- `--network none` (egress yok: exfil/callback engellenir), `--rm` (efemer),
  kaynak sınırları (memory/pids/cpus → fork-bomb/DoS), `-u 65534` (root değil),
  `--read-only` + tmpfs /work (imaja kalıcı yazma yok), `--cap-drop ALL` +
  `no-new-privileges`, subprocess timeout. Host bind-mount YOK → konteyner host FS'i görmez.
- Komut `sh -c <sarmalanmış>` ile TEK argv elemanı geçer → HOST shell'i yorumlamaz
  (shell metakarakteri host'a sızmaz); yorum yalnız konteyner içindeki sh'de olur.
- Çıktı konteyner içinde `head -c` ile kırpılır → sınırsız-stdout host-DoS'u kapatır.
- Timeout'ta konteyner best-effort `docker kill` edilir → yetim-konteyner sızıntısı kapanır.
- Savunma-derinliği: `agent/guards/cmd.py` denylist docker'a gitmeden ÖNCE bakar.

Varsayılan DEĞİL: opt-in (cli.py --real-cmd). Docker Desktop (Windows PATH'te `docker`)
gerekir; `docker_prefix` enjekte edilebilir (WSL yönlendirme / test)."""
from __future__ import annotations

import subprocess
import uuid
from collections.abc import Callable
from dataclasses import dataclass, field

from agent.guards.cmd import guard

_DEFAULT_TIMEOUT = 60
_DEFAULT_IMAGE = "alpine"
_MAX_OUTPUT = 1_000_000  # host'a dönecek çıktı tavanı (bayt) — sınırsız-stdout DoS'a karşı

# Konteyner sertleştirme bayrakları (asıl güvenlik sınırı).
_HARDENING: tuple[str, ...] = (
    "--rm",
    "--network", "none",
    "--memory", "512m",
    "--pids-limit", "256",
    "--cpus", "1",
    "-u", "65534:65534",
    "--read-only",
    "--tmpfs", "/work:rw,size=64m",
    "-w", "/work",
    "--cap-drop", "ALL",
    "--security-opt", "no-new-privileges",
)


def _wrap(komut: str) -> str:
    """Komutu alt-kabukta sarmala + çıktıyı (stdout+stderr) konteyner içinde kırp.
    Alt-kabuk `( ... )` metakarakterlere `{ ...; }`'den toleranslı (';;' hatası yok)."""
    return f"( {komut} ) 2>&1 | head -c {_MAX_OUTPUT}"


def build_argv(komut: str, image: str = _DEFAULT_IMAGE,
               docker_prefix: list[str] | None = None,
               name: str | None = None) -> list[str]:
    """`docker run <sertleştirme> <image> sh -c <sarmalanmış-komut>` argv'si. Sarmalanmış
    komut TEK eleman (host shell yorumlamaz). docker_prefix varsayılan ['docker']."""
    prefix = docker_prefix if docker_prefix is not None else ["docker"]
    name_flag = ["--name", name] if name else []
    return [*prefix, "run", *name_flag, *_HARDENING, image, "sh", "-c", _wrap(komut)]


@dataclass
class DockerSandboxExecutor:
    """Executor protokolü (run(tool, params) -> str). Yalnız run_cmd'yi çalıştırır."""

    image: str = _DEFAULT_IMAGE
    timeout: int = _DEFAULT_TIMEOUT
    docker_prefix: list[str] = field(default_factory=lambda: ["docker"])
    runner: Callable[..., subprocess.CompletedProcess] = subprocess.run

    def run(self, tool: str, params: dict) -> str:
        if tool != "run_cmd":
            return f"HATA: sandbox yalnizca run_cmd calistirir ('{tool}' desteklenmiyor)"
        dec = guard(params)  # savunma-derinligi: yikici desen -> docker'a gitmeden ret
        if not dec.allowed:
            return f"HATA: {dec.reason}"
        komut = str(params["komut"])
        name = f"octopus-sbx-{uuid.uuid4().hex[:12]}"
        argv = build_argv(komut, self.image, self.docker_prefix, name)
        try:
            proc = self.runner(argv, capture_output=True, text=True, timeout=self.timeout)
        except subprocess.TimeoutExpired:
            self._kill(name)  # yetim konteyneri temizle (best-effort)
            return f"HATA: komut zaman asimi ({self.timeout}s)"
        except FileNotFoundError:
            return "HATA: docker bulunamadi (Docker Desktop calisiyor mu?)"
        out = (proc.stdout or "") + (proc.stderr or "")
        return out.strip() or f"(cikti yok, exit={proc.returncode})"

    def _kill(self, name: str) -> None:
        """Timeout sonrası asili konteyneri sil — best-effort, hatayi yut."""
        try:
            self.runner([*self.docker_prefix, "kill", name],
                        capture_output=True, text=True, timeout=10)
        except Exception:  # noqa: BLE001 — temizlik asla ana akisi bozmamali
            pass
