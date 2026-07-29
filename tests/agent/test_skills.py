from pathlib import Path
from agent.skills import parse_frontmatter, Skill, SkillLibrary


def test_parse_frontmatter_extracts_meta_and_body():
    text = "---\nname: nmap\ndescription: port tarayici\ntool: nmap\n---\n\nGovde metni.\n"
    meta, body = parse_frontmatter(text)
    assert meta["name"] == "nmap"
    assert meta["description"] == "port tarayici"
    assert meta["tool"] == "nmap"
    assert body.strip() == "Govde metni."


def test_parse_frontmatter_no_frontmatter_returns_empty_meta():
    meta, body = parse_frontmatter("# Just markdown\nno frontmatter here")
    assert meta == {}
    assert "Just markdown" in body


def test_parse_frontmatter_handles_folded_scalar():
    text = "---\nname: attack-planner\ndescription: >-\n  cok satirli\n  aciklama\n---\nbody"
    meta, _ = parse_frontmatter(text)
    assert meta["name"] == "attack-planner"
    assert "cok satirli" in meta["description"]


def _write(p: Path, name: str, desc: str, body: str = "govde", extra: str = "") -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(f"---\nname: {name}\ndescription: {desc}\n{extra}---\n\n{body}\n", encoding="utf-8")


def test_load_indexes_three_families_and_skips_non_skills(tmp_path):
    _write(tmp_path / "agent/skills/tools/nmap.md", "nmap", "port tarayici", extra="tool: nmap\n")
    _write(tmp_path / "agent/skills/workflows/report-write.md", "report-write", "rapor yaz")
    _write(tmp_path / "rag/knowledge/methodologies/recon-advisor.md", "recon-advisor", "kesif")
    # frontmatter'siz dosya -> skill DEGIL
    (tmp_path / "rag/knowledge/methodologies/AGENTS.md").write_text("# index\nno fm", encoding="utf-8")
    # alt-dizin (osint/) -> metodoloji non-recursive oldugu icin ALINMAZ
    _write(tmp_path / "rag/knowledge/methodologies/osint/core__SKILL.md", "core", "engine")

    lib = SkillLibrary.load(root=tmp_path)
    assert "nmap" in lib.tools
    assert "report-write" in lib.workflows
    assert "recon-advisor" in lib.methodologies
    assert "core" not in lib.methodologies          # osint/ alt-paketi haric
    assert all("AGENTS" not in n for n in lib.methodologies)


def test_match_tool_and_get(tmp_path):
    _write(tmp_path / "agent/skills/tools/sqlmap.md", "sqlmap", "sqli otomasyonu", extra="tool: sqlmap\n")
    lib = SkillLibrary.load(root=tmp_path)
    assert lib.match_tool("sqlmap").name == "sqlmap"
    assert lib.match_tool("bilinmeyen") is None
    assert lib.get("sqlmap").kind == "tool"


def test_match_ranks_by_keyword_overlap(tmp_path):
    _write(tmp_path / "agent/skills/workflows/report-write.md", "report-write", "bulguyu rapora cevir")
    _write(tmp_path / "rag/knowledge/methodologies/recon-advisor.md", "recon-advisor", "kesif ve varlik")
    lib = SkillLibrary.load(root=tmp_path)
    hits = lib.match("rapor yazma")
    assert hits and hits[0].name == "report-write"


def test_manifest_text_lists_name_and_description(tmp_path):
    _write(tmp_path / "agent/skills/tools/nmap.md", "nmap", "port tarayici", extra="tool: nmap\n")
    lib = SkillLibrary.load(root=tmp_path)
    m = lib.manifest_text()
    assert "nmap" in m and "port tarayici" in m


def test_load_missing_dirs_is_empty_not_error(tmp_path):
    lib = SkillLibrary.load(root=tmp_path)   # hic dosya yok
    assert lib.tools == {} and lib.workflows == {} and lib.methodologies == {}


def test_manifest_text_ignores_unknown_kind():
    # bilinmeyen kind KeyError firlatMAmali (asla-cokme sozlesmesi)
    lib = SkillLibrary()
    assert lib.manifest_text(kinds=("tool", "bogus")) == ""
