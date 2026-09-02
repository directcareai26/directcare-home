# DirectCare AI — product marketing context

Shared context file read by the `mkt-*` skills before they ask questions.
Maintained by hand. Anything marked (VERIFY) has not been confirmed recently —
confirm with `dca-analytics` before using it in a deliverable.

## Company

DirectCare AI. Two public surfaces, do not mix them:

| Surface | Domain | Repo | Purpose |
|---|---|---|---|
| DTC store | www.directcare.ai | `directcare-home` | Consumer telehealth programs, buys traffic, takes intake |
| Corporate | www.directcareai.com | `directcareai-web` | Company/investor/partner story |

Other live properties: `train.directcare.ai` (HIPAA training), `portal.directcare.ai`
(patient portal + the mobile app's API), `mdsupport.ai`, `playfulnights.com`.

## What we sell (DTC)

Regulated telehealth programs: **ED (Surge Max)**, **TRT**, **HRT**, **hair loss**,
**weight loss / GLP-1**, **blood labs**, **CGM**.

Every one of these is a regulated health category. Ad platforms (Meta, Google)
apply health-vertical policy to all of them, and ED/HRT/GLP-1 draw the most
scrutiny.

## Second motion (B2B)

RPM/CCM — remote patient monitoring and chronic care management, sold to
practices, riding CMS reimbursement rails. Channel opens **October 2026**.
Different ICP, different buyer, different content. Do not blend it into DTC copy.

## Stack

- **CRM / email / SMS / funnels:** GoHighLevel (GHL). MCP connected. Workflow
  authoring is read-only over MCP — workflows are built in the GHL UI.
- **Clinical intake + patient portal:** Tellescope.
- **Paid:** Meta Ads (account 707327008899561). MCP connected.
- **Analytics:** GA4, Google Search Console, GTM `GTM-N7ZG3PT8`,
  Meta Pixel `1567193354573862`, Pinterest tag `549770546296`, Roku CAPI.
- **Finance:** QuickBooks Online (source of truth for revenue).
- **Outbound:** Apollo.io. MCP connected.
- **Hosting:** Vercel (marketing sites), Replit (DCA Care OS), Azure (PHI).

## Funnel reality (VERIFY before quoting)

The bottleneck is **follow-up and conversion, not traffic**. Baseline taken
2026-07: ~2,859 opportunities, roughly ~1% reaching enrollment. Paid spend is
gated behind CAC proof for that reason. Do not propose "more traffic" as the
answer to a conversion problem.

## Voice

Direct, clinical-plain, adult. No hype, no fake urgency, no shame-based hooks in
sensitive categories (ED, weight loss, hair loss). We are an
**administrative-only AI in healthcare** company — AI does the paperwork, humans
do the medicine. Never imply the AI diagnoses, prescribes, or replaces a
clinician.

## Brand

DCA purple only: plum `#241432`, purple `#6d28d9`, accent `#a855f7`.
The mobile app redesign v2 uses `#853FAC` — confirm which surface before picking.
Never blue, never off-brand.

## Hard constraints — read before producing anything

1. **`dca-risk-compliance` is a gate, not a reviewer.** Every outbound asset
   passes it before it ships. Health claims, HIPAA, FTC endorsement/testimonial
   rules, platform policy.
2. **No PHI, ever**, in prompts, files, screenshots, or external tools. No patient
   names, DOB, contact details, or diagnoses. Aggregates only.
3. **No testimonials or before/after imagery** without documented consent on file.
4. **No health outcome claims** without a substantiating source we can produce.
5. **Numbers are computed, not estimated.** Pull from GHL / GA / GSC / QBO via
   `dca-analytics`. Never invent a benchmark or a conversion rate.
6. **SMS is TCPA + A2P 10DLC territory** and we send through GHL. Consent
   language and opt-out are not optional.

## Agent routing

50 `dca-*` marketing subagents live in `DirectCareAI-SandBox/.claude/agents/`.
`dca-cmo-advisor` routes. The `mkt-*` skills supply frameworks the agents don't
have; the agents supply DCA context the skills don't have. Use both.
