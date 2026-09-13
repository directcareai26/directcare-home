#!/usr/bin/env python3
"""Crawl audit of www.directcare.ai + corporate.directcare.ai the way Ahrefs Site Audit / GSC see them.

Checks (E = error, exits 1; W = warning):
  E  sitemap URL not 200 · broken internal link (4xx/5xx/unreachable) · invalid JSON-LD · soft-404 ·
     duplicate <title> across pages · sitemap page canonicalised elsewhere but still listed
  W  redirecting internal links (3xx hop) · entry-point chain >1 hop or 302 · orphan pages (no inlinks
     from any crawled page) · <img> without alt · title >60 / meta >155 counts · missing og:/twitter tags

Usage: python3 scripts/site-health/crawl_audit.py [--no-slack] [--json out.json]
Slack: SITE_HEALTH_WEBHOOK env (same secret as site_health.py). Runs a positive control first: a known
404 and a known 308 on the live host must be classified correctly, or the run is declared UNDELIVERED.
Added 2026-09-13 after a manual crawl found 2,488 redirecting internal links, 17 duplicate posts, a stale
/blog index (73 orphans) and 9 non-200 sitemap URLs that no existing check would have reported.
"""
import argparse, collections, concurrent.futures as cf, html, json, os, re, ssl, sys, time, urllib.error, urllib.request
from urllib.parse import urljoin, urlparse

UA = {"User-Agent": "Mozilla/5.0 (compatible; DirectCareCrawlAudit/1.0; +https://www.directcare.ai)"}
CTX = ssl.create_default_context()
SITES = {"store": "https://www.directcare.ai", "corporate": "https://corporate.directcare.ai"}
ENTRY_HOSTS = ["directcare.ai", "www.directcare.ai", "corporate.directcare.ai"]
SKIP_EXT = re.compile(r"\.(png|jpe?g|webp|svg|gif|pdf|css|js|ico|mp4|xml|txt|json)$", re.I)


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


OPENER = urllib.request.build_opener(_NoRedirect, urllib.request.HTTPSHandler(context=CTX))


def get(url, timeout=25):
    try:
        r = OPENER.open(urllib.request.Request(url, headers=UA), timeout=timeout)
        return r.status, dict(r.headers), r.read(600_000).decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), ""
    except Exception as e:  # noqa: BLE001
        return None, {"error": str(e)[:80]}, ""


def chain(url, hops=6):
    out, cur = [], url
    for _ in range(hops):
        st, h, _ = get(cur)
        out.append((cur, st))
        loc = h.get("Location") or h.get("location")
        if st in (301, 302, 307, 308) and loc:
            cur = urljoin(cur, loc)
            continue
        break
    return out


def positive_control():
    """The checker must SEE a known 404 and a known 3xx before its 'clean' verdict means anything."""
    c404 = chain(SITES["store"] + "/this-page-does-not-exist-crawl-audit-control")
    c308 = chain(SITES["store"] + "/blog/")
    ok = c404[-1][1] == 404 and len(c308) == 2 and c308[0][1] in (301, 308) and c308[-1][1] == 200
    if not ok:
        print(f"!! UNDELIVERED: positive control failed (404 chain={c404}, 308 chain={c308})")
        sys.exit(2)
    print("positive control ok: 404 detected, 308 hop detected")


def audit_site(name, base):
    host = urlparse(base).netloc
    E, W = [], []
    st, _, rb = get(base + "/robots.txt")
    if st != 200:
        E.append(f"robots.txt -> HTTP {st}")
    sms = re.findall(r"(?im)^sitemap:\s*(\S+)", rb)
    urls = []
    for sm in sms:
        st, _, xb = get(sm)
        if st != 200:
            E.append(f"sitemap {sm} -> HTTP {st}")
            continue
        locs = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xb)
        for child in [l for l in locs if l.endswith(".xml")]:
            _, _, cb = get(child)
            locs += re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", cb)
        urls += [u for u in locs if not u.endswith(".xml") and not SKIP_EXT.search(u)]
    urls = sorted(set(urls))
    with cf.ThreadPoolExecutor(12) as ex:
        pages = dict(zip(urls, ex.map(get, urls)))
    titles, inlinks, links = collections.defaultdict(list), collections.Counter(), set()
    n_title_long = n_meta_long = n_noalt = n_og = 0
    for u, (st, h, b) in pages.items():
        if st != 200:
            E.append(f"sitemap URL not 200: {u} -> {st}")
            continue
        can = re.search(r'<link[^>]+rel=["\']canonical["\'][^>]*href=["\']([^"\']+)', b, re.I)
        can = can.group(1) if can else None
        if can and can.rstrip("/") != u.rstrip("/"):
            E.append(f"listed in sitemap but canonicalised to {can}: {u}")
        rm = re.search(r'<meta[^>]+name=["\']robots["\'][^>]+content=["\']([^"\']+)', b, re.I)
        if (rm and "noindex" in rm.group(1).lower()) or "noindex" in (h.get("X-Robots-Tag") or h.get("x-robots-tag") or "").lower():
            E.append(f"noindex page in sitemap: {u}")
        t = re.search(r"<title[^>]*>(.*?)</title>", b, re.I | re.S)
        t = html.unescape(t.group(1)).strip() if t else ""
        titles[t].append(u)
        if len(t) > 60:
            n_title_long += 1
        d = re.search(r'<meta[^>]+name=["\']description["\'][^>]+content=(["\'])(.*?)\1', b, re.I | re.S)
        if d and len(html.unescape(d.group(2))) > 155:
            n_meta_long += 1
        if not d:
            W.append(f"no meta description: {u}")
        h1 = re.findall(r"<h1[\s>]", b, re.I)
        if len(h1) != 1:
            W.append(f"{len(h1)} H1 tags: {u}")
        n_noalt += sum(1 for i in re.findall(r"<img\b[^>]*>", b, re.I) if not re.search(r"\balt=", i, re.I))
        if not all(re.search(r'property=["\']' + tag + r'["\']', b, re.I) for tag in ("og:title", "og:description", "og:image", "og:url")):
            n_og += 1
        for m in re.finditer(r'<script type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', b, re.S | re.I):
            try:
                json.loads(m.group(1))
            except Exception as e:  # noqa: BLE001
                E.append(f"invalid JSON-LD on {u}: {str(e)[:50]}")
        if re.search(r'(src|href)=["\']http://', b, re.I):
            W.append(f"mixed content (http:// resource): {u}")
        markup = re.sub(r"<script\b.*?</script>", "", b, flags=re.S | re.I)   # JS template strings are not links
        for m in re.finditer(r'<a[^>]+href=["\']([^"\'#]+)', markup, re.I):
            l = urljoin(u, m.group(1)).split("#")[0]
            if urlparse(l).netloc == host and not SKIP_EXT.search(l):
                links.add(l)
                inlinks[l.split("?")[0].rstrip("/")] += 1
    for t, us in titles.items():
        if len(us) > 1 and t:
            E.append(f"duplicate <title> on {len(us)} pages: {t[:60]} -> {', '.join(x.replace(base, '') for x in us)}")
    with cf.ThreadPoolExecutor(12) as ex:
        res = list(ex.map(chain, sorted(links)))
    broken = [c for c in res if c[-1][1] not in (200,)]
    redirecting = [c for c in res if len(c) > 1 and c[-1][1] == 200]
    for c in broken:
        E.append("broken internal link: " + " -> ".join(f"{x} [{s}]" for x, s in c))
    for c in redirecting[:40]:
        W.append("redirecting internal link: " + " -> ".join(f"{x} [{s}]" for x, s in c))
    if len(redirecting) > 40:
        W.append(f"... {len(redirecting) - 40} more redirecting internal links")
    orphans = [u for u in urls if pages[u][0] == 200 and inlinks.get(u.rstrip("/"), 0) == 0 and u.rstrip("/") != base]
    for o in orphans[:30]:
        W.append(f"orphan (no inlinks from crawled pages): {o}")
    if len(orphans) > 30:
        W.append(f"... {len(orphans) - 30} more orphans")
    st, _, _ = get(base + "/this-page-does-not-exist-crawl-audit")
    if st == 200:
        E.append("soft-404: random path returns 200")
    for h in ENTRY_HOSTS:
        if urlparse(base).netloc.endswith(h.split(".", 1)[-1]) and (h == host or (name == "store" and h == "directcare.ai")):
            for scheme in ("http", "https"):
                c = chain(f"{scheme}://{h}/")
                if any(s == 302 for _, s in c):
                    W.append("302 on entry point: " + " -> ".join(f"{x} [{s}]" for x, s in c))
                if len(c) > 2:
                    W.append(f"{len(c) - 1}-hop entry chain: " + " -> ".join(f"{x} [{s}]" for x, s in c))
    summary = {"pages": len(urls), "errors": len(E), "warnings": len(W), "internal_links": len(links),
               "broken_links": len(broken), "redirecting_links": len(redirecting), "orphans": len(orphans),
               "title_gt60": n_title_long, "meta_gt155": n_meta_long, "img_no_alt": n_noalt, "og_incomplete": n_og}
    return summary, E, W


def post_slack(webhook, text):
    req = urllib.request.Request(webhook, data=json.dumps({"text": text}).encode(), headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=30)
    except Exception as e:  # noqa: BLE001
        print(f"!! UNDELIVERED: slack post failed: {e}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-slack", action="store_true")
    ap.add_argument("--json")
    a = ap.parse_args()
    t0 = time.time()
    positive_control()
    report, worst = {}, 0
    lines = []
    for name, base in SITES.items():
        s, E, W = audit_site(name, base)
        report[name] = {"summary": s, "errors": E, "warnings": W}
        worst = max(worst, len(E))
        lines.append(f"*{name}* ({base}): {s['pages']} pages · {s['errors']} errors · {s['warnings']} warnings · "
                     f"links {s['internal_links']} (broken {s['broken_links']}, redirecting {s['redirecting_links']}) · "
                     f"orphans {s['orphans']} · title>60 {s['title_gt60']} · meta>155 {s['meta_gt155']} · img-no-alt {s['img_no_alt']}")
        for e in E[:15]:
            lines.append(f"  ❌ {e}")
        for w in W[:8]:
            lines.append(f"  ⚠️ {w}")
    text = ("🕷️ Crawl audit " + ("FAILED" if worst else "clean") + f" ({int(time.time() - t0)}s)\n" + "\n".join(lines))
    print(text)
    if a.json:
        with open(a.json, "w") as f:
            json.dump(report, f, indent=1)
    wh = os.environ.get("SITE_HEALTH_WEBHOOK")
    if wh and not a.no_slack:
        post_slack(wh, text[:3900])
    return 1 if worst else 0


if __name__ == "__main__":
    sys.exit(main())
