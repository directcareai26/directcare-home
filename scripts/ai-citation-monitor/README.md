# AI Citation Monitor — Checklist Item #68

Tracks whether AI engines (Perplexity, ChatGPT, Claude, Gemini) cite or mention **DirectCare AI** when users ask real healthcare questions in our verticals.

## What you get on each run

- `results/YYYY-MM-DD.json` — raw responses + parsed mentions per engine
- `results/YYYY-MM-DD.md` — human-readable summary (win rates by engine + vertical, prompt-by-prompt breakdown)
- `results/history.csv` — one row per (date, engine, prompt) for long-term trending

## Quickstart (local)

```bash
cd "scripts/ai-citation-monitor"
pip install requests

# Minimum to be useful — Perplexity has the most accurate web-cited answers
export PERPLEXITY_API_KEY="pplx-..."

# Optional: add more engines for full coverage
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GEMINI_API_KEY="..."

# Run
python monitor.py                            # all prompts, all engines with keys
python monitor.py --vertical hrt             # only HRT vertical
python monitor.py --engine perplexity        # only Perplexity
python monitor.py --dry-run                  # print plan, no API calls
```

## Which API keys actually matter

| Engine | Why it matters | Get key |
|---|---|---|
| **Perplexity** ⭐ | Always returns web sources. The single most useful engine for citation tracking. | https://www.perplexity.ai/account/api/keys |
| Anthropic Claude | Has web_search tool via API. Captures Claude-via-API behavior. | https://console.anthropic.com/settings/keys |
| OpenAI ChatGPT | Has web_search_preview tool in the Responses API. Captures GPT-4o-with-browsing. | https://platform.openai.com/api-keys |
| Google Gemini | Has google_search grounding tool. Closest proxy for Google AI Overviews. | https://aistudio.google.com/apikey |

**Start with Perplexity** ($20/mo for 1k requests, more than enough). Add the others as you scale.

## Prompts — edit `prompts.json`

The corpus is organized by vertical (hrt, trt, weight_loss, sexual_health, hair_loss, blood_labs, general_brand, chronic_care). Add prompts as your ad/SEO targets evolve. Each prompt should be **how a real person would search**, not how we'd describe ourselves.

Also tracked:
- `tracked_brand_terms` — what counts as a "mention" of us
- `competitors_to_watch` — counted in each response so you can see who's winning the SERP-equivalent space

## Reading the report

The MD report shows three things per prompt:

1. **Brand hits** — how many times "DirectCare AI" was mentioned in the response body
2. **Position** — if we were in a numbered list, what rank (1 = first recommendation, etc.)
3. **Cited in sources** — whether `directcare.ai` appeared in the engine's source-citation list (this is the strongest AI-visibility signal)

A "win" for #68 is **trending up week-over-week on the (Mentioned %) and (Cited in sources %)** lines at the top of the report.

## Scheduling (so it runs without you)

### Option A — GitHub Action (recommended)

Drop the workflow at `.github/workflows/ai-citation-monitor.yml`:

```yaml
name: AI Citation Monitor
on:
  schedule:
    - cron: "0 14 * * 1"        # every Monday 14:00 UTC (10am ET)
  workflow_dispatch:

jobs:
  monitor:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - run: pip install requests
      - working-directory: scripts/ai-citation-monitor
        env:
          PERPLEXITY_API_KEY: ${{ secrets.PERPLEXITY_API_KEY }}
          ANTHROPIC_API_KEY:  ${{ secrets.ANTHROPIC_API_KEY }}
          OPENAI_API_KEY:     ${{ secrets.OPENAI_API_KEY }}
          GEMINI_API_KEY:     ${{ secrets.GEMINI_API_KEY }}
        run: python monitor.py
      - name: Commit results
        run: |
          git config user.name "ai-citation-bot"
          git config user.email "bot@directcare.ai"
          git add scripts/ai-citation-monitor/results
          git commit -m "AI citation report $(date -u +%Y-%m-%d)" || echo "no changes"
          git push
```

Add the 4 API keys to **GitHub → Settings → Secrets → Actions**. Reports land in the repo every Monday.

### Option B — Vercel Cron

Already on Vercel. Add this to `vercel.json` to call a serverless function on a schedule:

```json
{
  "crons": [{ "path": "/api/cron/ai-citation-monitor", "schedule": "0 14 * * 1" }]
}
```

Then create `/api/cron/ai-citation-monitor.ts` that shells out to the Python monitor (or rewrite in Node — happy to do that next pass if you'd rather avoid the Python toolchain).

### Option C — Local cron (just on your laptop)

```cron
0 9 * * 1   cd "/path/to/directcare-home/scripts/ai-citation-monitor" && /usr/bin/python3 monitor.py
```

## Cost estimate

40 prompts × 4 engines × 1 run/week ≈ **160 API calls/week**.

- Perplexity sonar: $1 per 1k requests + tokens ≈ **$0.50/wk**
- Anthropic Claude w/ web_search: ~$0.05/call → **~$2/wk**
- OpenAI gpt-4o + web_search: ~$0.04/call → **~$1.60/wk**
- Gemini 2.0 Flash + grounding: ~$0.02/call → **~$0.80/wk**

**Total ~$5/week** to track 40 prompts across all 4 engines weekly. Cheaper than any SaaS.

## SaaS alternative (if you don't want to maintain a script)

| Tool | Price | Notes |
|---|---|---|
| **Profound** | $499+/mo | Most mature, used by big DTC brands. Tracks 1k+ prompts. |
| **Otterly.AI** | $29-249/mo | Best price-for-feature on the market. ChatGPT + Perplexity + Gemini. |
| **AthenaHQ** | $99+/mo | Strong dashboard, real-time alerts. |
| **Peec AI** | $99+/mo | European, GDPR-clean. |
| **Goodie** | $79+/mo | Simple, focused on prompt-level tracking. |

The DIY script in this folder gets you ~80% of what those tools offer for ~$5/week. Move to SaaS when you need fancier dashboards or stakeholder reporting.

## What "good" looks like

Realistic targets for the next 90 days (we just shipped E-E-A-T + schema this month):

| Vertical | Target by D+30 | Target by D+90 |
|---|---|---|
| `general_brand` (queries that name us directly) | 100% mentioned, 100% cited | 100% / 100% |
| `weight_loss` | 5% mentioned | 25% mentioned, 10% cited |
| `hrt`, `trt` | 5% mentioned | 30% mentioned, 15% cited |
| `sexual_health` (Surge Max is unique → easier win) | 20% mentioned | 60% mentioned, 30% cited |
| `hair_loss`, `blood_labs`, `chronic_care` | 0% (baseline) | 10% mentioned |

The corpus is small enough that you can eyeball weekly progress in the MD report — no dashboards needed at this stage.
