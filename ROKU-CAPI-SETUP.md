# Roku Conversions API (CAPI) — turn-on steps

Tracks **conversions from Roku ad campaigns** on directcare.ai.

Every page fires a **`LEAD`** conversion when a visitor clicks through to the intake portal
(`portal.tellescope.com`) — the genuine signup-intent signal — reusing the **same
`event_id`** as the Pinterest/Meta events so Roku can dedupe browser vs. server.

The **Conversions API** relay at [`api/roku-capi.js`](api/roku-capi.js) sends those events
server-to-server (IP + user-agent, plus SHA-256-hashed email/phone when available) to
`https://events.ads.rokuapi.net/v1/events`. It is **inert until you add two secrets in
Vercel** — the site works fine either way.

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
