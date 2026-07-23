# TRACKING.md — directcare-home (www.directcare.ai)

Map of every page → event → destination. Companion docs: `PINTEREST-CAPI-SETUP.md`,
`ROKU-CAPI-SETUP.md`, and the UTM taxonomy at
`~/DirectCareAI-SandBox/docs/DCA-UTM-NAMING-STANDARD.md`.

## Vendor tags (inline in every page `<head>`, no build step)

| Vendor | ID | Load pattern |
|---|---|---|
| Google Tag Manager | `GTM-N7ZG3PT8` | Loads immediately (gtm.js) |
| Meta Pixel | `1567193354573862` | Stub queues immediately; fbevents.js lazy-loads on first interaction or a timeout (10s on content pages, 2.5s on `/thankyou`) |
| Pinterest Tag | `549770546296` | Stub queues immediately; core.js lazy-loads (same pattern) |
| Roku Pixel | `Pacc66xnjXEH` | Stub queues immediately; rkp.loader.js lazy-loads (same pattern) |

Server-side relays (Vercel functions, no-op with HTTP 200 until env vars are set):

| Endpoint | Destination | Env vars required |
|---|---|---|
| `/api/pinterest-capi` | Pinterest Conversions API | `PINTEREST_CAPI_TOKEN`, `PINTEREST_AD_ACCOUNT_ID` (token rotation pending — see `PINTEREST-CAPI-SETUP.md`) |
| `/api/roku-capi` | Roku Conversions API | `ROKU_CAPI_TOKEN`, `ROKU_EVENT_GROUP_ID` (live, verified 2026-06-30) |
| `/api/lead` | Google Sheet webhook (geo-blocked waitlist only) | `SHEET_WEBHOOK_URL` |

## Page → event → destination

### All pages (site-wide, per-page inline snippets)

| Trigger | Event | Destination |
|---|---|---|
| Page load | `PageView` | Meta Pixel |
| Page load | `page` | Pinterest |
| Page load | `PAGE_VIEW` | Roku |
| Page load | GTM container fires | GA4 via GTM `GTM-N7ZG3PT8` |
| Click on `a[href*="tellescope.com"]` | `Lead` (content_name = link text) | Meta Pixel (browser only, no CAPI) |
| Click on `a[href*="portal.tellescope.com"]` | `lead` + `LEAD` (shared `event_id`) | Pinterest (browser + `/api/pinterest-capi`), Roku (browser + `/api/roku-capi`) |

> **KNOWN GAP (pre-existing, found 2026-07-23, not yet fixed):** the Pinterest/Roku
> click listener matches `portal.tellescope.com` — the patient-portal *login* link —
> but every intake CTA points at `business.tellescope.com/e/public/form?...`.
> So Pinterest/Roku lead events have effectively **never fired on real intake clicks**;
> only the Meta listener (`tellescope.com` substring) catches them. Fix-forward
> option: change the matcher to `'tellescope.com'` in each page's inline snippet
> (15+ files carry their own copy). The `/thankyou` page below closes the same gap
> from the other side — it fires on *completed* intakes, a far better signal than a
> click anyway.

### `/thankyou` (NEW — the conversion page)

Reached with `?p=<pillar>`; pillar allowlist = `surgemax` `trt` `glp1m` `glp1w`
`hrt` `hairm` `hairw` `labs` `supps` (anything else → `unspecified`). Fires once
per program per browser session (sessionStorage guard); one shared `event_id`
dedupes browser vs server events. `noindex,nofollow`.

| Event | Params | Destination |
|---|---|---|
| `lead_submitted` (dataLayer push) | `program`, `event_id` | GA4 via GTM — **needs a GTM trigger + GA4 event tag mapped to it (one-time GTM change, see below)** |
| `Lead` | `content_name` = pillar, `eventID` | Meta Pixel |
| `lead` | `event_id` | Pinterest (browser) + `/api/pinterest-capi` beacon |
| `LEAD` | `event_id` | Roku (browser) + `/api/roku-capi` beacon |

Privacy rule: event params carry the **pillar code only** (mirrors public page
paths). Never add condition language, clinical detail, or personal data to any
event, URL, or UTM.

Per-funnel aliases (302s in `vercel.json`, for pasting a single clean URL into
Tellescope form settings):

| Alias | Resolves to |
|---|---|
| `/surge-max-thankyou` | `/thankyou?p=surgemax` |
| `/trt-thankyou` | `/thankyou?p=trt` |
| `/hrt-thankyou` | `/thankyou?p=hrt` |
| `/mens-weight-loss-thankyou` | `/thankyou?p=glp1m` |
| `/womens-weight-loss-thankyou` | `/thankyou?p=glp1w` |
| `/mens-hair-loss-thankyou` | `/thankyou?p=hairm` |
| `/womens-hair-loss-thankyou` | `/thankyou?p=hairw` |

### `/unavailable` (geo-blocked waitlist)

| Event | Destination |
|---|---|
| Waitlist form POST | `/api/lead` → Google Sheet + inbox email |

## The funnel handoff — READ THIS BEFORE EXPECTING /thankyou TRAFFIC

Every program CTA is a plain `<a href>` **full navigation away from our domain**
to a Tellescope-hosted public form:

| Program page(s) | Tellescope form `f=` |
|---|---|
| `/surge-max` | `6a357b176f59958089c9161f` |
| `/mens-weight-loss`, `/womens-weight-loss`, `/weight-loss` | `69bb46e1daa89ddd6544007c` (one shared form) |
| `/mens-hair-loss`, `/womans-hair-loss` | `69c1e76a88e5800ffbb0c73b` (one shared form) |
| `/testosterone-replacement-therapy`, trt-* persona pages | `683872d1d3039feba26af038` |
| `/hormone-replacement-therapy` (+ symptom subpages, hrt-moms, perimenopause) | `69c1e89bf262d405b182c3fa` |

**Today, users never return to www.directcare.ai after submitting.** The form URL
carries no return/redirect parameter (`nextFormId=` chains Tellescope forms, not
external URLs). Therefore `/thankyou` receives **zero traffic until Tellescope is
configured to send submitters back**. Options, in preference order:

1. **Tellescope form "redirect on completion"** (form settings, per form): set the
   completion redirect to the matching alias, e.g.
   `https://www.directcare.ai/surge-max-thankyou`. One setting per form, five
   forms total. This is the intended activation path for this page.
2. **Tellescope S2S postback / webhook** on form submission → hit
   `/api/pinterest-capi` + `/api/roku-capi` (and a future Meta CAPI relay)
   server-to-server with the submitted email for match quality. Independent of
   the browser entirely; also the only path that attributes the affiliate
   `utm_clickId` already being propagated onto Tellescope links.
3. **Embed the form** (iframe/JS embed on our domain) so submission stays on
   www.directcare.ai and the page itself can detect completion. Larger change;
   check Tellescope embed support + HIPAA posture first.

Until one of these ships, the only lead signals remain the *click* events above
(Meta working; Pinterest/Roku broken per the KNOWN GAP note).

## One-time GTM step (after deploy)

In GTM `GTM-N7ZG3PT8`: add a Custom Event trigger for `lead_submitted`, a
dataLayer variable for `program`, and a GA4 event tag sending `lead_submitted`
with the `program` param. Without this, the dataLayer push lands in the container
but GA4 never sees it.
