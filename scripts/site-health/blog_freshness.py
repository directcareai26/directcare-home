#!/usr/bin/env python3
"""
blog_freshness.py — alert when the daily blog stops publishing.

The daily post crashed on every scheduled run from 2026-09-15 to 2026-10-02 (an
un-escaped {callout} in the writer prompt) and nobody noticed for 18 days. Each
failed run was visible in Actions; nothing pushed it to anyone.

This reads the LIVE www.directcare.ai/blog/posts.json — what readers actually get,
not the repo or the workflow status — and alerts Slack when the newest post is more
than MAX_AGE_DAYS old (America/New_York calendar days, the blog's own date basis).
It exits 1 when stale so the run also shows red in Actions.

Runs once a day from .github/workflows/blog-freshness.yml, so a stale blog produces
one alert per day until it recovers. Webhook: same as site_health.py.

Usage:
  python blog_freshness.py              # check; alert only if stale
  python blog_freshness.py --dry-run    # print, never post
  python blog_freshness.py --today 2026-10-09 --dry-run   # simulate a later date
"""
import argparse, datetime, json, sys, urllib.request
from zoneinfo import ZoneInfo

from site_health import BASE, TIMEOUT, UA, get_webhook, post_slack

MAX_AGE_DAYS = 2
FEED = BASE + "/blog/posts.json"


def newest_post():
    req = urllib.request.Request(f"{FEED}?cb={datetime.datetime.now().timestamp():.0f}", headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        posts = json.load(r)["posts"]
    if not posts:
        raise ValueError("posts.json has no posts")
    return max(posts, key=lambda p: p["date"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--webhook")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--today", help="YYYY-MM-DD override, for testing the alert path")
    args = ap.parse_args()

    today = (datetime.date.fromisoformat(args.today) if args.today
             else datetime.datetime.now(ZoneInfo("America/New_York")).date())

    # A feed we cannot read is itself an alert — never report healthy on an error.
    try:
        post = newest_post()
        newest = datetime.date.fromisoformat(post["date"])
        age = (today - newest).days
        stale = age > MAX_AGE_DAYS
        detail = f"Newest post is *{newest:%b %-d}* ({age} day(s) old): {BASE}/blog/{post['slug']}"
    except Exception as e:
        stale, detail = True, f"Could not read {FEED}: {type(e).__name__}: {e}"

    print(detail)
    if not stale:
        print(f"fresh — within {MAX_AGE_DAYS} days, no alert.")
        return 0

    msg = (f":warning: *DirectCare blog is stale* ({today:%Y-%m-%d})\n{detail}\n"
           f"_The daily post should publish every day. Check the Daily Blog Post runs: "
           f"https://github.com/directcareai26/directcare-home/actions/workflows/daily-blog.yml_")
    webhook = get_webhook(args.webhook)
    if args.dry_run or not webhook:
        print("\n[dry-run / no webhook]\n" + msg)
    else:
        print("✓ alert posted" if post_slack(webhook, msg) else "! alert failed")
    return 1


if __name__ == "__main__":
    sys.exit(main())
