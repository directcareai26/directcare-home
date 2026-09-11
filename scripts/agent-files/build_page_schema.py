#!/usr/bin/env python3
"""
build_page_schema.py — stamp a truthful `dateModified` on every non-blog page.

Blog posts carry datePublished/dateModified/author; the product and service
pages carry none. AI answer engines weight recency heavily, so a page with no
date competes against dated competitors from a standing start.

The hard part is not writing the date, it is making it TRUE.

  A naive `git log -1 <file>` dates the last commit that touched the file at
  all. Site-wide mechanical passes — a logo URL swap, a tracking pixel, an
  aria-hidden sweep — would then stamp every page as freshly updated. That is
  a fabricated freshness signal, and Google names that behaviour in its spam
  policy. It would also be a lie.

  So dateModified here is the date a page's READER-VISIBLE TEXT last changed.
  Markup, scripts, tracking, schema and asset URLs are stripped before
  comparing, so only wording moves the date.

Two properties worth knowing:

  * The walk follows --first-parent. On the full log, content is NOT monotonic
    across a branchy history: this repo has an older commit matching current
    text and a newer one differing, because work landed on side branches.
    Walking the mainline restores the ordering the comparison depends on.
  * Injecting schema does not move the date. The extractor drops <script>
    blocks, and JSON-LD lives in one, so re-running this cannot bump the very
    date it just wrote.

`lastReviewed` and `reviewedBy` are deliberately NOT written. They assert that
a named clinician reviewed the page on a date. That is the strongest possible
signal for medical content and it is the business's claim to make, not this
script's to infer. See the note printed at the end of a run.

Usage:
  python3 scripts/agent-files/build_page_schema.py           # write
  python3 scripts/agent-files/build_page_schema.py --check   # CI: fail if stale
  python3 scripts/agent-files/build_page_schema.py --dry-run
"""
import argparse
import html as _html
import json
import pathlib
import re
import subprocess
import sys
from xml.etree import ElementTree

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = "https://www.directcare.ai"
SITEMAP = ROOT / "sitemap.xml"
MARKER = "dca-page-schema"          # identifies the block we own

_DROP = re.compile(r"<(script|style|svg|noscript|template)\b[^>]*>.*?</\1>", re.S | re.I)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"\s+")


def visible_text(doc: str) -> str:
    """What a reader actually sees. Markup, scripts and attributes removed."""
    s = _COMMENT.sub("", doc)
    s = _DROP.sub("", s)
    s = _TAG.sub(" ", s)
    return _WS.sub(" ", _html.unescape(s)).strip()


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout


def content_changed_on(path: str):
    """Date the page's visible text last changed, and the commit that did it.

    Walks the first-parent mainline newest -> oldest, and returns the OLDEST
    commit still carrying today's text — i.e. the one that introduced it.
    """
    log = [l for l in git("log", "--first-parent", "--format=%H %ad",
                          "--date=short", "--", path).split("\n") if l.strip()]
    revs = [l.split(" ", 1) for l in log]
    if not revs:
        return None, None
    current = None
    introduced = None
    for sha, date in revs:
        blob = git("show", f"{sha}:{path}")
        if not blob:
            break                      # file absent this far back; stop here
        t = visible_text(blob)
        if current is None:
            current = t
        elif t != current:
            break                      # this commit predates the current text
        introduced = (sha, date)
    return (introduced[1], introduced[0][:7]) if introduced else (None, None)


def newest_post_date():
    """Date of the most recent blog post, from the same JSON the page reads."""
    f = ROOT / "blog" / "posts.json"
    try:
        posts = json.loads(f.read_text(encoding="utf-8")).get("posts", [])
        return max((p.get("date", "") for p in posts), default="") or None
    except Exception:
        return None


def sitemap_pages():
    """Non-blog public pages, as (url_path, html_file)."""
    tree = ElementTree.parse(SITEMAP)
    out = []
    seen = set()
    for loc in tree.getroot().iter():
        if not loc.tag.endswith("}loc"):
            continue
        u = (loc.text or "").strip()
        if not u.startswith(BASE):
            continue
        p = u[len(BASE):] or "/"
        segs = [s for s in p.strip("/").split("/") if s]
        if segs and segs[0] == "blog" and len(segs) > 1:
            continue                   # posts already carry their own dates
        rel = p.strip("/")
        cands = [ROOT / "index.html"] if not rel else [ROOT / f"{rel}.html", ROOT / rel / "index.html"]
        f = next((c for c in cands if c.is_file()), None)
        if f and f not in seen:
            seen.add(f)
            out.append((p, f))
    return out


def meta(doc, name):
    m = re.search(r'<meta[^>]+name=["\']%s["\'][^>]*content=["\']([^"\']*)' % name, doc, re.I)
    return _html.unescape(m.group(1)).strip() if m else ""


def block_for(path, doc, date):
    title = re.search(r"<title[^>]*>(.*?)</title>", doc, re.S | re.I)
    node = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": f"{BASE}{path}#webpage",
        "url": f"{BASE}{path}",
        "name": _html.unescape(_WS.sub(" ", title.group(1)).strip()) if title else path,
        "inLanguage": "en-US",
        "dateModified": date,
        # #org is defined by the MedicalOrganization block on all 18 of these
        # pages, so referencing it by @id merges cleanly rather than repeating
        # the organisation on every page.
        #
        # No isPartOf: the only WebSite node in the repo is on the homepage and
        # carries no @id, so pointing at "#website" would be a dangling
        # reference on every page — worse than omitting the property. Give the
        # WebSite node an @id and this is worth adding back.
        "publisher": {"@id": f"{BASE}/#org"},
    }
    desc = meta(doc, "description")
    if desc:
        node["description"] = desc
    return (
        f'<script type="application/ld+json" data-generated-by="{MARKER}">'
        + json.dumps(node, ensure_ascii=False, separators=(",", ":"))
        + "</script>"
    )


_OURS = re.compile(
    r'\n?<script type="application/ld\+json" data-generated-by="%s">.*?</script>' % MARKER,
    re.S,
)


def apply_to(doc: str, block: str):
    doc = _OURS.sub("", doc)                       # replace, never accumulate
    m = re.search(r"</head>", doc, re.I)
    if not m:
        return None
    return doc[: m.start()] + block + "\n" + doc[m.start():]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    pages = sitemap_pages()
    if not pages:
        print("! sitemap yielded no pages", file=sys.stderr)
        return 2

    stale, changed, undated = [], [], []
    print(f"{'page':40s} {'dateModified':13s} source")
    for path, f in pages:
        rel = f.relative_to(ROOT).as_posix()
        if path.strip("/") == "blog":
            # The index builds its grid from posts.json at request time, so its
            # own markup has not changed since July while the page a reader sees
            # changes daily. Dating it by its markup would understate it by
            # months; the newest post is what the page actually shows.
            date, sha = newest_post_date(), "posts.json"
        else:
            date, sha = content_changed_on(rel)
        if not date:
            undated.append(path)
            print(f"{path:40s} {'(no history)':13s} -")
            continue
        doc = f.read_text(encoding="utf-8", errors="surrogateescape")
        out = apply_to(doc, block_for(path, doc, date))
        if out is None:
            print(f"{path:40s} {'(no </head>)':13s} -", file=sys.stderr)
            continue
        print(f"{path:40s} {date:13s} {sha}")
        if out != doc:
            changed.append(rel)
            if args.check:
                stale.append(rel)
            elif not args.dry_run:
                f.write_text(out, encoding="utf-8", errors="surrogateescape")

    if args.check:
        if stale:
            print(f"\n! {len(stale)} page(s) have stale schema. Run:\n"
                  f"    python3 scripts/agent-files/build_page_schema.py", file=sys.stderr)
            for s in stale[:10]:
                print(f"    - {s}", file=sys.stderr)
            return 1
        print(f"\npage schema up to date ({len(pages)} pages)")
        return 0

    print(f"\n{'would update' if args.dry_run else 'updated'} {len(changed)} of {len(pages)} pages")
    if undated:
        print(f"no git history for: {', '.join(undated)}")
    print(
        "\nNOT written, on purpose: lastReviewed / reviewedBy. Those assert that a\n"
        "named clinician reviewed the page on a date — the strongest signal there is\n"
        "for medical content, and the one thing here that cannot be derived. Supply\n"
        "real review dates and they belong in this block."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
