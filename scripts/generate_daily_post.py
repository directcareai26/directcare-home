#!/usr/bin/env python3
"""
generate_daily_post.py — Use the Anthropic Claude API to draft one SEO-friendly
blog post about a DirectCare AI DTC product, render it to HTML, and update the
manifest. Run once per day from the scheduled task.

Requires:
  - ANTHROPIC_API_KEY env var
  - `anthropic` Python package (pip install anthropic)

Picks a topic deterministically from a rotating pool, avoiding any slug already
present in blog/posts.json so we don't repeat ourselves. Falls back to a hand-
written topic list if all rotation seeds have been used.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOG_DIR = REPO_ROOT / "blog"
MANIFEST_PATH = BLOG_DIR / "posts.json"
TOPIC_BANK_PATH = Path(__file__).resolve().parent / "topic_bank.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_post import write_post  # noqa: E402

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-7")
MAX_TOKENS = 8000

PRODUCTS = {
    "TRT": {
        "categorySlug": "trt",
        "product_link": "/testosterone-replacement-therapy",
        "product_eyebrow": "Ready to find your protocol?",
        "product_headline": "Testosterone therapy, tuned to your levels.",
        "product_blurb": "Injectable, oral, or enclomiphene — DirectCare AI's clinical team reviews your full hormone panel and recommends the protocol that fits your numbers and your life. Labs included.",
        "product_cta_label": "Start your TRT consult",
        "image": "https://crsurakhmbalgxim.public.blob.vercel-storage.com/%20Testosterone%20%E2%80%94%20lifestyleImage.png",
    },
    "HRT": {
        "categorySlug": "hrt",
        "product_link": "/hormone-replacement-therapy",
        "product_eyebrow": "Ready to feel like yourself again?",
        "product_headline": "Hormone therapy, built around your bloodwork.",
        "product_blurb": "Bioidentical estradiol and progesterone protocols, prescribed by a US-licensed clinician based on a real hormone panel — not a 5-question quiz. Labs and follow-up included.",
        "product_cta_label": "Start your HRT consult",
        "image": "https://crsurakhmbalgxim.public.blob.vercel-storage.com/Warm%20%26%20confident.png",
    },
    "Weight Loss": {
        "categorySlug": "weight-loss",
        "product_link": "/weight-loss/",
        "product_eyebrow": "Ready to start?",
        "product_headline": "Sustainable weight loss, built around your labs.",
        "product_blurb": "Compounded semaglutide and tirzepatide. Weekly injection, US-licensed clinician oversight, dose titration based on your real bloodwork — not a one-size-fits-all script.",
        "product_cta_label": "See if you qualify",
        "image": "https://crsurakhmbalgxim.public.blob.vercel-storage.com/Weight%20Loss%20%E2%80%94%20lifestyleImage.png",
    },
    "Sexual Health": {
        "categorySlug": "sexual-health",
        "product_link": "/surge-max/",
        "product_eyebrow": "Get your edge back.",
        "product_headline": "Sexual health, prescribed and discreet.",
        "product_blurb": "Compounded sildenafil, tadalafil, and combination protocols. US-licensed clinician oversight. Shipped discreetly.",
        "product_cta_label": "See your options",
        "image": "https://crsurakhmbalgxim.public.blob.vercel-storage.com/Sexual%20Health%20%E2%80%94%20lifestyleImage.png",
    },
    "Hair Regrowth": {
        "categorySlug": "hair-regrowth",
        "product_link": "/mens-hair-loss/",
        "product_eyebrow": "Keep what you have. Grow what you've lost.",
        "product_headline": "Hair regrowth protocols, by your clinician.",
        "product_blurb": "Topical and oral finasteride, dutasteride, and minoxidil — prescribed and titrated based on what your scalp actually needs.",
        "product_cta_label": "Start regrowth",
        "image": "https://crsurakhmbalgxim.public.blob.vercel-storage.com/Hair%20Regrowth%20%E2%80%94%20lifestyleImage.png",
    },
    "Blood Labs": {
        "categorySlug": "blood-labs",
        "product_link": "/blood-test/",
        "product_eyebrow": "Know your real numbers.",
        "product_headline": "Real labs. Plain-English plan.",
        "product_blurb": "A clinician-ordered, 80+ biomarker panel. Results in 3–5 days, with a personalized roadmap from a US-licensed clinician — not a chart you have to decode yourself.",
        "product_cta_label": "See my numbers",
        "image": "https://crsurakhmbalgxim.public.blob.vercel-storage.com/Health%20Check%20%E2%80%94%20lifestyleImage.png",
    },
    "Supplements": {
        "categorySlug": "supplements",
        "product_link": "/supplements/",
        "product_eyebrow": "Build your stack with intent.",
        "product_headline": "Physician-formulated supplement protocols.",
        "product_blurb": "DirectCare AI clinicians curate supplement protocols matched to your actual bloodwork — not a generic multivitamin.",
        "product_cta_label": "Browse supplements",
        "image": "https://crsurakhmbalgxim.public.blob.vercel-storage.com/flatlay%20of%20women%27s%20protocol%20bottles.png",
    },
}


DEFAULT_TOPIC_BANK = [
    {"category": "TRT", "angle": "How to read your free testosterone vs. total testosterone — and why one matters more than the other"},
    {"category": "TRT", "angle": "Estradiol on TRT: why some men need an aromatase inhibitor and most don't"},
    {"category": "TRT", "angle": "What hematocrit does on injectable testosterone and how often you should be donating blood"},
    {"category": "TRT", "angle": "Subcutaneous vs. intramuscular testosterone injections — what the data says about pharmacokinetics"},
    {"category": "TRT", "angle": "TRT and fertility: how to preserve sperm production while on testosterone therapy"},
    {"category": "HRT", "angle": "Perimenopause vs. menopause: how the lab values actually differ and what each one calls for"},
    {"category": "HRT", "angle": "Oral micronized progesterone vs. progestins — why the difference matters for breast and brain health"},
    {"category": "HRT", "angle": "The case for testosterone in women's HRT protocols (and why most clinics still don't offer it)"},
    {"category": "HRT", "angle": "Transdermal estradiol patches vs. gels vs. pellets — the real-world trade-offs"},
    {"category": "HRT", "angle": "HRT and bone density: how estradiol prevents fractures decades later"},
    {"category": "Weight Loss", "angle": "How to dose-titrate GLP-1s without spending a month nauseated"},
    {"category": "Weight Loss", "angle": "Muscle preservation on GLP-1s: the protein and resistance-training rules that matter"},
    {"category": "Weight Loss", "angle": "Maintenance dosing after GLP-1 weight loss — staying off without rebounding"},
    {"category": "Weight Loss", "angle": "GLP-1s and thyroid: what to monitor and when to stop"},
    {"category": "Weight Loss", "angle": "Why your weight-loss plateau is probably hormonal, not motivational"},
    {"category": "Sexual Health", "angle": "Sildenafil vs. tadalafil: how to pick the right ED medication for your life"},
    {"category": "Sexual Health", "angle": "Why ED is often a cardiovascular signal — and the labs that confirm it"},
    {"category": "Sexual Health", "angle": "Low libido in men: when it's testosterone, when it's stress, and when it's neither"},
    {"category": "Hair Regrowth", "angle": "Topical vs. oral finasteride: matching delivery to side-effect tolerance"},
    {"category": "Hair Regrowth", "angle": "Why dutasteride is more aggressive than finasteride — and when that's the right call"},
    {"category": "Hair Regrowth", "angle": "Female-pattern hair loss: the hormonal panel every clinician should run first"},
    {"category": "Hair Regrowth", "angle": "Minoxidil 5% vs. 7% compounded: dose-response data and side effects"},
    {"category": "Blood Labs", "angle": "The 10 biomarkers that actually predict longevity — and why most annual physicals miss half of them"},
    {"category": "Blood Labs", "angle": "ApoB vs. LDL: the cholesterol number cardiologists wish you'd ask about"},
    {"category": "Blood Labs", "angle": "How to read your hormone panel like a clinician (every marker, what it means, what's normal)"},
    {"category": "Blood Labs", "angle": "Ferritin and iron in women: the deficiency that's mistaken for menopause every day"},
    {"category": "Supplements", "angle": "Magnesium glycinate vs. citrate vs. threonate — choosing by what you actually need"},
    {"category": "Supplements", "angle": "Vitamin D3 + K2: dosing, blood-level targets, and why most patients are still deficient"},
    {"category": "Supplements", "angle": "Creatine monohydrate isn't just for the gym — the cognition and bone data women should know"},
    {"category": "Supplements", "angle": "Omega-3 EPA/DHA: the dose that actually moves your inflammation markers"},
]


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:80]


def existing_slugs() -> set[str]:
    if not MANIFEST_PATH.exists():
        return set()
    try:
        data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return set()
    return {p.get("slug", "") for p in data.get("posts", [])}


def load_topic_bank() -> list[dict[str, str]]:
    if TOPIC_BANK_PATH.exists():
        try:
            return json.loads(TOPIC_BANK_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return DEFAULT_TOPIC_BANK


def pick_topic(today: dt.date) -> dict[str, str]:
    """Pick a topic that hasn't been used yet, deterministic from date so re-runs
    on the same day pick the same topic."""
    topics = load_topic_bank()
    used = existing_slugs()

    # Order topics by a date-seeded hash, then take the first unused one.
    seed = today.isoformat()

    def score(t: dict[str, str]) -> str:
        h = hashlib.sha256(f"{seed}::{t['category']}::{t['angle']}".encode()).hexdigest()
        return h

    ordered = sorted(topics, key=score)
    for t in ordered:
        candidate_slug = slugify(t["angle"])
        if candidate_slug not in used:
            return t
    # All used — return the first ordered topic anyway; the model will rewrite it.
    return ordered[0]


PROMPT_TEMPLATE = """You are a senior medical writer for DirectCare AI, an AI-powered direct-to-patient telehealth platform. You write the brand's Blog — long-form, SEO-friendly, clinician-tone articles that help patients understand the science behind hormone therapy, weight loss, sexual health, hair regrowth, blood labs, and supplements.

## Brand voice
- Plain English, clinician's-eye view, never breathless.
- Concrete, not vague: real numbers, real biomarkers, real trade-offs.
- Empathetic but never patronizing. Treat the reader as an intelligent adult.
- "Real labs, plain-English plan" is the brand promise.
- Italicize one short emotional phrase per H2 (we render <em>...</em> in italic + brand color) — like "in plain English," "tuned to your numbers," "what actually changes," etc.

## Compliance & safety (HARD RULES)
- Never claim cure, miracle, or guaranteed results.
- Never name specific competitor compounded pharmacies.
- Never give a specific dose recommendation outside of standard published titration ranges.
- **Never claim DirectCare AI requires bloodwork before prescribing.** DirectCare AI offers blood labs as a product, and many patients choose them — but writing "Before any prescription at DirectCare AI, a clinician reviews [labs]" or "every patient does a baseline panel" is FALSE and creates compliance risk. Acceptable framings: "a thorough workup would typically include...", "if you choose to do bloodwork through us, the markers we look at first are...", "the labs worth having before a serious protocol are..." — keep the educational content, drop the procedural promise.
- Frame medication decisions as benefiting from clinician review of relevant context (symptoms, history, and labs when run), not as gated on labs.
- Note that compounded medications are not FDA-approved as finished products (the article disclaimer handles this; you can reference it casually).
- No before/after weight-loss specifics that imply average results.
- For GLP-1s, weight-loss percentages must be cited from named trials (SURMOUNT-5, STEP, etc.) — never just "studies show."

## SEO requirements
- Title is 50–65 characters, includes the primary keyword naturally.
- Meta description is 140–158 characters, includes primary + secondary keyword, ends with implicit value promise.
- The first paragraph (the deck) answers the search intent in 2 sentences before the article expands.
- Use H2s that are scannable questions or claims a reader would Google.
- 1,200–1,800 words in the body.
- Include a {{callout}} block once for the most important takeaway.

## Today's assignment
Category: {category}
Angle: {angle}
Date: {date_label}

## Output format — RESPOND WITH PURE JSON, NO COMMENTARY

Return a JSON object with this exact schema:

{{
  "slug": "kebab-case-slug-50-chars-max",
  "title": "Full title, 50-65 chars",
  "title_html": "Title with one <em>italic phrase</em> wrapped in em tags",
  "deck": "2-sentence deck that answers the search intent.",
  "meta_description": "140-158 char meta description.",
  "excerpt": "1-2 sentence card excerpt, max 240 chars.",
  "keywords": ["primary keyword", "secondary keyword", "long-tail keyword", "..."],
  "body_markdown": "Full article in markdown-lite. Use:\\n\\n## H2 headings\\n### H3 headings (sparingly)\\n**bold** and *italic*\\n- bullet lists\\n> blockquote for the single best line\\n[link text](https://or-internal-/path)\\n{{callout: optional eyebrow}} The single most important sentence in the article.\\n\\nKeep paragraphs short (2-4 sentences). Use blank lines between paragraphs. Do NOT use HTML tags — just markdown. End the body before any product CTA; the template adds that automatically."
}}

Generate the post now. Output JSON only — no prose before or after.
"""


def call_claude(topic: dict[str, str], date_label: str) -> dict:
    try:
        import anthropic  # type: ignore
    except ImportError:
        print("ERROR: anthropic package not installed. Run: pip install anthropic", file=sys.stderr)
        sys.exit(2)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set in environment.", file=sys.stderr)
        sys.exit(3)

    client = anthropic.Anthropic(api_key=api_key)
    prompt = PROMPT_TEMPLATE.format(category=topic["category"], angle=topic["angle"], date_label=date_label)

    resp = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=MAX_TOKENS,
        messages=[{"role": "user", "content": prompt}],
    )

    text = "".join(block.text for block in resp.content if getattr(block, "type", None) == "text")
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return json.loads(text)


def merge_product_metadata(payload: dict, category: str) -> dict:
    product = PRODUCTS.get(category, {})
    payload.setdefault("category", category)
    payload.setdefault("categorySlug", product.get("categorySlug", slugify(category)))
    payload.setdefault("image", product.get("image"))
    for k in ("product_link", "product_eyebrow", "product_headline", "product_blurb", "product_cta_label"):
        if k in product:
            payload.setdefault(k, product[k])
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the daily blog post.")
    parser.add_argument("--date", help="Override date (YYYY-MM-DD). Defaults to today.")
    parser.add_argument("--dry-run", action="store_true", help="Print payload, don't write files.")
    parser.add_argument("--category", help="Force a specific category from PRODUCTS.")
    parser.add_argument("--angle", help="Force a specific angle (requires --category).")
    args = parser.parse_args()

    today = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    date_label = today.strftime("%B %-d, %Y")

    if args.category and args.angle:
        topic = {"category": args.category, "angle": args.angle}
    else:
        topic = pick_topic(today)

    print(f"[generate_daily_post] {today} — {topic['category']}: {topic['angle']}", file=sys.stderr)

    payload = call_claude(topic, date_label)
    payload["date"] = today.isoformat()
    payload["dateLabel"] = date_label
    payload = merge_product_metadata(payload, topic["category"])

    if args.dry_run:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    path = write_post(payload)
    print(json.dumps({"ok": True, "path": str(path.relative_to(REPO_ROOT)), "slug": payload["slug"], "title": payload["title"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
