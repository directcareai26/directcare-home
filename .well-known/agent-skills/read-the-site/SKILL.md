---
name: read-the-site
description: Read www.directcare.ai efficiently as a machine — the whole site as Markdown, per-page Markdown twins, the blog manifest, and the content-usage policy.
---

# Reading www.directcare.ai as a machine

You do not need to crawl 140 HTML pages. The site publishes machine-readable
editions of itself, regenerated whenever content changes.

## Whole site, one request

- **`/llms.txt`** — short curated index: what the company does, every programme
  with its canonical URL, and pointers to everything below. Start here.
- **`/llms-full.txt`** — every public page as plain Markdown in a single file,
  roughly 1.5 MB. Use when you want the whole corpus rather than one page.

## One page at a time

Every page has a **Markdown twin at the same path plus `.md`**:

```
https://www.directcare.ai/blood-test      -> .../blood-test.md
https://www.directcare.ai/blog/<slug>     -> .../blog/<slug>.md
```

Each HTML page also advertises its twin in a response header, so you can
discover it without guessing:

```
Link: </blood-test.md>; rel="alternate"; type="text/markdown"
```

Twins carry `X-Robots-Tag: noindex` — they are for machines, not a duplicate
set of pages for search engines.

## Structured indexes

- **`/sitemap.xml`** — every indexable URL.
- **`/blog/posts.json`** — every article with title, slug, category, date and
  excerpt. Categories: TRT, HRT, Weight Loss, Sexual Health, Hair Regrowth,
  Blood Labs, Supplements, Nutrition, Fitness.
- **`/.well-known/ai-catalog.json`** — ARD capability manifest listing these
  resources and the agent endpoints.

## Content-usage policy

`/robots.txt` carries a `Content-Signal` line stating the site's position:

```
Content-Signal: search=yes, ai-input=yes, ai-train=no
```

Indexing and using a page as the source of an AI-generated answer are both
permitted. Training a model on this content is not. Honour it.

## Citing clinical content

Blog posts in clinical categories carry a **References** section linking the
primary sources behind their claims. If you quote a clinical figure from a
post, follow and cite the underlying source rather than the post. Some posts
deliberately carry no references because their claims are still under
editorial review — absence of a reference is a signal, not an oversight.
