"""Runtime skill katmani: model bir aracı KULLANMADAN once dogru kullanimini
okur (post-call correction). Uc aile: arac skilleri, is-akisi skilleri, metodoloji
skilleri. SAF/IO-ince: yalniz dosya oku; asla dongude exception firlatma."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import yaml

# Skill kaynaklari (repo koku'ne gore). Metodoloji dizini NON-RECURSIVE taranir
# (osint/ alt-paketi, AGENTS.md, SOURCE.md, _scope-guard.md haric — frontmatter kapisi).
TOOL_SKILLS_DIR = Path("agent/skills/tools")
WORKFLOW_SKILLS_DIR = Path("agent/skills/workflows")
METHODOLOGY_SKILLS_DIR = Path("rag/knowledge/methodologies")

_FM_DELIM = "---"


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str
    kind: str            # "tool" | "workflow" | "methodology"
    tool: str | None     # arac skilleri icin katalog arac adi; digerlerinde None
    path: str


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Bastaki ---...--- YAML blogunu ayir. Blok yoksa ({}, text). Asla cokmez."""
    t = text or ""
    if not t.lstrip().startswith(_FM_DELIM):
        return {}, t
    # ilk satir --- ; kapanis --- 'e kadar
    lines = t.splitlines()
    # bastaki bos satirlari atla
    start = 0
    while start < len(lines) and not lines[start].strip():
        start += 1
    if start >= len(lines) or lines[start].strip() != _FM_DELIM:
        return {}, t
    end = None
    for i in range(start + 1, len(lines)):
        if lines[i].strip() == _FM_DELIM:
            end = i
            break
    if end is None:
        return {}, t
    fm_text = "\n".join(lines[start + 1:end])
    body = "\n".join(lines[end + 1:])
    try:
        meta = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError:
        return {}, t
    if not isinstance(meta, dict):
        return {}, t
    return meta, body


def _load_dir(directory: Path, kind: str, *, recursive: bool) -> dict[str, Skill]:
    """Dizindeki *.md dosyalarindan frontmatter'i name+description olanlari Skill yap.
    recursive=False -> yalniz o dizin (alt-paketler haric). IO hatasi -> o dosyayi atla."""
    out: dict[str, Skill] = {}
    if not directory.is_dir():
        return out
    paths = directory.rglob("*.md") if recursive else directory.glob("*.md")
    for p in sorted(paths):
        try:
            text = p.read_text(encoding="utf-8")
        except OSError:
            continue
        meta, body = parse_frontmatter(text)
        name = meta.get("name")
        desc = meta.get("description")
        if not name or not desc:
            continue
        tool = meta.get("tool", name) if kind == "tool" else None
        key = str(tool) if kind == "tool" else str(name)
        out[key] = Skill(
            name=str(name), description=str(desc).strip(), body=body.strip(),
            kind=kind, tool=(str(tool) if tool is not None else None), path=str(p),
        )
    return out


@dataclass
class SkillLibrary:
    tools: dict[str, Skill] = field(default_factory=dict)
    workflows: dict[str, Skill] = field(default_factory=dict)
    methodologies: dict[str, Skill] = field(default_factory=dict)

    @classmethod
    def load(cls, root: Path = Path(".")) -> "SkillLibrary":
        root = Path(root)
        return cls(
            tools=_load_dir(root / TOOL_SKILLS_DIR, "tool", recursive=False),
            workflows=_load_dir(root / WORKFLOW_SKILLS_DIR, "workflow", recursive=False),
            methodologies=_load_dir(root / METHODOLOGY_SKILLS_DIR, "methodology", recursive=False),
        )

    def match_tool(self, tool_name: str) -> Skill | None:
        return self.tools.get(tool_name)

    def get(self, name: str) -> Skill | None:
        for table in (self.tools, self.workflows, self.methodologies):
            for s in table.values():
                if s.name == name:
                    return s
        return None

    def match(self, query: str) -> list[Skill]:
        """Basit anahtar-kelime ortusmesi (embedding YAGNI). workflow+methodology uzerinde."""
        terms = {w for w in (query or "").lower().split() if len(w) > 2}
        if not terms:
            return []
        scored: list[tuple[int, Skill]] = []
        for table in (self.workflows, self.methodologies):
            for s in table.values():
                hay = f"{s.name} {s.description}".lower()
                score = sum(1 for t in terms if t in hay)
                if score:
                    scored.append((score, s))
        scored.sort(key=lambda x: (-x[0], x[1].name))
        return [s for _, s in scored]

    def manifest_text(self, kinds: tuple[str, ...] = ("tool", "workflow", "methodology")) -> str:
        """Kompakt kesif manifesti: her skill icin 'name — description' satiri."""
        tables = {"tool": self.tools, "workflow": self.workflows, "methodology": self.methodologies}
        lines: list[str] = []
        for k in kinds:
            for s in tables.get(k, {}).values():
                lines.append(f"- {s.name} — {s.description}")
        return "\n".join(lines)

    def tool_skill_injection(self, skill: Skill) -> str:
        """Harness'in modele enjekte ettigi 'once oku' kilavuz metni (user turu)."""
        return (
            f"ARAÇ KILAVUZU — {skill.name}: bu aracı çalıştırmadan önce doğru kullanımını oku, "
            f"gerekiyorsa ```arac``` bloğunu düzelt, sonra tekrar çağır.\n\n{skill.body}"
        )
