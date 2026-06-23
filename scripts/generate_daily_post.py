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
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BLOG_DIR = REPO_ROOT / "blog"
MANIFEST_PATH = BLOG_DIR / "posts.json"
TOPIC_BANK_PATH = Path(__file__).resolve().parent / "topic_bank.json"
# Ledger of bank angles the generator has already consumed. Keyed on the exact
# bank angle string so an angle is never re-picked even if its generated slug
# varies day to day (the bug that produced two "grip strength" posts).
USED_TOPICS_PATH = Path(__file__).resolve().parent / "used_topics.json"

sys.path.insert(0, str(Path(__file__).resolve().parent))
from render_post import write_post  # noqa: E402

CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-opus-4-7")
MAX_TOKENS = 8000

BLOB = "https://crsurakhmbalgxim.public.blob.vercel-storage.com"

# Image pools per category — generator picks one deterministically per post.
# Mix of original lifestyle images + new Firefly photography set.
IMAGE_POOLS = {
    "TRT": [
        f"{BLOB}/Firefly_Gemini%20Flash_Healthy%20confident%20man%20in%20his%20early%2040s%20smiling%20naturally%20outdoors%2C%20fit%20physique%2C%20ener%2022947.png",
        f"{BLOB}/Firefly_Professional%20businessman%20in%20his%2040s%20smiling%20confidently%20in%20modern%20office%2C%20healthy%20app%2022947.png",
        f"{BLOB}/Firefly_Ultra%20realistic%20portrait%20of%20healthy%20smiling%20man%20age%2035-45%2C%20natural%20sunlight%2C%20genuine%20%2022947.png",
        f"{BLOB}/Firefly_Ultra%20realistic%20portrait%20of%20healthy%20smiling%20man%20age%2035-45%2C%20natural%20sunlight%2C%20genuine%20%20395753.png",
        f"{BLOB}/%20Testosterone%20%E2%80%94%20lifestyleImage.png",
    ],
    "HRT": [
        f"{BLOB}/Firefly_Beautiful%20confident%20woman%20age%2050-60%20smiling%20outdoors%2C%20healthy%20glowing%20skin%2C%20natural%20e%2022947.png",
        f"{BLOB}/Firefly_Active%20mature%20woman%20walking%20through%20a%20park%20in%20morning%20sunlight%2C%20healthy%20aging%20concept%2022947.png",
        f"{BLOB}/Warm%20%26%20confident.png",
        f"{BLOB}/perimenopausal%20woman.png",
    ],
    "Weight Loss": [
        f"{BLOB}/GLP-1%20Nutrition.png",
        f"{BLOB}/Emotional%20Eating.png",
        f"{BLOB}/Firefly_Gemini%20Flash_Ultra-realistic%20professional%20fitness%20photography%20of%20a%20strong%20athletic%20man%20performing%20%2022947.png",
        f"{BLOB}/the%20strength%20couple.png",
    ],
    "Sexual Health": [
        f"{BLOB}/Sexual%20Health%20%E2%80%94%20lifestyleImage.png",
        f"{BLOB}/Morning%20bed%2C%20foreheads%20touching.png",
        f"{BLOB}/Firefly_Ultra%20realistic%20portrait%20of%20healthy%20smiling%20man%20age%2035-45%2C%20natural%20sunlight%2C%20genuine%20%20395753.png",
    ],
    "Hair Regrowth": [
        f"{BLOB}/Hair%20Regrowth%20%E2%80%94%20lifestyleImage.png",
        f"{BLOB}/woman%20tying%20hair%20up%20confidently.png",
    ],
    "Blood Labs": [
        f"{BLOB}/Firefly_Gemini%20Flash_Professional%20nutritionist%20consulting%20with%20healthy%20adult%20client%2C%20discussing%20meal%20plan%20%2022947.png",
        f"{BLOB}/Health%20Check%20%E2%80%94%20lifestyleImage.png",
        f"{BLOB}/Progress%20%26%20Biomarkers.png",
    ],
    "Supplements": [
        f"{BLOB}/flatlay%20of%20women%27s%20protocol%20bottles.png",
        f"{BLOB}/Firefly_Gemini%20Flash_Professional%20nutritionist%20consulting%20with%20healthy%20adult%20client%2C%20discussing%20meal%20plan%20%2022947.png",
    ],
    "Nutrition": [
        f"{BLOB}/GLP-1%20Nutrition.png",
        f"{BLOB}/Firefly_Happy%20healthy%20family%20sharing%20nutritious%20meal%20at%20dining%20table%2C%20natural%20laughter%2C%20authe%2022947.png",
        f"{BLOB}/Firefly_Gemini%20Flash_Diverse%20group%20of%20healthy%20adults%20smiling%20naturally%20together%2C%20authentic%20expressions%2C%20he%20395753.png",
        f"{BLOB}/Emotional%20Eating.png",
        f"{BLOB}/Vibrant%20%26%20energetic%20%28younger%2040s%2C%20more%20uplift%29.png",
    ],
    "Fitness": [
        f"{BLOB}/Firefly_Professional%20fitness%20model%20performing%20dumbbell%20shoulder%20press%20in%20upscale%20gym%2C%20natural%2022947.png",
        f"{BLOB}/Firefly_Athletic%20woman%20performing%20kettlebell%20workout%20in%20bright%20modern%20fitness%20studio%2C%20natural%2022947.png",
        f"{BLOB}/Firefly_Gemini%20Flash_Ultra-realistic%20professional%20fitness%20photography%20of%20a%20strong%20athletic%20man%20performing%20%2022947.png",
        f"{BLOB}/Firefly_Active%20mature%20woman%20walking%20through%20a%20park%20in%20morning%20sunlight%2C%20healthy%20aging%20concept%2022947.png",
        f"{BLOB}/Lifestyle%20%26%20Exercise.png",
    ],
}

PRODUCTS = {
    "TRT": {
        "categorySlug": "trt",
        "product_link": "/testosterone-replacement-therapy",
        "product_eyebrow": "Ready to find your protocol?",
        "product_headline": "Testosterone therapy, tuned to your levels.",
        "product_blurb": "Injectable, oral, or enclomiphene — DirectCare AI's clinical team reviews your full hormone panel and recommends the protocol that fits your numbers and your life.",
        "product_cta_label": "Start your TRT consult",
    },
    "HRT": {
        "categorySlug": "hrt",
        "product_link": "/hormone-replacement-therapy",
        "product_eyebrow": "Ready to feel like yourself again?",
        "product_headline": "Hormone therapy, built around your bloodwork.",
        "product_blurb": "Bioidentical estradiol and progesterone protocols, prescribed by a US-licensed clinician based on a real hormone panel — not a 5-question quiz.",
        "product_cta_label": "Start your HRT consult",
    },
    "Weight Loss": {
        "categorySlug": "weight-loss",
        "product_link": "/weight-loss/",
        "product_eyebrow": "Ready to start?",
        "product_headline": "Sustainable weight loss, built around your labs.",
        "product_blurb": "Compounded semaglutide and tirzepatide. Weekly injection, US-licensed clinician oversight, dose titration based on your real bloodwork — not a one-size-fits-all script.",
        "product_cta_label": "See if you qualify",
    },
    "Sexual Health": {
        "categorySlug": "sexual-health",
        "product_link": "/surge-max/",
        "product_eyebrow": "Get your edge back.",
        "product_headline": "Sexual health, prescribed and discreet.",
        "product_blurb": "Compounded sildenafil, tadalafil, and combination protocols. US-licensed clinician oversight. Shipped discreetly.",
        "product_cta_label": "See your options",
    },
    "Hair Regrowth": {
        "categorySlug": "hair-regrowth",
        "product_link": "/mens-hair-loss/",
        "product_eyebrow": "Keep what you have. Grow what you've lost.",
        "product_headline": "Hair regrowth protocols, by your clinician.",
        "product_blurb": "Topical and oral finasteride, dutasteride, and minoxidil — prescribed and titrated based on what your scalp actually needs.",
        "product_cta_label": "Start regrowth",
    },
    "Blood Labs": {
        "categorySlug": "blood-labs",
        "product_link": "/blood-test/",
        "product_eyebrow": "Know your real numbers.",
        "product_headline": "Real labs. Plain-English plan.",
        "product_blurb": "A clinician-ordered, 80+ biomarker panel. Results in 3–5 days, with a personalized roadmap from a US-licensed clinician — not a chart you have to decode yourself.",
        "product_cta_label": "See my numbers",
    },
    "Supplements": {
        "categorySlug": "supplements",
        "product_link": "/supplements/",
        "product_eyebrow": "Build your stack with intent.",
        "product_headline": "Physician-formulated supplement protocols.",
        "product_blurb": "DirectCare AI clinicians curate supplement protocols matched to your actual bloodwork — not a generic multivitamin.",
        "product_cta_label": "Browse supplements",
    },
    "Nutrition": {
        "categorySlug": "nutrition",
        "product_link": "/weight-loss/",
        "product_eyebrow": "Make weight loss easier",
        "product_headline": "Compounded GLP-1, with clinician oversight.",
        "product_blurb": "DirectCare AI prescribes compounded semaglutide and tirzepatide with the nutrition guidance to make a suppressed appetite still hit protein and fiber.",
        "product_cta_label": "See if you qualify",
    },
    "Fitness": {
        "categorySlug": "fitness",
        "product_link": "/weight-loss/",
        "product_eyebrow": "Stack the right protocol on the right habits",
        "product_headline": "Real protocols, built around your bloodwork.",
        "product_blurb": "DirectCare AI prescribes hormone, weight-loss, and longevity protocols designed to layer on top of the training and nutrition habits that actually move outcomes.",
        "product_cta_label": "Start an intake",
    },
}


def pick_image(category: str, date_iso: str, slug: str) -> str:
    """Deterministically rotate through the category's image pool so two
    posts in the same category don't get the same photo back-to-back."""
    pool = IMAGE_POOLS.get(category) or [
        f"{BLOB}/Warm%20%26%20confident.png"
    ]
    seed = f"{date_iso}::{category}::{slug}"
    idx = int(hashlib.sha256(seed.encode()).hexdigest(), 16) % len(pool)
    return pool[idx]


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
    # ---- Nutrition (mix of science + recipe angles) ----
    {"category": "Nutrition", "angle": "The 30-gram protein lunch rule: why a real lunch beats a snack-as-meal"},
    {"category": "Nutrition", "angle": "A clinician-built sheet-pan chicken thigh recipe for high-protein meal prep"},
    {"category": "Nutrition", "angle": "What 'eat the rainbow' actually means clinically — phytonutrient targets by color"},
    {"category": "Nutrition", "angle": "Plant protein for women in perimenopause: the lentil, tofu, and tempeh rotation"},
    {"category": "Nutrition", "angle": "Fiber on a GLP-1: why 25-35g daily makes the appetite suppression sustainable"},
    {"category": "Nutrition", "angle": "An easy 20-minute salmon and asparagus dinner with omega-3 targets that matter"},
    {"category": "Nutrition", "angle": "The protein-and-fiber breakfast template — three rotations for busy mornings"},
    {"category": "Nutrition", "angle": "Greek yogurt parfait recipe: 30g protein, 8g fiber, 5 minutes, three variations"},
    {"category": "Nutrition", "angle": "Why fasted coffee may sabotage your cortisol curve — and what to drink first instead"},
    {"category": "Nutrition", "angle": "A Mediterranean grain bowl recipe that holds in the fridge for 3 days"},
    {"category": "Nutrition", "angle": "Magnesium-rich foods vs. magnesium supplements — when food is actually enough"},
    {"category": "Nutrition", "angle": "Slow-cooker bean chili: 25g plant protein, 12g fiber, weeknight-easy"},
    # ---- Fitness ----
    {"category": "Fitness", "angle": "Zone 2 cardio for adults over 40: what it is, why it matters, and how to measure it"},
    {"category": "Fitness", "angle": "The two-lift-per-day minimum: a busy-week strength template that still preserves muscle"},
    {"category": "Fitness", "angle": "Why grip strength predicts longevity — and the 3 exercises that build it"},
    {"category": "Fitness", "angle": "Mobility before workouts: 5 minutes that meaningfully reduces injury risk"},
    {"category": "Fitness", "angle": "Walking versus running for cardiovascular risk reduction — what the data actually says"},
    {"category": "Fitness", "angle": "Lifting through perimenopause: the rep ranges and recovery rules that hold up"},
    {"category": "Fitness", "angle": "Rucking: the under-rated cardio that builds strength at the same time"},
    {"category": "Fitness", "angle": "Heart rate variability (HRV) — what the number means and when to act on it"},
]


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text)
    text = re.sub(r"-+", "-", text)
    return text.strip("-")[:80]


def manifest_posts() -> list[dict[str, str]]:
    if not MANIFEST_PATH.exists():
        return []
    try:
        return json.loads(MANIFEST_PATH.read_text(encoding="utf-8")).get("posts", [])
    except json.JSONDecodeError:
        return []


def load_topic_bank() -> list[dict[str, str]]:
    if TOPIC_BANK_PATH.exists():
        try:
            return json.loads(TOPIC_BANK_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass
    return DEFAULT_TOPIC_BANK


def load_used_angles() -> set[str]:
    """Bank angles the generator has already produced a post from."""
    if USED_TOPICS_PATH.exists():
        try:
            return set(json.loads(USED_TOPICS_PATH.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            return set()
    return set()


def record_used_angle(angle: str) -> None:
    """Append an angle to the used-topics ledger (after a successful publish)."""
    used = load_used_angles()
    used.add(angle)
    USED_TOPICS_PATH.write_text(json.dumps(sorted(used), indent=2) + "\n", encoding="utf-8")


def category_last_used() -> dict[str, str]:
    """category -> most recent ISO date a post in that category was published."""
    last: dict[str, str] = {}
    for p in manifest_posts():
        cat, date = p.get("category", ""), p.get("date", "")
        if cat and (cat not in last or date > last[cat]):
            last[cat] = date
    return last


_STOPWORDS = {
    "with", "your", "that", "this", "what", "when", "from", "have", "they", "them",
    "more", "most", "than", "into", "about", "actually", "really", "should", "could",
    "does", "doesnt", "isnt", "arent", "and", "the", "for", "you", "are", "but", "not",
    "how", "why", "which", "their", "these", "those", "will", "can", "its", "vs",
}


def _tokens(s: str) -> set[str]:
    return {w for w in re.split(r"[^a-z0-9]+", (s or "").lower()) if len(w) > 3} - _STOPWORDS


def angle_already_covered(angle: str) -> bool:
    """True if a heavily-overlapping post already exists in the manifest.

    Catches near-duplicates whose slugs differ (e.g. 'grip-strength-longevity-
    3-exercises' vs '...-predictor-three-exercises') AND posts created outside
    the generator (manual scripts), which the ledger alone wouldn't know about.
    """
    cand = _tokens(angle)
    if len(cand) < 2:
        return False
    threshold = max(2, int(0.5 * len(cand)))
    for p in manifest_posts():
        existing = _tokens(p.get("slug", "")) | _tokens(p.get("title", ""))
        overlap = cand & existing
        # Either a broad overlap (>= half the candidate's meaningful tokens), OR
        # two-plus shared DISTINCTIVE terms — long tokens (>= 7 chars) are almost
        # always drug names / biomarkers (sildenafil, tadalafil, minoxidil,
        # semaglutide, estradiol, hematocrit), so two matching = same topic.
        distinctive = {w for w in overlap if len(w) >= 7}
        if len(overlap) >= threshold or len(distinctive) >= 2:
            return True
    return False


def pick_topic(today: dt.date) -> dict[str, str]:
    """Pick the next topic on a true rotation.

    1. Rotate CATEGORIES by staleness — the category that's gone longest
       without a post comes first (never-used categories first of all).
    2. Within the chosen category, order angles by a date-seeded hash for
       day-to-day variety, and skip any angle already used (ledger) or already
       covered by an existing post (keyword-overlap heuristic).

    Deterministic per day: same date -> same pick on re-run.
    """
    topics = load_topic_bank()
    used_angles = load_used_angles()
    last_used = category_last_used()
    seed = today.isoformat()

    # Distinct categories in bank order
    bank_categories: list[str] = []
    for t in topics:
        if t["category"] not in bank_categories:
            bank_categories.append(t["category"])

    # Stalest category first. Never-used categories sort to the very front.
    categories_by_staleness = sorted(
        bank_categories, key=lambda c: last_used.get(c, "0000-00-00")
    )

    def angle_score(t: dict[str, str]) -> str:
        return hashlib.sha256(f"{seed}::{t['angle']}".encode()).hexdigest()

    # Walk categories stalest-first; first fresh angle wins.
    for cat in categories_by_staleness:
        cat_topics = sorted((t for t in topics if t["category"] == cat), key=angle_score)
        for t in cat_topics:
            if t["angle"] in used_angles:
                continue
            if angle_already_covered(t["angle"]):
                continue
            return t

    # Fallback 1: any angle not in the ledger, regardless of coverage heuristic.
    for t in sorted(topics, key=angle_score):
        if t["angle"] not in used_angles:
            return t

    # Fallback 2: bank exhausted. Return the stalest category's first angle and
    # let the model write a fresh take. Signals the topic bank needs refilling.
    print(
        "[generate_daily_post] WARNING: topic bank exhausted — every angle has "
        "been used. Add more angles to topic_bank.json / DEFAULT_TOPIC_BANK.",
        file=sys.stderr,
    )
    cat = categories_by_staleness[0]
    return sorted((t for t in topics if t["category"] == cat), key=angle_score)[0]


PROMPT_TEMPLATE = """You are a senior medical writer for DirectCare AI, an AI-powered direct-to-patient telehealth platform. You write the brand's Blog — long-form, SEO-friendly, clinician-tone articles that help patients understand the science behind hormone therapy, weight loss, sexual health, hair regrowth, blood labs, supplements, nutrition (including recipes), and fitness/training.

## Category nuances
- **Recipe posts (Nutrition):** include real ingredient lists, real method steps numbered 1-5, an approximate nutrition block (protein/fiber/carbs/fat/calories), and 2-4 variations. Tone is still clinician-built, not food-blogger breathless.
- **Workout posts (Fitness):** include real exercise names, sets/reps/rest, progression rules, and warm-up notes. Cite ACSM or similar.
- **Science posts (TRT/HRT/Weight Loss/Sexual Health/Hair Regrowth/Blood Labs/Supplements):** lead with the clinical signal or trade-off, cite literature inline.

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

    # Build the SDK client with built-in retries. A single transient network
    # blip (e.g. "Connection reset by peer") used to kill the whole daily cron
    # run; max_retries lets the SDK retry with exponential backoff internally.
    client = anthropic.Anthropic(api_key=api_key, max_retries=5, timeout=120.0)
    prompt = PROMPT_TEMPLATE.format(category=topic["category"], angle=topic["angle"], date_label=date_label)

    # Outer retry loop on top of the SDK's internal retries: covers connection
    # errors, server overloads, and the occasional bad-JSON response. We sleep
    # between attempts so a flaky network at 8 AM doesn't lose the day.
    last_err: Exception | None = None
    for attempt in range(1, 6):
        try:
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
        except Exception as err:  # noqa: BLE001 — we want to retry on anything transient
            last_err = err
            wait = min(60, 5 * (2 ** (attempt - 1)))  # 5, 10, 20, 40, 60
            print(
                f"[generate_daily_post] attempt {attempt}/5 failed: {type(err).__name__}: {err}. "
                f"Retrying in {wait}s..." if attempt < 5 else
                f"[generate_daily_post] attempt {attempt}/5 failed: {type(err).__name__}: {err}.",
                file=sys.stderr,
            )
            if attempt < 5:
                time.sleep(wait)

    # All retries exhausted — re-raise so the wrapper logs failure and the next
    # trigger (login or 8 AM) retries cleanly without a half-written post.
    raise SystemExit(f"ERROR: Claude API call failed after 5 attempts: {last_err}")


def merge_product_metadata(payload: dict, category: str) -> dict:
    product = PRODUCTS.get(category, {})
    payload.setdefault("category", category)
    payload.setdefault("categorySlug", product.get("categorySlug", slugify(category)))
    # Image: rotate through category's pool deterministically (date + slug seed)
    if not payload.get("image"):
        date_iso = payload.get("date") or dt.date.today().isoformat()
        payload["image"] = pick_image(category, date_iso, payload.get("slug", ""))
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

    # Burn the angle in the ledger ONLY after a successful write, so a failed
    # generation (network blip) doesn't permanently consume the topic. Skip
    # when the angle was forced via --angle (manual one-off, not from the bank).
    if not (args.category and args.angle):
        record_used_angle(topic["angle"])

    print(json.dumps({"ok": True, "path": str(path.relative_to(REPO_ROOT)), "slug": payload["slug"], "title": payload["title"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
