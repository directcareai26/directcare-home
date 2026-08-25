# Daily Healthcare Question Miner

An **"Answer The Public"-style question-discovery engine** built on **free sources**,
scoped to DirectCare AI's DTC categories. It surfaces the top healthcare questions
people ask each day so we can latch onto them for SEO pages and daily social posts.

> We don't scrape `answerthepublic.com` — it has no API, CAPTCHAs bots, and caps its
> free tier. Its raw material is Google Autocomplete + People-Also-Ask, which we pull
> ourselves, plus our own Search Console demand and real Reddit questions.

## What it does (daily, in the cloud)

```
seed categories → pull questions → filter (healthcare + our lines) →
dedupe vs watermark → cluster/score/draft (Claude) → brief + queue → Slack + email + artifact
```

| Source | Signal | Cost |
|---|---|---|
| **Google Search Console** | our REAL question queries + current rank ("we're #8, push to #3") | free |
| **Google Autocomplete** | the ATP engine itself (`suggestqueries.google.com`) | free |
| **Reddit** (health subs) | real patient-language questions | free, best-effort* |

\* Reddit's public JSON is often rate-limited from GitHub's datacenter IPs. The job
degrades quietly if a sub is unreachable — GSC + Autocomplete carry the value.

## Token efficiency (Doctrine D7)

The LLM only runs on **net-new** questions. Every question ever surfaced is stored in
`state/seen_questions.json` (a cheap deterministic delta-check). Zero new questions →
**quiet run, no LLM call**. In CI the watermark persists via `actions/cache` (rolling
keys), so nothing is committed to the repo and there's **no Vercel deploy side-effect**.

## Compliance gate

Nothing here is publish-ready. Each draft spec carries a health-claim risk flag
(`🔴 HIGH` / `🟠 MED` / `🟢 LOW`) and `status: DRAFT — requires dca-risk-compliance review`.
The LLM is instructed never to state efficacy, invent stats/prices, or write diagnostic
copy — it uses `[STAT]`/`[PRICE]` placeholders. HRT/TRT/ED/GLP-1/peptide claims are
flagged HIGH by default.

## Outputs

- **Brief** → Slack (`#growth`) + email to DaChé, and `out/<date>.md`.
- **Content queue** → `content-queue/<date>.json` — machine-readable draft specs
  (theme, question, target keyword, angle, outline, format, compliance flag).
- Both ship as the workflow **artifact** `question-miner-<run_id>` (30-day retention).

## Fleet handoff — seeding GHL drafts (the compliance-gated last mile)

CI can't reach the GHL MCP or the `dca-risk-compliance` subagent (those live on the DCA
Mac). So CI produces the **draft specs**; the local fleet turns them into GHL drafts:

1. The DCA seat pulls the latest `content-queue/<date>.json` (from the run artifact).
2. `dca-risk-compliance` reviews each spec — anything flagged HIGH gets clinical review.
3. Approved specs → `mcp__ghl__blogs_create-blog-post` (status **draft**) / social
   draft shells (`dca-content-planning` calendar). Never auto-publish.

## Run it locally

```bash
pip install -r requirements.txt
python mine_questions.py --dry-run          # build, print, write out/ + queue; no send
python mine_questions.py --send             # + Slack + email
python mine_questions.py --send --no-reddit # skip the flaky Reddit pass
```

Credentials resolve from env first (GitHub Actions secrets), then the local
`~/DirectCareAI-SandBox/tooling/.vault`. Without `ANTHROPIC_API_KEY` it still produces
a deterministic (non-LLM) ranked brief so the pipeline is testable offline.

## Config knobs (repo → Settings → Variables, optional)

| Var | Default | Notes |
|---|---|---|
| `QM_MODEL` | `claude-opus-4-8` | set to `claude-haiku-4-5` / `claude-sonnet-5` to cut cost |
| `QM_EFFORT` | `medium` | `low`/`medium`/`high`/`xhigh`/`max` |
| `QM_MAX_NEW` | `70` | cap of net-new questions sent to the LLM per run (rest stay for next day) |

## Reuses existing secrets

`GSC_TOKEN_JSON`, `ANTHROPIC_API_KEY`, `SLACK_WEBHOOK_GROWTH`, `GMAIL_SMTP_*`,
`REPORT_EMAIL_TO` — the same set the daily SEO report uses. No new infra.
