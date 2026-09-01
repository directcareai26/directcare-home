// Vercel Serverless Function: receives a completed DirectCare AI quiz and
// upserts the person into GoHighLevel with their answers as custom fields.
//
// Requires Vercel env vars:  GHL_PIT  (Private Integration Token, "pit-...")
//                            GHL_LOCATION_ID
//
// The PIT never reaches the browser. Clinical answers are never logged.

const GHL = "https://services.leadconnectorhq.com";
const UA = "DirectCareAI-Quiz/1.0";
const NAME_MAX = 100;

let fieldCache = null;      // { normalisedName: fieldId }
let fieldCacheAt = 0;
const CACHE_MS = 10 * 60 * 1000;

function headers() {
  return {
    Authorization: "Bearer " + process.env.GHL_PIT,
    Version: "2021-07-28",
    "Content-Type": "application/json",
    Accept: "application/json",
    "User-Agent": UA,
  };
}

// Must match how the fields were created (truncate at 100 with an ellipsis).
function normName(name) {
  let n = String(name || "").trim();
  if (n.length > NAME_MAX) n = n.slice(0, NAME_MAX - 1).replace(/\s+$/, "") + "…";
  return n.toLowerCase();
}
// Fallback key: mirrors how GHL derives fieldKey, so "X?" and "X?:" collapse together.
function looseName(name) {
  return String(name || "").trim().slice(0, NAME_MAX)
    .toLowerCase().replace(/[^a-z0-9]+/g, "");
}
// Answers that belong on GHL's STANDARD contact fields, not a custom field.
const STANDARD = {
  "date of birth": "dateOfBirth",
  "what is your date of birth": "dateOfBirth",
  "what is your address": "address1",
  "what is your address?": "address1",
};

async function loadFields() {
  if (fieldCache && Date.now() - fieldCacheAt < CACHE_MS) return fieldCache;
  const r = await fetch(`${GHL}/locations/${process.env.GHL_LOCATION_ID}/customFields`, {
    headers: headers(),
  });
  if (!r.ok) throw new Error("customFields " + r.status);
  const j = await r.json();
  const map = { exact: {}, loose: {} };
  (j.customFields || []).forEach((f) => {
    map.exact[normName(f.name)] = f.id;
    const lk = looseName(f.name);
    if (!map.loose[lk]) map.loose[lk] = f.id;   // first wins, keeps it deterministic
  });
  fieldCache = map;
  fieldCacheAt = Date.now();
  return map;
}

// The Tellescope->GHL sync (tooling/tellescope-ghl-sync) owns the funnel taxonomy:
// every contact gets "funnel - <funnel>" plus a stage tag. Quiz leads were only
// getting quiz-* tags, so they sat outside every segment and workflow built on it.
// Map the quiz slug onto the same names so a quiz lead and a Tellescope lead are
// indistinguishable downstream.
const FUNNEL_NAME = {
  "ed": "ed surge max", "surge-max": "ed surge max", "ed-surge-max": "ed surge max",
  "hrt": "hrt", "trt": "trt",
  "weight-loss": "weight loss", "mens-weight-loss": "weight loss", "womens-weight-loss": "weight loss",
  "mens-hair-loss": "hair loss men", "womens-hair-loss": "hair loss women",
  "womans-hair-loss": "hair loss women",
};

function slugTag(s) {
  return String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "").slice(0, 50);
}

export default async function handler(req, res) {
  if (req.method !== "POST") {
    res.setHeader("Allow", "POST");
    return res.status(405).json({ ok: false, error: "Method not allowed" });
  }
  if (!process.env.GHL_PIT || !process.env.GHL_LOCATION_ID) {
    console.error("quiz-submit: GHL env vars missing");
    return res.status(500).json({ ok: false, error: "Not configured" });
  }

  let body = req.body;
  if (typeof body === "string") { try { body = JSON.parse(body); } catch (_) { body = {}; } }
  body = body || {};

  const c = body.contact || {};
  const email = String(c.email || "").trim().slice(0, 160);
  let phone = String(c.phone || "").trim().slice(0, 40);
  // GHL silently drops non-E.164 numbers, so normalise US 10/11-digit input.
  const digits = phone.replace(/\D/g, "");
  if (/^\d{10}$/.test(digits)) phone = "+1" + digits;
  else if (/^1\d{10}$/.test(digits)) phone = "+" + digits;
  else if (digits && phone[0] === "+") phone = "+" + digits;
  if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) {
    return res.status(400).json({ ok: false, error: "Valid email required" });
  }

  const funnel = slugTag(body.funnel || "unknown");
  const outcome = body.outcome || {};
  const answers = Array.isArray(body.answers) ? body.answers.slice(0, 300) : [];

  let customFields = [];
  const standardFields = {};
  let matched = 0, unmatched = [];
  try {
    const map = await loadFields();
    answers.forEach((a) => {
      const value = Array.isArray(a.value) ? a.value.join(", ") : String(a.value);
      const std = STANDARD[String(a.title || "").trim().toLowerCase()];
      if (std) { standardFields[std] = value.slice(0, 200); matched++; return; }
      const id = map.exact[normName(a.title)] || map.loose[looseName(a.title)];
      if (!id) { if (unmatched.length < 25) unmatched.push(String(a.title).slice(0, 60)); return; }
      customFields.push({ id, value: value.slice(0, 4000) });
      matched++;
    });
  } catch (e) {
    console.error("quiz-submit: field map failed:", e.message);
  }

  const isPartial = !!body.partial;
  const tags = ["quiz-" + funnel];

  // Canonical funnel tags, matching the sync. NOTE: the stage tag is deliberately
  // always "started" — a finished quiz is not a submitted medical intake, and
  // "funnel intake - submitted" must keep meaning Tellescope's own submittedAt.
  // Mislabelling that flag is what put 180 contacts in the wrong segment in Aug 2026.
  const canonical = FUNNEL_NAME[funnel];
  if (canonical) {
    tags.push("funnel - " + canonical);
    tags.push("funnel intake - started");
  }

  if (isPartial) {
    // Captured at the contact step, before any clinical questions. Not an outcome.
    tags.push("quiz-started");
  } else {
    tags.push("quiz-completed");
    tags.push(outcome.disqualified ? "quiz-not-eligible" : "quiz-eligible");
    (outcome.flags || []).slice(0, 20).forEach((f) => tags.push("flag-" + slugTag(f)));
    (Array.isArray(body.products) ? body.products : []).slice(0, 4)
      .forEach((p) => tags.push("product-" + slugTag(p)));
  }

  const h = req.headers;
  const payload = {
    locationId: process.env.GHL_LOCATION_ID,
    email,
    firstName: String(c.firstName || "").slice(0, 80),
    lastName: String(c.lastName || "").slice(0, 80),
    source: "Website quiz - " + funnel + (isPartial ? " (started)" : ""),
    customFields,
  };
  if (phone) payload.phone = phone;
  // date of birth / address answers land on the native contact fields
  if (standardFields.dateOfBirth) payload.dateOfBirth = standardFields.dateOfBirth;
  if (standardFields.address1) payload.address1 = standardFields.address1;
  const st = h["x-vercel-ip-country-region"];
  if (st) payload.state = String(st).slice(0, 4);

  try {
    const r = await fetch(`${GHL}/contacts/upsert`, {
      method: "POST", headers: headers(), body: JSON.stringify(payload),
    });
    const text = await r.text();
    if (!r.ok) {
      // Never echo the body back to the browser - it can contain answer text.
      console.error("quiz-submit: upsert " + r.status + " " + text.slice(0, 300));
      return res.status(502).json({ ok: false, error: "Upstream error" });
    }
    let out = {}; try { out = JSON.parse(text); } catch (_) {}
    const contactId = (out.contact && out.contact.id) || out.id || null;

    // Tags go through the dedicated endpoint. Sending them in the upsert body
    // REPLACES every tag the contact already had, wiping existing segmentation.
    if (contactId && tags.length) {
      try {
        const tr = await fetch(`${GHL}/contacts/${contactId}/tags`, {
          method: "POST", headers: headers(), body: JSON.stringify({ tags }),
        });
        if (!tr.ok) console.error("quiz-submit: tag add " + tr.status);
      } catch (e) { console.error("quiz-submit: tag add failed:", e.message); }
    }
    console.log(`quiz-submit ok funnel=${funnel} partial=${isPartial} eligible=${!outcome.disqualified} ` +
                `fields=${matched}/${answers.length} contact=${contactId}`);
    if (unmatched.length) console.warn("quiz-submit unmatched fields:", unmatched.join(" | "));
    return res.status(200).json({ ok: true, eligible: !outcome.disqualified });
  } catch (e) {
    console.error("quiz-submit: network:", e.message);
    return res.status(502).json({ ok: false, error: "Upstream error" });
  }
}
