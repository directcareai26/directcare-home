#!/usr/bin/env python3
"""
site_health.py — uptime / broken-page monitor for directcare.ai.

Checks the homepage, every critical product/funnel page, and the full live sitemap.
Alerts a Slack channel (webhook) the moment any URL stops returning HTTP 200, so an
outage like the silent product-page 404s can never go unnoticed again.

Behaviour:
  • Failure-only by default — stays quiet while everything is green (high signal).
  • Each failing URL is re-checked twice before alerting, to avoid paging on a transient blip.
  • Re-alerts every run while still down (keeps reminding until fixed).
  • Once-a-day "all green" heartbeat (08:00 ET window) so you know it's alive.

Webhook: SITE_HEALTH_WEBHOOK env (GitHub secret) or --webhook, or ../.vault/slack.env fallback.

Usage:
  python site_health.py                 # check; alert only if something is down (+ daily heartbeat)
  python site_health.py --heartbeat     # force-send the green summary (to test the webhook)
  python site_health.py --dry-run       # print results, never post to Slack
"""
import os, sys, json, time, argparse, datetime, pathlib, urllib.request, urllib.error

BASE = "https://www.directcare.ai"

# Always-checked critical paths (homepage, products, funnels, key redirects).
CRITICAL = [
    # intake / ad-landing funnels (paid traffic lands here — must never 404):
    "/surge-max/start", "/testosterone-replacement-therapy/start", "/hormone-replacement-therapy/start", "/mens-hair-loss/start", "/womans-hair-loss/start", "/weight-loss/start",
    "/", "/about", "/blog/",
    "/surge-max", "/weight-loss", "/mens-weight-loss", "/womens-weight-loss",
    "/mens-hair-loss", "/womans-hair-loss", "/chronic-care",
    "/hormone-replacement-therapy", "/testosterone-replacement-therapy",
    "/mens-health", "/womens-health", "/blood-test", "/supplements", "/peptides", "/together",
    # high-value redirect aliases that must resolve:
    "/sildenafil", "/hair-loss", "/remote-patient-monitoring", "/weight-loss/men", "/weight-loss/women",
]

TIMEOUT = 20
UA = "DirectCareSiteHealth/1.0 (+monitoring)"
VAULT = pathlib.Path(__file__).resolve().parents[3] / "tooling" / ".vault"


def get_webhook(cli):
    if cli:
        return cli
    w = os.environ.get("SITE_HEALTH_WEBHOOK")
    if w:
        return w
    f = VAULT / "slack.env"
    if f.exists():
        for line in f.read_text().splitlines():
            if line.startswith("SITE_HEALTH_WEBHOOK="):
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def check(url):
    """Return (ok, status, final_url, note). Follows redirects; 200 = healthy."""
    req = urllib.request.Request(url, headers={"User-Agent": UA}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return (r.status == 200, r.status, r.geturl(), "")
    except urllib.error.HTTPError as e:
        return (False, e.code, url, f"HTTP {e.code}")
    except Exception as e:
        return (False, 0, url, f"{type(e).__name__}: {e}")


def build_targets():
    paths = list(dict.fromkeys(CRITICAL))           # ordered-unique
    targets = [BASE + p for p in paths]
    # merge live sitemap so newly-added pages are auto-covered
    try:
        req = urllib.request.Request(BASE + "/sitemap.xml", headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            xml = r.read().decode("utf-8", "ignore")
        import re
        for loc in re.findall(r"<loc>([^<]+)</loc>", xml):
            loc = loc.strip().rstrip("/")
            if loc and loc.startswith("http") and loc not in targets:
                targets.append(loc)
    except Exception:
        pass                                        # sitemap optional; critical list still runs
    return targets


def post_slack(webhook, text):
    req = urllib.request.Request(webhook, data=json.dumps({"text": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=30)
        return True
    except Exception as e:
        print(f"! Slack post failed: {e}")
        return False


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--webhook")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--heartbeat", action="store_true")
    args = ap.parse_args()

    targets = build_targets()
    failures = []
    for url in targets:
        ok, status, final, note = check(url)
        if not ok:
            # re-check twice before trusting the failure (transient-blip guard)
            confirmed = True
            for _ in range(2):
                time.sleep(3)
                ok2, status, final, note = check(url)
                if ok2:
                    confirmed = False
                    break
            if confirmed:
                failures.append((url, status, note))

    now = datetime.datetime.now(datetime.timezone.utc)
    print(f"Checked {len(targets)} URLs at {now.isoformat()}Z — {len(failures)} down")
    for u, s, n in failures:
        print(f"  DOWN {s or ''} {u} {n}")

    webhook = get_webhook(args.webhook)

    if failures:
        lines = [f":rotating_light: *DirectCare site health — {len(failures)} page(s) DOWN*  ({now:%Y-%m-%d %H:%M} UTC)"]
        for u, s, n in failures[:25]:
            lines.append(f"• `{s or 'ERR'}` {u}  {('— ' + n) if n else ''}")
        lines.append(f"_Checked {len(targets)} URLs on www.directcare.ai. Re-checks every 15 min until resolved._")
        msg = "\n".join(lines)
        if args.dry_run or not webhook:
            print("\n[dry-run / no webhook]\n" + msg)
        else:
            print("✓ alert posted" if post_slack(webhook, msg) else "! alert failed")
        sys.exit(0)

    # all green — heartbeat once a day (08:00 ET = 12:00 UTC window) or when forced
    heartbeat = args.heartbeat or (now.hour == 12 and now.minute < 15)
    if heartbeat:
        msg = (f":white_check_mark: *DirectCare site health — all green* ({now:%Y-%m-%d %H:%M} UTC)\n"
               f"All {len(targets)} monitored URLs on www.directcare.ai returning HTTP 200.")
        if args.dry_run or not webhook:
            print("\n[dry-run / no webhook]\n" + msg)
        else:
            print("✓ heartbeat posted" if post_slack(webhook, msg) else "! heartbeat failed")
    else:
        print("all green — no alert (quiet).")


if __name__ == "__main__":
    main()
