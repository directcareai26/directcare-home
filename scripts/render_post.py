#!/usr/bin/env python3
"""
render_post.py — Render a single blog post from a structured JSON payload.

Reads a post JSON file (or stdin) and writes:
  - blog/<slug>/index.html         (the post page)
Updates:
  - blog/posts.json                (manifest, newest-first)

Used by both the seed-post bootstrap and the daily generator.
"""
from __future__ import annotations

import argparse
import datetime as dt
import html as _html
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOG_DIR = REPO_ROOT / "blog"
TEMPLATE_PATH = BLOG_DIR / "_post-template.html"
MANIFEST_PATH = BLOG_DIR / "posts.json"
SITEMAP_PATH = REPO_ROOT / "sitemap.xml"
RSS_PATH = BLOG_DIR / "rss.xml"
SITE_BASE = "https://www.directcare.ai"
RSS_TITLE = "DirectCare AI Blog"
RSS_DESCRIPTION = (
    "Plain-English breakdowns of the science behind TRT, HRT, GLP-1 weight loss, "
    "sexual health, hair regrowth, nutrition, fitness, blood labs, and supplements. "
    "Written by US-licensed clinicians at DirectCare AI."
)

# Pages that should appear in sitemap.xml in addition to the blog posts.
# (priority, changefreq, path)
SITEMAP_STATIC_PAGES: list[tuple[str, str, str]] = [
    ("1.0", "weekly", "/"),
    ("0.9", "monthly", "/hormone-replacement-therapy"),
    ("0.9", "monthly", "/testosterone-replacement-therapy"),
    ("0.9", "monthly", "/weight-loss/"),
    ("0.9", "monthly", "/surge-max/"),
    ("0.9", "monthly", "/mens-hair-loss/"),
    ("0.9", "monthly", "/womans-hair-loss/"),
    ("0.9", "monthly", "/blood-test/"),
    ("0.8", "monthly", "/supplements/"),
    ("0.8", "monthly", "/chronic-care/"),
    ("0.7", "monthly", "/peptides"),
    ("0.7", "monthly", "/together"),
    ("0.6", "daily",   "/blog/"),
    ("0.4", "yearly",  "/safety/"),
    ("0.3", "yearly",  "/privacy-policy/"),
    ("0.3", "yearly",  "/terms-and-conditions/"),
    ("0.3", "yearly",  "/medical-consent/"),
    ("0.3", "yearly",  "/ccpa/"),
]


# ---- markdown-lite -> HTML ---------------------------------------------------
# We accept a small subset of markdown so the generator can output clean text
# instead of raw HTML. Supports: ## h2, ### h3, **bold**, [text](url), > blockquote,
# - bullet lists, blank-line paragraphs, and a {{callout: ...}} block.

H2_RE = re.compile(r"^##\s+(.+?)\s*$")
H3_RE = re.compile(r"^###\s+(.+?)\s*$")
BOLD_RE = re.compile(r"\*\*(.+?)\*\*")
EM_RE = re.compile(r"(?<!\*)\*([^*\n]+?)\*(?!\*)")  # *italic* (single asterisk)
LINK_RE = re.compile(r"\[(.+?)\]\((https?://[^\s)]+)\)")
INTERNAL_LINK_RE = re.compile(r"\[(.+?)\]\((/[^\s)]*)\)")
CALLOUT_RE = re.compile(r"^\{\{callout(?::\s*(.+?))?\}\}\s*(.+)$")


def _inline(text: str) -> str:
    text = LINK_RE.sub(r'<a href="\2" target="_blank" rel="noopener noreferrer">\1</a>', text)
    text = INTERNAL_LINK_RE.sub(r'<a href="\2">\1</a>', text)
    text = BOLD_RE.sub(r"<strong>\1</strong>", text)
    text = EM_RE.sub(r"<em>\1</em>", text)
    return text


def md_to_html(md: str) -> str:
    """Tiny markdown subset → HTML, indented for embedding in <div class="article-body">."""
    lines = md.replace("\r\n", "\n").split("\n")
    out: list[str] = []
    i = 0
    paragraph: list[str] = []
    in_list = False
    list_buf: list[str] = []

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            joined = " ".join(s.strip() for s in paragraph).strip()
            if joined:
                out.append(f"      <p>{_inline(joined)}</p>")
            paragraph = []

    def flush_list() -> None:
        nonlocal in_list, list_buf
        if in_list and list_buf:
            out.append("      <ul>")
            for li in list_buf:
                out.append(f"        <li>{_inline(li)}</li>")
            out.append("      </ul>")
        in_list = False
        list_buf = []

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            flush_paragraph()
            flush_list()
            i += 1
            continue

        m = H2_RE.match(stripped)
        if m:
            flush_paragraph(); flush_list()
            out.append(f"      <h2>{_inline(m.group(1))}</h2>")
            i += 1
            continue

        m = H3_RE.match(stripped)
        if m:
            flush_paragraph(); flush_list()
            out.append(f"      <h3>{_inline(m.group(1))}</h3>")
            i += 1
            continue

        if stripped.startswith("> "):
            flush_paragraph(); flush_list()
            quote_lines = []
            while i < len(lines) and lines[i].strip().startswith("> "):
                quote_lines.append(lines[i].strip()[2:])
                i += 1
            out.append(f"      <blockquote>{_inline(' '.join(quote_lines))}</blockquote>")
            continue

        m = CALLOUT_RE.match(stripped)
        if m:
            flush_paragraph(); flush_list()
            eyebrow = m.group(1) or "Worth knowing"
            body = m.group(2)
            out.append(
                "      <div class=\"callout\">\n"
                f"        <div class=\"callout-eyebrow\">{_inline(eyebrow)}</div>\n"
                f"        {_inline(body)}\n"
                "      </div>"
            )
            i += 1
            continue

        if stripped.startswith("- "):
            flush_paragraph()
            in_list = True
            list_buf.append(stripped[2:])
            i += 1
            continue
        else:
            flush_list()

        paragraph.append(stripped)
        i += 1

    flush_paragraph()
    flush_list()
    return "\n".join(out)


# ---- template rendering ------------------------------------------------------

def _escape_attr(s: str) -> str:
    return _html.escape(s or "", quote=True)


def render_post(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    """Render one post. Returns (html, manifest_entry)."""
    required = ["slug", "title", "category", "deck", "body_markdown"]
    missing = [k for k in required if not payload.get(k)]
    if missing:
        raise ValueError(f"Missing required post fields: {missing}")

    slug = payload["slug"].strip().lower()
    if not re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", slug):
        raise ValueError(f"Invalid slug: {slug!r}")

    title = payload["title"].strip()
    # Optional title_html lets the author wrap part of the title in <em>...</em>.
    title_html = payload.get("title_html") or _html.escape(title)
    category = payload["category"].strip()
    deck = payload["deck"].strip()
    body_html = md_to_html(payload["body_markdown"])

    date_iso = payload.get("date") or dt.date.today().isoformat()
    date_obj = dt.date.fromisoformat(date_iso)
    date_label = payload.get("dateLabel") or date_obj.strftime("%B %-d, %Y")

    image = payload.get("image") or "https://crsurakhmbalgxim.public.blob.vercel-storage.com/Warm%20%26%20confident.png"
    meta_description = (payload.get("meta_description") or deck)[:300]
    keywords = ", ".join(payload.get("keywords") or [category])
    excerpt = (payload.get("excerpt") or deck)[:240]

    product_eyebrow = payload.get("product_eyebrow", "Ready to take the next step?")
    product_headline = payload.get("product_headline", "Personalized telehealth, on your terms.")
    product_blurb = payload.get("product_blurb", "A US-licensed clinician reviews your bloodwork and builds a protocol around your real numbers. Labs included.")
    product_link = payload.get("product_link", "/")
    product_cta_label = payload.get("product_cta_label", "Get started")

    template = TEMPLATE_PATH.read_text(encoding="utf-8")

    replacements = {
        "{{SLUG}}": slug,
        "{{TITLE}}": _escape_attr(title),
        "{{TITLE_HTML}}": title_html,
        "{{META_DESCRIPTION}}": _escape_attr(meta_description),
        "{{KEYWORDS}}": _escape_attr(keywords),
        "{{CATEGORY}}": _escape_attr(category),
        "{{DATE_ISO}}": date_iso,
        "{{DATE_LABEL}}": _escape_attr(date_label),
        "{{IMAGE}}": _escape_attr(image),
        "{{DECK}}": _escape_attr(deck),
        "{{BODY_HTML}}": body_html,
        "{{PRODUCT_EYEBROW}}": _escape_attr(product_eyebrow),
        "{{PRODUCT_HEADLINE}}": _escape_attr(product_headline),
        "{{PRODUCT_BLURB}}": _escape_attr(product_blurb),
        "{{PRODUCT_LINK}}": _escape_attr(product_link),
        "{{PRODUCT_CTA_LABEL}}": _escape_attr(product_cta_label),
    }
    for k, v in replacements.items():
        template = template.replace(k, v)

    manifest_entry = {
        "slug": slug,
        "title": title,
        "excerpt": excerpt,
        "category": category,
        "categorySlug": payload.get("categorySlug") or re.sub(r"[^a-z0-9]+", "-", category.lower()).strip("-"),
        "date": date_iso,
        "dateLabel": date_label,
        "image": image,
        "keywords": payload.get("keywords") or [category],
    }
    return template, manifest_entry


def write_post(payload: dict[str, Any]) -> Path:
    html, entry = render_post(payload)
    # Flat files (e.g. blog/foo.html) so Vercel's cleanUrls serves them at /blog/foo
    post_path = BLOG_DIR / f"{entry['slug']}.html"
    post_path.write_text(html, encoding="utf-8")
    update_manifest(entry)
    update_sitemap()
    update_rss()
    return post_path


def _rfc822(date_iso: str) -> str:
    """RSS 2.0 dates must be RFC 822 format, e.g. 'Tue, 27 May 2026 08:00:00 -0500'."""
    try:
        d = dt.date.fromisoformat(date_iso)
    except (ValueError, TypeError):
        d = dt.date.today()
    # 08:00 local Eastern publication time, expressed as a fixed offset (-0400 EDT).
    # Buffer/Zapier/LinkedIn don't care about exact tz precision — they just need RFC 822.
    return dt.datetime(d.year, d.month, d.day, 8, 0, 0).strftime("%a, %d %b %Y %H:%M:%S -0400")


def _xml_escape(text: str) -> str:
    """Escape XML-special characters for safe embedding in element text."""
    return (
        (text or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def _cdata(text: str) -> str:
    """Wrap text in CDATA so RSS readers don't have to decode HTML entities."""
    safe = (text or "").replace("]]>", "]]]]><![CDATA[>")
    return f"<![CDATA[{safe}]]>"


def update_rss(limit: int = 30) -> None:
    """Regenerate /blog/rss.xml from the current manifest. Newest 30 posts.

    RSS 2.0 + Atom self-link. Includes:
      - <title>, <link>, <guid> per post
      - <pubDate> in RFC 822 format
      - <description> as CDATA-wrapped excerpt
      - <category> for filtering by Buffer/Zapier
      - <media:content> + <enclosure> so LinkedIn renders the image preview
    """
    posts: list[dict[str, Any]] = []
    if MANIFEST_PATH.exists():
        try:
            posts = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")).get("posts", [])
        except json.JSONDecodeError:
            posts = []

    # Manifest is newest-first; cap the feed.
    posts = posts[:limit]

    today = dt.datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
    last_build = today
    if posts:
        last_build = _rfc822(posts[0].get("date", ""))

    out: list[str] = []
    out.append('<?xml version="1.0" encoding="UTF-8"?>')
    out.append('<rss version="2.0"')
    out.append('  xmlns:atom="http://www.w3.org/2005/Atom"')
    out.append('  xmlns:content="http://purl.org/rss/1.0/modules/content/"')
    out.append('  xmlns:media="http://search.yahoo.com/mrss/"')
    out.append('  xmlns:dc="http://purl.org/dc/elements/1.1/">')
    out.append("  <channel>")
    out.append(f"    <title>{_xml_escape(RSS_TITLE)}</title>")
    out.append(f"    <link>{SITE_BASE}/blog/</link>")
    out.append(f'    <atom:link href="{SITE_BASE}/blog/rss.xml" rel="self" type="application/rss+xml" />')
    out.append(f"    <description>{_xml_escape(RSS_DESCRIPTION)}</description>")
    out.append("    <language>en-us</language>")
    out.append(f"    <lastBuildDate>{last_build}</lastBuildDate>")
    out.append("    <generator>DirectCare AI blog pipeline</generator>")
    out.append(f"    <image>")
    out.append(f"      <url>https://cdn.prod.website-files.com/67e9a176f4ad60e0a777c24a/67e9a176f4ad60e0a777c2a3_DC%20logo%20long%20trans.png</url>")
    out.append(f"      <title>{_xml_escape(RSS_TITLE)}</title>")
    out.append(f"      <link>{SITE_BASE}/blog/</link>")
    out.append(f"    </image>")

    for p in posts:
        slug = p.get("slug")
        if not slug:
            continue
        url = f"{SITE_BASE}/blog/{slug}"
        title = p.get("title", "")
        excerpt = p.get("excerpt", "")
        category = p.get("category", "")
        date = _rfc822(p.get("date", ""))
        image = p.get("image", "")

        out.append("    <item>")
        out.append(f"      <title>{_xml_escape(title)}</title>")
        out.append(f"      <link>{url}</link>")
        out.append(f'      <guid isPermaLink="true">{url}</guid>')
        out.append(f"      <pubDate>{date}</pubDate>")
        out.append(f"      <dc:creator>DirectCare AI Clinical Team</dc:creator>")
        if category:
            out.append(f"      <category>{_xml_escape(category)}</category>")
        out.append(f"      <description>{_cdata(excerpt)}</description>")
        if image:
            # <enclosure> is the RSS 2.0 standard image hint; <media:content> is what
            # LinkedIn and modern feed readers actually look for.
            out.append(f'      <enclosure url="{_xml_escape(image)}" type="image/png" length="0" />')
            out.append(f'      <media:content url="{_xml_escape(image)}" medium="image" />')
            out.append(f'      <media:thumbnail url="{_xml_escape(image)}" />')
        out.append("    </item>")

    out.append("  </channel>")
    out.append("</rss>")
    out.append("")
    RSS_PATH.write_text("\n".join(out), encoding="utf-8")


def update_sitemap() -> None:
    """Regenerate sitemap.xml from SITEMAP_STATIC_PAGES + the current blog manifest."""
    posts: list[dict[str, Any]] = []
    if MANIFEST_PATH.exists():
        try:
            posts = json.loads(MANIFEST_PATH.read_text(encoding="utf-8")).get("posts", [])
        except json.JSONDecodeError:
            posts = []

    today_iso = dt.date.today().isoformat()
    lines = ['<?xml version="1.0" encoding="UTF-8"?>',
             '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">']

    for priority, freq, path in SITEMAP_STATIC_PAGES:
        lastmod = today_iso if path in ("/", "/blog/") else None
        lines.append("  <url>")
        lines.append(f"    <loc>https://www.directcare.ai{path}</loc>")
        if lastmod:
            lines.append(f"    <lastmod>{lastmod}</lastmod>")
        lines.append(f"    <changefreq>{freq}</changefreq>")
        lines.append(f"    <priority>{priority}</priority>")
        lines.append("  </url>")

    for p in posts:
        slug = p.get("slug")
        date = p.get("date", today_iso)
        if not slug:
            continue
        lines.append("  <url>")
        lines.append(f"    <loc>https://www.directcare.ai/blog/{slug}</loc>")
        lines.append(f"    <lastmod>{date}</lastmod>")
        lines.append("    <changefreq>monthly</changefreq>")
        lines.append("    <priority>0.5</priority>")
        lines.append("  </url>")

    lines.append("</urlset>")
    lines.append("")
    SITEMAP_PATH.write_text("\n".join(lines), encoding="utf-8")


def update_manifest(entry: dict[str, Any]) -> None:
    data: dict[str, Any] = {"posts": []}
    if MANIFEST_PATH.exists():
        try:
            data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            data = {"posts": []}
    posts = [p for p in data.get("posts", []) if p.get("slug") != entry["slug"]]
    posts.append(entry)
    # newest-first by date, then slug for stability
    posts.sort(key=lambda p: (p.get("date", ""), p.get("slug", "")), reverse=True)
    data["posts"] = posts
    MANIFEST_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Render a blog post from a JSON payload.")
    parser.add_argument("json_file", nargs="?", help="Path to post JSON (or read stdin if omitted).")
    args = parser.parse_args()

    if args.json_file:
        payload = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
    else:
        payload = json.loads(sys.stdin.read())

    path = write_post(payload)
    print(f"wrote {path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
