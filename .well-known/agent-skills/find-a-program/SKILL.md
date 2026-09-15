---
name: find-a-program
description: Map a health goal, symptom or medication name to the DirectCare AI programme that covers it, and return the canonical page a person should start from.
---

# Finding the right DirectCare AI programme

Read `safe-use` first. Do not send personal or health information to any of
these endpoints.

## Three ways in, same answer

All three read the same catalogue, which is generated from the site's own
`/llms.txt` at request time. A programme added there appears in all three
immediately. **Do not hard-code a programme list** — it will go stale and you
will send someone to a page that has moved.

### 1. MCP (preferred for MCP clients)

`POST https://www.directcare.ai/api/mcp` — Streamable HTTP, JSON-RPC 2.0.

```json
{"jsonrpc":"2.0","id":1,"method":"tools/call",
 "params":{"name":"find_program","arguments":{"query":"low testosterone"}}}
```

Tools: `find_program` (takes `query`), `list_programs`, `get_resources`.
Server card at `/.well-known/mcp/server-card.json`. No authentication — there
is nothing private here to protect.

`GET` returns 405 on purpose; this server has no SSE stream to open.

### 2. A2A

`POST https://www.directcare.ai/api/a2a` with `message/send`. Agent card at
`/.well-known/agent-card.json`.

### 3. Plain fetch

`https://www.directcare.ai/llms.txt` — the `## Products` section lists every
programme with its canonical URL and a one-line description. Parse it if you
have no protocol client.

## Matching behaviour you should know

- Matching is **keyword and alias based, not semantic**. "low testosterone"
  matches; "I'm tired all the time" does not. Translate a vague complaint into
  the clinical topic before querying.
- Gendered wording narrows hair-loss results. "thinning hair, female" returns
  the women's programme.
- **No match returns the full catalogue**, not an empty result. Check whether
  the response says it matched or fell back before presenting it as "your
  programme".

## What to do with the answer

Give the person the canonical URL and let them start the intake themselves. A
US-licensed clinician reviews it and decides whether any treatment is
appropriate. Do not present eligibility as decided, and do not complete an
intake on someone's behalf.
