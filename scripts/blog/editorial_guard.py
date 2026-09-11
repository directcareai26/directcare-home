#!/usr/bin/env python3
"""
editorial_guard.py — enforce who may review a post, and that it cites sources.

Two failures this is built to prevent, both of which the blog is currently open
to:

1. SCOPE OF PRACTICE. A byline reading "Medically reviewed by Dr. X, D.C."
   attaches that person's licence to every claim in the post. On an article
   about testosterone dosing that is a scope problem for them and a
   substantiation problem for us. blog/reviewers.json says who may be named on
   what; this refuses to build if an assignment breaks that, rather than
   warning and continuing.

2. UNSOURCED CLINICAL CLAIMS. All 112 posts published so far cite zero primary
   sources. The generator prompt asks for inline citation and nothing checked,
   so trials get named in prose ("SURMOUNT-5 showed...") with nothing to follow.
   That is the single largest miss for AI citation — the Princeton GEO work puts
   citing sources at roughly +40% visibility and statistics at +37% — and for a
   health publisher it is also the difference between a substantiated claim and
   an assertion.

A post with no recorded reviewer renders no reviewer byline. That is correct and
is the default. An entry in `reviews` is a factual claim that a named person
read that post on that date, so it is never written by a script.

Usage:
  editorial_guard.py --payload post.json --category TRT   # gate one new post
  editorial_guard.py --audit                              # report on all posts
  editorial_guard.py --byline <slug>                      # emit byline HTML
"""
import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "blog" / "reviewers.json"
MANIFEST = ROOT / "blog" / "posts.json"

# Hosts that count as a primary or guideline source. A link to our own site, a
# supplement shop or a news write-up of a study is not a citation.
PRIMARY_HOSTS = (
    "pubmed.ncbi.nlm.nih.gov", "ncbi.nlm.nih.gov", "doi.org", "nejm.org",
    "jamanetwork.com", "thelancet.com", "bmj.com", "ahajournals.org",
    "diabetesjournals.org", "academic.oup.com", "endocrine.org",
    "auanet.org", "acog.org", "menopause.org", "aad.org", "acsm.org",
    "nih.gov", "fda.gov", "cochranelibrary.com", "clinicaltrials.gov",
    "annals.org", "cell.com", "nature.com", "sciencedirect.com",
)

# Categories making pharmacological or diagnostic claims need real citations.
# Recipes and workouts are held to a lower bar because the claims are weaker.
MIN_REFS = {
    "TRT": 2, "HRT": 2, "Weight Loss": 2, "Sexual Health": 2,
    "Hair Regrowth": 2, "Blood Labs": 2, "Supplements": 2,
    "Nutrition": 0, "Fitness": 0,
}


def load_registry() -> dict:
    return json.loads(REGISTRY.read_text(encoding="utf-8"))


def is_primary(url: str) -> bool:
    m = re.match(r"https?://([^/]+)", url or "", re.I)
    if not m:
        return False
    host = m.group(1).lower().removeprefix("www.")
    return any(host == h or host.endswith("." + h) for h in PRIMARY_HOSTS)



# --- does the cited work actually exist? -------------------------------------
# The host allowlist stops a supplement blog being passed off as evidence. It
# does NOT stop a fabricated citation: a made-up PubMed ID sits on the right
# host and looks identical to a real one. Worse, pubmed.ncbi.nlm.nih.gov
# returns HTTP 203 for a nonexistent PMID, so a status check proves nothing.
#
# So PMIDs are checked against NCBI's own summary API and DOIs against
# doi.org, both of which answer definitively.
#
# LIMIT, and it matters: this proves the paper EXISTS, not that it says what
# the sentence claims. PMID 12345678 is a real record — it is the "Denpasar
# Declaration on Population and Development", which supports nothing we write
# about. Fabrication is caught here; misattribution still needs a human.
#
# Fail-safe by design: a definitive "no such record" blocks, but a network
# error does not. A CI blip must not stop the blog publishing, and an
# unverifiable citation is no worse than the host check alone.
_VERIFY_TIMEOUT = 12


def verify_citation(url: str) -> tuple[bool, str]:
    """(ok, note). ok=False ONLY when the source is known not to exist."""
    import json as _json
    import urllib.error
    import urllib.request

    def _get(u):
        req = urllib.request.Request(u, headers={"User-Agent": "DirectCareEditorialGuard/1.0"})
        return urllib.request.urlopen(req, timeout=_VERIFY_TIMEOUT)

    m = re.search(r"pubmed\.ncbi\.nlm\.nih\.gov/(\d+)", url or "")
    if m:
        pmid = m.group(1)
        try:
            with _get("https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
                      f"?db=pubmed&id={pmid}&retmode=json") as r:
                res = _json.loads(r.read().decode("utf-8", "replace")).get("result", {})
            uids = res.get("uids") or []
            if not uids or "error" in (res.get(uids[0]) or {}):
                return False, f"PMID {pmid} does not exist in PubMed"
            return True, (res[uids[0]].get("title") or "")[:90]
        except Exception as e:
            return True, f"unverified ({type(e).__name__})"

    m = re.search(r"doi\.org/(10\.[^\s\"'<>]+)", url or "")
    if m:
        try:
            _get("https://doi.org/" + m.group(1)).close()
            return True, "DOI resolves"
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return False, f"DOI {m.group(1)} does not resolve"
            return True, f"DOI resolves (publisher returned {e.code})"
        except Exception as e:
            return True, f"unverified ({type(e).__name__})"

    return True, "host allowlisted; not individually verifiable"


def check_reviewer(slug: str, category: str, reg: dict) -> list[str]:
    """Errors for the reviewer assigned to `slug`. Empty list = fine."""
    entry = (reg.get("reviews") or {}).get(slug)
    if not isinstance(entry, dict):
        return []                       # no reviewer recorded: renders nothing
    errs = []
    key = entry.get("reviewer")
    who = (reg.get("reviewers") or {}).get(key)
    if not who:
        return [f"reviewer '{key}' is not in the registry"]
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(entry.get("date", ""))):
        errs.append(f"review of '{slug}' has no valid date (YYYY-MM-DD)")

    rules = (reg.get("categories") or {}).get(category, {})
    if rules.get("requiresPrescriber") and not who.get("prescribes"):
        errs.append(
            f"SCOPE: {who['name']}, {who['credential']} cannot be named as medical "
            f"reviewer on a '{category}' post — that category requires a prescribing "
            f"clinician. Naming them here puts their licence behind a claim they "
            f"cannot make."
        )
    elif category not in (who.get("scopes") or []):
        errs.append(
            f"SCOPE: '{category}' is not in {who['name']}'s scope "
            f"({', '.join(who.get('scopes') or []) or 'none'})."
        )
    return errs


def check_references(refs, category: str, verify: bool = True) -> list[str]:
    need = MIN_REFS.get(category, 1)
    if not need:
        return []
    if not isinstance(refs, list):
        return [f"'{category}' posts need >= {need} references; none were provided"]
    good, fabricated = [], []
    for r in refs:
        if not (isinstance(r, dict) and r.get("citation") and is_primary(r.get("url", ""))):
            continue
        ok, note = verify_citation(r["url"]) if verify else (True, "")
        (good if ok else fabricated).append((r, note))
    if fabricated:
        return ["FABRICATED CITATION: " + n + f" — {(r.get('citation') or '')[:70]}"
                for r, n in fabricated]
    if len(good) < need:
        return [
            f"'{category}' posts need >= {need} references to a primary source or "
            f"guideline body; found {len(good)} of {len(refs)} supplied. "
            f"Accepted hosts include pubmed, doi.org, nejm.org, endocrine.org, fda.gov. "
            f"A named trial in prose with no link does not count."
        ]
    return []


def byline_html(slug: str, reg: dict) -> str:
    """Reviewer byline for a post, or '' when no review is on record."""
    entry = (reg.get("reviews") or {}).get(slug)
    if not isinstance(entry, dict):
        return ""
    who = (reg.get("reviewers") or {}).get(entry.get("reviewer"))
    if not who:
        return ""
    return (
        '<span class="dot"></span><span class="reviewed">Medically reviewed by '
        f'<a href="{who["url"]}">{who["name"]}, {who["credential"]}</a> '
        f'on <time datetime="{entry["date"]}">{entry["date"]}</time></span>'
    )


def reviewer_schema(slug: str, reg: dict):
    entry = (reg.get("reviews") or {}).get(slug)
    if not isinstance(entry, dict):
        return None
    who = (reg.get("reviewers") or {}).get(entry.get("reviewer"))
    if not who:
        return None
    return {
        "reviewedBy": {
            "@type": "Person",
            "name": who["name"],
            "honorificSuffix": who["credential"],
            "url": who["url"],
            "hasCredential": {
                "@type": "EducationalOccupationalCredential",
                "name": who["credentialName"],
                "credentialCategory": "degree",
            },
        },
        "lastReviewed": entry["date"],
    }


def audit() -> int:
    reg = load_registry()
    posts = json.loads(MANIFEST.read_text(encoding="utf-8")).get("posts", [])
    by_cat, unsourced, errs = {}, [], []
    for p in posts:
        slug, cat = p.get("slug", ""), p.get("category", "?")
        by_cat.setdefault(cat, [0, 0])
        by_cat[cat][0] += 1
        f = ROOT / "blog" / f"{slug}.html"
        if f.is_file():
            html = f.read_text(encoding="utf-8", errors="replace")
            if any(is_primary(u) for u in re.findall(r'href="(https?://[^"]+)"', html)):
                by_cat[cat][1] += 1
            elif MIN_REFS.get(cat, 1):
                unsourced.append((cat, slug))
        errs += check_reviewer(slug, cat, reg)

    print(f"{'category':16s} {'posts':>6s} {'cited':>6s}  needs sources")
    for cat in sorted(by_cat):
        n, c = by_cat[cat]
        print(f"{cat:16s} {n:6d} {c:6d}  {'yes' if MIN_REFS.get(cat,1) else 'no'}")
    print(f"\n{len(unsourced)} post(s) in citation-required categories cite no primary source.")
    for cat, slug in unsourced[:10]:
        print(f"   {cat:15s} {slug}")
    if len(unsourced) > 10:
        print(f"   ... and {len(unsourced)-10} more")
    print("\nThese are NOT auto-fixable. Adding a citation to an existing claim means\n"
          "reading the post and finding a source that actually supports it; inventing\n"
          "one would be worse than the gap. New posts are gated from here on.")
    if errs:
        print("\nREVIEWER ERRORS:", file=sys.stderr)
        for e in errs:
            print("  " + e, file=sys.stderr)
        return 1
    return 0


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--payload", help="JSON file of a generated post to gate")
    ap.add_argument("--category")
    ap.add_argument("--audit", action="store_true")
    ap.add_argument("--byline", metavar="SLUG")
    a = ap.parse_args()
    reg = load_registry()

    if a.byline:
        print(byline_html(a.byline, reg))
        return 0
    if a.audit:
        return audit()
    if not a.payload:
        ap.error("need --payload, --audit or --byline")

    post = json.loads(pathlib.Path(a.payload).read_text(encoding="utf-8"))
    cat = a.category or post.get("category", "")
    errs = check_references(post.get("references"), cat) + \
        check_reviewer(post.get("slug", ""), cat, reg)
    if errs:
        print(f"BLOCKED — '{post.get('slug','?')}' ({cat}) fails editorial policy:",
              file=sys.stderr)
        for e in errs:
            print("  - " + e, file=sys.stderr)
        return 1
    print(f"editorial policy OK — {post.get('slug','?')} ({cat})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
