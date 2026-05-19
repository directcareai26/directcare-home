# DirectCare AI — Home Page

The unified home page for DirectCare AI — designed to surface every offering (men's, women's, weight loss, HRT, TRT, sexual health, hair regrowth, supplements, blood labs, chronic care) and route to the correct subpage.

Single-file static site. Vanilla HTML / CSS / JS. No build step.

## Live

- Vercel: (set on first deploy)
- GitHub: https://github.com/directcareai26/directcare-home

## Structure

```
index.html         # Full page — nav, hero, gender split, offering grid, how it works, stats, why, testimonials, FAQ, final CTA, footer
icon.png           # Brand mark — favicon
apple-icon.png     # iOS home-screen icon
favicon-16.png     # 16x16 favicon
favicon-32.png     # 32x32 favicon
icon-192.png       # 192x192 PWA icon
```

## Local preview

```bash
python3 -m http.server 3055
open http://localhost:3055
```

Or use the Claude Code `home-page-dcai` launch config (port 3055).

## Linked subpages

| Section | Destination |
|---|---|
| Women's Health hub | https://women.directcare.ai/ |
| Men's Health hub | https://mens.directcare.ai/ |
| Weight Loss (GLP-1) | https://www.directcare.ai/weight-loss-program |
| HRT | https://www.directcare.ai/start-hrt |
| Testosterone (TRT) | https://mens.directcare.ai/#testosterone |
| Sexual Health | https://sexual-health-mocha.vercel.app/ |
| Hair Regrowth (Men) | https://mens-hair-loss.vercel.app/ |
| Hair Regrowth (Women) | https://womens-hair-loss.vercel.app/ |
| Blood Labs (Journeys) | https://www.directcare.ai/journeys |
| Supplements | https://www.directcare.ai/supplements |
| Chronic Condition Care | https://www.directcare.ai/chronicconditioncare |

## Webflow migration

Once final, the page will be broken into Webflow-friendly chunks (each under 50k chars per code embed). The current structure splits cleanly along section boundaries — nav, hero, trust bar, gender split, offering grid, how it works, stats, why-directcare, testimonials, FAQ, final CTA, footer.

## Design system

Matches existing DirectCare AI subpages (mens-hair-loss, womens-hair-loss, mens.directcare.ai, women.directcare.ai, sexual-health-mocha):
- Brand primary: `#af4bed`, deep `#9043bf`, darker `#762ba4`, text `#44215A`
- Lavender soft: `#fbf5fe`, line `#E9D9F2`
- Ink `#281A31`, muted `#5b4d65`
- Fonts: Inter (body) + Manrope (display, 800)
- Radii: 18 / 28 / 40px
