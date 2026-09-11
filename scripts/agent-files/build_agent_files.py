#!/usr/bin/env python3
"""
build_agent_files.py — generate the machine-readable edition of www.directcare.ai.

Most AI crawlers do not execute JavaScript and do not want our CSS. This script
emits a plain-Markdown twin of every public page, plus one whole-site file, so an
AI engine can read the catalogue in one request instead of crawling 129 pages and
parsing 100 KB of HTML each time.

Outputs (all git-tracked, all regenerated from scratch every run):

  <page>.md      A Markdown twin beside each HTML page. /blood-test.html ->
                 /blood-test.md ; /blog/foo.html -> /blog/foo.md. Served as the
                 target of the Link: rel=alternate header set in vercel.json.
  llms-full.txt  Every page's Markdown concatenated, with a table of contents.
                 Companion to the hand-written llms.txt, which stays a short
                 curated index — this is the full text.

The page list comes from sitemap.xml, deliberately: that is already the single
source of truth for "what is public", so a page cannot appear here without also
being in the sitemap, and noindex/internal pages cannot leak in.

Stdlib only — this runs in the daily-blog GitHub Action, which has no pip step.

Usage:
  python3 scripts/agent-files/build_agent_files.py            # write files
  python3 scripts/agent-files/build_agent_files.py --check    # CI: fail if stale
  python3 scripts/agent-files/build_agent_files.py --verbose
"""
import argparse
import html as _html
import json
import pathlib
import re
import sys
from xml.etree import ElementTree

ROOT = pathlib.Path(__file__).resolve().parents[2]
BASE = "https://www.directcare.ai"
SITEMAP = ROOT / "sitemap.xml"
LLMS_FULL = ROOT / "llms-full.txt"
# Record of what this script generated, so the next run can delete what it
# no longer generates WITHOUT guessing from file extensions. The repo contains
# plenty of hand-written Markdown that must never be swept.
MANIFEST = ROOT / "scripts" / "agent-files" / "generated-files.txt"

# Blocks that carry no page meaning: scripts, styles, SVG sprites, template
# comments, and the site chrome that repeats identically on all 129 pages.
_DROP_BLOCKS = re.compile(
    r"<(script|style|svg|noscript|template)\b[^>]*>.*?</\1>", re.S | re.I
)
_COMMENTS = re.compile(r"<!--.*?-->", re.S)
_NAV = re.compile(r"<nav\b[^>]*>.*?</nav>", re.S | re.I)
_FOOTER = re.compile(r"<footer\b[^>]*>.*?</footer>", re.S | re.I)
# "Related articles" / "you might also like" rails are navigation, not content,
# and they make every blog post look 30% identical to every other one.
_RELATED = re.compile(
    r'<section[^>]*class="[^"]*(related|more-posts)[^"]*"[^>]*>.*?</section>', re.S | re.I
)

_TAG = re.compile(r"<[^>]+>")
_WS = re.compile(r"[ \t\r\f\v]+")
_BLANKS = re.compile(r"\n{3,}")

# Site chrome that lives OUTSIDE <nav>/<footer> and so survives those rules.
# The mobile drawer is a second full copy of the main menu; left in, every page
# opens with the same 20 links and an engine sees 129 near-identical documents.
_CHROME_CLASSES = ("mobile-drawer", "nav-menu", "cookie", "skip-link", "announcement-bar")


def _strip_containers(s: str, needles=_CHROME_CLASSES) -> str:
    """Remove <div>/<aside> blocks whose open tag mentions a chrome class.

    Regex cannot match balanced tags, and `<div ...>.*?</div>` stops at the
    FIRST </div> — which for a nested menu truncates mid-way and leaves the
    tail behind. So scan forward counting depth and cut the real close tag.
    """
    open_re = re.compile(
        r'<(div|aside|section)\b[^>]*(?:class|id)="[^"]*(?:%s)[^"]*"[^>]*>'
        % "|".join(map(re.escape, needles)),
        re.I,
    )
    while True:
        m = open_re.search(s)
        if not m:
            return s
        tag = m.group(1)
        depth, i = 1, m.end()
        step = re.compile(r"</?%s\b[^>]*>" % tag, re.I)
        while depth and i < len(s):
            nxt = step.search(s, i)
            if not nxt:
                # Unbalanced markup: drop only the open tag rather than the
                # rest of the document.
                return s[: m.start()] + s[m.end() :]
            depth += -1 if nxt.group(0).startswith("</") else 1
            i = nxt.end()
        s = s[: m.start()] + s[i:]


def _text(fragment: str) -> str:
    """HTML fragment -> plain text, entities resolved, whitespace collapsed."""
    t = _TAG.sub(" ", fragment)
    t = _html.unescape(t)
    t = _WS.sub(" ", t)
    return t.strip()


def _meta(doc: str, name: str) -> str:
    m = re.search(
        r'<meta[^>]+(?:name|property)=["\']%s["\'][^>]*content=["\']([^"\']*)' % re.escape(name),
        doc,
        re.I,
    )
    if not m:
        m = re.search(
            r'<meta[^>]+content=["\']([^"\']*)["\'][^>]*(?:name|property)=["\']%s["\']'
            % re.escape(name),
            doc,
            re.I,
        )
    return _html.unescape(m.group(1)).strip() if m else ""


def _body(doc: str) -> str:
    """The part of the page that is actually about this page."""
    m = re.search(r"<body\b[^>]*>(.*)</body>", doc, re.S | re.I)
    s = m.group(1) if m else doc
    s = _COMMENTS.sub("", s)
    s = _DROP_BLOCKS.sub("", s)
    s = _NAV.sub("", s)
    s = _FOOTER.sub("", s)
    s = _RELATED.sub("", s)
    s = _strip_containers(s)
    return s


def _to_markdown(fragment: str) -> str:
    """Structure-preserving HTML -> Markdown. Headings, lists, tables, links."""
    s = fragment

    # <br> and block boundaries become newlines before tags are stripped.
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)

    # Links: keep the destination, it is how an engine follows our internal graph.
    def _link(m):
        href, inner = m.group(1), _text(m.group(2))
        if not inner:
            return ""
        if href.startswith("/"):
            href = BASE + href
        if href.startswith(("mailto:", "tel:", "#")):
            return inner
        return f"[{inner}]({href})"

    s = re.sub(r'<a\b[^>]*href=["\']([^"\']*)["\'][^>]*>(.*?)</a>', _link, s, flags=re.S | re.I)

    # Images: alt text carries real meaning on a health site (product shots,
    # clinician headshots); the binary does not.
    s = re.sub(
        r'<img\b[^>]*alt=["\']([^"\']+)["\'][^>]*>',
        lambda m: f"![{_html.unescape(m.group(1))}]",
        s,
        flags=re.I,
    )
    s = re.sub(r"<img\b[^>]*>", "", s, flags=re.I)

    # Tables -> pipe tables. Comparison tables are among the most-cited blocks
    # on a health site, so flattening them to prose would lose the point.
    def _table(m):
        rows = re.findall(r"<tr\b[^>]*>(.*?)</tr>", m.group(1), re.S | re.I)
        out, header_done = [], False
        for r in rows:
            cells = [
                _text(c)
                for c in re.findall(r"<t[hd]\b[^>]*>(.*?)</t[hd]>", r, re.S | re.I)
            ]
            if not cells:
                continue
            out.append("| " + " | ".join(cells) + " |")
            if not header_done:
                out.append("| " + " | ".join("---" for _ in cells) + " |")
                header_done = True
        return "\n\n" + "\n".join(out) + "\n\n"

    s = re.sub(r"<table\b[^>]*>(.*?)</table>", _table, s, flags=re.S | re.I)

    # Headings. h1 is rendered as the document title separately, so shift down.
    for lvl in range(1, 7):
        s = re.sub(
            r"<h%d\b[^>]*>(.*?)</h%d>" % (lvl, lvl),
            lambda m, l=lvl: "\n\n" + "#" * min(l + 1, 6) + " " + _text(m.group(1)) + "\n\n",
            s,
            flags=re.S | re.I,
        )

    s = re.sub(r"<li\b[^>]*>(.*?)</li>", lambda m: "\n- " + _text(m.group(1)), s, flags=re.S | re.I)
    s = re.sub(r"</(p|div|section|article|ul|ol|header|dl)>", "\n\n", s, flags=re.I)
    s = re.sub(r"<(dt)\b[^>]*>(.*?)</dt>", lambda m: "\n\n**" + _text(m.group(2)) + "**\n", s, flags=re.S | re.I)
    s = re.sub(r"<(strong|b)\b[^>]*>(.*?)</\1>", lambda m: "**" + _text(m.group(2)) + "**", s, flags=re.S | re.I)

    # Inline tags are removed with NO separator — they sit inside a word, so
    # replacing them with a space shatters it. A wordmark built from one span
    # per letter (<span>G</span><span>o</span>...) otherwise reads "G o o g l e".
    s = re.sub(r"</?(span|em|i|b|u|small|sup|sub|abbr|mark|code|font)\b[^>]*>", "", s, flags=re.I)

    s = _TAG.sub(" ", s)
    s = _html.unescape(s)

    # Tidy: collapse runs of spaces without eating the newlines we just made.
    s = "\n".join(_WS.sub(" ", line).rstrip() for line in s.split("\n"))
    s = _BLANKS.sub("\n\n", s)
    return s.strip()


def sitemap_paths():
    """Public URL paths, in sitemap order. Raises if the sitemap is unreadable."""
    tree = ElementTree.parse(SITEMAP)
    ns = {"s": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    out = []
    for loc in tree.getroot().iter():
        if not loc.tag.endswith("}loc") and loc.tag != "loc":
            continue
        u = (loc.text or "").strip()
        if not u.startswith(BASE):
            continue
        p = u[len(BASE) :] or "/"
        if p not in out:
            out.append(p)
    return out


def html_for(path: str):
    """Map a URL path to the HTML file that serves it, mirroring cleanUrls."""
    rel = path.strip("/")
    for cand in ([ROOT / "index.html"] if not rel else
                 [ROOT / f"{rel}.html", ROOT / rel / "index.html"]):
        if cand.is_file():
            return cand
    return None


def md_target(path: str):
    """Where the Markdown twin lives. Mirrors the HTML file's own location."""
    rel = path.strip("/")
    if not rel:
        return ROOT / "index.md"
    if (ROOT / f"{rel}.html").is_file():
        return ROOT / f"{rel}.md"
    return ROOT / rel / "index.md"


def blog_index_posts() -> str:
    """The post list, rendered from posts.json.

    blog/index.html builds its grid client-side by fetching posts.json, so the
    served HTML names only the 4 hard-coded featured posts. Agents do not run
    JavaScript, so a straight conversion of that page advertises a blog of 112
    posts and then lists almost none of them. Read the same JSON the browser
    reads and write the list out flat.
    """
    f = ROOT / "blog" / "posts.json"
    if not f.is_file():
        return ""
    try:
        posts = json.loads(f.read_text(encoding="utf-8")).get("posts", [])
    except Exception:
        return ""
    if not posts:
        return ""
    out = [f"\n\n## All posts ({len(posts)})\n"]
    for p in posts:
        slug, title = p.get("slug", ""), p.get("title", "").strip()
        if not slug or not title:
            continue
        bits = [b for b in (p.get("date", ""), p.get("category", "")) if b]
        out.append(f"\n### [{title}]({BASE}/blog/{slug})\n")
        if bits:
            out.append(f"{' · '.join(bits)}\n")
        if p.get("excerpt"):
            out.append(f"\n{p['excerpt'].strip()}\n")
    return "".join(out)


def render(path: str, doc: str) -> str:
    title = _text(re.search(r"<title[^>]*>(.*?)</title>", doc, re.S | re.I).group(1)) \
        if re.search(r"<title[^>]*>", doc, re.I) else path
    desc = _meta(doc, "description")
    body = _to_markdown(_body(doc))

    head = [f"# {title}", ""]
    if desc:
        head += [f"> {desc}", ""]
    head += [f"Source: {BASE}{path}", ""]
    if path.strip("/") == "blog":
        body += blog_index_posts()
    return "\n".join(head) + "\n" + body + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true",
                    help="exit 1 if any output is missing or stale (for CI)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    paths = sitemap_paths()
    if not paths:
        print("! sitemap yielded no paths — refusing to wipe the agent files", file=sys.stderr)
        return 2

    pages, missing = [], []
    for p in paths:
        f = html_for(p)
        if not f:
            missing.append(p)
            continue
        pages.append((p, render(p, f.read_text(encoding="utf-8", errors="replace"))))

    stale = []

    # 1. Per-page Markdown twins.
    written = set()
    for p, md in pages:
        t = md_target(p)
        written.add(t)
        if args.check:
            if not t.is_file() or t.read_text(encoding="utf-8") != md:
                stale.append(str(t.relative_to(ROOT)))
        else:
            t.parent.mkdir(parents=True, exist_ok=True)
            t.write_text(md, encoding="utf-8")

    # 2. Whole-site file.
    toc = "\n".join(
        f"- [{md.splitlines()[0].lstrip('# ').strip()}]({BASE}{p})" for p, md in pages
    )
    full = (
        "# DirectCare AI — full site text\n\n"
        "> Every public page of www.directcare.ai as plain Markdown, so an AI system\n"
        "> can read the whole site in one request. Generated from sitemap.xml; see\n"
        "> llms.txt for the short curated index.\n\n"
        f"Pages: {len(pages)}\n\n"
        "## Contents\n\n" + toc + "\n\n---\n\n"
        + "\n\n---\n\n".join(md for _, md in pages)
        + "\n"
    )
    if args.check:
        if not LLMS_FULL.is_file() or LLMS_FULL.read_text(encoding="utf-8") != full:
            stale.append("llms-full.txt")
    else:
        LLMS_FULL.write_text(full, encoding="utf-8")

    # 3. Sweep orphans: a .md whose page left the sitemap must not linger, or
    #    agents keep reading a page we retired.
    #
    #    Deletion is driven ONLY by the manifest this script wrote last run —
    #    never by scanning for *.md. The repo is full of hand-written Markdown
    #    (README.md, TRACKING.md, .agents/product-marketing.md, ...) and an
    #    extension-based sweep with a hardcoded allowlist deletes those the
    #    moment someone adds a new one. If the manifest is missing we delete
    #    nothing, because we cannot tell authored files from generated ones.
    previous = set()
    if MANIFEST.is_file():
        for line in MANIFEST.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#"):
                previous.add(ROOT / line)

    orphans = sorted(p for p in previous - written if p.is_file())
    manifest_body = (
        "# Generated by scripts/agent-files/build_agent_files.py — do not edit.\n"
        "# Every path here is machine-written and safe to delete on regeneration.\n"
        + "".join(f"{p.relative_to(ROOT).as_posix()}\n" for p in sorted(written))
    )

    if args.check:
        stale += [str(o.relative_to(ROOT)) + " (orphan)" for o in orphans]
        if not MANIFEST.is_file() or MANIFEST.read_text(encoding="utf-8") != manifest_body:
            stale.append(MANIFEST.name)
    else:
        for o in orphans:
            o.unlink()
        MANIFEST.write_text(manifest_body, encoding="utf-8")

    if missing:
        print(f"! {len(missing)} sitemap path(s) had no HTML file: {missing[:5]}", file=sys.stderr)

    if args.check:
        if stale:
            print(f"! agent files are stale ({len(stale)}). Run:\n"
                  f"    python3 scripts/agent-files/build_agent_files.py", file=sys.stderr)
            for s in stale[:15]:
                print(f"    - {s}", file=sys.stderr)
            return 1
        print(f"agent files up to date ({len(pages)} pages)")
        return 0

    kb = len(full.encode()) // 1024
    print(f"wrote {len(pages)} .md twins + llms-full.txt ({kb} KB)"
          + (f", removed {len(orphans)} orphan(s)" if orphans else ""))
    if args.verbose:
        for p, md in pages[:10]:
            print(f"   {p:55s} {len(md):6d} chars")
    return 2 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
