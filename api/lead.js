// Vercel Serverless Function: receives a waitlist signup, enriches it with the
// visitor's real geolocation (from Vercel edge headers), and forwards it to a
// Google Apps Script web app that appends a row to a Google Sheet AND emails an inbox.
// Set SHEET_WEBHOOK_URL in the Vercel project env to the Apps Script /exec URL.
export default async function handler(req, res) {
  if (req.method !== 'POST') {
    res.setHeader('Allow', 'POST');
    return res.status(405).json({ ok: false, error: 'Method not allowed' });
  }

  let data = req.body;
  if (typeof data === 'string') {
    try { data = JSON.parse(data); }
    catch (_) { data = Object.fromEntries(new URLSearchParams(data)); }
  }
  data = data || {};

  // Server-side geo is more reliable than anything the client sends
  const h = req.headers;
  const lead = {
    ts: new Date().toISOString(),
    first_name: (data.first_name || '').toString().slice(0, 80),
    email: (data.email || '').toString().slice(0, 160),
    country: h['x-vercel-ip-country'] || data.country || '',
    region: h['x-vercel-ip-country-region'] || data.region || '',
    city: h['x-vercel-ip-city'] ? decodeURIComponent(h['x-vercel-ip-city']) : '',
    ua: (h['user-agent'] || '').toString().slice(0, 300),
    source: 'directcare.ai /unavailable (geo-blocked)',
  };

  // Basic guardrails
  if (!lead.email || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(lead.email)) {
    return res.status(400).json({ ok: false, error: 'Valid email required' });
  }

  const url = process.env.SHEET_WEBHOOK_URL;
  if (url) {
    try {
      await fetch(url, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(lead),
      });
    } catch (err) {
      // Don't fail the user if the sheet is momentarily unreachable; log for debugging.
      console.error('SHEET_WEBHOOK_URL forward failed:', err && err.message);
    }
  } else {
    console.log('Lead received (SHEET_WEBHOOK_URL not set yet):', lead);
  }

  return res.status(200).json({ ok: true });
}
