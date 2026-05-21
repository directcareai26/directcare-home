# DirectCare AI Blog — Auto-Publish Spec

Source of truth for any automation (cowork skill, GitHub Action, manual script)
that creates blog posts in this repo. If you're publishing a post, follow this
file exactly.

- **Repo:** [`directcareai26/directcare-home`](https://github.com/directcareai26/directcare-home) · branch `main`
- **Blog folder:** `blog/`
- **Live URL pattern:** `https://www.directcare.ai/blog/<slug>`
- **Deploy:** push to `main` → Vercel auto-deploys to production in ~30s. No
  CLI needed unless the GitHub webhook is failing (rare).

---

## Files touched per new post (exactly 3)

### 1. `blog/<slug>.html` — the post

Copy `blog/_post-template.html` to `blog/<slug>.html` and fill these placeholders.
Every token below must be replaced — no `{{...}}` leftovers in the published file.

| Token | What goes in |
|---|---|
| `{{SLUG}}` | Same as the filename, no extension. Kebab-case, ≤ 60 chars, no stop words. |
| `{{TITLE}}` | Plain-text title. Used in `<title>`, OG, Twitter, JSON-LD. No HTML. |
| `{{TITLE_HTML}}` | Same as TITLE, but may wrap one key word in `<em>…</em>` for the italic-purple accent. |
| `{{META_DESCRIPTION}}` | 140–160 chars. Used 5× (meta, og, twitter, schema). No quotes. |
| `{{KEYWORDS}}` | Comma-separated, 5–10 terms. Used in `<meta name="keywords">`. |
| `{{CATEGORY}}` | Human-readable label from the allow-list below. |
| `{{DATE_ISO}}` | `2026-05-22T08:00:00-05:00` (Central Time, 8am publish slot). |
| `{{DATE_LABEL}}` | `May 22, 2026`. Long-form for the card and meta row. |
| `{{IMAGE}}` | Full URL to a hero image. Prefer an existing `…lifestyleImage.png` in the blob (see "Image map" below). |
| `{{DECK}}` | One-sentence subhead, ~160 chars. Renders in serif under the H1. |
| `{{BODY_HTML}}` | The article. See "Body structure" below. |
| `{{PRODUCT_EYEBROW}}` | E.g. `Related program`. Sits above the in-article CTA card. |
| `{{PRODUCT_HEADLINE}}` | E.g. `Start a clinician-built TRT protocol.` |
| `{{PRODUCT_BLURB}}` | One sentence under the headline. |
| `{{PRODUCT_CTA_LABEL}}` | E.g. `See the protocol →` |
| `{{PRODUCT_LINK}}` | Absolute URL to the matching product page on directcare.ai. |

### 2. `blog/posts.json` — index entry (prepend newest first)

This is what the `/blog/` index uses to render cards + power the category filter.

```json
{
  "slug": "<slug>",
  "title": "<plain title — no HTML>",
  "excerpt": "<one sentence, ≤ 160 chars, ends with a period>",
  "category": "<Category Label>",
  "categorySlug": "<category-slug>",
  "date": "2026-05-22",
  "dateLabel": "May 22, 2026",
  "image": "<full blob URL>",
  "keywords": ["...", "...", "..."]
}
```

**Order matters** — newest post is the first element of the `posts` array. The
index renders the top item as the large featured card and the rest as the grid.

### 3. `blog/index.html` — re-render the server-side cards

`index.html` ships with the post cards **server-rendered into the HTML** (commit
`fa95b64` — cheap citability insurance so AI crawlers / GEO see the post list
without executing JS). The client-side JS reads `posts.json` for the category
filter, but the initial paint comes from the HTML.

**Rule:** every time `posts.json` changes, the corresponding `<article>` card
markup inside `index.html`'s `#postsGrid` (and the featured `#postFeatured`
slot for the newest post) must be regenerated to match.

If the automation can't safely regenerate the cards, fall back to: leave
`index.html` alone, ship only `<slug>.html` + `posts.json`, and the JS-side
fetch will surface the new post on second paint. Crawlers will miss it for the
first ~24h until the next manual index regen — acceptable for low-priority
posts, not for posts you want indexed fast.

---

## Body structure (`{{BODY_HTML}}`)

Wrap everything in `<div class="article-body">`. All these elements are styled
in the template already — don't add inline `style=` attributes.

```html
<div class="article-body">
  <p>Lead paragraph — serif, 1.1rem.</p>

  <h2>Section header (Geist, sans, italic-purple <em>emphasis</em> optional)</h2>
  <p>...</p>

  <h3>Sub-section header</h3>
  <p>...</p>

  <ul>
    <li>List items.</li>
  </ul>

  <blockquote>Pull quote — auto-styled with brand-purple left border.</blockquote>

  <div class="callout">
    <div class="callout-eyebrow">Clinician note</div>
    Body of the callout box (cream background, brand eyebrow on top).
  </div>

  <p><strong>Inline emphasis</strong> uses &lt;strong&gt;, not bold.</p>
</div>
```

**Length target:** 900–1,400 words. Matches the three existing posts.

**Headings:** every post should have 3–6 `<h2>` sections. Use `<em>` inside
one or two of them for the italic-purple accent — pattern matches the rest of
the site.

---

## Category allow-list

Only these are valid. Adding a new category requires updating the filter pills
in `index.html` first.

| `category` (label) | `categorySlug` |
|---|---|
| Weight Loss | `weight-loss` |
| HRT | `hrt` |
| TRT | `trt` |
| Sexual Health | `sexual-health` |
| Hair Regrowth | `hair-regrowth` |
| Blood Labs | `blood-labs` |
| Supplements | `supplements` |

---

## Image map (use existing blob URLs, don't upload new ones unless needed)

| Category | Default hero image URL |
|---|---|
| Weight Loss | `https://crsurakhmbalgxim.public.blob.vercel-storage.com/Weight%20Loss%20%E2%80%94%20lifestyleImage.png` |
| TRT | `https://crsurakhmbalgxim.public.blob.vercel-storage.com/%20Testosterone%20%E2%80%94%20lifestyleImage.png` |
| HRT | `https://crsurakhmbalgxim.public.blob.vercel-storage.com/Warm%20%26%20confident.png` |
| Sexual Health | `https://crsurakhmbalgxim.public.blob.vercel-storage.com/Sexual%20Health%20%E2%80%94%20lifestyleImage.png` |
| Hair Regrowth | `https://crsurakhmbalgxim.public.blob.vercel-storage.com/Hair%20Regrowth%20%E2%80%94%20lifestyleImage.png` |
| Blood Labs | `https://crsurakhmbalgxim.public.blob.vercel-storage.com/Health%20Check%20%E2%80%94%20lifestyleImage.png` |
| Supplements | `https://crsurakhmbalgxim.public.blob.vercel-storage.com/flatlay%20of%20women%27s%20protocol%20bottles.png` |

To upload a new image to the blob, use the REST API with the
`BLOB_READ_WRITE_TOKEN` env var:

```bash
curl --http1.1 -X PUT \
  -H "Authorization: Bearer $BLOB_READ_WRITE_TOKEN" \
  -H "x-content-type: image/png" \
  -H "x-add-random-suffix: 0" \
  -H "x-cache-control-max-age: 31536000" \
  --data-binary "@/path/to/image.png" \
  "https://blob.vercel-storage.com/<filename>.png"
```

Note: force HTTP/1.1 for files > ~5MB to avoid the LibreSSL HTTP/2 bug on macOS.

---

## Product CTA card — recommended pairings

Each post embeds one in-article product CTA. Pair the post category to the
closest product:

| Post category | `PRODUCT_LINK` | `PRODUCT_HEADLINE` example |
|---|---|---|
| Weight Loss | `https://www.directcare.ai/weight-loss-program` | `Start a clinician-built GLP-1 protocol.` |
| HRT | `https://www.directcare.ai/start-hrt` | `Start an HRT plan built around your labs.` |
| TRT | `https://www.directcare.ai/mens-health/#testosterone` | `Start TRT or enclomiphene with a clinician.` |
| Sexual Health | `https://www.directcare.ai/surge-max` | `Start a personalized sexual-health protocol.` |
| Hair Regrowth (men) | `https://www.directcare.ai/mens-hair-loss` | `Start the men's hair regrowth protocol.` |
| Hair Regrowth (women) | `https://www.directcare.ai/womans-hair-loss` | `Start the women's hair regrowth protocol.` |
| Blood Labs | `https://www.directcare.ai/blood-test` | `Run the full 70–80 biomarker panel.` |
| Supplements | `https://www.directcare.ai/supplements` | `Build your supplement protocol with a clinician.` |

---

## Git workflow

```bash
cd "/Users/dachewilliams/Desktop/Claude Code/Home Page (DCAI)/"
git checkout main && git pull --ff-only

# write the 3 files:
#   blog/<slug>.html
#   blog/posts.json   (prepended)
#   blog/index.html   (regenerated cards)

git add blog/<slug>.html blog/posts.json blog/index.html
git commit -m "blog: <slug> — <short headline>

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
git push origin main
```

**Author email must be `directcareai@gmail.com`** — Vercel's CLI deploys
reject other authors. (Git-push deploys are more forgiving but use the same
email for consistency.)

After push, Vercel deploys automatically. Verify at
`https://www.directcare.ai/blog/<slug>` within ~60s. If the webhook didn't
fire, manually trigger with `npx vercel --prod --yes` from the repo root.

---

## Hard medical/compliance rules

1. **Never name a real patient.** Use illustrative composites only.
2. **Never claim FDA approval of a compounded formulation.** The active
   ingredients are FDA-approved; the finished compounded product is not.
3. **Always frame care as clinician-prescribed**, not AI-prescribed.
4. **No claims of cure** ("treats", "cures", "guarantees results", etc.).
   Use "may help", "supports", "designed to support".
5. **Always include the disclaimer paragraph** at the bottom of the article
   body. Copy it verbatim from any existing post (look for the
   `class="article-disclaimer"` block in `semaglutide-tirzepatide-difference.html`).
6. **Pregnancy / breastfeeding warning** must appear on any post mentioning
   Finasteride, Dutasteride, or Tretinoin.

---

## Recommended cadence

- **Frequency:** one post per weekday (Mon–Fri, 8am Central). No weekend posts.
- **Rotation:** cycle through categories so the same one doesn't post twice in
  a row.
- **Keyword strategy:** lean into long-tail comparison queries
  ("X vs Y", "how to choose between…", "what changes when…") — every post in
  the repo right now is a comparison/explainer, and that's what AI search
  engines cite from.

---

## Sanity checklist before pushing

- [ ] `blog/<slug>.html` exists, no `{{...}}` placeholders left
- [ ] `blog/posts.json` has the new entry as the first item in the array
- [ ] `blog/index.html` server-rendered cards include the new post
- [ ] All 4 URLs in the article body resolve (no 404s in CTA, image, canonical, OG)
- [ ] Post body is 900–1,400 words
- [ ] Category is in the allow-list
- [ ] Disclaimer paragraph is present at the bottom
- [ ] Commit author is `directcareai@gmail.com`

If automation can't satisfy the checklist, **don't push** — log the failure
and surface it instead of publishing a broken post.
