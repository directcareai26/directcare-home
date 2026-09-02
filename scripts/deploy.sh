#!/usr/bin/env bash
# The only supported way to put directcare.ai live.
#
# On 2026-08-30 and again on 2026-09-02 the site was reverted to a July snapshot
# because a second checkout (SandBox/repo-work/directcare-home) was linked to the
# same Vercel project and someone deployed from it. Everything below exists to
# make that impossible to do by accident.
set -euo pipefail

CANON="$HOME/directcare-home"
RED=$'\033[31m'; GRN=$'\033[32m'; YEL=$'\033[33m'; OFF=$'\033[0m'
die(){ echo "${RED}REFUSING TO DEPLOY:${OFF} $1" >&2; exit 1; }
ok(){ echo "  ${GRN}ok${OFF}  $1"; }

# 1. only from the canonical checkout ---------------------------------------
[ "$(cd "$(dirname "$0")/.." && pwd)" = "$CANON" ] \
  || die "run this from $CANON, not $(pwd). Other copies must never deploy."
cd "$CANON"
ok "running from the canonical checkout"

# 2. no other checkout may hold a .vercel link to this project --------------
STRAYS=$(find "$HOME" /private/tmp -name project.json -path '*/.vercel/*' \
          -not -path "$CANON/*" -not -path '*/node_modules/*' 2>/dev/null \
          | xargs grep -l '"projectName":"directcare-home"' 2>/dev/null || true)
[ -z "$STRAYS" ] || die "another checkout can deploy this project:
$STRAYS
Delete its .vercel directory before deploying."
ok "no stray deployable copies"

# 3. branch + freshness ------------------------------------------------------
BRANCH=$(git branch --show-current)
[ "$BRANCH" = "main" ] || die "on '$BRANCH'. Production deploys from main only."
git fetch origin --quiet
BEHIND=$(git rev-list --count main..origin/main)
[ "$BEHIND" = "0" ] || die "main is $BEHIND commits behind origin/main. Pull first."
[ -z "$(git status --porcelain --untracked-files=no)" ] \
  || die "uncommitted changes. Commit or stash them — deploys ship committed state only."
ok "on main, level with origin, tree clean"

# 4. the tree must actually contain the site --------------------------------
for p in erectile-dysfunction/index.html welcome.html thankyou.html \
         surge/f1/index.html surge/f5/index.html surge-max/start/index.html; do
  [ -e "$p" ] || die "missing $p — this tree is not the whole site."
done
grep -q '6a91c05fa9cb082abb340d5e' surge-max/start/index.html \
  || die "surge-max/start is not pointing at the current Tellescope form."
! grep -q '6a357b176f59958089c9161f' surge-max/start/index.html \
  || die "surge-max/start still references the RETIRED Tellescope form."
grep -q 'SURGE MAX is \$179 for a 10-pack' surge-max/index.html \
  || die "surge-max FAQ still carries stale pricing."
ok "content preflight passed"

# 5. deploy a clean copy of committed state ---------------------------------
STAGE=$(mktemp -d)
trap 'rm -rf "$STAGE"' EXIT
git archive HEAD | tar -x -C "$STAGE"
cp -r .vercel "$STAGE/.vercel"
echo "  deploying $(git rev-parse --short HEAD) — $(find "$STAGE" -type f -not -path '*/.vercel/*' | wc -l | tr -d ' ') files"
( cd "$STAGE" && vercel deploy --prod --yes )

# 6. verify what actually went live -----------------------------------------
echo "  verifying…"; sleep 6
FAIL=0
check(){ code=$(curl -s -o /tmp/dep.html -w '%{http_code}' -A 'Mozilla/5.0' "https://www.directcare.ai/$1?cb=$RANDOM")
  if [ "$code" != "200" ]; then echo "  ${RED}FAIL${OFF} /$1 -> HTTP $code"; FAIL=1
  elif [ -n "${2:-}" ] && ! grep -q "$2" /tmp/dep.html; then echo "  ${RED}FAIL${OFF} /$1 missing: $2"; FAIL=1
  else ok "/$1"; fi; }
check "erectile-dysfunction" 'SURGE MAX is \$179'
check "welcome"
check "thankyou"
check "surge-max/start" '6a91c05fa9cb082abb340d5e'
for f in f1 f2 f3 f4 f5; do check "surge/$f" '6a91c05fa9cb082abb340d5e'; done
[ "$FAIL" = "0" ] || die "live verification failed — the deploy is serving the wrong tree."
echo "${GRN}deployed and verified${OFF}"
