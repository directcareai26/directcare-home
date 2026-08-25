#!/usr/bin/env python3
"""Static link/button/intake audit for directcare.ai (directcare-home).
Resolves every internal href against real files + vercel.json route table.
Flags: broken internal links, dead buttons (#, empty, javascript:void), and
maps intake (Tellescope) forms per product page to catch mis-wired intakes.
"""
import json, os, re, sys
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ---- 1. Build the set of valid internal routes -----------------------------
valid = set()          # routes that resolve (served or redirected)
static_assets = set()  # actual files served as-is

def add_route(r):
    r = r.rstrip('/') or '/'
    valid.add(r)

for dirpath, _dirs, files in os.walk(ROOT):
    if '/.git' in dirpath or '/node_modules' in dirpath:
        continue
    for fn in files:
        rel = os.path.relpath(os.path.join(dirpath, fn), ROOT)
        route = '/' + rel.replace(os.sep, '/')
        static_assets.add(route)
        if fn.endswith('.html'):
            # cleanUrls: strip .html
            add_route(route[:-5])
            valid.add(route)  # explicit .html also works
            if fn == 'index.html':
                add_route(os.path.dirname(route) or '/')
        else:
            valid.add(route)

# ---- 2. Fold in vercel.json redirects + rewrites ---------------------------
with open(os.path.join(ROOT, 'vercel.json')) as f:
    vj = json.load(f)
route_rules = []  # (regex, is_wildcard)
for rule in vj.get('redirects', []) + vj.get('rewrites', []):
    src = rule['source']
    # ignore host-conditional apex redirects (they still resolve)
    add_route(src)
    if ':path*' in src or ':slug' in src or ':path' in src:
        prefix = src.split(':')[0].rstrip('/')
        route_rules.append(prefix)

def resolves(path):
    p = path.rstrip('/') or '/'
    if p in valid or path in valid:
        return True
    if p in static_assets or path in static_assets:
        return True
    # wildcard rule prefixes (e.g. /blog/:slug, /post/:path*, /hair-loss/:path*)
    for prefix in route_rules:
        if p == prefix or p.startswith(prefix + '/'):
            return True
    # blog slug rewrite: /blog/<slug> -> /blog/<slug>.html
    if p.startswith('/blog/'):
        cand = '/' + p.lstrip('/') + '.html'
        if cand in static_assets:
            return True
    return False

# ---- 3. Scan every HTML page ------------------------------------------------
HTML_FILES = []
for dirpath, _dirs, files in os.walk(ROOT):
    if '/.git' in dirpath or '/node_modules' in dirpath:
        continue
    for fn in files:
        if fn.endswith('.html'):
            HTML_FILES.append(os.path.join(dirpath, fn))
HTML_FILES.sort()

href_re = re.compile(r'(?:href|action)\s*=\s*"([^"]*)"', re.I)
onclick_re = re.compile(r"""(?:onclick|onsubmit)\s*=\s*(?:"([^"]*)"|'([^']*)')""", re.I)
FORM_ID = re.compile(r'f=([a-f0-9]{24})')

broken = defaultdict(list)      # page -> [(href, reason)]
dead_buttons = defaultdict(list)
external = set()
page_forms = defaultdict(set)   # page -> set(form ids)
portal_products = defaultdict(set)

SITE_HOSTS = ('www.directcare.ai', 'directcare.ai')

for path in HTML_FILES:
    rel = '/' + os.path.relpath(path, ROOT).replace(os.sep, '/')
    with open(path, encoding='utf-8', errors='replace') as f:
        html = f.read()
    html = html.replace('&amp;', '&')

    for fid in FORM_ID.findall(html):
        page_forms[rel].add(fid)
    for prod in re.findall(r'portal\.tellescope\.com/register\?product=([a-z0-9-]+)', html):
        portal_products[rel].add(prod)

    for m in href_re.finditer(html):
        raw = m.group(1).strip()
        if not raw:
            dead_buttons[rel].append((raw or '(empty)', 'empty href'))
            continue
        low = raw.lower()
        if low in ('#',) :
            dead_buttons[rel].append((raw, 'href="#" (no target)'))
            continue
        if low.startswith('javascript:'):
            if 'void' in low or low in ('javascript:;',):
                dead_buttons[rel].append((raw, 'javascript:void dead link'))
            continue
        if low.startswith(('mailto:', 'tel:', 'sms:', 'data:')):
            continue
        if low.startswith('#'):
            # in-page anchor: check id/name exists
            anchor = raw[1:]
            if anchor and not re.search(r'(?:id|name)\s*=\s*["\']?'+re.escape(anchor)+r'\b', html):
                broken[rel].append((raw, 'in-page anchor target not found'))
            continue
        # normalize protocol-relative
        if low.startswith('//'):
            raw = 'https:' + raw
            low = raw.lower()
        if low.startswith('http'):
            mhost = re.match(r'https?://([^/]+)(/[^?#]*)?', raw)
            host = mhost.group(1).lower() if mhost else ''
            if any(host == h or host.endswith('.'+h) for h in SITE_HOSTS):
                sub = mhost.group(2) or '/'
                sub = sub.split('?')[0].split('#')[0]
                if not resolves(sub):
                    broken[rel].append((raw, f'own-site path does not resolve: {sub}'))
            else:
                external.add((host, raw.split('?')[0][:90]))
            continue
        # relative or root-absolute internal
        target = raw.split('?')[0].split('#')[0]
        if not target:
            continue
        if not target.startswith('/'):
            base = os.path.dirname(rel)
            target = os.path.normpath(os.path.join(base, target))
        if not resolves(target):
            broken[rel].append((raw, f'internal path does not resolve: {target}'))

    for m in onclick_re.finditer(html):
        js = (m.group(1) or m.group(2) or '')
        u = re.search(r"""(?:location\.href|window\.open|location\.assign|location\s*=)\s*[=(]?\s*['"]([^'"]+)['"]""", js)
        if u:
            t = u.group(1)
            tl = t.lower()
            if tl.startswith('http') or tl.startswith('mailto') or tl.startswith('tel'):
                continue
            tp = t.split('?')[0].split('#')[0]
            if tp.startswith('/') and not resolves(tp):
                broken[rel].append((t, f'onclick nav path does not resolve: {tp}'))

# ---- 4. Report --------------------------------------------------------------
print("="*78)
print(f"AUDIT: {len(HTML_FILES)} HTML pages scanned")
print("="*78)

print("\n########## BROKEN INTERNAL LINKS ##########")
if not any(broken.values()):
    print("  none ✅")
for pg in sorted(broken):
    if broken[pg]:
        print(f"\n{pg}")
        for href, why in broken[pg]:
            print(f"   ✗ {href}   -- {why}")

print("\n########## DEAD BUTTONS (href=# / empty / js:void) ##########")
tot=0
for pg in sorted(dead_buttons):
    if dead_buttons[pg]:
        print(f"\n{pg}  ({len(dead_buttons[pg])})")
        seen=set()
        for href, why in dead_buttons[pg]:
            k=(href,why)
            if k in seen: continue
            seen.add(k); tot+=1
            print(f"   • {href}  -- {why}")
if tot==0: print("  none ✅")

print("\n########## INTAKE FORM MAP (non-blog product pages) ##########")
for pg in sorted(set(page_forms)|set(portal_products)):
    if pg.startswith('/blog/'): continue
    forms = ' '.join(sorted(page_forms.get(pg,[])))
    prods = ' '.join(sorted(portal_products.get(pg,[])))
    print(f"   {pg:<58} {forms} {('product='+prods) if prods else ''}")

print("\n########## EXTERNAL HOSTS REFERENCED ##########")
hosts=defaultdict(int)
for h,_ in external: hosts[h]+=1
for h in sorted(hosts): print(f"   {h}  ({hosts[h]})")
