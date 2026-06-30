# DirectCare AI — Daily SEO / AEO / GEO Report

Automated daily brief to Dache (Slack + email, 7 AM ET) covering:

1. **SEO** — Google Search Console: keywords we rank for, week-over-week clicks/impressions,
   branded vs non-branded, and "striking distance" (pos 5–20) opportunities.
2. **AEO / GEO** — live probes of AI engines (ChatGPT w/ web search) measuring whether
   DirectCare AI is cited for our verticals vs competitors (Hims, Ro, Found, …).
3. **Web mentions** — pages that referenced DirectCare AI / directcare.ai in the last 7 days.
4. **Keywords we should rank for** — GSC striking-distance + AI-recommended target keywords.

## Run locally (dry-run, reads creds from ../.vault)
```bash
pip install -r requirements.txt
python daily_report.py --dry-run        # build only
python daily_report.py --send           # build + deliver
```

## Cloud (GitHub Actions)
`.github/workflows/daily-seo-report.yml` runs daily at 11:00 UTC (7 AM EDT / 6 AM EST).
Required repo secrets: `GSC_TOKEN_JSON`, `OPENAI_API_KEY`, `SLACK_WEBHOOK_PERSONAL`,
`GMAIL_SMTP_USER`, `GMAIL_SMTP_HOST`, `GMAIL_SMTP_PORT`, `GMAIL_SMTP_APP_PASSWORD`, `REPORT_EMAIL_TO`.
