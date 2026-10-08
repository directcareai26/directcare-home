// TikTok Events API relay — the server half of the browser pixel, so a conversion
// still lands when an ad blocker or ITP eats the client beacon.
//
// Deliberately a SEPARATE endpoint from api/meta-capi.js rather than a fan-out
// inside it. The Meta relay is the one carrying revenue reporting today; a
// TikTok outage, a bad token or a schema change on their side must not be able
// to take it down.
//
// PRIVACY: customer information is SHA-256 hashed here and never logged, and
// ALLOWED_PROPS decides what may describe the purchase. content_name is NOT on
// that list — on this site the product names the treatment, and the browser
// pixel carrying it does not oblige the server copy to. Same line the Meta
// relay holds.
import crypto from 'node:crypto';

const API = 'https://business-api.tiktok.com/open_api/v1.3/event/track/';
const PIXEL = process.env.TIKTOK_PIXEL_ID || 'DALCA3JC77UES97566D0';

// TikTok expects these SHA-256 hashed. The client normalises (lowercased email,
// digits-only phone with country code) so the browser hash and this hash are
// taken over the identical string and resolve to one person.
const HASHED = { em: 'email', ph: 'phone', external_id: 'external_id' };
// Passed through as-is. ttp/ttclid are TikTok's fbp/fbc.
const RAW = { ttp: 'ttp', ttclid: 'ttclid' };

// value and currency describe the transaction. content_name and
// content_category describe the TREATMENT, so they stop at the browser.
const ALLOWED_PROPS = ['value', 'currency', 'order_id', 'content_type', 'content_id'];

const sha256 = (v) => crypto.createHash('sha256').update(String(v)).digest('hex');
const isHashed = (v) => /^[a-f0-9]{64}$/i.test(String(v));

function buildUser(input, req) {
  const out = {};
  for (const [src, dest] of Object.entries(HASHED)) {
    const v = input[src];
    if (v === undefined || v === null || v === '') continue;
    out[dest] = isHashed(v) ? String(v).toLowerCase() : sha256(v);
  }
  for (const [src, dest] of Object.entries(RAW)) {
    if (input[src]) out[dest] = String(input[src]);
  }
  const h = req.headers || {};
  const fwd = String(h['x-forwarded-for'] || '').split(',')[0].trim();
  if (fwd) out.ip = fwd;
  if (h['user-agent']) out.user_agent = String(h['user-agent']);
  return out;
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ ok: false, error: 'Method not allowed' });
  }
  if (!process.env.TIKTOK_CAPI_TOKEN) {
    console.error('tiktok-capi: TIKTOK_CAPI_TOKEN missing');
    return res.status(500).json({ ok: false, error: 'Not configured' });
  }

  let body = req.body;
  if (typeof body === 'string') { try { body = JSON.parse(body); } catch { body = {}; } }
  body = body || {};

  const eventName = String(body.event_name || '').slice(0, 60);
  if (!eventName) return res.status(400).json({ ok: false, error: 'event_name required' });

  const user = buildUser(body.user_data || {}, req);
  // Without an identifier TikTok cannot attribute the event, and sending it
  // anyway just inflates the count with rows nothing can match.
  if (!Object.keys(user).some((k) => k !== 'ip' && k !== 'user_agent')) {
    return res.status(200).json({ ok: true, skipped: 'no matchable identifier' });
  }

  const properties = {};
  for (const k of ALLOWED_PROPS) {
    if (body.custom_data && body.custom_data[k] !== undefined) properties[k] = body.custom_data[k];
  }

  const payload = {
    event_source: 'web',
    event_source_id: PIXEL,
    data: [{
      event: eventName,
      // seconds, not milliseconds — TikTok rejects ms as out of range
      event_time: Math.floor(Date.now() / 1000),
      // same id the browser pixel sent, so TikTok dedupes rather than
      // double-counting the conversion
      event_id: String(body.event_id || ''),
      user,
      page: {
        url: String(body.event_source_url || ''),
        referrer: String(body.referrer_url || ''),
      },
      properties,
      limited_data_use: body.opt_out === true || undefined,
    }],
  };
  if (process.env.TIKTOK_TEST_EVENT_CODE) payload.test_event_code = process.env.TIKTOK_TEST_EVENT_CODE;

  try {
    const r = await fetch(API, {
      method: 'POST',
      headers: {
        'Access-Token': process.env.TIKTOK_CAPI_TOKEN,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    });
    const text = await r.text();
    let j = {}; try { j = JSON.parse(text); } catch { /* keep text */ }
    // TikTok answers 200 with a non-zero `code` on rejection, so HTTP status
    // alone is not the success signal.
    if (!r.ok || (j.code !== undefined && j.code !== 0)) {
      console.error(`tiktok-capi: ${r.status} code=${j.code} ${String(j.message || text).slice(0, 200)}`);
      return res.status(200).json({ ok: false });
    }
    return res.status(200).json({ ok: true });
  } catch (e) {
    console.error('tiktok-capi: network', e.message);
    return res.status(200).json({ ok: false });
  }
}
