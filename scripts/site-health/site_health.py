#!/usr/bin/env python3
"""
site_health.py — uptime / broken-page monitor for directcare.ai.

Checks the homepage, every critical product/funnel page, and the full live sitemap.
Alerts a Slack channel (webhook) the moment any URL stops returning HTTP 200, so an
outage like the silent product-page 404s can never go unnoticed again.

Behaviour:
  • Failure-only by default — stays quiet while everything is green (high signal).
  • A URL that fails the sweep is re-checked in three spaced rounds (15 s, 30 s, 60 s
    apart — about two minutes end to end) and only alerts if it fails every round.
    A GitHub runner's path to Vercel can degrade for a minute or two at a time
    (2026-09-10: two healthy blog pages hit "Connection reset by peer" on three
    tries 3 s apart), and a quick triple-retry inside that window still pages.
  • Re-alerts every run while still down (keeps reminding until fixed).
  • Once-a-day "all green" heartbeat (08:00 ET window) so you know it's alive.
  • Wall-clock guarded: the sweep and the re-check rounds stop before the workflow's
    10-minute job timeout, so a full outage (every request timing out) still produces
    an alert instead of a killed job.

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

# Confirmation rounds for anything that failed the sweep. Each value is the pause
# before that round; a URL drops out the moment it comes back. Total ≈ 105 s.
RECHECK_DELAYS = (15, 30, 60)
# Stop sweeping new URLs after this long so the re-check rounds and the alert
# still fit inside the workflow's 10-minute job timeout.
SWEEP_BUDGET = 6 * 60
# Hard stop for everything (sweep + rounds); whatever is still failing is alerted.
DEADLINE = 8.5 * 60
SWEEP_BUDGET_LEFT_MIN = DEADLINE - SWEEP_BUDGET   # sweep may run until this much time remains


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


def sweep(targets, time_left):
    """First pass over every target. Returns ({url: (status, note)}, urls_checked)."""
    suspects = {}
    checked = 0
    for url in targets:
        if time_left() < SWEEP_BUDGET_LEFT_MIN:
            print(f"! sweep stopped after {checked}/{len(targets)} URLs — out of time budget", flush=True)
            break
        ok, status, final, note = check(url)
        checked += 1
        if not ok:
            suspects[url] = (status, note)
            print(f"  suspect {status or 'ERR'} {url} {note}", flush=True)
    return suspects, checked


def confirm(suspects, time_left):
    """Re-check suspects in spaced rounds; drop any that recover. Returns the confirmed set."""
    failures = dict(suspects)
    for i, delay in enumerate(RECHECK_DELAYS, 1):
        if not failures:
            break
        if time_left() < delay + 30:
            print(f"! skipping re-check round {i} — out of time budget", flush=True)
            break
        time.sleep(delay)
        for url in list(failures):
            if time_left() < 0:
                break
            ok, status, final, note = check(url)
            if ok:
                print(f"  recovered (round {i}) {url}", flush=True)
                del failures[url]
            else:
                failures[url] = (status, note)
    return failures



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

    try:
        sys.stdout.reconfigure(line_buffering=True)   # timestamps in the Actions log are real
    except Exception:
        pass

    t0 = time.monotonic()
    def time_left():
        return DEADLINE - (time.monotonic() - t0)

    targets = build_targets()
    suspects, checked = sweep(targets, time_left)
    if suspects:
        print(f"{len(suspects)} suspect(s) after sweep — confirming over {sum(RECHECK_DELAYS)} s", flush=True)
    confirmed = confirm(suspects, time_left)
    failures = [(u, s, n) for u, (s, n) in confirmed.items()]

    now = datetime.datetime.now(datetime.timezone.utc)
    elapsed = time.monotonic() - t0
    print(f"Checked {checked} URLs at {now.isoformat()}Z in {elapsed:.0f}s — {len(failures)} down")
    for u, s, n in failures:
        print(f"  DOWN {s or ''} {u} {n}")

    webhook = get_webhook(args.webhook)

    if failures:
        lines = [f":rotating_light: *DirectCare site health — {len(failures)} page(s) DOWN*  ({now:%Y-%m-%d %H:%M} UTC)"]
        for u, s, n in failures[:25]:
            lines.append(f"• `{s or 'ERR'}` {u}  {('— ' + n) if n else ''}")
        partial = f" (sweep stopped early at {checked} of {len(targets)})" if checked < len(targets) else ""
        lines.append(f"_Each page failed {len(RECHECK_DELAYS) + 1} checks over ~{sum(RECHECK_DELAYS)} s. "
                     f"Checked {checked} URLs on www.directcare.ai{partial}. Re-checks every scheduled run until resolved._")
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
