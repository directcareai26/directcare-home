// Pinterest Conversions API (CAPI) relay — server-side event forwarding.
//
// Emits Pinterest's full event schema (deduped against the browser pintrk event by
// `event_id`), including SHA-256-hashed user data for match quality. Produces:
//   { "data": [ { action_source, event_id, event_name, event_time,
//                 user_data: { client_ip_address, client_user_agent, em[], hashed_maids[] },
//                 custom_data } ] }
//
// Callers (browser beacon, iOS app, intake form) POST JSON:
//   { event_name, event_id, event_url, event_time?, action_source?,
//     email? | em?, maid? | hashed_maids?, custom_data? }
//   - email / maid  : PLAINTEXT — normalized + SHA-256 hashed here (never logged/stored)
//   - em / hashed_maids : already SHA-256-hashed (passed through as-is)
//
// SECRETS — set in Vercel → Project → Settings → Environment Variables (never in repo):
//   PINTEREST_CAPI_TOKEN     = the Conversions API access token (pina_...)
//   PINTEREST_AD_ACCOUNT_ID  = your Pinterest ad account id
// Until both are set, the endpoint no-ops with HTTP 200 so the site keeps working.

const crypto = require('crypto');

const HEX64 = /^[a-f0-9]{64}$/i;

// Pinterest requires SHA-256 of the normalized value. Normalize emails (trim + lowercase);
// pass through values that are already a 64-char hex SHA-256.
function sha256(value) {
  return crypto.createHash('sha256').update(value).digest('hex');
}
function hashEmail(raw) {
  if (raw == null) return null;
  const v = String(raw).trim();
  if (!v) return null;
  if (HEX64.test(v)) return v.toLowerCase(); // already hashed
  return sha256(v.trim().toLowerCase());
}
function hashId(raw) {
  if (raw == null) return null;
  const v = String(raw).trim();
  if (!v) return null;
  if (HEX64.test(v)) return v.toLowerCase(); // already hashed
  return sha256(v.toLowerCase());
}
// Accept a single value or an array; return a hashed array (or undefined if none).
function hashArray(value, fn) {
  if (value == null) return undefined;
  const arr = Array.isArray(value) ? value : [value];
  const out = arr.map(fn).filter(Boolean);
  return out.length ? out : undefined;
}

module.exports = async (req, res) => {
  if (req.method !== 'POST') {
    res.status(405).json({ error: 'method_not_allowed' });
    return;
  }

  const token = process.env.PINTEREST_CAPI_TOKEN;
  const account = process.env.PINTEREST_AD_ACCOUNT_ID;
  if (!token || !account) {
    res.status(200).json({ skipped: 'capi_not_configured' });
    return;
  }

  // sendBeacon delivers a text/plain string; parse defensively.
  let body = req.body;
  if (typeof body === 'string') {
    try { body = JSON.parse(body); } catch (e) { body = {}; }
  }
  body = body || {};

  // Build user_data — IP/UA from the request, hashed identifiers from the payload.
  const user_data = {
    client_ip_address: String(req.headers['x-forwarded-for'] || '').split(',')[0].trim(),
    client_user_agent: req.headers['user-agent'] || '',
  };
  const em = hashArray(body.em != null ? body.em : body.email, hashEmail);
  const hashed_maids = hashArray(
    body.hashed_maids != null ? body.hashed_maids : body.maid,
    hashId
  );
  if (em) user_data.em = em;
  if (hashed_maids) user_data.hashed_maids = hashed_maids;

  const event = {
    action_source: body.action_source || 'web',
    event_id: body.event_id, // dedupes against the browser pintrk event
    event_name: body.event_name || 'lead',
    event_time: Number.isFinite(body.event_time)
      ? body.event_time
      : Math.floor(Date.now() / 1000),
    user_data,
    custom_data: body.custom_data && typeof body.custom_data === 'object'
      ? body.custom_data
      : {},
  };
  if (body.event_url) event.event_source_url = body.event_url;

  try {
    const r = await fetch(
      `https://api.pinterest.com/v5/ad_accounts/${account}/events`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ data: [event] }),
      }
    );
    const text = await r.text();
    res.status(r.ok ? 200 : 502).json({ ok: r.ok, status: r.status, body: text.slice(0, 500) });
  } catch (err) {
    res.status(502).json({ ok: false, error: String(err) });
  }
};
