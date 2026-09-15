#!/usr/bin/env python3
"""
build_skills_index.py — generate /.well-known/agent-skills/index.json.

Agent Skills Discovery RFC v0.2.0. Each entry carries a sha256 digest of the
SKILL.md it points at, so a client can verify it fetched the document the
index described.

That digest is exactly why this file is generated and never hand-edited: the
moment someone fixes a typo in a SKILL.md, a hand-maintained digest is wrong,
and a wrong digest is worse than none — it tells a careful client the document
has been tampered with.

Discovery is by directory: any .well-known/agent-skills/<name>/SKILL.md is
picked up. Adding a skill means adding a folder, not editing JSON.

Usage:
  python3 scripts/agent-files/build_skills_index.py           # write
  python3 scripts/agent-files/build_skills_index.py --check   # CI: fail if stale
"""
import argparse
import hashlib
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / ".well-known" / "agent-skills"
INDEX = SKILLS_DIR / "index.json"
BASE = "https://www.directcare.ai"
SCHEMA = "https://schemas.agentskills.io/discovery/0.2.0/schema.json"

# RFC: lowercase alphanumeric and hyphens.
NAME_RE = re.compile(r"^[a-z0-9-]+$")


def front_matter(text: str) -> dict:
    """Parse the leading --- block. Enough for name/description; not a YAML parser."""
    m = re.match(r"---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return {}
    out = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def collect():
    skills = []
    problems = []
    for d in sorted(p for p in SKILLS_DIR.iterdir() if p.is_dir()):
        f = d / "SKILL.md"
        if not f.is_file():
            problems.append(f"{d.name}/ has no SKILL.md")
            continue
        raw = f.read_bytes()
        fm = front_matter(raw.decode("utf-8", "replace"))
        name = fm.get("name") or d.name
        desc = fm.get("description", "").strip()
        if not NAME_RE.match(name):
            problems.append(f"{d.name}: name '{name}' is not lowercase alphanumeric/hyphen")
        if name != d.name:
            problems.append(f"{d.name}: front-matter name '{name}' does not match the directory")
        if not desc:
            problems.append(f"{d.name}: no description in front matter")
        skills.append({
            "name": name,
            "type": "skill-md",
            "description": desc,
            "url": f"{BASE}/.well-known/agent-skills/{d.name}/SKILL.md",
            # Digest is over the raw bytes of the artifact, per the RFC.
            "digest": "sha256:" + hashlib.sha256(raw).hexdigest(),
        })
    return skills, problems


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="exit 1 if the index is missing or stale")
    args = ap.parse_args()

    if not SKILLS_DIR.is_dir():
        print(f"! {SKILLS_DIR} does not exist", file=sys.stderr)
        return 2

    skills, problems = collect()
    if problems:
        for p in problems:
            print(f"! {p}", file=sys.stderr)
        return 1
    if not skills:
        print("! no skills found — refusing to write an empty index", file=sys.stderr)
        return 1

    body = json.dumps({"$schema": SCHEMA, "skills": skills}, indent=2) + "\n"

    if args.check:
        if not INDEX.is_file() or INDEX.read_text(encoding="utf-8") != body:
            print("! agent-skills index is stale. Run:\n"
                  "    python3 scripts/agent-files/build_skills_index.py", file=sys.stderr)
            return 1
        print(f"agent-skills index up to date ({len(skills)} skills)")
        return 0

    INDEX.write_text(body, encoding="utf-8")
    print(f"wrote {INDEX.relative_to(ROOT)} — {len(skills)} skills")
    for s in skills:
        print(f"   {s['name']:18s} {s['digest'][:23]}…  {s['description'][:56]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
