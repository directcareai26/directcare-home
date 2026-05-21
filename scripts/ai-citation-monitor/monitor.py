#!/usr/bin/env python3
"""
DirectCare AI — Citation tracking across AI engines.

Item #68 from the 70-point AI Visibility Checklist:
  "AI citation tracking set up for core brand terms" (Critical)

What this does
---------------
Loops through every tracked prompt in prompts.json, asks N AI engines that
have web access ("did you mention DirectCare AI for this query?"), parses the
response for brand mentions and competitor mentions, and writes:

  results/YYYY-MM-DD.json      raw per-engine responses + parsed mentions
  results/YYYY-MM-DD.md        human-readable summary report
  results/history.csv          one row per (date, engine, prompt) for trending

Currently wired engines (skipped automatically if API key missing):
  - Perplexity (PERPLEXITY_API_KEY)        ← MOST IMPORTANT, always cites sources
  - Anthropic Claude w/ web_search tool    (ANTHROPIC_API_KEY)
  - OpenAI ChatGPT (gpt-4o + Responses web_search) (OPENAI_API_KEY)
  - Google Gemini w/ Google Search grounding (GEMINI_API_KEY)

Usage
-----
  pip install requests
  export PERPLEXITY_API_KEY=pplx-...
  export ANTHROPIC_API_KEY=sk-ant-...     # optional
  export OPENAI_API_KEY=sk-...            # optional
  export GEMINI_API_KEY=...               # optional
  python monitor.py                       # full run, all prompts, all engines
  python monitor.py --vertical hrt        # only HRT prompts
  python monitor.py --engine perplexity   # only one engine
  python monitor.py --dry-run             # print plan, don't call APIs

Schedule
--------
  - GitHub Action (recommended): see .github/workflows/ai-citation-monitor.yml
  - Vercel Cron Job: see vercel-cron-handler.ts
  - Local cron:  0 9 * * * cd /path && python monitor.py
"""

from __future__ import annotations
import argparse
import csv
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

try:
    import requests
except ImportError:
    print("ERROR: requests not installed. Run: pip install requests", file=sys.stderr)
    sys.exit(1)

HERE = Path(__file__).resolve().parent
PROMPTS_FILE = HERE / "prompts.json"
RESULTS_DIR = HERE / "results"
RESULTS_DIR.mkdir(exist_ok=True)


# ---------------------------- Brand parsing -------------------------------

def parse_mentions(text: str, brand_terms: list[str], competitors: list[str]) -> dict:
    """Return {brand_hits, competitor_hits, position} for a single response."""
    if not text:
        return {"brand_hits": 0, "competitors": {}, "position": None, "first_mention_idx": None}
    lower = text.lower()
    brand_hits = 0
    first_idx = None
    for term in brand_terms:
        for m in re.finditer(re.escape(term.lower()), lower):
            brand_hits += 1
            if first_idx is None or m.start() < first_idx:
                first_idx = m.start()
    competitor_hits = {}
    for c in competitors:
        n = lower.count(c.lower())
        if n:
            competitor_hits[c] = n
    # Position = rank among brand mentions in numbered/bulleted lists
    position = None
    if first_idx is not None:
        prefix = text[:first_idx]
        list_markers = re.findall(r"(?:^|\n)\s*(?:(\d+)[\.\)]|[-*•])\s", prefix)
        if list_markers:
            # Last numbered marker before the brand = its rank
            nums = [int(m) for m in list_markers if m and m.isdigit()]
            if nums:
                position = nums[-1] + 1  # +1 because the next item is the brand
            else:
                position = len(list_markers) + 1
    return {
        "brand_hits": brand_hits,
        "competitors": competitor_hits,
        "position": position,
        "first_mention_idx": first_idx,
    }


# ---------------------------- Engines -------------------------------------
# Each engine returns (response_text, citations_list_or_None, error_str_or_None).

def call_perplexity(prompt: str) -> tuple[str, list[str] | None, str | None]:
    key = os.getenv("PERPLEXITY_API_KEY")
    if not key:
        return "", None, "PERPLEXITY_API_KEY not set"
    try:
        r = requests.post(
            "https://api.perplexity.ai/chat/completions",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "sonar",
                "messages": [{"role": "user", "content": prompt}],
                "return_citations": True,
            },
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        text = data["choices"][0]["message"]["content"]
        citations = data.get("citations") or []
        return text, citations, None
    except Exception as e:
        return "", None, f"Perplexity error: {e}"


def call_anthropic(prompt: str) -> tuple[str, list[str] | None, str | None]:
    key = os.getenv("ANTHROPIC_API_KEY")
    if not key:
        return "", None, "ANTHROPIC_API_KEY not set"
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-5",
                "max_tokens": 1500,
                "tools": [{"type": "web_search_20250305", "name": "web_search", "max_uses": 4}],
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        # Concatenate all text blocks
        text_parts = []
        citations = []
        for block in data.get("content", []):
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
                for cit in (block.get("citations") or []):
                    if cit.get("url"):
                        citations.append(cit["url"])
        return "\n".join(text_parts), citations or None, None
    except Exception as e:
        return "", None, f"Anthropic error: {e}"


def call_openai(prompt: str) -> tuple[str, list[str] | None, str | None]:
    key = os.getenv("OPENAI_API_KEY")
    if not key:
        return "", None, "OPENAI_API_KEY not set"
    try:
        r = requests.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
            json={
                "model": "gpt-4o",
                "input": prompt,
                "tools": [{"type": "web_search_preview"}],
            },
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        text = data.get("output_text", "")
        citations = []
        for item in data.get("output", []):
            for cit in (item.get("citations") or []):
                if cit.get("url"):
                    citations.append(cit["url"])
        return text, citations or None, None
    except Exception as e:
        return "", None, f"OpenAI error: {e}"


def call_gemini(prompt: str) -> tuple[str, list[str] | None, str | None]:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        return "", None, "GEMINI_API_KEY not set"
    try:
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={key}",
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"role": "user", "parts": [{"text": prompt}]}],
                "tools": [{"google_search": {}}],
            },
            timeout=120,
        )
        r.raise_for_status()
        data = r.json()
        text_parts = []
        citations = []
        for cand in data.get("candidates", []):
            for part in cand.get("content", {}).get("parts", []):
                if "text" in part:
                    text_parts.append(part["text"])
            grounding = cand.get("groundingMetadata", {})
            for chunk in grounding.get("groundingChunks", []):
                web = chunk.get("web", {})
                if web.get("uri"):
                    citations.append(web["uri"])
        return "\n".join(text_parts), citations or None, None
    except Exception as e:
        return "", None, f"Gemini error: {e}"


ENGINES = {
    "perplexity": call_perplexity,
    "anthropic": call_anthropic,
    "openai": call_openai,
    "gemini": call_gemini,
}


# ---------------------------- Run loop ------------------------------------

def iter_prompts(corpus: dict, only_vertical: str | None) -> Iterable[tuple[str, str]]:
    for vertical, prompts in corpus["prompts"].items():
        if only_vertical and vertical != only_vertical:
            continue
        for p in prompts:
            yield vertical, p


def run(args) -> int:
    corpus = json.loads(PROMPTS_FILE.read_text())
    brand_terms = corpus["tracked_brand_terms"]
    competitors = corpus["competitors_to_watch"]
    engines_to_use = [args.engine] if args.engine else list(ENGINES.keys())

    # Sanity check: any keys available?
    available = [e for e in engines_to_use if ENGINES[e].__name__.replace("call_", "").upper() + "_API_KEY" in os.environ
                 or {
                     "perplexity": "PERPLEXITY_API_KEY",
                     "anthropic": "ANTHROPIC_API_KEY",
                     "openai": "OPENAI_API_KEY",
                     "gemini": "GEMINI_API_KEY",
                 }[e] in os.environ]
    print(f"Engines requested: {engines_to_use}")
    print(f"Engines with API keys: {available}")
    if not available and not args.dry_run:
        print("\n⚠️  No API keys set. Try at minimum:  export PERPLEXITY_API_KEY=pplx-...\n")
        return 2

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    runs = []
    for vertical, prompt in iter_prompts(corpus, args.vertical):
        for engine in engines_to_use:
            if args.dry_run:
                print(f"  [DRY] {engine:<11}  {vertical:<14}  {prompt}")
                continue
            print(f"  → {engine:<11}  {vertical:<14}  {prompt[:60]}...")
            text, citations, err = ENGINES[engine](prompt)
            mentions = parse_mentions(text, brand_terms, competitors)
            cit_has_dcai = bool(citations and any("directcare.ai" in c.lower() for c in citations))
            runs.append({
                "date": today,
                "engine": engine,
                "vertical": vertical,
                "prompt": prompt,
                "error": err,
                "response": text,
                "citations": citations,
                "brand_hits": mentions["brand_hits"],
                "position": mentions["position"],
                "competitor_hits": mentions["competitors"],
                "citation_includes_directcare_ai": cit_has_dcai,
            })
            time.sleep(0.5)  # polite

    if args.dry_run:
        print(f"\n{len(list(iter_prompts(corpus, args.vertical)))} prompts × {len(engines_to_use)} engines")
        return 0

    # ----- Write outputs -----
    json_path = RESULTS_DIR / f"{today}.json"
    json_path.write_text(json.dumps(runs, indent=2))
    print(f"\nWrote {json_path}")

    md_path = RESULTS_DIR / f"{today}.md"
    md_path.write_text(render_markdown(runs, today))
    print(f"Wrote {md_path}")

    # Append history CSV
    csv_path = RESULTS_DIR / "history.csv"
    is_new = not csv_path.exists()
    with csv_path.open("a", newline="") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(["date", "engine", "vertical", "prompt", "brand_hits", "position",
                        "cited_in_sources", "top_competitor", "error"])
        for r in runs:
            top_comp = max(r["competitor_hits"].items(), key=lambda kv: kv[1], default=("", 0))[0]
            w.writerow([r["date"], r["engine"], r["vertical"], r["prompt"],
                        r["brand_hits"], r["position"], r["citation_includes_directcare_ai"],
                        top_comp, r["error"] or ""])
    print(f"Appended {csv_path}")
    return 0


def render_markdown(runs: list[dict], today: str) -> str:
    total = len(runs)
    wins = sum(1 for r in runs if r["brand_hits"] > 0)
    cited = sum(1 for r in runs if r["citation_includes_directcare_ai"])
    errs = sum(1 for r in runs if r["error"])
    lines = [
        f"# AI Citation Report — {today}",
        "",
        f"- **{wins}/{total}** prompts where DirectCare AI was mentioned in the response (**{wins/total*100 if total else 0:.0f}%**)",
        f"- **{cited}/{total}** prompts where directcare.ai appeared in cited sources (**{cited/total*100 if total else 0:.0f}%**)",
        f"- **{errs}** API errors",
        "",
        "## Win/Loss by vertical & engine",
        "",
        "| Vertical | Engine | Mentioned | Cited in sources | Top competitor mentioned |",
        "|---|---|---|---|---|",
    ]
    # Pivot
    by_key = {}
    for r in runs:
        k = (r["vertical"], r["engine"])
        d = by_key.setdefault(k, {"total": 0, "wins": 0, "cited": 0, "competitors": {}})
        d["total"] += 1
        if r["brand_hits"] > 0:
            d["wins"] += 1
        if r["citation_includes_directcare_ai"]:
            d["cited"] += 1
        for c, n in r["competitor_hits"].items():
            d["competitors"][c] = d["competitors"].get(c, 0) + n
    for (vert, eng), d in sorted(by_key.items()):
        top = max(d["competitors"].items(), key=lambda kv: kv[1], default=("—", 0))[0]
        lines.append(f"| {vert} | {eng} | {d['wins']}/{d['total']} | {d['cited']}/{d['total']} | {top} |")
    lines += ["", "## Prompt-by-prompt detail", ""]
    for r in runs:
        status = "✅" if r["brand_hits"] > 0 else ("⚠️" if r["error"] else "❌")
        lines.append(f"### {status} `{r['engine']}` — _{r['vertical']}_")
        lines.append(f"> {r['prompt']}")
        lines.append("")
        if r["error"]:
            lines.append(f"**Error:** {r['error']}")
        else:
            lines.append(f"**Brand hits:** {r['brand_hits']}   **Position:** {r['position'] or '—'}   "
                         f"**Cited in sources:** {'yes' if r['citation_includes_directcare_ai'] else 'no'}")
            if r["competitor_hits"]:
                lines.append(f"**Competitors named:** " + ", ".join(f"{k} ({v})" for k, v in r["competitor_hits"].items()))
            if r["citations"]:
                lines.append("**Sources:**")
                for c in r["citations"][:6]:
                    lines.append(f"  - {c}")
            preview = r["response"][:600].replace("\n", " ")
            lines.append(f"\n```\n{preview}{'…' if len(r['response']) > 600 else ''}\n```")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--vertical", help="Only run prompts from this vertical (hrt, trt, weight_loss, etc.)")
    ap.add_argument("--engine", choices=list(ENGINES.keys()), help="Only query this engine")
    ap.add_argument("--dry-run", action="store_true", help="Print plan, don't call APIs")
    args = ap.parse_args()
    return run(args)


if __name__ == "__main__":
    sys.exit(main())
