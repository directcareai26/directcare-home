// Meta Conversions API bridge. Mirrors every browser pixel event server-side with
// the same event_id so Meta de-duplicates, and adds the two parameters a browser
// cannot send about itself: client_ip_address and client_user_agent.
//
// Env: META_CAPI_TOKEN (ads_management), optional META_TEST_EVENT_CODE.
//
// PRIVACY: customer information is SHA-256 hashed here and never logged. Nothing
// describing a health condition is accepted or forwarded — see ALLOWED_CUSTOM.

import crypto from 'crypto';

// 1068250912518605 = "DCAI - Main Website Aug2026", the dataset attached to ad
// account 707327008899561. 1567193354573862 is a legacy tag on the pages that is
// NOT in that ad account and rejects this token, so server events would be wasted.
const PIXELS = (process.env.META_CAPI_PIXELS || '1068250912518605').split(',').map(s => s.trim()).filter(Boolean);
const GRAPH = 'https://graph.facebook.com/v21.0';

// hashed, per Meta's normalisation rules (the client normalises; we hash)
const HASHED = ['em', 'ph', 'fn', 'ln', 'db', 'ge', 'ct', 'st', 'zp', 'country', 'external_id'];
// passed through as-is (never hashed, per Meta's spec)
const RAW = [
  'client_ip_address', 'client_user_agent', 'fbc', 'fbp',
  'subscription_id', 'lead_id', 'fb_login_id',
  'page_id', 'page_scoped_user_id',            // messenger bot events
  'ctwa_clid',                                  // click-to-WhatsApp
  'ig_account_id', 'ig_sid',                    // instagram
  'anon_id', 'madid',                           // app events only
];
// custom_data keys we will forward — deliberately excludes anything naming a
// product, condition, page or funnel, which on a telehealth site would turn an
// ad event into a disclosure about someone's health.
const ALLOWED_CUSTOM = ['value', 'currency', 'order_id', 'num_items', 'predicted_ltv'];

const sha256 = (v) => crypto.createHash('sha256').update(String(v)).digest('hex');
const isHashed = (v) => /^[a-f0-9]{64}$/i.test(String(v));

function buildUserData(input, req) {
  const out = {};
  for (const k of HASHED) {
    const v = input[k];
    if (v === undefined || v === null || v === '') continue;
    const list = Array.isArray(v) ? v : [v];
    const hashed = list.map((x) => (isHashed(x) ? String(x).toLowerCase() : sha256(x)));
    out[k] = hashed.length === 1 ? hashed[0] : hashed;
  }
  for (const k of RAW) if (input[k]) out[k] = String(input[k]);

  const h = req.headers;
  const fwd = (h['x-forwarded-for'] || '').split(',')[0].trim();
  if (!out.client_ip_address && fwd) out.client_ip_address = fwd;
  if (!out.client_user_agent && h['user-agent']) out.client_user_agent = String(h['user-agent']);
  return out;
}

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ ok: false, error: 'Method not allowed' });
  }
  if (!process.env.META_CAPI_TOKEN) {
    console.error('meta-capi: META_CAPI_TOKEN missing');
    return res.status(500).json({ ok: false, error: 'Not configured' });
  }

  let body = req.body;
  if (typeof body === 'string') { try { body = JSON.parse(body); } catch { body = {}; } }
  body = body || {};

  const eventName = String(body.event_name || '').slice(0, 60);
  if (!eventName) return res.status(400).json({ ok: false, error: 'event_name required' });

  const user_data = buildUserData(body.user_data || {}, req);
  // Meta needs at least one identifier to match on
  if (!Object.keys(user_data).some((k) => k !== 'client_ip_address' && k !== 'client_user_agent')) {
    return res.status(200).json({ ok: true, skipped: 'no matchable identifier' });
  }

  const custom_data = {};
  for (const k of ALLOWED_CUSTOM) if (body.custom_data && body.custom_data[k] !== undefined) {
    custom_data[k] = body.custom_data[k];
  }

  // action_source must be truthful — Meta's terms require it to describe where
  // the event really happened.
  const ACTION_SOURCES = ['website', 'app', 'email', 'phone_call', 'chat',
                          'physical_store', 'system_generated', 'business_messaging', 'other'];
  const action_source = ACTION_SOURCES.includes(body.action_source) ? body.action_source : 'website';

  const event = {
    event_name: eventName,
    event_time: Math.floor(Date.now() / 1000),
    event_id: String(body.event_id || crypto.randomUUID()),
    action_source,
    user_data,
    ...(Object.keys(custom_data).length ? { custom_data } : {}),
  };

  // website events also require event_source_url; non-web events must not carry it
  if (action_source === 'website') {
    event.event_source_url = String(body.event_source_url || '').split('?')[0].slice(0, 500);
  }
  // referrer helps attribution; strip the query so no ids ride along
  if (body.referrer_url) event.referrer_url = String(body.referrer_url).split('?')[0].slice(0, 500);

  // suppress this event from ads delivery/optimisation while still measuring it
  if (body.opt_out === true) event.opt_out = true;

  // Limited Data Use. [] = normal processing; ['LDU'] with 0/0 lets Meta geolocate.
  if (process.env.META_LDU === '1') {
    event.data_processing_options = ['LDU'];
    event.data_processing_options_country = 0;
    event.data_processing_options_state = 0;
  } else if (Array.isArray(body.data_processing_options)) {
    event.data_processing_options = body.data_processing_options;
    if (body.data_processing_options_country !== undefined)
      event.data_processing_options_country = Number(body.data_processing_options_country);
    if (body.data_processing_options_state !== undefined)
      event.data_processing_options_state = Number(body.data_processing_options_state);
  }

  // segmentation label for reporting — never a condition or product on this site
  if (body.customer_segmentation) event.customer_segmentation = String(body.customer_segmentation).slice(0, 100);

  // links a downstream event (a CRM close) back to the original website lead,
  // which is what Conversions API for Lead Optimisation matches on
  const oed = body.original_event_data;
  if (oed && oed.event_name) {
    event.original_event_data = {
      event_name: String(oed.event_name).slice(0, 60),
      ...(oed.event_time ? { event_time: Number(oed.event_time) } : {}),
      ...(oed.order_id ? { order_id: String(oed.order_id).slice(0, 100) } : {}),
      ...(oed.event_id ? { event_id: String(oed.event_id).slice(0, 100) } : {}),
    };
  }

  const payload = { data: [event] };
  const testCode = body.test_event_code || process.env.META_TEST_EVENT_CODE;
  if (testCode) payload.test_event_code = String(testCode);

  const results = await Promise.all(PIXELS.map(async (pixel) => {
    try {
      const r = await fetch(`${GRAPH}/${pixel}/events?access_token=${encodeURIComponent(process.env.META_CAPI_TOKEN)}`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload),
      });
      const text = await r.text();
      if (!r.ok) { console.error(`meta-capi: pixel ${pixel} ${r.status} ${text.slice(0, 200)}`); return false; }
      return true;
    } catch (e) { console.error('meta-capi: network', e.message); return false; }
  }));

  // never echo user_data back to the browser
  return res.status(200).json({ ok: results.some(Boolean), sent: results.filter(Boolean).length });
}
