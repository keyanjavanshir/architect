#!/usr/bin/env python3
"""Find the domain packs that match a request.

Usage:
  python3 find_pack.py "I make aftermovies for events and need help with music"
  python3 find_pack.py "..." --dirs .agent-architect/domains path/to/domain-scout/domains
  add --json for machine-readable output

A pack is a folder with DOMAIN.md (see github.com/keyanjavanshir/domain-scout). Packs are
ranked by how many of their `keywords` appear in the request; multi-word keywords count
more. A project folder can also hold OVERLAY.md, the team's own details for that pack.
Prints nothing and exits 1 when no pack matches.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import yaml

DEFAULT_DIRS = [".agent-architect/domains", ".agent-architect/domain-scout/domains"]


def read_frontmatter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return {}
    head = text.split("\n---", 1)[0][3:]
    try:
        data = yaml.safe_load(head) or {}
    except yaml.YAMLError:
        return {}
    return data if isinstance(data, dict) else {}


def singular(word: str) -> str:
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def normalise(text: str) -> str:
    """Lowercase, keep words only, and make plurals singular, padded for whole-word search."""
    words = re.sub(r"[^a-z0-9]+", " ", text.lower()).split()
    return " " + " ".join(singular(w) for w in words) + " "


def discover(dirs: list[Path]) -> dict[str, dict]:
    """Return packs by name. Earlier dirs win; overlays are found in any dir."""
    packs: dict[str, dict] = {}
    overlays: dict[str, Path] = {}
    for base in dirs:
        if not base.is_dir():
            continue
        for folder in sorted(p for p in base.iterdir() if p.is_dir()):
            domain, overlay = folder / "DOMAIN.md", folder / "OVERLAY.md"
            if overlay.is_file():
                overlays.setdefault(folder.name, overlay)
            if domain.is_file() and folder.name not in packs:
                fm = read_frontmatter(domain)
                packs[folder.name] = {
                    "name": folder.name,
                    "path": str(folder),
                    "title": fm.get("title", folder.name),
                    "status": fm.get("status", "unknown"),
                    "checked": str(fm.get("checked", "")),
                    "keywords": [str(k) for k in fm.get("keywords") or []],
                    "related": list(fm.get("related") or []),
                }
    for name, pack in packs.items():
        pack["overlay"] = str(overlays[name]) if name in overlays else None
    return packs


def score(request: str, pack: dict) -> tuple[int, list[str]]:
    text = normalise(request)
    hits = [k for k in pack["keywords"] if normalise(k) in text]
    return sum(len(k.split()) for k in hits), hits


def rank(request: str, packs: dict[str, dict]) -> list[dict]:
    results = []
    for pack in packs.values():
        points, hits = score(request, pack)
        if points:
            results.append({**pack, "score": points, "matched": hits})
    results.sort(key=lambda p: (-p["score"], p["name"]))
    return results


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("request", help="the user's request, in their words")
    ap.add_argument("--dirs", nargs="+", type=Path, default=[Path(d) for d in DEFAULT_DIRS],
                    help="folders that hold packs, in priority order")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    packs = discover(args.dirs)
    if not packs:
        print("No packs found in: " + ", ".join(map(str, args.dirs)), file=sys.stderr)
        return 1
    results = rank(args.request, packs)
    if args.json:
        print(json.dumps(results, indent=2))
        return 0 if results else 1
    if not results:
        print("No pack matches this request. Continue with the generic interview, or offer domain-scout.",
              file=sys.stderr)
        return 1
    for p in results:
        overlay = f"  overlay: {p['overlay']}" if p["overlay"] else ""
        print(f"- {p['name']}  score {p['score']}  [{p['status']}, checked {p['checked']}]  {p['path']}{overlay}")
        print(f"    matched: {', '.join(p['matched'])}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
