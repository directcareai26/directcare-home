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
    post_dir = BLOG_DIR / entry["slug"]
    post_dir.mkdir(parents=True, exist_ok=True)
    post_path = post_dir / "index.html"
    post_path.write_text(html, encoding="utf-8")
    update_manifest(entry)
    return post_path


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
