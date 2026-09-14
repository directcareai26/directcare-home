#!/usr/bin/env python3
"""Apply gate-approved answer-first paragraphs to existing posts.

Reads the compliance verdicts JSON (rows: slug, verdict, final) and, for each APPROVE with a final paragraph, inserts
<p class="answer-first">…</p> as the first paragraph of the article body (right before the first <p> that follows the
post header), plus the .answer-first style rule in the post's inline <style>. Idempotent. --dry-run prints placement
for one post and changes nothing. 2026-09-14.
"""
import argparse, html, json, os, re, sys
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CSS = ".answer-first{font-size:1.08rem;line-height:1.65;font-weight:500;color:var(--ink,#1c1330);padding:16px 20px;border-left:3px solid var(--brand-deep,#500978);background:rgba(80,9,120,.04);border-radius:8px;margin:0 0 28px}"


def inject(path, para):
    s = open(path).read()
    if 'class="answer-first"' in s:
        return "already"
    m = re.search(r"<article\b[^>]*>", s)
    if not m:
        return "no <article>"
    # first body paragraph after the header block: the first <p> that comes after the last header element
    start = m.end()
    hdr_end = max((s.find(tag, start) for tag in ("</header>", "{{REVIEWER_BYLINE}}", 'class="post-deck"')), default=-1)
    search_from = hdr_end if hdr_end > 0 else start
    p = re.search(r"<p\b(?![^>]*class=\"(?:post-deck|byline|reviewer)\")[^>]*>", s[search_from:])
    if not p:
        return "no first <p>"
    pos = search_from + p.start()
    block = f'<p class="answer-first">{html.escape(para, quote=False)}</p>\n'
    s = s[:pos] + block + s[pos:]
    if ".answer-first{" not in s:
        s = s.replace("</style>", CSS + "\n</style>", 1)
    open(path, "w").write(s)
    return "ok"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("verdicts")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    rows = json.load(open(a.verdicts))
    n = collections = 0
    stats = {}
    for r in rows:
        if r.get("verdict") != "APPROVE" or not r.get("final"):
            stats["skipped"] = stats.get("skipped", 0) + 1
            continue
        path = os.path.join(ROOT, "blog", r["slug"] + ".html")
        if not os.path.exists(path):
            stats["missing"] = stats.get("missing", 0) + 1
            continue
        if a.dry_run:
            s = open(path).read(); m = re.search(r"<article\b[^>]*>", s)
            print(r["slug"], "->", "would insert before first body <p>" if m else "no article")
            break
        res = inject(path, r["final"])
        stats[res] = stats.get(res, 0) + 1
    print("apply_answer_first:", stats)


if __name__ == "__main__":
    main()
