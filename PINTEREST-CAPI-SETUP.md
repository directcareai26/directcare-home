# Pinterest Conversions API (CAPI) — turn-on steps

The Pinterest **Tag** (pixel `549770546296`) is already live in every page's `<head>`.
It fires `PageView` on load and a **`lead`** event when a visitor clicks through to the
intake portal (`portal.tellescope.com`).

The **Conversions API** relay at [`api/pinterest-capi.js`](api/pinterest-capi.js) sends those
same events server-to-server for better match quality and ad-blocker resilience. It is
**inert until you add two secrets in Vercel** — the site works fine either way.

## To turn CAPI on
1. **Rotate the access token** in Pinterest → Ads → **Conversions** → Conversion settings
   (the old `pina_…` token was shared in chat, so treat it as exposed and re-issue it).
2. Vercel → project **directcare-home** → **Settings → Environment Variables** → add (Production):
   - `PINTEREST_CAPI_TOKEN` = the freshly rotated `pina_…` token
   - `PINTEREST_AD_ACCOUNT_ID` = your Pinterest ad account id
3. Redeploy (Actions tab → **Deploy to Vercel (manual)**, or `gh workflow run deploy.yml`).

## Verify it's working
- Pinterest → Conversions → your tag should show **browser + server** events arriving,
  deduplicated by `event_id`.
- Quick endpoint check: `curl -X POST https://www.directcare.ai/api/pinterest-capi`
  returns `{"skipped":"capi_not_configured"}` before setup, and a Pinterest status after.

## Event payload (what callers can send)
POST JSON to `/api/pinterest-capi` from the browser beacon, the iOS app, or an intake form:

| Field | Notes |
|---|---|
| `event_name` | e.g. `lead`, `page_visit`, `signup`, `checkout` (default `lead`) |
| `event_id` | dedupes the server event against the browser `pintrk` event |
| `action_source` | `web` (default), or `app_ios` / `app_android` from the app |
| `event_time` | unix seconds (defaults to now) |
| `event_url` | page URL (sent as `event_source_url`) |
| `email` / `maid` | **plaintext** — normalized + SHA-256 hashed server-side into `em` / `hashed_maids` |
| `em` / `hashed_maids` | already SHA-256-hashed — passed through as-is |
| `custom_data` | optional object (default `{}`) |

`client_ip_address` and `client_user_agent` are added automatically from the request.
Plaintext email/maid are hashed in-memory and never logged or stored.

## Security
- The token is a **server-side secret** — it lives ONLY in Vercel env vars, never in the repo
  or in client-side HTML. `.env` / `.env.local` are gitignored if you test locally.
