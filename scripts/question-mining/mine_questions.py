#!/usr/bin/env python3
"""
mine_questions.py — DirectCare AI daily healthcare-question miner.

An "Answer The Public"-style question-discovery engine built on FREE sources
(no paid API), scoped to DirectCare AI's DTC categories, deduped against a
persisted watermark, then clustered / scored / drafted by Claude and delivered
as a daily brief plus a compliance-flagged content queue.

Why not scrape answerthepublic.com directly: it has no public API, aggressively
CAPTCHAs bots, and caps its free tier at a couple searches/day. Its raw material
is just Google Autocomplete + People-Also-Ask, which we pull ourselves.

Sources (all free):
  • Google Search Console  — our REAL question queries + current rank (highest ROI)
  • Google Autocomplete    — the ATP engine itself (suggestqueries.google.com)
  • Reddit (health subs)   — real patient-language questions (best-effort)

Token efficiency (Doctrine D7): the LLM only runs on NET-NEW questions. Everything
already surfaced is filtered out by a persisted watermark (state/seen_questions.json).
Zero new questions => quiet run, no LLM call.

Compliance: nothing here is publishable. Draft specs are written to a content queue
tagged with a health-claim risk flag and DRAFT status, for dca-risk-compliance +
the DCA fleet to review before anything goes near GHL / the site.

Usage:
  python mine_questions.py --dry-run          # build, print, write out/ + queue; no send
  python mine_questions.py --send             # build + deliver Slack + email + write queue
  python mine_questions.py --send --no-reddit # skip the (flaky-from-CI) Reddit pass
"""
import os, re, sys, ssl, json, time, html, smtplib, datetime, argparse, pathlib
import urllib.request, urllib.error, urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parents[1]                                    # ~/directcare-home
VAULT = pathlib.Path.home() / "DirectCareAI-SandBox" / "tooling" / ".vault"
OUT = HERE / "out"; OUT.mkdir(exist_ok=True)
STATE = HERE / "state"; STATE.mkdir(exist_ok=True)
SEEN_FILE = STATE / "seen_questions.json"
QUEUE_DIR = ROOT / "content-queue"; QUEUE_DIR.mkdir(exist_ok=True)

SITE = "sc-domain:directcare.ai"
UA = "dca-question-miner/1.0 (+https://www.directcare.ai; contact@directcareai.com)"

# LLM knobs (per claude-api skill: default opus-4-8; effort tunable for a daily job)
QM_MODEL = os.environ.get("QM_MODEL", "claude-opus-4-8")
QM_EFFORT = os.environ.get("QM_EFFORT", "medium")
MAX_NEW_TO_LLM = int(os.environ.get("QM_MAX_NEW", "70"))  # bound tokens; overflow is logged, not silent

# ------------------------------------------------------------------ categories
# Seeds fan out ATP-style (seed x modifier) into the autocomplete engine. Kept
# to 3 seeds/category x 8 modifiers (~192 calls) — autocomplete expands each into
# ~10 suggestions, so a modest fan-out already yields a deep pool without tripping
# Google's rate limiting. Widen via more seeds + a higher QM_MAX_AUTO if desired.
CATEGORY_SEEDS = {
    "TRT (men)":        ["testosterone replacement therapy", "low testosterone", "enclomiphene"],
    "HRT (women)":      ["hrt for women", "bioidentical hormone therapy", "perimenopause treatment"],
    "GLP-1 / weight":   ["semaglutide", "tirzepatide", "compounded glp-1"],
    "Sexual health":    ["erectile dysfunction treatment", "ed medication online", "surge max"],
    "Hair loss":        ["finasteride", "minoxidil", "womens hair regrowth"],
    "Blood labs":       ["at home hormone test", "testosterone blood test", "hormone blood panel"],
    "Chronic care/RPM": ["remote patient monitoring", "continuous glucose monitor", "chronic care management"],
    "Peptides":         ["peptide therapy", "bpc-157", "peptides for recovery"],
}
PREFIX_MODS = ["how to", "what is", "is", "does"]                       # go before the seed
SUFFIX_MODS = ["cost", "side effects", "without insurance", "online"]   # go after the seed
QWORDS = {"how", "what", "why", "when", "where", "which", "who", "can", "is", "are",
          "do", "does", "should", "will", "would", "could", "am", "was", "were"}

# Health terms used to keep GSC queries (autocomplete/reddit are already scoped).
CATEGORY_TERMS = set()
for _c, _seeds in CATEGORY_SEEDS.items():
    for _s in _seeds:
        for _t in re.findall(r"[a-z0-9\-]+", _s.lower()):
            if len(_t) > 2:
                CATEGORY_TERMS.add(_t)
CATEGORY_TERMS |= {
    "testosterone", "hormone", "hormones", "menopause", "perimenopause", "estrogen",
    "progesterone", "trt", "hrt", "semaglutide", "tirzepatide", "glp", "ozempic",
    "wegovy", "mounjaro", "weight", "erectile", "ed", "sildenafil", "tadalafil",
    "libido", "finasteride", "minoxidil", "hair", "peptide", "peptides", "bloodwork",
    "labs", "biomarker", "cgm", "glucose", "rpm", "monitoring", "telehealth", "clinic",
    "enclomiphene", "sperm", "fertility", "hot", "flashes", "low", "libido",
}


def norm(q):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", q.lower())).strip()


def is_question(q):
    ql = q.strip().lower()
    return ql.endswith("?") or ql.split(" ", 1)[0] in QWORDS or " how " in f" {ql} "


def category_of(q):
    ql = q.lower()
    best, hits = "General", 0
    for cat, seeds in CATEGORY_SEEDS.items():
        h = sum(1 for t in {tok for s in seeds for tok in re.findall(r"[a-z0-9\-]+", s.lower()) if len(tok) > 2} if t in ql)
        if h > hits:
            best, hits = cat, h
    return best


def health_related(q):
    ql = q.lower()
    return any(t in ql for t in CATEGORY_TERMS)


# ------------------------------------------------------------------ credentials
def load_vault_env():
    for f in ["llm_providers.env", "anthropic.env", "google_api_key.env", "slack.env", "gmail_smtp.env"]:
        p = VAULT / f
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def gsc_credentials():
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request
    raw = os.environ.get("GSC_TOKEN_JSON")
    d = json.loads(raw) if raw else json.loads((VAULT / "gsc_token.json").read_text())
    creds = Credentials(
        token=d.get("token"), refresh_token=d.get("refresh_token"),
        token_uri=d.get("token_uri"), client_id=d.get("client_id"),
        client_secret=d.get("client_secret"), scopes=d.get("scopes"),
    )
    if not creds.valid:
        creds.refresh(Request())
    return creds


# ------------------------------------------------------------------ sources
def _get_json(url, timeout=15, tries=2):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.loads(r.read().decode("utf-8", "ignore"))
        except Exception as e:                                # noqa: BLE001 — degrade, don't crash the run
            last = e
            time.sleep(1.0 + i)
    raise last


def google_autocomplete():
    """The ATP engine: expand each seed x modifier and collect Google suggestions."""
    cap = int(os.environ.get("QM_MAX_AUTO", "260"))
    queries = []
    for cat, seeds in CATEGORY_SEEDS.items():
        for seed in seeds:
            queries += [(cat, f"{m} {seed}") for m in PREFIX_MODS]
            queries += [(cat, f"{seed} {m}") for m in SUFFIX_MODS]
    dropped = max(0, len(queries) - cap)
    queries = queries[:cap]

    found = {}                                                # norm -> raw text
    for i, (cat, query) in enumerate(queries, 1):
        try:
            data = _get_json("https://suggestqueries.google.com/complete/search?client=firefox&hl=en&q="
                             + urllib.parse.quote(query))
            for s in (data[1] if isinstance(data, list) and len(data) > 1 else []):
                n = norm(s)
                if n and n not in found:
                    found[n] = s
        except Exception:                                     # noqa: BLE001
            pass
        if i % 40 == 0:
            print(f"  autocomplete {i}/{len(queries)} · {len(found)} suggestions", flush=True)
        time.sleep(0.05)                                      # politeness
    if dropped:
        print(f"  (autocomplete capped at {cap}; dropped {dropped} seed-queries — raise QM_MAX_AUTO)")
    return found


REDDIT_SUBS = ["Testosterone", "TRT", "menopause", "hairloss", "tressless",
               "Semaglutide", "tirzepatidecompound", "loseit", "Peptides", "erectiledysfunction"]


def reddit_questions():
    """Best-effort: Reddit's public JSON is often rate-limited from CI IPs — degrade quietly."""
    found = {}
    ok = 0
    for sub in REDDIT_SUBS:
        try:
            data = _get_json(f"https://www.reddit.com/r/{sub}/top.json?t=week&limit=40")
            for child in data.get("data", {}).get("children", []):
                title = child.get("data", {}).get("title", "").strip()
                if title and is_question(title) and len(title) <= 140:
                    found[norm(title)] = title
            ok += 1
        except Exception:                                     # noqa: BLE001
            pass
        time.sleep(0.5)
    return found, ok


def gsc_questions():
    """Our real search-demand: question-style queries we already get impressions for, with rank."""
    from googleapiclient.discovery import build
    svc = build("searchconsole", "v1", credentials=gsc_credentials(), cache_discovery=False)
    end = datetime.date.today() - datetime.timedelta(days=3)  # GSC lags ~3 days
    start = end - datetime.timedelta(days=27)                 # last 4 weeks for a fuller pool
    body = {"startDate": str(start), "endDate": str(end), "dimensions": ["query"], "rowLimit": 25000}
    rows = svc.searchanalytics().query(siteUrl=SITE, body=body).execute().get("rows", [])
    out = {}
    for r in rows:
        q = r["keys"][0]
        if (is_question(q) or health_related(q)) and health_related(q):
            out[norm(q)] = {"q": q, "impr": int(r["impressions"]), "clicks": int(r["clicks"]),
                            "pos": round(r["position"], 1)}
    return out


# ------------------------------------------------------------------ merge + score
def build_pool(auto, reddit, gsc):
    """Merge sources into one keyed pool with signals attached."""
    pool = {}

    def touch(n, raw, source):
        it = pool.setdefault(n, {"q": raw, "sources": set(), "is_q": is_question(raw),
                                 "category": category_of(raw), "gsc": None})
        it["sources"].add(source)

    for n, raw in auto.items():
        touch(n, raw, "autocomplete")
    for n, raw in reddit.items():
        touch(n, raw, "reddit")
    for n, g in gsc.items():
        touch(n, g["q"], "gsc")
        pool[n]["gsc"] = g
        pool[n]["category"] = category_of(g["q"])
    return pool


def prescore(it):
    s = 0.0
    g = it.get("gsc")
    if g:
        s += 2                                                # real demand we can see
        if 5 <= g["pos"] <= 20 and g["impr"] >= 10:
            s += 3                                            # striking distance — push to page 1
        s += min(g["impr"] / 50.0, 3)
    if len(it["sources"]) > 1:
        s += 2                                                # cross-source corroboration
    if "autocomplete" in it["sources"]:
        s += 1                                                # Google thinks it's commonly searched
    if it["is_q"]:
        s += 1
    return round(s, 2)


# ------------------------------------------------------------------ watermark (D7)
def load_seen():
    if SEEN_FILE.exists():
        try:
            return json.loads(SEEN_FILE.read_text())
        except Exception:                                     # noqa: BLE001
            return {}
    return {}


def save_seen(seen):
    SEEN_FILE.write_text(json.dumps(seen, indent=0, sort_keys=True))


# ------------------------------------------------------------------ LLM synthesis
CLUSTER_SCHEMA = {
    "type": "object", "additionalProperties": False, "required": ["clusters"],
    "properties": {"clusters": {"type": "array", "items": {
        "type": "object", "additionalProperties": False,
        "required": ["theme", "category", "questions"],
        "properties": {
            "theme": {"type": "string"},
            "category": {"type": "string"},
            "questions": {"type": "array", "items": {
                "type": "object", "additionalProperties": False,
                "required": ["question", "intent", "target_keyword", "format", "angle",
                             "outline", "compliance_risk", "compliance_note", "priority"],
                "properties": {
                    "question": {"type": "string"},
                    "intent": {"type": "string", "enum": ["informational", "commercial", "transactional"]},
                    "target_keyword": {"type": "string"},
                    "format": {"type": "string", "enum": ["blog", "short-video", "carousel", "email", "faq"]},
                    "angle": {"type": "string"},
                    "outline": {"type": "array", "items": {"type": "string"}},
                    "compliance_risk": {"type": "string", "enum": ["LOW", "MED", "HIGH"]},
                    "compliance_note": {"type": "string"},
                    "priority": {"type": "integer"},
                }}},
        }}}},
}

SYSTEM = """You are DirectCare AI's SEO content strategist. DirectCare AI is a US telehealth brand
(directcare.ai) offering TRT, HRT (men's + women's), GLP-1 weight loss, sexual health (Surge Max),
hair loss, at-home blood labs, and chronic care / RPM.

You will receive real healthcare questions mined from Google Autocomplete, Google Search Console,
and Reddit. Cluster them into content themes and turn the best ones into brief-ready draft specs.

HARD COMPLIANCE RULES (this is regulated health marketing):
- NEVER state or imply efficacy / medical outcomes ("cures", "guaranteed", "X% of men", "reverses").
- NEVER invent statistics, prices, or testimonials. Use placeholders [STAT], [PRICE], [SOURCE] instead.
- Angles must be EDUCATIONAL/informational, not diagnostic or prescriptive.
- Flag compliance_risk: HIGH for anything touching HRT/TRT/ED/GLP-1/peptide clinical claims,
  dosing, or "results"; MED for category/cost/comparison topics; LOW for general education.
- compliance_note: one line on what a reviewer must check before publish.
Every draft is a DRAFT for human + dca-risk-compliance review — never publish-ready.

Prioritize questions that (a) already show search demand, (b) match a product line, and
(c) are bottom-funnel / commercial where compliant. Return concise, clean JSON only."""


def synthesize(new_items):
    """Cluster + score + draft-spec the net-new questions with Claude. Returns dict or None."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if not key:
        return None
    try:
        import anthropic
    except ImportError:
        print("! anthropic SDK not installed — skipping LLM synthesis")
        return None

    lines = []
    for it in new_items:
        g = it.get("gsc")
        sig = f"[{it['category']}] pre={it['prescore']} src={'+'.join(sorted(it['sources']))}"
        if g:
            sig += f" gsc(impr={g['impr']},clicks={g['clicks']},pos={g['pos']})"
        lines.append(f"- {it['q']}  {sig}")
    payload = "\n".join(lines)

    client = anthropic.Anthropic()
    try:
        resp = client.messages.create(
            model=QM_MODEL, max_tokens=16000,
            thinking={"type": "adaptive"},
            output_config={"effort": QM_EFFORT,
                           "format": {"type": "json_schema", "schema": CLUSTER_SCHEMA}},
            system=SYSTEM,
            messages=[{"role": "user", "content":
                       "Cluster these net-new healthcare questions and produce compliant draft "
                       "specs for the ~15 highest-opportunity ones. Questions with their signals:\n\n"
                       + payload}],
        )
    except Exception as e:                                     # noqa: BLE001
        print(f"! LLM synthesis failed: {e}")
        return None

    text = next((b.text for b in resp.content if b.type == "text"), "")
    try:
        return json.loads(text)
    except Exception:                                          # noqa: BLE001
        print("! could not parse LLM JSON")
        return None


# ------------------------------------------------------------------ render
def render_markdown(today, stats, new_items, clusters):
    L = [f"# DirectCare AI — Daily Healthcare Question Miner\n**{today}** · free-source ATP engine\n"]
    L.append(f"- **New questions today:** {stats['new']} (from {stats['pool']} in pool this run)")
    L.append(f"- **Sources:** autocomplete {stats['auto']} · GSC {stats['gsc']} · Reddit {stats['reddit']}"
             f" ({stats['reddit_subs_ok']}/{len(REDDIT_SUBS)} subs reachable)")
    L.append(f"- **Total ever seen:** {stats['seen_total']}\n")

    if clusters and clusters.get("clusters"):
        L.append("## Top opportunities → draft specs\n")
        allq = [(c["theme"], c["category"], q) for c in clusters["clusters"] for q in c["questions"]]
        allq.sort(key=lambda t: -t[2].get("priority", 0))
        for theme, cat, q in allq[:20]:
            flag = {"HIGH": "🔴", "MED": "🟠", "LOW": "🟢"}.get(q["compliance_risk"], "⚪")
            L.append(f"### {q['question']}")
            L.append(f"_{cat} · {q['intent']} · {q['format']} · compliance {flag} {q['compliance_risk']}_  ")
            L.append(f"**Target keyword:** `{q['target_keyword']}`  ")
            L.append(f"**Angle:** {q['angle']}  ")
            if q.get("outline"):
                L.append("**Outline:** " + " → ".join(q["outline"]))
            L.append(f"**⚠ Compliance:** {q['compliance_note']}\n")
    else:
        L.append("## Top new questions (deterministic ranking — no LLM this run)\n")
        L.append("| Question | Category | Signals | Score |\n|---|---|---|--:|")
        for it in new_items[:25]:
            g = it.get("gsc")
            sig = "+".join(sorted(it["sources"])) + (f" · pos {g['pos']}, {g['impr']} impr" if g else "")
            L.append(f"| {it['q']} | {it['category']} | {sig} | {it['prescore']} |")

    L.append("\n---")
    L.append("_All drafts are DRAFT status — route through dca-risk-compliance before GHL/site. "
             "Sources: Google Autocomplete + Search Console + Reddit (all free). "
             "Watermark dedupes against every prior day (Doctrine D7)._")
    return "\n".join(L)


def render_slack(today, stats, clusters):
    top = []
    if clusters and clusters.get("clusters"):
        themes = [c["theme"] for c in clusters["clusters"][:4]]
        top = themes
    lines = [f":mag: *DirectCare AI — Daily Question Miner* · {today}",
             f"*{stats['new']} net-new* healthcare questions "
             f"(autocomplete {stats['auto']} · GSC {stats['gsc']} · reddit {stats['reddit']})"]
    if top:
        lines.append("*Top themes:* " + " · ".join(top))
    lines.append("Compliance-flagged draft queue in the email + workflow artifact :page_facing_up:")
    return "\n".join(lines)


def write_queue(today, clusters, new_items):
    """Machine-readable draft specs for the DCA fleet to turn into GHL drafts (post-compliance)."""
    payload = {"date": today, "status": "DRAFT — requires dca-risk-compliance review before publish",
               "generated_by": "scripts/question-mining/mine_questions.py"}
    if clusters and clusters.get("clusters"):
        payload["clusters"] = clusters["clusters"]
    else:
        payload["clusters"] = [{"theme": "Ungrouped (no LLM run)", "category": "General",
                                "questions": [{"question": it["q"], "intent": "informational",
                                               "target_keyword": it["q"], "format": "blog",
                                               "angle": "(pending LLM synthesis)", "outline": [],
                                               "compliance_risk": "MED",
                                               "compliance_note": "Manual review required.",
                                               "priority": int(it["prescore"])} for it in new_items[:25]]}]
    (QUEUE_DIR / f"{today}.json").write_text(json.dumps(payload, indent=2))


# ------------------------------------------------------------------ delivery
def send_slack(text):
    hook = (os.environ.get("SLACK_WEBHOOK_GROWTH") or os.environ.get("SLACK_WEBHOOK_MARKETING")
            or os.environ.get("SLACK_WEBHOOK_PERSONAL"))
    if not hook:
        print("! no Slack webhook configured"); return
    try:
        urllib.request.urlopen(urllib.request.Request(
            hook, data=json.dumps({"text": text}).encode(),
            headers={"Content-Type": "application/json"}), timeout=30)
        print("✓ Slack sent")
    except Exception as e:                                     # noqa: BLE001
        print(f"! Slack failed: {e}")


def send_email(subject, md):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    user = os.environ.get("GMAIL_SMTP_USER"); pw = os.environ.get("GMAIL_SMTP_APP_PASSWORD")
    host = os.environ.get("GMAIL_SMTP_HOST", "smtp.gmail.com"); port = int(os.environ.get("GMAIL_SMTP_PORT", "587"))
    to = [t.strip() for t in os.environ.get("REPORT_EMAIL_TO", "dache@directcareai.com").split(",") if t.strip()]
    if not (user and pw):
        print("! no Gmail SMTP creds"); return
    body = ("<pre style='font-family:ui-monospace,Menlo,monospace;font-size:13px;white-space:pre-wrap'>"
            + html.escape(md) + "</pre>")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject; msg["From"] = user; msg["To"] = ", ".join(to)
    msg.attach(MIMEText(md, "plain")); msg.attach(MIMEText(body, "html"))
    try:
        ctx = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=60) as s:
                s.login(user, pw); s.sendmail(user, to, msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=60) as s:
                s.starttls(context=ctx); s.login(user, pw); s.sendmail(user, to, msg.as_string())
        print(f"✓ Email sent to {', '.join(to)}")
    except Exception as e:                                     # noqa: BLE001
        print(f"! Email failed: {e}")


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-reddit", action="store_true")
    ap.add_argument("--no-gsc", action="store_true")
    args = ap.parse_args()
    load_vault_env()
    today = datetime.date.today().isoformat()

    print("· google autocomplete ...", flush=True); auto = google_autocomplete()
    reddit, reddit_ok = ({}, 0)
    if not args.no_reddit:
        print("· reddit ...", flush=True); reddit, reddit_ok = reddit_questions()
    gsc = {}
    if not args.no_gsc:
        print("· gsc ...", flush=True)
        try:
            gsc = gsc_questions()
        except Exception as e:                                # noqa: BLE001
            print(f"! GSC unavailable ({e}) — continuing without it")

    pool = build_pool(auto, reddit, gsc)
    for it in pool.values():
        it["prescore"] = prescore(it)

    seen = load_seen()
    new_items = [dict(it, norm=n) for n, it in pool.items() if n not in seen]
    new_items.sort(key=lambda it: -it["prescore"])
    for it in new_items:                                      # advance the watermark
        seen[it["norm"]] = today

    if len(new_items) > MAX_NEW_TO_LLM:
        print(f"· capping LLM input to top {MAX_NEW_TO_LLM} of {len(new_items)} new "
              f"(remaining {len(new_items) - MAX_NEW_TO_LLM} stay in the watermark for next run)")
    to_llm = new_items[:MAX_NEW_TO_LLM]

    stats = {"new": len(new_items), "pool": len(pool), "auto": len(auto), "gsc": len(gsc),
             "reddit": len(reddit), "reddit_subs_ok": reddit_ok, "seen_total": len(seen)}

    # D7: quiet on empty — no LLM, short note only.
    if not new_items:
        print("· no net-new questions — quiet run (no LLM call)")
        if args.send:
            send_slack(f":mag: DirectCare AI Question Miner · {today} — no net-new questions today.")
        save_seen(seen)
        return

    clusters = synthesize(to_llm) if not args.dry_run or os.environ.get("ANTHROPIC_API_KEY") else None
    for it in to_llm:                                          # serialize sources for JSON out
        it["sources"] = sorted(it["sources"])

    md = render_markdown(today, stats, new_items, clusters)
    slack = render_slack(today, stats, clusters)
    (OUT / f"{today}.md").write_text(md)
    write_queue(today, clusters, new_items)
    print(f"\n=== brief -> {OUT}/{today}.md · queue -> {QUEUE_DIR}/{today}.json ===\n")
    print(md[:1800])

    if args.send:
        send_slack(slack)
        send_email(f"DirectCare AI — Daily Healthcare Question Miner ({today})", md)
    else:
        print("\n(dry-run: not sent. Use --send to deliver.)")

    save_seen(seen)


if __name__ == "__main__":
    main()
