# Roku conversion tracking — client pixel + Conversions API

Tracks **conversions from Roku ad campaigns** on directcare.ai using BOTH halves of Roku's
recommended hybrid setup, deduped against each other by a shared `event_id`:

1. **Client-side JS pixel** (`rkp`, pixel/advertiser id `Pacc66xnjXEH`) — installed
   lazy-loaded in the `<head>` of every page (loader `https://cdn.ravm.tv/ust/dist/rkp.loader.js`,
   same first-interaction/10s pattern as GTM/Meta/Pinterest). Fires `PAGE_VIEW` on load and
   `LEAD` on the portal click-through. **Live in the markup — no config needed.**
2. **Conversions API (server-side)** — relay at [`api/roku-capi.js`](api/roku-capi.js) sends the
   same events server-to-server (IP + user-agent, plus SHA-256-hashed email/phone when
   available) to `https://events.ads.rokuapi.net/v1/events`. **Inert until two secrets are set
   in Vercel** (below) — the site works fine either way.

The conversion trigger on both is a visitor clicking through to the intake portal
(`portal.tellescope.com`) — the genuine signup-intent signal — and both reuse the **same
`event_id`** (shared with Pinterest/Meta) so Roku dedupes browser vs. server within its
10-minute window.

## To turn CAPI on
1. Vercel → project **directcare-home** → **Settings → Environment Variables** → add (Production):
   - `ROKU_CAPI_TOKEN` = the Conversions API bearer key (JWT) from Ads Manager → **Events → CAPI**
   - `ROKU_EVENT_GROUP_ID` = the **Event Group ID** for directcare.ai
   (The key was never pasted in chat — it came in via the local `.secrets` file — so it does
   **not** need rotating, unlike the Pinterest token.)
2. Redeploy (Actions tab → **Deploy to Vercel (manual)**, or `gh workflow run deploy.yml`).

## Verify it's working
- Quick endpoint check: `curl -X POST https://www.directcare.ai/api/roku-capi`
  returns `{"skipped":"capi_not_configured"}` before setup, and a Roku status after.
- Roku Ads Manager → **Events** → your Event Group should show conversions arriving.
- Roku also exposes a **test endpoint** (`/v1/test_events`) — point `ENDPOINT` there
  temporarily in `api/roku-capi.js` if you want to validate without affecting live reporting.

## Event payload (what callers can send)
POST JSON to `/api/roku-capi` from the browser beacon, the iOS app, or an intake form:

| Field | Notes |
|---|---|
| `event_name` | Roku standard events: `LEAD` (default), `SIGN_UP`, `COMPLETE_REGISTRATION`, `PURCHASE`, `ADD_TO_CART`, `INITIATE_CHECKOUT`, `PAGE_VIEW`, … |
| `event_id` | dedupes the server event against any client-side Roku pixel event |
| `event_source` | `website` (default), `mobile_app`, `ctv_app`, `physical_store` |
| `event_time` | unix seconds (defaults to now) |
| `event_url` | page URL (sent as `event_source_url`) |
| `email` / `phone` | **plaintext** — normalized + SHA-256 hashed server-side into `em` / `ph` |
| `em` / `ph` | already SHA-256-hashed — passed through as-is |
| `custom_data` | optional object, e.g. `{ "value": 99.99, "currency": "USD", "order_id": "…" }` |

`client_ip_address` and `client_user_agent` are added automatically from the request;
`is_hashed: true` is set whenever a hashed `em`/`ph` is included. Plaintext email/phone are
hashed in-memory and never logged or stored.
