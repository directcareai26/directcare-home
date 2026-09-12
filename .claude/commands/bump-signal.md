---
description: Bump the dc-signal.js cache-buster across every HTML page, then stop
allowed-tools: Bash, Read, Edit, Glob, Grep
---

Bump the tracking script's cache-buster to today across the whole site.

## Why this exists

`vercel.json` serves `/(.*)\.(css|js)` with `max-age=31536000, immutable`. A visitor
who has loaded `dc-signal.js` once keeps that copy for a year. Editing the script
without bumping the `?v=` query string in the HTML means the change reaches nobody,
and nothing fails loudly. The PostToolUse hook in `.claude/settings.json` blocks the
edit for exactly this reason and sends you here.

## Current state

- Version strings in use right now: !`grep -rhoE 'dc-signal[.]js[?]v=[0-9]+' --include='*.html' . | sed 's/.*v=//' | sort | uniq -c`
- Today: !`date +%Y%m%d`
- Pages carrying the script: !`grep -rl 'dc-signal[.]js' --include='*.html' . | wc -l`

## What to do

1. Set `NEW=$(date +%Y%m%d)`.
2. Rewrite every `dc-signal.js?v=<old>` to `dc-signal.js?v=$NEW` across all `*.html`.
3. Change the same string in `scripts/lp/core.py`. It is the generator for the five
   `/surge/f*` pages, so a page edited by hand there is overwritten on the next build.
4. Run `python3 scripts/lp/build.py` to regenerate those five pages.
5. Re-run the version grep and confirm it reports exactly **one** value, equal to today.

## Then stop

Do not commit, do not push, do not deploy. Print the exact commands for the user:

```
git add -A && git commit -m "tracking: cache-bust dc-signal.js to <NEW>"
./scripts/deploy.sh
```

Deploys are the user's act. `./scripts/deploy.sh` is the only supported route; a raw
`vercel --prod` from the wrong tree reverted production on 2026-08-30 and 2026-09-02,
and the PreToolUse hook refuses it.
