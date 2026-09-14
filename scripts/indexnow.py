#!/usr/bin/env python3
"""IndexNow submitter — tells Bing (and every IndexNow participant: Yandex, Seznam, Naver, plus the engines that read
Bing's index: ChatGPT search, Copilot, DuckDuckGo, Yahoo, Ecosia) which URLs changed, instantly.

  python3 scripts/indexnow.py URL [URL ...]        # submit specific URLs (any of our hosts)
  python3 scripts/indexnow.py --sitemap             # submit every URL in both hosts' sitemaps (initial seed / rare)
  python3 scripts/indexnow.py --changed             # URLs whose HTML changed in the last commit (daily workflow)

Key 62e90fa19e7f4d38d448fb73cdf46a66 is hosted at /<key>.txt on www.directcare.ai and corporate.directcare.ai. 2026-09-14.
"""
import json, re, subprocess, sys, urllib.request
KEY = "62e90fa19e7f4d38d448fb73cdf46a66"
HOSTS = {"www.directcare.ai": "https://www.directcare.ai", "corporate.directcare.ai": "https://corporate.directcare.ai"}

def sitemap_urls(base):
    xml = urllib.request.urlopen(base + "/sitemap.xml", timeout=30).read().decode()
    return [u for u in re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", xml) if not u.endswith(".xml")]

def changed_urls():
    out = subprocess.run(["git", "diff", "--name-only", "HEAD~1", "HEAD"], capture_output=True, text=True).stdout.split()
    urls = []
    for f in out:
        if not f.endswith(".html") or f.startswith(("optimized/", "content-queue/")) or "/_" in f or f.startswith("_"):
            continue
        path = "/" + f[:-5]
        path = path[:-6] if path.endswith("/index") else path
        path = "/" if path == "" else path
        urls.append("https://www.directcare.ai" + path)
    return urls

def submit(urls):
    by_host = {}
    for u in urls:
        h = u.split("/")[2]
        if h in HOSTS: by_host.setdefault(h, []).append(u)
    rc = 0
    for host, us in by_host.items():
        body = {"host": host, "key": KEY, "keyLocation": f"{HOSTS[host]}/{KEY}.txt", "urlList": sorted(set(us))[:10000]}
        req = urllib.request.Request("https://api.indexnow.org/IndexNow", data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json; charset=utf-8"}, method="POST")
        try:
            r = urllib.request.urlopen(req, timeout=30); print(f"indexnow {host}: {len(body['urlList'])} url(s) -> HTTP {r.status}")
        except urllib.error.HTTPError as e:
            print(f"!! UNDELIVERED indexnow {host}: HTTP {e.code} {e.read().decode()[:120]}"); rc = 1
    return rc

if __name__ == "__main__":
    a = sys.argv[1:]
    if a == ["--sitemap"]: urls = [u for b in HOSTS.values() for u in sitemap_urls(b)]
    elif a == ["--changed"]: urls = changed_urls()
    else: urls = a
    if not urls: print("indexnow: nothing to submit"); sys.exit(0)
    sys.exit(submit(urls))
