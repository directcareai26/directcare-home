# auth.md — DirectCare AI

**There is no authentication on this service, and nothing to register for.**

This document exists so an agent does not have to guess. A 404 here is
ambiguous: it could mean no authentication exists, or that authentication
exists and is simply not discoverable. It is the former.

## Audience

Any automated client — an MCP client, an A2A agent, a crawler, an assistant
acting for a person. All of them are treated identically, because all of them
receive the same public information.

## Registration

**None exists.** There is no registration endpoint, no provisioning endpoint,
no client credentials to obtain, no identity to assert, and no claim ceremony.
Do not attempt to register; there is nothing listening.

## Credentials

**Send none.** No `Authorization` header is read by any endpoint on this
origin. Sending a bearer token, an API key or an identity assertion will not
grant additional access, because there is no additional access to grant, and
it puts a credential somewhere it does not belong.

## Why there is no authentication

Every endpoint an agent can reach here returns information that is already
public on www.directcare.ai — the programme catalogue, canonical page URLs,
and the machine-readable editions of the site. There is nothing private behind
these endpoints, so there is nothing to protect.

This is also why the site publishes **no** `/.well-known/oauth-authorization-server`
and **no** `/.well-known/oauth-protected-resource`. Those documents would name
an issuer, a token endpoint and a protected resource that do not exist. An
agent following them would find nothing. Their absence is the accurate signal.

## What DirectCare AI deliberately does not expose

No patient data, no clinical records, no intake submission, no ordering, and
no write path of any kind. These surfaces are read-only by construction, not
by configuration, so there is no permission that would unlock more.

**Do not send personal or health information to any endpoint here.** It is not
needed — every tool works from a general query like "low testosterone" — and
it is not stored.

## What you can reach, without credentials

| Surface | Endpoint |
|---|---|
| MCP server | `https://www.directcare.ai/api/mcp` |
| MCP server card | `/.well-known/mcp/server-card.json` |
| A2A agent | `/api/a2a` |
| A2A agent card | `/.well-known/agent-card.json` |
| Agent skills | `/.well-known/agent-skills/index.json` |
| Capability catalogue (ARD) | `/.well-known/ai-catalog.json` |
| API catalogue (RFC 9727) | `/.well-known/api-catalog` |
| Site as Markdown | `/llms.txt`, `/llms-full.txt`, any page path + `.md` |
| Content-usage policy | `/robots.txt` (`Content-Signal`) |

Start with `/.well-known/agent-skills/safe-use/SKILL.md`. It states the limits
of every surface listed above.

## If this changes

If DirectCare AI ever exposes an authenticated agent API, this document will
describe how to register for it, and the OAuth discovery documents will be
published alongside it. Until then, their absence is deliberate and correct.

---

*DirectCare AI is a US-only direct-to-patient telehealth service. Treatment is
decided by a US-licensed clinician after an intake the person completes
themselves. Nothing reachable from here changes that.*
