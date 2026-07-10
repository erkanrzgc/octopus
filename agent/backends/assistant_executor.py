"""Asistan araclari (file/web/cmd) executor'i. Dosya islemleri workspace_root altinda;
run_cmd HOST'a DEGIL enjekte sandbox'a delege (guvenlik siniri sandbox'ta); web enjekte
istemci/backend ile (varsayilan urllib, test'te sahte)."""
from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from agent.executor import MockExecutor


def _default_http_get(url: str) -> str:
    import urllib.request
    with urllib.request.urlopen(url, timeout=15) as r:  # noqa: S310 - SSRF guard'i policy'de
        return r.read(200_000).decode("utf-8", "replace")


def _default_search(sorgu: str) -> str:
    return f"[web_search backend tanimsiz] sorgu: {sorgu}"


class AssistantExecutor:
    def __init__(self, workspace_root: str, sandbox=None,
                 http_get: Callable[[str], str] | None = None,
                 search: Callable[[str], str] | None = None) -> None:
        self.root = Path(workspace_root).resolve()
        self.sandbox = sandbox or MockExecutor()
        self.http_get = http_get or _default_http_get
        self.search = search or _default_search

    def _path(self, yol: str) -> Path:
        p = Path(yol)
        return p.resolve() if p.is_absolute() else (self.root / p).resolve()

    def run(self, tool: str, params: dict) -> str:
        try:
            if tool == "read_file":
                return self._path(params["yol"]).read_text(encoding="utf-8")
            if tool == "write_file":
                p = self._path(params["yol"])
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_text(params.get("icerik", ""), encoding="utf-8")
                return f"yazildi: {params['yol']} ({len(params.get('icerik', ''))} bayt)"
            if tool == "edit_file":
                p = self._path(params["yol"])
                text = p.read_text(encoding="utf-8")
                eski = params["eski"]
                if eski not in text:
                    return f"HATA: '{eski}' bulunamadi"
                p.write_text(text.replace(eski, params["yeni"]), encoding="utf-8")
                return f"duzenlendi: {params['yol']}"
            if tool == "list_dir":
                p = self._path(params.get("yol", "."))
                return "\n".join(sorted(c.name + ("/" if c.is_dir() else "")
                                        for c in p.iterdir())) or "(bos)"
            if tool == "grep":
                p = self._path(params.get("yol", "."))
                desen = params["desen"]
                hits = []
                files = p.rglob("*") if p.is_dir() else [p]
                for f in files:
                    if not f.is_file():
                        continue
                    try:
                        for i, line in enumerate(
                                f.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
                            if desen in line:
                                hits.append(f"{f.relative_to(self.root)}:{i}: {line.strip()}")
                    except OSError:
                        continue
                return "\n".join(hits) or f"(eslesme yok: {desen})"
            if tool == "run_cmd":
                return self.sandbox.run("run_cmd", params)   # HOST'a DEGIL sandbox'a
            if tool == "web_fetch":
                return self.http_get(params["url"])
            if tool == "web_search":
                return self.search(params["sorgu"])
        except KeyError as e:
            return f"HATA: eksik parametre {e}"
        except OSError as e:
            return f"HATA: {type(e).__name__}: {e}"
        return f"HATA: bilinmeyen asistan araci '{tool}'"
