# /olympia — handoff (2026-09-22)

Written because the session that started this hit ~220k context. Everything below is
MEASURED unless labelled otherwise. Resume from here; do not re-derive.

## Where the work is
- Canonical clone: `~/DirectCareAI-SandBox/repo-work/directcare-home` (freshly cloned, level with origin/main, no `.vercel` link — keep it that way).
- Built, uncommitted: `olympia/index.html` (71,392 bytes). Passes `scripts/predeploy_check.py`.
- Compose script: `/private/tmp/claude-501/-Users-mentor-social/f91155c2-6910-436f-a66e-4313898fdbd4/scratchpad/compose_olympia.py`
- Compliance review was dispatched and had NOT returned when the session ended. Transcript:
  `/private/tmp/claude-501/-Users-mentor-social/f91155c2-6910-436f-a66e-4313898fdbd4/tasks/a258896158bb5813b.output`
  (JSONL — do not cat it whole into context.)

## What v1 already has (built, verified)
Composed from the site's OWN nav/footer/`<style>`/tracking head lifted out of `mens-health.html`,
so it is inside the design system, not beside it. Verified: HTML parses with 0 structural
issues; 35/35 internal links resolve through `cleanUrls` + the 129-entry redirect table;
18/18 local assets exist; 1 `h1`; every `img` has alt; every `target=_blank` has `rel=noopener`;
robots.txt does NOT disallow it (so `noindex` is readable); correctly absent from sitemap.xml.

Six program cards route to the existing product pages. Verified each has a real intake:
`/weight-loss`, `/testosterone-replacement-therapy`, `/hormone-replacement-therapy`,
`/surge-max`, `/mens-hair-loss`, `/womans-hair-loss` each reach a `/start` page that exists
on disk; `/blood-test` reaches Fullscript checkout. No new flow was invented.

## Deltas the owner's copy deck requires (NOT yet applied)
1. §2 — move the OLYMPIA26 strip to DIRECTLY UNDER the hero. v1 has it after the programs.
   Rationale given: SMS arrivals already hold the code; the strip confirms they're in the
   right place. "Do not lead with 20% off" still governs the hero itself.
2. §3 — REPLACE the three steps. v1 copied the booth page's framing ("no health questions on
   this page"). The owner flags this as a COMPLIANCE distinction: on /olympia the intake IS
   the clinical step. Use the deck's wording verbatim.
3. §5 — ADD a "Why cash-pay" section. VERIFIED SAFE: all 7 program pages carry dollar prices,
   so "Pricing is shown on each program page" is true.
4. §6 — coaches must go through a CAPTURE step before FlexOffers, not a direct link. v1 links
   straight out. Reference impl: `~/olympia-lead-capture/app/partner/PartnerFlow.js`
   (328 lines, created 2026-09-22 10:43 — newer than this session's first read of that dir).
5. §7 — ADD a capture fallback form for cold flyer scans. v1 has no form at all.
6. §9 — meta becomes: Title `DirectCare AI — Olympia 2026 Access`;
   Description `Private, cash-pay telehealth with licensed clinician evaluation. Complete your
   intake and your treatment ships to your door.`

## THE BLOCKER on §6 and §7
The deck says "post to the same GHL shape the booth uses." **directcare-home cannot do that today.**
`api/lead.js` in THIS repo is not a GHL endpoint — it is a geo-block waitlist handler that
forwards `{first_name, email}` to a Google Sheet via `SHEET_WEBHOOK_URL`, and hardcodes
`source: 'directcare.ai /unavailable (geo-blocked)'`. The booth's GHL-posting `/api/lead`
lives in the SEPARATE `olympia-lead-capture` codebase with its own env.

So §6 and §7 need a NEW serverless route here plus GHL credentials in the `directcare-home`
Vercel project env. That is a real build with a secrets dependency — not a reuse. Get the
owner's call before assuming it.

## Printed-URL situation (measured across all 21 flyer files)
| Printed URL | Flyers | Live |
|---|---|---|
| DIRECTCARE.AI/OLYMPIA | 10 (files 11–20) | 404 |
| DIRECTCARE.AI/PARTNER | 11 (files 01–10, 21) | 404 |

`/partners` and `/affiliate` are also 404 (owner's claim — independently confirmed).
Apex→www redirect DOES carry the path, so bare `directcare.ai/olympia` in SMS will work.
Owner initially said "build /olympia only", then reopened /partner in the deck suggesting a
redirect to `/olympia#partner`. UNRESOLVED — needs a decision.

## Corrections to earlier premises (all measured)
- The git guard does NOT apply to this repo. `tooling/git-hooks/pre-commit` matches only
  remotes under `github.com[:/]DirectCare-AI/*`; this repo is `directcareai26/directcare-home`,
  so the hook hits `exit 0`. `core.hooksPath` is unset in both clones. Using the canonical
  clone is still correct practice — but `scripts/deploy.sh` names
  `SandBox/repo-work/directcare-home` as the cause of TWO production reverts (2026-08-30,
  2026-09-02) and refuses to deploy if it finds a `.vercel` link outside `~/directcare-home`.
- "directcare.ai makes no free-consultation claim": inverted. `free evaluation` appears in 48
  HTML files, `free consultation` in 3 product pages. /olympia deliberately makes NO fee claim.
- The warning block's "17 references" is EXACTLY right (9 SMS + 6 GHL-WORKFLOW templates +
  2 email). The 3 extra raw hits are prose inside the warning block itself
  (GHL-WORKFLOW.md lines 10, 12, 17). The 17 need NO change once /olympia exists; what needs
  removing is the warning block, GHL-WORKFLOW.md lines 10–32 (fenced by `---` at 8 and 33).

## Self-caught defect (already fixed in v1)
v1 said "Enter it when you check out" — an order-flow mechanism documented NOWHERE on
directcare.ai. Replaced with "Save it for your first order."
STILL OPEN: the promo email says *"go to directcare.ai/olympia and enter OLYMPIA26"*,
promising a code-entry field that has nothing to wire to. That email line is wrong regardless
of what ships.

## Deploy
`~/directcare-home` (the ONLY checkout deploy.sh accepts) is on branch `feat/tiktok-pixel`
with 203 modified tracked files, 7 untracked, 5 ahead / 26 behind origin/main. deploy.sh
requires clean + on main + level with origin, so it WILL refuse. That is another actor's
uncommitted work — do not stash or clear it without the owner's say-so.
Owner's chosen path: build + commit + push from the canonical clone; the owner deploys.

---

# COMPLIANCE REVIEW RESULT — 2026-09-22

**RULING: NO — not safe to publish as written. 6 Blockers, 10 Majors.**
Full report is in the subagent transcript (JSONL, do not cat whole):
`/private/tmp/claude-501/-Users-mentor-social/f91155c2-6910-436f-a66e-4313898fdbd4/tasks/a258896158bb5813b.output`

I independently re-verified the reviewer's code-level claims. **All confirmed:**
- Nested `<a>` at line 813 (real functional bug — `/womans-hair-loss` link sits inside the
  `/mens-hair-loss` card anchor; women scanning the flyer land on the men's page).
- 5× `href="/peptides"` on the page (nav + drawer + footer). Peptides is owner-CONFIRMED
  **not for sale** and is the most performance-coded category for this audience.
- "compounded" = 1 and "not FDA-approved" = 1, both only in footer boilerplate (line ~1019),
  while all five prescription destination pages carry the disclosure ON PAGE (weight-loss 34×).
- Performance disclaimer at line 947; first program card at line 763. The disclaimer sits
  184 lines BELOW the first exit from the page. Owner requirement #3 is effectively unmet.

## Blockers that COPY CAN FIX (one editing pass — reviewer supplied paste-ready wording)
- **B1** Put "Not for athletic or performance enhancement" in a hero band above the cards,
  plus inline on the TRT and Weight Loss cards. Keep line 947 too.
- **B2** Compounding disclosure onto the Weight Loss / Women's Hormones / Sexual Health cards,
  and promote it out of the footer. "GLP-1 medication" unqualified reads as Ozempic/Wegovy while
  the program delivers compounded tirzepatide/semaglutide.
- **M1** H1 "…not a counter." — the implicit comparison against the supplement aisle is the
  wrong frame for this audience AND disparages `/supplements`, which DCA sells.
  Reviewer's minimal fix: `<h1>Care that starts with a clinician.</h1>`
- **M2–M9, m1–m5** — card claims, affiliate payout display/disclaimer, affiliate disclosure
  obligation, nested anchor, `/peptides` removal.

## Blockers that COPY CANNOT FIX — owner/counsel decisions
- **B3** OLYMPIA26 has **no verified redemption mechanism**. `grep -rl "OLYMPIA26"` over the whole
  repo returns exactly one file: the page I just wrote. No coupon UI anywhere on directcare.ai.
  I found this independently before the review. Flyers are printed. → DaChé must produce the
  coupon object and a test-redemption screenshot.
- **B5** `/olympia` would be the FIRST url in the estate where consumer clinical intake and
  FlexOffers affiliate recruitment share a rendered page. **Only Scott can waive this.**
  (The AdvertiserMax tracking lib is already site-wide — that part is pre-existing, not new.)
- **B6** Paying non-clinician coaches a recurring per-patient commission for steering people they
  already advise into hormone therapy → state anti-kickback / fee-splitting / patient-brokering,
  EKRA. **Outside healthcare regulatory counsel, not an agent.**
- **M8/M9** "does not create a patient relationship" may be legally wrong; entity framing is
  self-contradictory between hero, footer and JSON-LD. → counsel.

## B4 is NOT a defect — resolve it by stating the canonical artifact
The reviewer flagged that `olympia-copy.txt` and `index.html` diverge. They diverge because I
caught and removed my own invented claim ("Enter it when you check out") AFTER extracting the
copy for review. The reviewer notes the copy.txt variant is the riskier one.
**`olympia/index.html` is canonical. `olympia-copy.txt` is a stale extract — delete it.**

## Verification owed by humans before re-review
- **DaChé:** OLYMPIA26 redeems at 20% + where it's entered; mixed-cart exclusion behaviour;
  Sept 30 expiry vs actual Olympia Weekend dates; payout figures vs FlexOffers terms; flyer PDF.
- **Dr. Pepin:** TRT labs-before-every-prescription (absolute claim currently on the card);
  weight-loss compounded status; women's HRT compounded / off-label testosterone;
  Surge Max formulation (already an open estate item — 7 citrulline files uncommitted).
- **Counsel:** B6, M8, M9.
- **Scott:** B5 waiver, and final approval.

## Separate ticket — do NOT block /olympia on it
Every prescription destination in this funnel makes a fee claim ("free evaluation" ×48 files
sitewide, "free consultation" ×3). `/olympia` correctly makes none. If "free evaluation" is
substantiated this is fine; if not, the Olympia flyers are now driving traffic into it.
→ route to `dca-risk-compliance`.

---

# OWNER DECISIONS — 2026-09-22 (supersede earlier blockers)

1. **B3 CLEARED.** OLYMPIA26 works; it is a **Stripe promo code**. "Enter it at checkout" is now
   accurate. Update the code card on `/olympia` accordingly.
2. **B5 RESOLVED BY SEPARATION, not waiver.** Clinical intake must NOT share a page with
   affiliate recruitment. → **Remove the entire `#coaches` section from `/olympia`.**
3. **Coaches who want to purchase** → point at the existing product pages. No special flow.
4. **B6** → owner asked for maximally compliant copy. Written to `PARTNER-COPY-DRAFT.md`.
   **Copy mitigates but cannot cure** a recurring per-patient commission to non-clinicians that
   varies by service prescribed. Structural remedy (flat per-lead or flat monthly FMV fee) is a
   FlexOffers program-terms change. Still needs counsel.

**CONSEQUENCE — /partner is now required.** Recruitment has to live somewhere, and `/partner` is
already printed on 11 of 21 flyers and is a 404. Building it satisfies the separation requirement
and fixes the 11 dead flyers at once. This supersedes the earlier "only build /olympia" decision.

## Revised build list
- `/olympia` — consumer only. Apply B1, B2, M1, M2, M5, M6, M7, M8, m1–m5. DELETE `#coaches`.
  Update code card to "Enter it at checkout." Remove 5× `/peptides` links. Fix nested `<a>` L813.
- `/partner` — new page from `PARTNER-COPY-DRAFT.md`. Same site design system.
- Delete the stale `olympia-copy.txt` extract; `olympia/index.html` is canonical (closes B4).

---

# SCOPE REDUCTION — 2026-09-22 (owner: "I am not using those flyers")

The printed flyers are OUT. Every flyer-derived argument in this document is void.

**`/partner` on directcare.ai is NO LONGER NEEDED.** Its only justification was the 11 printed
flyers. Coaches are already served by the booth app, VERIFIED live 2026-09-22:
  https://olympia-lead-capture.vercel.app/partner  → 200
`PARTNER-COPY-DRAFT.md` stays on disk as the compliant wording if a web partner page is ever
built, but it is not on the critical path. **Do not build /partner.**

**`/olympia` is STILL REQUIRED.** The flyer was only 1 of its 3 justifications. The other two
stand: **17 live references** point at it — 9 SMS snippets, 6 GHL-WORKFLOW templates, 2 in the
promo email. Those still 404 on arrival until the page ships.

**`/olympia` becomes CONSUMER-ONLY — remove the coach fork entirely.**
Without flyer QR scans there are no cold arrivals who must sort themselves by audience. Everyone
reaching /olympia came via SMS or email, which means they were captured at the booth as a
consumer; coaches were routed to the booth app's own /partner flow at capture time.
Consequences:
- Delete the two-door fork from the hero. Single CTA.
- Delete the `#coaches` section and the payout table.
- **B5 is fully eliminated** — no affiliate recruitment on the page at all, so the
  clinical-intake/recruitment collision cannot occur.
- **B6 no longer blocks /olympia.** It remains open against the partner program itself, wherever
  that lives, and still needs counsel — but it is off this page's critical path.

## Blocker status after this reduction
- B3 CLEARED (Stripe promo code, owner-confirmed).
- B4 CLEARED (index.html canonical; delete the stale olympia-copy.txt).
- B5 ELIMINATED (no recruitment on the page).
- B6 OFF THIS PAGE (still open for the partner program; counsel).
- **B1 and B2 REMAIN** — the two that are mine to fix in copy:
  B1 performance disclaimer must render above the first program card (currently L947 vs L763);
  B2 compounding / "not FDA-approved" must appear on the Weight Loss, Women's Hormones and
  Sexual Health cards, not only in footer boilerplate.
- Majors remaining on /olympia: M1 (H1 comparative), M2 (TRT absolute labs claim), M5 (hair
  "regrowth" + off-label), M6 (labs "near you" + collapsed panel), M7 (labs Rx disclaimer +
  remove 5× /peptides), M8 (patient-relationship wording — counsel), M9 (entity framing —
  counsel), m1 (nested <a> L813 — real bug), m2–m5.
- M3/M4 (affiliate payout display + disclosure duties) NO LONGER APPLY to /olympia.

**Remaining build is one page, one editing pass.** No new API route, no GHL wiring, no /partner.
