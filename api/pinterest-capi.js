// Pinterest Conversions API (CAPI) relay — server-side event forwarding.
//
// The browser tag (in each page's <head>) sends a 'lead' here via navigator.sendBeacon
// when a visitor clicks through to the intake portal. This function forwards it to
// Pinterest server-to-server, deduped against the browser event by `event_id`.
//
// SECRETS — set these in Vercel → Project → Settings → Environment Variables
// (NEVER commit them to the repo):
//   PINTEREST_CAPI_TOKEN     = the Conversions API access token (pina_...)
//   PINTEREST_AD_ACCOUNT_ID  = your Pinterest ad account id
//
// Until both are set, this endpoint no-ops gracefully (returns 200 "not configured")
// so the site keeps working and the browser tag alone still tracks conversions.

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

  const ip = String(req.headers['x-forwarded-for'] || '').split(',')[0].trim();
  const ua = req.headers['user-agent'] || '';

  const payload = {
    data: [
      {
        event_name: body.event_name || 'lead',
        action_source: 'web',
        event_time: Math.floor(Date.now() / 1000),
        event_id: body.event_id, // dedupes against the browser pintrk event
        event_source_url: body.event_url,
        user_data: {
          client_ip_address: ip,
          client_user_agent: ua,
        },
      },
    ],
  };

  try {
    const r = await fetch(
      `https://api.pinterest.com/v5/ad_accounts/${account}/events`,
      {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(payload),
      }
    );
    const text = await r.text();
    res.status(r.ok ? 200 : 502).json({ ok: r.ok, status: r.status, body: text.slice(0, 500) });
  } catch (err) {
    res.status(502).json({ ok: false, error: String(err) });
  }
};
