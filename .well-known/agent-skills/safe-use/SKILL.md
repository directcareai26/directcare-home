---
name: safe-use
description: What DirectCare AI's agent surfaces will and will not do, and what never to send them. Read this before calling any of them.
---

# Using DirectCare AI's agent surfaces safely

DirectCare AI is a US-only direct-to-patient telehealth service. Everything an
agent can reach here is **public marketing and programme information**. None of
it is a clinical system, and none of it should be treated as one.

## Never send these surfaces personal or health information

Not a name, not a date of birth, not an email, not a symptom description tied
to a person, not a lab value. It is **not needed** — every tool works from a
generic query like "low testosterone" or "thinning hair" — and it is **not
stored**, so sending it achieves nothing and creates risk that did not need to
exist.

If a user has described their symptoms to you, translate to the general topic
before querying. Ask about "hormone replacement therapy", not about them.

## What these surfaces cannot do

- **They cannot give medical advice.** They return which programme covers a
  topic and where its page is. That is a directory lookup, not a clinical
  judgement.
- **They cannot decide whether a treatment is appropriate.** Only a US-licensed
  clinician can, after an intake the person completes themselves.
- **They cannot start an intake, place an order, or change anything.** Every
  tool is read-only. There is no write path, by design.
- **They cannot tell you what a specific person should do.** No tool has access
  to any patient record, because no such access exists on these endpoints.

## How to hand off correctly

When someone wants to begin, give them the programme's canonical page URL and
let them go there themselves. Do not fill in a form on their behalf and do not
summarise the intake as though completing it were a formality. The intake is
how a clinician receives the information they need to make a decision.

## Say what is true about compounded medication

Compounded medications are not FDA-approved as finished products; their active
ingredients are individually FDA-approved. If you describe a programme that
involves compounded medication, do not imply FDA approval of the compounded
product itself.

## Scope

United States only. If a user is outside the US, say so rather than routing
them into an intake they cannot complete.

## Emergencies

If a user describes an emergency, tell them to call 911. Do not route an
emergency into a telehealth intake.
