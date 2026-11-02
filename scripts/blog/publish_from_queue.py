#!/usr/bin/env python3
"""Publish the next pre-written post from blog-queue/ (one per run).

The daily-blog workflow calls this before the AI generator. If the queue has a
post, it is published for today's date and the generator is skipped; when the
queue is empty (exit 3) the workflow falls back to generating a post as before.

Queue layout (blog-queue/ is excluded from deploys in .vercelignore):
  blog-queue/NN-<slug>.json        render_post payload; lowest NN publishes first
  blog-queue/images/<file>.jpg     moved to optimized/ when its post publishes

At publish time, links to /blog/<slug> posts that are not live yet are removed
(a "Related guides" item that is only such a link is dropped entirely), so a
queued post never ships a link that 404s.

Exit codes: 0 published, 3 queue empty, 1 the head post failed the editorial
guard (it stays in the queue; the workflow falls back to the generator).

  python3 scripts/blog/publish_from_queue.py --date 2026-11-03 [--dry-run]
"""
import argparse, datetime as dt, json, pathlib, re, shutil, sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
QUEUE = ROOT / "blog-queue"
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "scripts" / "blog"))


def next_item():
    items = sorted(p for p in QUEUE.glob("*.json") if re.match(r"\d+-", p.name))
    return items[0] if items else None


def drop_unpublished_links(body: str, own_slug: str, live: set) -> str:
    def dead(slug):
        return slug != own_slug and slug not in live
    # whole list item that is nothing but a dead link
    body = re.sub(r'<li>\s*<a href="/blog/([a-z0-9-]+)">.*?</a>\s*</li>\s*',
                  lambda m: "" if dead(m.group(1)) else m.group(0), body, flags=re.S)
    # inline dead links -> plain text
    body = re.sub(r'<a href="/blog/([a-z0-9-]+)">(.*?)</a>',
                  lambda m: m.group(2) if dead(m.group(1)) else m.group(0), body, flags=re.S)
    # a list emptied by the above
    return re.sub(r"<ul>\s*</ul>\s*", "", body)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--date", help="YYYY-MM-DD (default: today)")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    item = next_item()
    if not item:
        print("publish_from_queue: queue empty")
        return 3
    payload = json.loads(item.read_text(encoding="utf-8"))
    payload.pop("source_url", None)
    slug = payload["slug"]
    date = dt.date.fromisoformat(a.date) if a.date else dt.date.today()
    payload["date"] = date.isoformat()
    payload["dateLabel"] = date.strftime("%B %-d, %Y")

    manifest = json.loads((ROOT / "blog" / "posts.json").read_text(encoding="utf-8"))
    live = {p["slug"] for p in manifest["posts"]}
    if slug in live:
        print(f"publish_from_queue: {slug} is already live; removing it from the queue", file=sys.stderr)
        if not a.dry_run:
            item.unlink()
        return 1
    payload["body_html"] = drop_unpublished_links(payload["body_html"], slug, live)

    import editorial_guard as guard
    from render_post import write_post
    problems = (guard.check_references(payload.get("references"), payload["category"])
                + guard.check_reviewer(slug, payload["category"], guard.load_registry()))
    if problems:
        print(f"publish_from_queue: BLOCKED {slug}:", *problems, sep="\n  - ", file=sys.stderr)
        return 1

    images = sorted((QUEUE / "images").glob(f"blog-{slug}-*")) if (QUEUE / "images").exists() else []
    if a.dry_run:
        print(json.dumps({"dry_run": True, "slug": slug, "date": payload["date"],
                          "images": [p.name for p in images]}, indent=2))
        return 0
    for img in images:
        shutil.move(str(img), str(ROOT / "optimized" / img.name))
    path = write_post(payload)
    item.unlink()
    print(json.dumps({"ok": True, "path": str(path.relative_to(ROOT)), "slug": slug,
                      "title": payload["title"], "remaining": len(list(QUEUE.glob('[0-9]*-*.json')))}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
