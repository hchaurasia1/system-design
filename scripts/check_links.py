#!/usr/bin/env python3
"""Check that every relative link and #anchor in the repo's markdown files resolves.

Usage: python3 scripts/check_links.py [repo_root]
Exits non-zero if any link is broken.
"""
import re
import sys
from pathlib import Path

LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")


def github_slug(text: str) -> str:
    # Mirrors GitHub's anchor generation: lowercase, drop punctuation, spaces -> hyphens.
    # Hyphens are NOT collapsed, so "A — B" becomes "a--b".
    text = re.sub(r"`|\*|_(?=\S)|(?<=\S)_", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = text.strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors_for(path: Path) -> set[str]:
    seen: dict[str, int] = {}
    anchors = set()
    in_fence = False
    for line in path.read_text().splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = HEADING_RE.match(line)
        if not m:
            continue
        slug = github_slug(m.group(2))
        count = seen.get(slug, 0)
        anchors.add(slug if count == 0 else f"{slug}-{count}")
        seen[slug] = count + 1
    return anchors


def links_in(path: Path) -> list[tuple[int, str]]:
    out = []
    in_fence = False
    for lineno, line in enumerate(path.read_text().splitlines(), 1):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        for target in LINK_RE.findall(line):
            if not re.match(r"^[a-z]+:", target):
                out.append((lineno, target))
    return out


def main() -> int:
    root = Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve()
    files = sorted(p for p in root.rglob("*.md") if ".git" not in p.parts)
    cache: dict[Path, set[str]] = {}
    broken = []

    for f in files:
        for lineno, target in links_in(f):
            file_part, _, anchor = target.partition("#")
            dest = (f.parent / file_part).resolve() if file_part else f
            if not dest.exists():
                broken.append(f"{f.relative_to(root)}:{lineno}  missing file: {target}")
                continue
            if anchor and dest.suffix == ".md":
                if dest not in cache:
                    cache[dest] = anchors_for(dest)
                if anchor not in cache[dest]:
                    broken.append(f"{f.relative_to(root)}:{lineno}  missing anchor: {target}")

    if broken:
        print("Broken links:")
        print("\n".join(f"  {b}" for b in broken))
        return 1
    print(f"All links OK across {len(files)} file(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
