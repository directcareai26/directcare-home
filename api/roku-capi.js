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
    custom_data: body.custom_data && typeof body.custom_data === 'object'
      ? body.custom_data
      : {},
  };
  if (body.event_url) event.event_source_url = body.event_url;

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
