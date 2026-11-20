#!/usr/bin/env python3
"""Validate an agent-architect blueprint and/or the agent and skill files in a project.

Usage:
  python3 validate.py --blueprint PATH      # check the design, print its summary
  python3 validate.py --out PROJECT_DIR     # check rendered (or hand-written) files
  add --strict to treat warnings as errors

Works on any project, not only rendered ones, so it doubles as an audit tool.
Exit code 1 when errors are found.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tomllib
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from blueprint_lib import (  # noqa: E402
    LIMITS,
    NAME_RE,
    BlueprintError,
    check_blueprint,
    load_blueprint,
    summary,
    yaml,
)

SKILL_DIRS = ["skills", ".agents/skills", ".claude/skills", ".github/skills", ".gemini/skills", ".cursor/skills", ".opencode/skills", ".codex/skills"]
MD_AGENT_DIRS = {".claude/agents": True, ".github/agents": False, ".gemini/agents": True, ".cursor/agents": True, ".opencode/agents": False}
LINK_RE = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")


def split_frontmatter(text: str) -> tuple[dict | None, str, str | None]:
    if not text.startswith("---"):
        return None, text, "missing YAML frontmatter"
    parts = text.split("\n---", 1)
    if len(parts) < 2:
        return None, text, "frontmatter is not closed with ---"
    raw = parts[0][3:]
    body = parts[1].split("\n", 1)[1] if "\n" in parts[1] else ""
    if yaml is not None:
        try:
            data = yaml.safe_load(raw) or {}
        except yaml.YAMLError as exc:
            return None, body, f"invalid YAML frontmatter: {exc}"
    else:  # minimal fallback: top-level scalars only
        data = {}
        for line in raw.splitlines():
            m = re.match(r"^([A-Za-z0-9_-]+):\s*(.*)$", line)
            if m:
                data[m.group(1)] = m.group(2).strip().strip('"')
    if not isinstance(data, dict):
        return None, body, "frontmatter must be a mapping"
    return data, body, None


class Report:
    def __init__(self) -> None:
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def err(self, where, msg):
        self.errors.append(f"{where}: {msg}")

    def warn(self, where, msg):
        self.warnings.append(f"{where}: {msg}")


def check_skill(skill_dir: Path, root: Path, rep: Report) -> str | None:
    where = str(skill_dir.relative_to(root))
    sk = skill_dir / "SKILL.md"
    if not sk.is_file():
        rep.err(where, "no SKILL.md")
        return None
    text = sk.read_text(encoding="utf-8", errors="replace")
    fm, body, problem = split_frontmatter(text)
    if problem:
        rep.err(where, problem)
        return None
    name, desc = fm.get("name"), fm.get("description")
    if not name:
        rep.err(where, "frontmatter needs 'name'")
    elif not NAME_RE.match(str(name)) or len(str(name)) > 64:
        rep.err(where, f"name '{name}' must be kebab-case, max 64 chars")
    elif name != skill_dir.name:
        rep.err(where, f"name '{name}' must match its folder name '{skill_dir.name}'")
    if not desc:
        rep.err(where, "frontmatter needs 'description'")
    elif len(str(desc)) > LIMITS["description_chars"]:
        rep.err(where, f"description is {len(str(desc))} chars (max 1024)")
    n = len(body.strip().splitlines())
    if n > LIMITS["skill_body_lines_hard"]:
        rep.err(where, f"SKILL.md body is {n} lines (max 500)")
    elif n > LIMITS["skill_body_lines"]:
        rep.warn(where, f"SKILL.md body is {n} lines; aim for under 200 and move detail to references/")
    linked = set()
    for target in LINK_RE.findall(body):
        if re.match(r"^[a-z]+:", target):
            continue
        p = (skill_dir / target).resolve()
        if not p.exists():
            rep.err(where, f"links to missing file '{target}'")
        else:
            linked.add(p)
    for ref in sorted(skill_dir.rglob("*.md")):
        if ref.name == "SKILL.md":
            continue
        rel = ref.relative_to(skill_dir)
        ref_text = ref.read_text(encoding="utf-8", errors="replace")
        lines = len(ref_text.splitlines())
        if lines > LIMITS["reference_lines"] and "contents" not in ref_text[:600].lower():
            rep.warn(where, f"{rel} is {lines} lines; add a Contents list at the top")
        if ref.resolve() not in linked and rel.parts[0] == "references":
            rep.warn(where, f"{rel} is not linked from SKILL.md, so agents will not know to read it")
        for target in LINK_RE.findall(ref_text):
            if target.endswith(".md") and not re.match(r"^[a-z]+:", target):
                rep.warn(where, f"{rel} links to {target}; keep references one level deep")
                break
    return str(name) if name else None


def check_md_agent(path: Path, root: Path, needs_name: bool, rep: Report) -> None:
    where = str(path.relative_to(root))
    text = path.read_text(encoding="utf-8", errors="replace")
    fm, body, problem = split_frontmatter(text)
    if problem:
        rep.err(where, problem)
        return
    if needs_name and not fm.get("name"):
        rep.err(where, "frontmatter needs 'name'")
    if not fm.get("description"):
        rep.err(where, "frontmatter needs 'description' (it decides when the agent is used)")
    elif len(str(fm["description"])) > LIMITS["description_chars"]:
        rep.warn(where, "description is over 1024 chars")
    if not body.strip():
        rep.err(where, "empty prompt body; some harnesses silently ignore the agent")
    if len(body) > LIMITS["agent_body_chars_hard"]:
        rep.err(where, f"prompt body is {len(body)} chars (Copilot CLI max 30,000)")
    elif len(body.strip().splitlines()) > LIMITS["agent_prompt_lines"] + 25:
        rep.warn(where, f"prompt is {len(body.strip().splitlines())} lines; move knowledge into a skill")


def check_toml_agent(path: Path, root: Path, rep: Report) -> None:
    where = str(path.relative_to(root))
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        rep.err(where, f"invalid TOML: {exc}")
        return
    for key in ("name", "description", "developer_instructions"):
        if not str(data.get(key, "")).strip():
            rep.err(where, f"missing required '{key}'")


def same_tree(a: Path, b: Path) -> bool:
    """True when two skill folders hold the same files with the same bytes (e.g. --no-symlinks copies)."""
    def files(base: Path) -> dict[str, bytes]:
        return {str(f.relative_to(base)): f.read_bytes() for f in sorted(base.rglob("*")) if f.is_file()}
    return files(a) == files(b)


def check_project(root: Path, rep: Report) -> int:
    count = 0
    seen: dict[str, Path] = {}
    for d in SKILL_DIRS:
        base = root / d
        if not base.is_dir():
            continue
        for skill_dir in sorted(p for p in base.iterdir() if p.is_dir()):
            if not (skill_dir / "SKILL.md").exists():
                continue
            count += 1
            name = check_skill(skill_dir, root, rep)
            if name:
                real = skill_dir.resolve()
                if name in seen and seen[name] != real and not same_tree(seen[name], real):
                    rep.warn(str(skill_dir.relative_to(root)), f"skill '{name}' also exists at {seen[name].relative_to(root.resolve())} with different content")
                seen.setdefault(name, real)
    for d, needs_name in MD_AGENT_DIRS.items():
        base = root / d
        if not base.is_dir():
            continue
        for f in sorted(base.rglob("*.md")):
            count += 1
            if f.parent != base and d == ".cursor/agents":
                rep.warn(str(f.relative_to(root)), "Markdown nested under .cursor/agents is loaded as an agent; move reference docs into a skill")
            check_md_agent(f, root, needs_name, rep)
    codex = root / ".codex/agents"
    if codex.is_dir():
        for f in sorted(codex.glob("*.toml")):
            count += 1
            check_toml_agent(f, root, rep)
    return count


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--blueprint")
    ap.add_argument("--out")
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args(argv)
    if not args.blueprint and not args.out:
        ap.error("give --blueprint, --out, or both")

    rep = Report()
    if args.blueprint:
        try:
            bp = load_blueprint(args.blueprint)
        except (BlueprintError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 2
        errors, warnings = check_blueprint(bp)
        rep.errors += [f"blueprint: {e}" for e in errors]
        rep.warnings += [f"blueprint: {w}" for w in warnings]
        print(summary(bp))
        print()
    if args.out:
        root = Path(args.out)
        n = check_project(root, rep)
        print(f"Checked {n} agent and skill files under {os.path.abspath(root)}.")

    for w in rep.warnings:
        print(f"warning: {w}")
    for e in rep.errors:
        print(f"error: {e}")
    failed = bool(rep.errors) or (args.strict and bool(rep.warnings))
    print(f"\n{len(rep.errors)} error(s), {len(rep.warnings)} warning(s).")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
