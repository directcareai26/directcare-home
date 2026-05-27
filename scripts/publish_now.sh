#!/usr/bin/env bash
# publish_now.sh — one-command end-to-end publish of today's blog post.
#
# Same pipeline the daily cron runs, but on demand. Use when the user says
# "make me a blog post", "publish today's blog", or similar.
#
# Optional args: pass through to generate_daily_post.py
#   ./publish_now.sh                          → generator picks topic
#   ./publish_now.sh --category Fitness       → forces a category (random angle)
#   ./publish_now.sh --category Nutrition --angle "Greek lentil soup recipe with 22g protein"
#
# Requires:
#   - ANTHROPIC_API_KEY in environment (set in your shell rc or .env)
#   - git push permissions on directcareai26/directcare-home
#   - vercel CLI logged in
set -euo pipefail

REPO="/Users/dachewilliams/Desktop/Claude Code/Home Page (DCAI)"
cd "$REPO"

if [ -z "${ANTHROPIC_API_KEY:-}" ]; then
  echo "ERROR: ANTHROPIC_API_KEY is not set." >&2
  echo "  Add it to your shell rc: export ANTHROPIC_API_KEY=sk-ant-..." >&2
  exit 1
fi

echo "==> Generating post..."
GEN_OUT=$(python3 scripts/generate_daily_post.py "$@")
echo "$GEN_OUT"

# Extract slug + title from the generator's JSON tail
SLUG=$(echo "$GEN_OUT" | python3 -c "import json,sys; d=json.loads(sys.stdin.read().strip().split('\n')[-1] if sys.stdin else '{}'); print(d.get('slug',''))" 2>/dev/null || true)

# Fallback: pull newest slug from manifest
if [ -z "$SLUG" ]; then
  SLUG=$(python3 -c "import json; print(json.load(open('blog/posts.json'))['posts'][0]['slug'])")
fi

if [ -z "$SLUG" ]; then
  echo "ERROR: couldn't determine new post slug." >&2
  exit 2
fi

echo ""
echo "==> Slug: $SLUG"

# Sanity check: HTML exists, has h1 + cover + 3 h2s
HTML_PATH="blog/${SLUG}.html"
if [ ! -f "$HTML_PATH" ]; then
  echo "ERROR: $HTML_PATH does not exist." >&2
  exit 3
fi
H2_COUNT=$(grep -c "<h2>" "$HTML_PATH" || echo 0)
if [ "$H2_COUNT" -lt 3 ]; then
  echo "WARNING: only $H2_COUNT <h2> tags found in $HTML_PATH — generator may have failed." >&2
fi

TITLE=$(grep -oE '<title>[^<]+' "$HTML_PATH" | head -1 | sed 's/<title>//' | sed 's/ | DirectCare AI Blog//')
echo "==> Title: $TITLE"

echo ""
echo "==> Commit + push..."
git add blog/posts.json "$HTML_PATH" sitemap.xml 2>/dev/null || true
git commit -m "blog: ${TITLE}" -m "Auto-published from publish_now.sh"
git push origin main

echo ""
echo "==> Force production deploy on Vercel..."
npx vercel --prod --yes 2>&1 | tail -5

echo ""
echo "==> Verifying live URL..."
URL="https://www.directcare.ai/blog/${SLUG}"
for i in $(seq 1 12); do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" "${URL}?cb=${RANDOM}")
  if [ "$CODE" = "200" ]; then
    echo "==> LIVE: $URL"
    exit 0
  fi
  echo "  attempt $i: HTTP $CODE — retrying in 10s..."
  sleep 10
done

echo "WARNING: $URL still not returning 200. Check Vercel deploys." >&2
exit 4
