# Deploying directcare.ai

```bash
cd ~/directcare-home && ./scripts/deploy.sh
```

That is the only supported route. Nothing else should run `vercel deploy --prod`.

## Why the ceremony

Twice — 2026-08-30 and 2026-09-02 — the live site was reverted to a July snapshot.
Both times the cause was the same: a **second checkout carrying its own `.vercel/`
link to the `directcare-home` project**, at `DirectCareAI-SandBox/repo-work/directcare-home`.
A `vercel deploy --prod` there uploaded that folder's files, so the live site lost
`/erectile-dysfunction`, `/welcome`, `/thankyou`, every `/surge/f*` landing page,
and reverted six pages of pricing. The second incident ran for roughly a day.

It also went the other way: production was being deployed from a feature branch that
was 60 commits behind `origin/main`, so those deploys were wiping out blog posts and
the Meta Pixel work. Two trees, each overwriting the other, whoever deployed last.

## The rules that now hold

1. **`main` is the only deploy branch.** It carries both histories as of
   `f590415`. Deploying anything else reverts somebody's work.
2. **Only `~/directcare-home` may hold a `.vercel/` link** for this project.
   `scripts/deploy.sh` scans the filesystem and refuses if it finds another.
3. **Deploys ship committed state**, staged through `git archive`, so uncommitted
   or untracked files never reach production by accident.
4. **The script verifies the live site afterwards** and fails loudly if the
   deployment is serving the wrong tree.

## What the script blocks

| Check | Refuses when |
|---|---|
| location | not run from `~/directcare-home` |
| stray copies | any other directory has a `.vercel` link to this project |
| branch | not on `main` |
| freshness | `main` is behind `origin/main` |
| clean tree | uncommitted tracked changes |
| content | the ED page, welcome/thankyou, or a `/surge/f*` page is missing |
| form id | `/surge-max/start` lacks the current Tellescope form, or still has the retired one |
| pricing | the Surge Max FAQ still shows stale pricing |
| live | any verified URL 404s or lacks its marker after deploy |

## Backstop

`com.directcareai.siteguard` (on the pipeline Mac, every 15 min) fetches the live
pages and emails if they stop matching `tooling/site-guard/expected.json`. It is
what caught both incidents. When a price or form id changes legitimately, update
that file in the same change.
