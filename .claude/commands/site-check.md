---
description: Mechanical pre-deploy check of directcare.ai — links, cache-buster, chrome drift. Read-only.
allowed-tools: Bash, Read, Grep, Glob
---

Decide one thing: **GO or NO-GO** for deploying this tree.

## The three checks

**1. Links.** !`python3 scripts/link_audit.py 2>&1 | sed -n '/BROKEN INTERNAL LINKS/,/INTAKE FORM MAP/p'`

Note: the auditor's "dead buttons" section is largely false positives. Anchors
carrying `data-start` are wired by a click handler in `scripts/lp/core.py`, and
`welcome.html` assigns its review link in script. Judge the **broken internal links**
section, not the button count.

**2. Cache-buster consistency.** !`grep -rhoE 'dc-signal[.]js[?]v=[0-9]+' --include='*.html' . | sed 's/.*v=//' | sort | uniq -c`

There must be exactly one value. `vercel.json` serves js and css as immutable for a
year, so a page left on an older value keeps serving the old script forever. If the
script changed today, that value must be today's date. Run `/bump-signal` to fix.

**3. Chrome drift.** Count distinct `<nav>` and `<footer>` blocks outside `/blog`.
Measured 2026-09-11: 29 distinct footers, 8 navs, 13 pages with no nav. This is not a
blocker, it is a number to watch. If it grew since last check, say so, because "update
the footer" is a 29-file job, not a one-file job.

## Verdict

End with one line: `GO` or `NO-GO: <reasons>`.

Then print, without running them:

```
git add -A && git commit -m "<message>"
./scripts/deploy.sh
```

`./scripts/deploy.sh` is the only supported deploy route. It refuses to ship off main,
behind origin, with a dirty tree, or from a checkout holding a stale `.vercel` link. A
raw `vercel --prod` from the wrong tree reverted production on 2026-08-30 and again on
2026-09-02, and the project's PreToolUse hook now refuses it.

This command never commits, pushes, or deploys.
