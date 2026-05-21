#!/usr/bin/env python3
"""
Pre-render blog post cards from /blog/posts.json into /blog/index.html
so crawlers (and AI engines) see the post links in raw HTML.

Run this whenever you add a post to posts.json:
    python3 scripts/build_blog_index.py
"""
import html
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
POSTS = json.loads((ROOT / "blog/posts.json").read_text())["posts"]
INDEX = ROOT / "blog/index.html"

def esc(s: str) -> str:
    return html.escape(str(s or ""), quote=True)

def featured_html(p: dict) -> str:
    return (
        f'<a class="featured-post" href="/blog/{esc(p["slug"])}" style="text-decoration: none;">'
        f'<div>'
        f'<div class="meta"><span>{esc(p["category"])}</span><span class="dot"></span><span class="date">{esc(p.get("dateLabel") or p.get("date") or "")}</span></div>'
        f'<h2>{esc(p["title"])}</h2>'
        f'<p class="excerpt">{esc(p["excerpt"])}</p>'
        f'<span class="cta">Read the post →</span>'
        f'</div>'
        f'<div class="featured-post-image"><img src="{esc(p["image"])}" alt="" loading="eager" /></div>'
        f'</a>'
    )

def card_html(p: dict) -> str:
    return (
        f'<a class="post-card" href="/blog/{esc(p["slug"])}">'
        f'<div class="post-card-image"><img src="{esc(p["image"])}" alt="" loading="lazy" /></div>'
        f'<div class="post-card-body">'
        f'<div class="post-card-meta"><span>{esc(p["category"])}</span><span class="dot"></span><span class="date">{esc(p.get("dateLabel") or p.get("date") or "")}</span></div>'
        f'<h3>{esc(p["title"])}</h3>'
        f'<p>{esc(p["excerpt"])}</p>'
        f'<span class="post-card-readmore">Read the post →</span>'
        f'</div>'
        f'</a>'
    )

featured = featured_html(POSTS[0]) if POSTS else ""
cards = "".join(card_html(p) for p in POSTS[1:])
posts_inline = json.dumps({"posts": POSTS}, separators=(",", ":"))

text = INDEX.read_text()

# 1) Inject featured into featured-slot
text = re.sub(
    r'<div id="featured-slot">[\s\S]*?</div>',
    f'<div id="featured-slot">{featured}</div>',
    text, count=1,
)

# 2) Inject cards into post-grid
text = re.sub(
    r'<div class="post-grid" id="post-grid">[\s\S]*?</div>',
    f'<div class="post-grid" id="post-grid">{cards}</div>',
    text, count=1,
)

# 3) Inject inline posts JSON before the closing </body> (idempotent)
inline_tag = f'<script type="application/json" id="posts-data">{posts_inline}</script>'
text = re.sub(
    r'<script type="application/json" id="posts-data">[\s\S]*?</script>\s*',
    "", text,
)
text = text.replace("</body>", f"{inline_tag}\n</body>", 1)

INDEX.write_text(text)
print(f"✓ Server-rendered {len(POSTS)} post(s) into {INDEX.relative_to(ROOT)}")
print(f"  Featured: {POSTS[0]['title'][:60]}…" if POSTS else "  (no posts)")
print(f"  Grid: {len(POSTS) - 1} additional card(s)" if len(POSTS) > 1 else "")
