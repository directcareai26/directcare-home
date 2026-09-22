// Vercel Serverless Function: captures a partner (affiliate) applicant from /partner
// and upserts them into GoHighLevel BEFORE they are handed off to FlexOffers.
//
// Why capture first: the booth app learned this the hard way. Linking straight out to
// FlexOffers loses every applicant who abandons the signup, and those are exactly the
// people worth a follow-up. See ~/olympia-lead-capture/app/partner/PartnerFlow.js.
//
// Requires Vercel env vars: GHL_PIT (Private Integration Token, "pit-..."), GHL_LOCATION_ID.
// Both already exist on this project — the same pair api/quiz-submit.js uses.
// The PIT never reaches the browser.
//
// TAGGING CONTRACT — read before changing any string here.
//   * `olympia-2026` is DELIBERATELY ABSENT. That tag triggers the consumer
//     code-delivery workflow, which would text a coach "20% off your first order".
//     Partners get `olympia-2026-partner` instead. The two must never converge.
//   * `event-lead` is the only tag shared with the consumer funnel, so it stays
//     the honest total for the event.
//   * `partner - reached flexoffers` is PRESENCE-ONLY. GHL's tag endpoint ADDS and
//     never removes, so an opposite "did not reach" tag would leave a coach carrying
//     both and poison the first filter anyone writes. Absence means never reached it.
//     The money segment is `audience - partner` AND NOT `partner - reached flexoffers`.
//   * That tag means they OPENED the FlexOffers signup, not that they finished it.
//     Nothing here may label these contacts "partners".

const GHL = "https://services.leadconnectorhq.com";

const headers = () => ({
  Authorization: "Bearer " + process.env.GHL_PIT,
  Version: "2021-07-28",
  "Content-Type": "application/json",
  Accept: "application/json",
});

// GHL silently drops non-E.164 numbers, so normalise US 10/11-digit input.
function e164(raw) {
  const s = String(raw || "").trim();
  const d = s.replace(/\D/g, "");
  if (/^\d{10}$/.test(d)) return "+1" + d;
  if (/^1\d{10}$/.test(d)) return "+" + d;
  if (d && s[0] === "+") return "+" + d;
  return "";
}

const emailOk = (e) => /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(e);

// Tags go through the dedicated endpoint. Sending them in the upsert body REPLACES
// every tag the contact already had, wiping existing segmentation.
async function addTags(contactId, tags) {
  if (!contactId || !tags.length) return;
  try {
    const r = await fetch(`${GHL}/contacts/${contactId}/tags`, {
      method: "POST", headers: headers(), body: JSON.stringify({ tags }),
    });
    if (!r.ok) console.error("partner-lead: tag add " + r.status);
  } catch (e) {
    console.error("partner-lead: tag add failed:", e.message);
  }
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ ok: false, error: "Method not allowed" });
  }
  if (!process.env.GHL_PIT || !process.env.GHL_LOCATION_ID) {
    console.error("partner-lead: GHL env vars missing");
    return res.status(500).json({ ok: false, error: "Not configured" });
  }

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (_) { body = {}; } }
  body = body || {};

  const email = String(body.email || "").trim().toLowerCase().slice(0, 160);
  if (!emailOk(email)) {
    return res.status(400).json({ ok: false, error: "Valid email required" });
  }

  // ---- beacon: they tapped through to the FlexOffers signup -----------------
  // Fired by sendBeacon on the handoff. Adds one tag; never creates a new contact
  // with partial data and never re-writes the fields captured a moment ago.
  if (body.action === "reached-flexoffers") {
    let id = String(body.contactId || "").trim().slice(0, 64) || null;
    if (!id) {
      // The capture response is the normal source of the id. If the page lost it
      // (reload, restored tab), look the contact up rather than upserting blind.
      try {
        const q = await fetch(`${GHL}/contacts/search/duplicate` +
          `?locationId=${encodeURIComponent(process.env.GHL_LOCATION_ID)}` +
          `&email=${encodeURIComponent(email)}`, { headers: headers() });
        if (q.ok) {
          const out = await q.json();
          id = (out.contact && out.contact.id) || null;
        }
      } catch (e) { console.error("partner-lead: lookup failed:", e.message); }
    }
    if (!id) {
      console.warn("partner-lead: reached-flexoffers with no resolvable contact");
      return res.status(200).json({ ok: true, tagged: false });
    }
    await addTags(id, ["partner - reached flexoffers"]);
    console.log("partner-lead reached-flexoffers contact=" + id);
    return res.status(200).json({ ok: true, tagged: true });
  }

  // ---- capture --------------------------------------------------------------
  const firstName = String(body.firstName || "").trim().slice(0, 80);
  const lastName  = String(body.lastName  || "").trim().slice(0, 80);
  const business  = String(body.business  || "").trim().slice(0, 120);
  const city      = String(body.city      || "").trim().slice(0, 80);
  const phone     = e164(body.phone);

  if (!firstName) return res.status(400).json({ ok: false, error: "First name required" });
  if (!phone)     return res.status(400).json({ ok: false, error: "Valid mobile required" });
  if (!business)  return res.status(400).json({ ok: false, error: "Business name required" });
  if (!body.consent) return res.status(400).json({ ok: false, error: "Consent required" });

  const payload = {
    locationId: process.env.GHL_LOCATION_ID,
    email, firstName, lastName, phone,
    companyName: business,
    source: "Website - /partner",
  };
  if (city) payload.city = city;
  const region = req.headers["x-vercel-ip-country-region"];
  if (region) payload.state = String(region).slice(0, 4);

  const tags = [
    "olympia-2026-partner",   // NOT `olympia-2026` — see the contract above.
    "audience - partner",
    "event-lead",
    "consent - marketing",
    "channel - web partner page",
  ];

  try {
    const r = await fetch(`${GHL}/contacts/upsert`, {
      method: "POST", headers: headers(), body: JSON.stringify(payload),
    });
    const text = await r.text();
    if (!r.ok) {
      // Never echo the upstream body to the browser.
      console.error("partner-lead: upsert " + r.status + " " + text.slice(0, 300));
      return res.status(502).json({ ok: false, error: "Upstream error" });
    }
    let out = {}; try { out = JSON.parse(text); } catch (_) {}
    const contactId = (out.contact && out.contact.id) || out.id || null;
    await addTags(contactId, tags);
    console.log("partner-lead ok contact=" + contactId);
    return res.status(200).json({ ok: true, contactId });
  } catch (e) {
    console.error("partner-lead: network:", e.message);
    return res.status(502).json({ ok: false, error: "Upstream error" });
  }
}
