#!/usr/bin/env python3
"""Conflict-proof publish for the daily-blog workflow.

Two runs that overlap (or a push that lands mid-run) used to leave conflict markers in blog/posts.json and the
derived files, and the step died on a JSONDecodeError (2026-09-14). This makes the commit deterministic:
  1. capture what THIS run produced: the new post files, its manifest entry, its review record, its used angle
  2. fetch origin/main and hard-reset the working tree to it (untracked new post files survive)
  3. re-apply the captured entry/record/angle on top of origin's versions (idempotent, by slug)
  4. regenerate every derived file (sitemap, blog index, page schema, twins/llms-full)
  5. commit and push; on a rejected push, repeat from 2 (up to 3 times)
Run from the repo root inside the workflow after the generator wrote the post.
"""
import json, os, pathlib, subprocess, sys
ROOT = pathlib.Path(__file__).resolve().parents[2]
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "scripts"))


def sh(*a, check=True):
    r = subprocess.run(a, capture_output=True, text=True)
    if check and r.returncode:
        print(r.stdout, r.stderr, file=sys.stderr)
        raise SystemExit(f"command failed: {' '.join(a)}")
    return r


def load(p):
    return json.loads(pathlib.Path(p).read_text())


def main():
    posts = load("blog/posts.json")["posts"]
    origin_before = json.loads(sh("git", "show", "HEAD:blog/posts.json").stdout)["posts"]
    known = {p["slug"] for p in origin_before}
    new_entries = [p for p in posts if p["slug"] not in known]
    if not new_entries:
        print("publish_merge: no new post in the manifest; nothing to do"); return 0
    reviews = load("blog/reviewers.json").get("reviews", {})
    new_reviews = {p["slug"]: reviews[p["slug"]] for p in new_entries if p["slug"] in reviews}
    used = load("scripts/used_topics.json") if pathlib.Path("scripts/used_topics.json").exists() else []
    used_before = json.loads(sh("git", "show", "HEAD:scripts/used_topics.json").stdout) if sh("git", "cat-file", "-e", "HEAD:scripts/used_topics.json", check=False).returncode == 0 else []
    new_angles = [a for a in used if a not in used_before]
    print(f"publish_merge: new posts {[p['slug'] for p in new_entries]}, reviews {list(new_reviews)}, angles {len(new_angles)}")
    for attempt in range(1, 4):
        sh("git", "fetch", "origin", "main")
        sh("git", "reset", "--hard", "origin/main")          # tracked files back to origin; new post html/md stay (untracked)
        m = load("blog/posts.json"); have = {p["slug"] for p in m["posts"]}
        m["posts"] = [p for p in new_entries if p["slug"] not in have] + m["posts"]
        m["posts"].sort(key=lambda p: p.get("date", ""), reverse=True)
        pathlib.Path("blog/posts.json").write_text(json.dumps(m, indent=2) + "\n")
        rv = load("blog/reviewers.json"); rv.setdefault("reviews", {}).update(new_reviews)
        pathlib.Path("blog/reviewers.json").write_text(json.dumps(rv, indent=2) + "\n")
        if new_angles:
            u = load("scripts/used_topics.json") if pathlib.Path("scripts/used_topics.json").exists() else []
            u += [a for a in new_angles if a not in u]
            pathlib.Path("scripts/used_topics.json").write_text(json.dumps(u, indent=2) + "\n")
        import render_post
        render_post.update_sitemap()
        sh("python3", "scripts/build_blog_index.py")
        sh("python3", "scripts/agent-files/build_page_schema.py", check=False)
        sh("python3", "scripts/agent-files/build_agent_files.py")
        sh("git", "add", "-A", "blog", "sitemap.xml", "llms-full.txt", "scripts/used_topics.json", "scripts/agent-files/generated-files.txt")
        sh("git", "add", "-A", "--", "*.md", check=False)
        title = new_entries[0]["title"]
        if sh("git", "diff", "--cached", "--quiet", check=False).returncode == 0:
            print("publish_merge: nothing to commit"); return 0
        sh("git", "commit", "-m", f"blog: {title}", "-m", "Auto-published by the daily-blog GitHub Action.")
        r = sh("git", "push", "origin", "main", check=False)
        if r.returncode == 0:
            print(f"Published: {new_entries[0]['slug']}")
            gh = os.environ.get("GITHUB_OUTPUT")
            if gh:
                open(gh, "a").write(f"deployed_slug={new_entries[0]['slug']}\n")
            return 0
        print(f"publish_merge: push rejected (attempt {attempt}); re-merging on the newer origin", file=sys.stderr)
    raise SystemExit("publish_merge: gave up after 3 attempts")


if __name__ == "__main__":
    sys.exit(main())
