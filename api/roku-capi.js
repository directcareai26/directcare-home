// Roku Conversions API (CAPI) relay — server-side event forwarding.
//
// Emits Roku's Conversions API event schema (deduped against any client-side Roku
// pixel by `event_id`), with SHA-256-hashed user data for match quality. Produces:
//   { "event_group_id", "events": [ { event_id, event_name, event_type: "conversion",
//       event_time, event_source, event_source_url,
//       user_data: { is_hashed, em, ph, client_ip_address, client_user_agent },
//       custom_data } ] }
//
// Callers (browser beacon, iOS app, intake form) POST JSON:
//   { event_name, event_id, event_url, event_time?, event_source?,
//     email? | em?, phone? | ph?, custom_data? }
//   - email / phone : PLAINTEXT — normalized + SHA-256 hashed here (never logged/stored)
//   - em / ph       : already SHA-256-hashed (passed through as-is)
//
// SECRETS — set in Vercel → Project → Settings → Environment Variables (never in repo):
//   ROKU_CAPI_TOKEN      = the Conversions API bearer key (JWT) from Ads Manager → Events → CAPI
//   ROKU_EVENT_GROUP_ID  = the Event Group ID for this property (directcare.ai)
// Until both are set, the endpoint no-ops with HTTP 200 so the site keeps working.

const crypto = require('crypto');

// Health-data firewall for outbound ad relays. Pinterest's Ad Data Terms bar sending Ad Data that relates to a
// medical condition, and from 2026-11-14 that becomes an explicit "health information" warranty with an audit right.
// Our condition-named URLs and program labels would otherwise carry exactly that, so: the event URL is reduced to
// origin + path with the query string dropped, any condition-named path is replaced by a neutral token, and
// custom_data is passed through a value allow-list rather than forwarded wholesale. 2026-09-14.
const CONDITION_PATH = /(testosterone|trt|hormone|hrt|menopause|perimenopause|erectile|sexual|surge-max|semaglutide|tirzepatide|glp-?1|weight-loss|hair-loss|hair|peptide|libido|fertility|chronic-care|blood-test)/i;
const CD_ALLOW = new Set(['value', 'currency', 'order_id', 'num_items', 'order_quantity']);

function safeEventUrl(raw) {
  try {
    const u = new URL(raw);
    const path = CONDITION_PATH.test(u.pathname) ? '/p' : u.pathname;
    return u.origin + path;               // query string and condition-bearing path dropped
  } catch (e) {
    return undefined;
  }
}

function safeCustomData(cd) {
  const out = {};
  if (!cd || typeof cd !== 'object') return out;
  for (const k of Object.keys(cd)) {
    if (!CD_ALLOW.has(k)) continue;       // drops program, pillar, content_name, search_string, etc.
    const v = cd[k];
    if (typeof v === 'number' || typeof v === 'string') out[k] = v;
  }
  return out;
}


const ENDPOINT = 'https://events.ads.rokuapi.net/v1/events';
const HEX64 = /^[a-f0-9]{64}$/i;

function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}

// Roku email normalization: lowercase, trim, strip the "+tag" between "+" and "@".
function hashEmail(raw) {
  if (raw == null) return null;
  let v = String(raw).trim();
  if (!v) return null;
  if (HEX64.test(v)) return v.toLowerCase(); // already hashed
  v = v.toLowerCase();
  v = v.replace(/\+[^@]*@/, '@'); // remove chars after "+" and before "@"
  return sha256(v);
}

// Roku phone normalization: digits only (keep leading country code), then SHA-256.
function hashPhone(raw) {
  if (raw == null) return null;
  let v = String(raw).trim();
  if (!v) return null;
  if (HEX64.test(v)) return v.toLowerCase(); // already hashed
  v = v.replace(/[^0-9]/g, '');
  if (!v) return null;
  return sha256(v);
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'method_not_allowed' });
    return;
  }

  const token = process.env.ROKU_CAPI_TOKEN;
  const eventGroupId = process.env.ROKU_EVENT_GROUP_ID;
  if (!token || !eventGroupId) {
    res.status(200).json({ skipped: 'capi_not_configured' });
    return;
  }

  // sendBeacon delivers a text/plain string; parse defensively.
  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { body = {}; }
  }
  body = body || {};

  // user_data — IP/UA from the request, hashed identifiers from the payload.
  const user_data = {
    client_ip_address: String(req.headers['x-forwarded-for'] || '').split(',')[0].trim(),
    client_user_agent: req.headers['user-agent'] || '',
  };
  const em = hashEmail(body.em != null ? body.em : body.email);
  const ph = hashPhone(body.ph != null ? body.ph : body.phone);
  if (em) user_data.em = em;
  if (ph) user_data.ph = ph;
  // is_hashed flags whether em/ph are SHA-256 (always true here — we hash before sending).
  if (em || ph) user_data.is_hashed = true;

  const event = {
    event_id: body.event_id, // dedupes against any client-side Roku pixel event
    event_name: body.event_name || 'LEAD',
    event_type: 'conversion',
    event_time: Number.isFinite(body.event_time)
      ? body.event_time
      : Math.floor(Date.now() / 1000),
    event_source: body.event_source || 'website',
    user_data,
    custom_data: safeCustomData(body.custom_data),
  };
  const cleanUrl = safeEventUrl(body.event_url);
  if (cleanUrl) event.event_source_url = cleanUrl;

  try {
    const r = await fetch(ENDPOINT, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/json',
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ event_group_id: eventGroupId, events: [event] }),
    });
    const text = await r.text();
    res.status(r.ok ? 200 : 502).json({ ok: r.ok, status: r.status, body: text.slice(0, 500) });
  } catch (err) {
    res.status(502).json({ ok: false, error: String(err) });
  }
};
