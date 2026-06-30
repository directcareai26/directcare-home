#!/usr/bin/env python3
"""
daily_report.py — DirectCare AI daily SEO + AEO + GEO intelligence report.

Pulls REAL data and emails/Slacks a single daily brief to Dache:
  • SEO   — Google Search Console: keywords we rank for, week-over-week movement,
            branded vs non-branded, and "striking distance" opportunities.
  • AEO/GEO — whether AI engines (ChatGPT/Gemini) cite DirectCare AI for our
            vertical queries (reuses the existing ai-citation-monitor engine calls).
  • Mentions — web pages that referenced DirectCare AI / directcare.ai in the last few days.
  • Keywords — what we rank for now + keywords we SHOULD target (with rationale).

Credentials: read from environment first (GitHub Actions secrets), then fall back to
the local ~/DirectCareAI-SandBox/tooling/.vault for dry-runs.

Usage:
  python daily_report.py --dry-run     # build report, print + write to out/, no send
  python daily_report.py --send        # build + deliver via Slack webhook + Gmail SMTP
  python daily_report.py --send --no-aeo   # skip the (slower) AI-citation pass
"""
import os, sys, json, html, ssl, smtplib, datetime, argparse, pathlib, urllib.request, urllib.error

ROOT = pathlib.Path(__file__).resolve().parents[2]          # ~/DirectCareAI-SandBox
VAULT = ROOT / "tooling" / ".vault"
OUT = pathlib.Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)

SITE = "sc-domain:directcare.ai"
BRAND_TERMS = ["directcare", "direct care", "directcareai", "direct care ai", "surge max", "surgemax"]
COMPETITORS = ["Hims", "Hers", "Ro", "Henry Meds", "Mochi Health", "Noom", "BlueChew", "Nurx", "Found", "Sesame"]
VERTICALS = {
    "HRT (women)": "online HRT / bioidentical hormone therapy for women, perimenopause, menopause",
    "TRT (men)": "online testosterone replacement therapy, enclomiphene, low T",
    "Weight loss": "compounded semaglutide / tirzepatide GLP-1 telehealth",
    "Sexual health": "compounded ED treatment, sildenafil/tadalafil, 4-in-1 Surge Max",
    "Hair loss": "topical/oral finasteride, minoxidil, women's hair regrowth",
    "Blood labs": "at-home hormone blood panels, 80+ biomarker testing",
    "Chronic care / RPM": "remote patient monitoring, chronic condition management",
}

# ---------------------------------------------------------------- credentials
def load_vault_env():
    """Populate os.environ from vault .env files if keys are not already set (local dry-run)."""
    files = ["llm_providers.env", "openai.env", "google_api_key.env", "slack.env", "gmail_smtp.env"]
    for f in files:
        p = VAULT / f
        if not p.exists():
            continue
        for line in p.read_text().splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))

def gsc_credentials():
    """Build GSC creds from GSC_TOKEN_JSON env (CI) or the vault file (local)."""
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

# ---------------------------------------------------------------- SEO (GSC)
def is_branded(q):
    ql = q.lower()
    return any(b in ql for b in BRAND_TERMS)

def gsc_query(svc, start, end):
    body = {"startDate": str(start), "endDate": str(end), "dimensions": ["query"], "rowLimit": 25000}
    rows = svc.searchanalytics().query(siteUrl=SITE, body=body).execute().get("rows", [])
    return {r["keys"][0]: r for r in rows}

def seo_section():
    from googleapiclient.discovery import build
    svc = build("searchconsole", "v1", credentials=gsc_credentials(), cache_discovery=False)
    end = datetime.date.today() - datetime.timedelta(days=3)        # GSC lags ~3 days
    start = end - datetime.timedelta(days=6)                        # last 7 days
    pend = start - datetime.timedelta(days=1)
    pstart = pend - datetime.timedelta(days=6)                      # prior 7 days
    cur = gsc_query(svc, start, end)
    prev = gsc_query(svc, pstart, pend)

    def totals(d):
        c = sum(r["clicks"] for r in d.values()); i = sum(r["impressions"] for r in d.values())
        return int(c), int(i)
    cc, ci = totals(cur); pc, pi = totals(prev)

    rows = list(cur.values())
    branded = [r for r in rows if is_branded(r["keys"][0])]
    nonbranded = [r for r in rows if not is_branded(r["keys"][0])]
    top = sorted(rows, key=lambda r: (-r["clicks"], -r["impressions"]))[:15]
    striking = sorted([r for r in nonbranded if 5 <= r["position"] <= 20 and r["impressions"] >= 10],
                      key=lambda r: -r["impressions"])[:15]
    # newly-appearing non-branded queries vs prior week
    new_q = sorted([r for r in nonbranded if r["keys"][0] not in prev and r["impressions"] >= 5],
                   key=lambda r: -r["impressions"])[:10]

    return {
        "range": f"{start} → {end}", "prior": f"{pstart} → {pend}",
        "clicks": cc, "impressions": ci, "clicks_prev": pc, "impressions_prev": pi,
        "n_queries": len(rows), "n_branded": len(branded), "n_nonbranded": len(nonbranded),
        "top": [(r["keys"][0], int(r["clicks"]), int(r["impressions"]), round(r["position"], 1)) for r in top],
        "striking": [(r["keys"][0], int(r["impressions"]), int(r["clicks"]), round(r["position"], 1)) for r in striking],
        "new": [(r["keys"][0], int(r["impressions"]), round(r["position"], 1)) for r in new_q],
    }

# ---------------------------------------------------------------- LLM helpers
def openai_websearch(prompt):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    body = {"model": "gpt-4o", "tools": [{"type": "web_search_preview"}], "input": prompt}
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.load(r)
        chunks = []
        for item in data.get("output", []):
            for c in item.get("content", []) or []:
                if c.get("type") in ("output_text", "text"):
                    chunks.append(c.get("text", ""))
        return "\n".join(chunks).strip() or json.dumps(data)[:500]
    except Exception as e:
        return f"(openai web search failed: {e})"

def openai_chat(prompt):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    body = {"model": "gpt-4o", "messages": [{"role": "user", "content": prompt}], "temperature": 0.3}
    req = urllib.request.Request(
        "https://api.openai.com/v1/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            data = json.load(r)
        return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"(openai chat failed: {e})"

# ---------------------------------------------------------------- AEO / GEO
def aeo_section():
    """Ask AI engines our vertical queries; measure whether DirectCare AI is cited."""
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return {"available": False}
    probes = [
        ("HRT", "Best online HRT clinic for women in their 40s with blood labs included? List specific providers."),
        ("TRT", "Best online TRT clinic in 2026 with bloodwork included? List specific providers."),
        ("Weight loss", "Best telehealth for compounded tirzepatide / semaglutide with care coaching? List providers."),
        ("Sexual health", "Best online ED clinic offering a compounded 4-in-1 sexual health formula? List providers."),
        ("Hair loss", "Best online hair regrowth clinic for women and men? List specific providers."),
    ]
    results = []
    for vert, q in probes:
        ans = openai_websearch(q) or ""
        al = ans.lower()
        cited = any(b in al for b in ["directcare", "direct care ai", "surge max"])
        comps = [c for c in COMPETITORS if c.lower() in al]
        results.append({"vertical": vert, "cited": cited, "competitors": comps})
    wins = sum(1 for r in results if r["cited"])
    return {"available": True, "win_rate": f"{wins}/{len(results)}", "results": results}

# ---------------------------------------------------------------- mentions
def mentions_section():
    prompt = (
        "Search the web for pages, articles, forums, Reddit threads, directories, or press "
        "that mention 'DirectCare AI' or the website directcare.ai, published or updated in the "
        "LAST 7 DAYS. For each, give: the site/title, the URL, the date if known, and a one-line "
        "summary of the mention and its sentiment. If you find none, say so explicitly. "
        "Do NOT include directcare.ai's own pages."
    )
    res = openai_websearch(prompt)
    return res or "(web mention search unavailable — no OPENAI_API_KEY)"

# ---------------------------------------------------------------- keyword reco
def keyword_reco(seo):
    striking = "\n".join(f"- {k} (pos {p}, {i} impressions)" for k, i, c, p in seo["striking"]) or "- (none in striking distance yet)"
    prompt = f"""You are an SEO strategist for DirectCare AI, a US telehealth brand (directcare.ai) selling:
HRT, TRT, GLP-1 weight loss, sexual health (Surge Max), hair loss, blood labs, and chronic care / RPM.
Main competitors: {", ".join(COMPETITORS)}.

Google Search Console "striking distance" queries (we rank pos 5-20 but could push to page 1):
{striking}

Based on these verticals and competitor landscape, recommend 12 high-intent keywords DirectCare AI
SHOULD target but likely is not ranking for yet. For each give: keyword | intent (commercial/informational)
| rough difficulty (low/med/high) | which page should target it. Prioritize commercial, bottom-funnel,
"compounded / without insurance / online / cost" style queries that convert. Be concise; output a clean
markdown table only."""
    res = openai_chat(prompt)
    return res or "(keyword recommendations unavailable — no OPENAI_API_KEY)"

# ---------------------------------------------------------------- render
def arrow(cur, prev):
    if prev == 0:
        return f"{cur} (new)"
    d = cur - prev
    sign = "▲" if d > 0 else ("▼" if d < 0 else "▬")
    pct = (d / prev * 100) if prev else 0
    return f"{cur} {sign}{abs(d)} ({pct:+.0f}% WoW)"

def render_markdown(seo, aeo, mentions, reco, today):
    L = []
    L.append(f"# DirectCare AI — Daily SEO / AEO / GEO Report\n**{today}** · directcare.ai\n")
    L.append("## 1. SEO — Google Search Console")
    L.append(f"_Window: {seo['range']} (vs prior {seo['prior']})_\n")
    L.append(f"- **Clicks:** {arrow(seo['clicks'], seo['clicks_prev'])}")
    L.append(f"- **Impressions:** {arrow(seo['impressions'], seo['impressions_prev'])}")
    L.append(f"- **Queries with data:** {seo['n_queries']} ({seo['n_branded']} branded / {seo['n_nonbranded']} non-branded)\n")
    L.append("**Top keywords we rank for (by clicks):**\n")
    L.append("| Keyword | Clicks | Impr | Avg pos |\n|---|--:|--:|--:|")
    for k, c, i, p in seo["top"]:
        L.append(f"| {k} | {c} | {i} | {p} |")
    L.append("\n**Striking distance — closest to page 1 (push these):**\n")
    if seo["striking"]:
        L.append("| Keyword | Impr | Clicks | Avg pos |\n|---|--:|--:|--:|")
        for k, i, c, p in seo["striking"]:
            L.append(f"| {k} | {i} | {c} | {p} |")
    else:
        L.append("_No non-branded queries in the pos 5–20 band yet — site is early; focus on content + the target keywords below._")
    if seo["new"]:
        L.append("\n**New non-branded queries this week:**")
        for k, i, p in seo["new"]:
            L.append(f"- {k} ({i} impr, pos {p})")
    L.append("\n## 2. AEO / GEO — AI engine citations")
    if aeo.get("available"):
        L.append(f"_Are AI assistants recommending DirectCare AI for our verticals?_ **Win rate: {aeo['win_rate']}**\n")
        L.append("| Vertical | DirectCare cited? | Competitors named |\n|---|:--:|---|")
        for r in aeo["results"]:
            L.append(f"| {r['vertical']} | {'✅' if r['cited'] else '❌'} | {', '.join(r['competitors']) or '—'} |")
    else:
        L.append("_AEO pass skipped (no OPENAI_API_KEY)._")
    L.append("\n## 3. Web mentions (last 7 days)\n")
    L.append(mentions)
    L.append("\n## 4. Keywords we should rank for\n")
    L.append(reco)
    L.append("\n---\n_Automated daily brief. Data: Google Search Console + live AI-engine probes._")
    return "\n".join(L)

def render_slack(seo, aeo, today):
    lines = [f":bar_chart: *DirectCare AI — Daily SEO/AEO/GEO* · {today}",
             f"*SEO (7d):* {arrow(seo['clicks'], seo['clicks_prev'])} clicks · {arrow(seo['impressions'], seo['impressions_prev'])} impressions · {seo['n_queries']} queries"]
    if seo["top"]:
        tops = ", ".join(f"{k} (pos {p})" for k, c, i, p in seo["top"][:5])
        lines.append(f"*Top terms:* {tops}")
    if aeo.get("available"):
        lines.append(f"*AEO/GEO citation win rate:* {aeo['win_rate']} verticals")
    lines.append("Full report emailed to dache@directcareai.com :email:")
    return "\n".join(lines)

# ---------------------------------------------------------------- delivery
def send_slack(text):
    hook = (os.environ.get("SLACK_WEBHOOK_GROWTH")
            or os.environ.get("SLACK_WEBHOOK_PERSONAL")
            or os.environ.get("SLACK_WEBHOOK_MARKETING"))
    if not hook:
        print("! no Slack webhook configured"); return False
    req = urllib.request.Request(hook, data=json.dumps({"text": text}).encode(),
                                 headers={"Content-Type": "application/json"})
    try:
        urllib.request.urlopen(req, timeout=30); print("✓ Slack sent"); return True
    except Exception as e:
        print(f"! Slack failed: {e}"); return False

def md_to_html(md):
    return "<pre style='font-family:ui-monospace,Menlo,monospace;font-size:13px;white-space:pre-wrap'>" + html.escape(md) + "</pre>"

def send_email(subject, md):
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    user = os.environ.get("GMAIL_SMTP_USER"); pw = os.environ.get("GMAIL_SMTP_APP_PASSWORD")
    host = os.environ.get("GMAIL_SMTP_HOST", "smtp.gmail.com"); port = int(os.environ.get("GMAIL_SMTP_PORT", "587"))
    to = os.environ.get("REPORT_EMAIL_TO", "dache@directcareai.com")
    if not (user and pw):
        print("! no Gmail SMTP creds"); return False
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject; msg["From"] = user; msg["To"] = to
    msg.attach(MIMEText(md, "plain")); msg.attach(MIMEText(md_to_html(md), "html"))
    try:
        ctx = ssl.create_default_context()
        if port == 465:
            with smtplib.SMTP_SSL(host, port, context=ctx, timeout=60) as s:
                s.login(user, pw); s.sendmail(user, [to], msg.as_string())
        else:
            with smtplib.SMTP(host, port, timeout=60) as s:
                s.starttls(context=ctx); s.login(user, pw); s.sendmail(user, [to], msg.as_string())
        print(f"✓ Email sent to {to}"); return True
    except Exception as e:
        print(f"! Email failed: {e}"); return False

# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--send", action="store_true", help="deliver via Slack + email")
    ap.add_argument("--dry-run", action="store_true", help="build only; no send")
    ap.add_argument("--no-aeo", action="store_true", help="skip the AI-citation pass")
    ap.add_argument("--no-mentions", action="store_true", help="skip web mention search")
    args = ap.parse_args()
    load_vault_env()
    today = datetime.date.today().isoformat()

    print("· SEO (GSC) ..."); seo = seo_section()
    print("· AEO/GEO ..."); aeo = {"available": False} if args.no_aeo else aeo_section()
    print("· mentions ..."); mentions = "(skipped)" if args.no_mentions else mentions_section()
    print("· keyword reco ..."); reco = keyword_reco(seo)

    md = render_markdown(seo, aeo, mentions, reco, today)
    slack = render_slack(seo, aeo, today)
    (OUT / f"{today}.md").write_text(md)
    (OUT / f"{today}.slack.txt").write_text(slack)
    print(f"\n=== report written to {OUT}/{today}.md ===\n")
    print(md[:1500])

    if args.send:
        send_slack(slack)
        send_email(f"DirectCare AI — Daily SEO/AEO/GEO Report ({today})", md)
    else:
        print("\n(dry-run: not sent. Use --send to deliver.)")

if __name__ == "__main__":
    main()
