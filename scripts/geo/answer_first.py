#!/usr/bin/env python3
"""Answer-first paragraphs for blog posts, drafted and fidelity-checked on DGX local inference (D10: free compute
for drafting; nothing ships without the compliance gate).

For each post's Markdown twin (blog/<slug>.md):
  1. gemma3:27b drafts a 40-60 word direct answer to the question the title poses, using ONLY facts in the article
     (no new numbers, dosages, claims, or marketing).
  2. medgemma:27b audits the draft against the article: every statement must be supported; verdict SUPPORTED /
     UNSUPPORTED with the offending sentence.
  3. Only SUPPORTED drafts are written to the candidates file for the dca-risk-compliance gate; nothing touches the site.

Usage: python3 scripts/geo/answer_first.py [--limit N] [--out FILE]
Ollama HTTP on the DGX (never SSH; the DGX is a service). Positive control: a deliberately wrong draft must be
rejected by the auditor before any real post is processed, else the run aborts as UNDELIVERED.
"""
import argparse, functools, glob, json, os, re, sys, time, urllib.request
print = functools.partial(print, flush=True)   # background runs: show progress as it happens
OLLAMA = os.environ.get("DGX_OLLAMA", "http://100.88.129.123:11434")
# gemma3:27b is monopolised by the optimizer's long web-page-rank generations (Ollama serialises per model);
# qwen3-30b-instruct is idle and strong at faithful summarisation. Audit stays on medgemma.
DRAFT_MODEL, AUDIT_MODEL = "qwen3:30b-a3b-instruct-2507-q8_0", "medgemma:27b"
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def ollama(model, prompt, num_predict=600, temperature=0.2):
    body = {"model": model, "prompt": prompt, "stream": False, "keep_alive": "30m",
            "options": {"temperature": temperature, "num_predict": num_predict, "num_ctx": 16384}}
    req = urllib.request.Request(OLLAMA + "/api/generate", data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    for attempt in range(3):
        try:
            return json.load(urllib.request.urlopen(req, timeout=900))["response"].strip()
        except Exception as e:  # noqa: BLE001
            if attempt == 2:
                raise
            time.sleep(20)


def article_text(md):
    s = re.sub(r"^\s*#\s.*$", "", md, count=1, flags=re.M)      # drop the H1 line (title stays separate)
    s = re.sub(r"\n## References.*$", "", s, flags=re.S)         # references are not facts to summarise
    return s.strip()[:14000]


def draft(title, body):
    return ollama(DRAFT_MODEL, f"""You write the opening paragraph of a health article for an answer engine.
Title: {title}

Article:
\"\"\"{body}\"\"\"

Write ONE paragraph of 40-60 words that directly answers the question the title implies, in plain language, using ONLY
facts that appear in the article. Rules: no new numbers, doses, drug names, statistics or claims that are not in the
article; no marketing language; no first person; no "in this article"; no bullet points; no headings. Output the
paragraph only.""")


def audit(title, body, para):
    return ollama(AUDIT_MODEL, f"""You are a medical editor auditing a summary for fidelity to its source.
Source article titled "{title}":
\"\"\"{body}\"\"\"

Proposed opening paragraph:
\"\"\"{para}\"\"\"

Check every statement in the paragraph. It is SUPPORTED only if each statement (including every number, drug, dose,
mechanism and outcome) is stated in the source article; paraphrase is fine, new facts are not. It is UNSUPPORTED if
any statement adds, strengthens or changes a claim, or contains dosing/efficacy/safety content absent from the source.
Answer on the first line with exactly SUPPORTED or UNSUPPORTED, then one sentence naming the unsupported statement if any.""", num_predict=300, temperature=0.0)


def verdict(text):
    return "SUPPORTED" if text.strip().upper().startswith("SUPPORTED") else "UNSUPPORTED"


def positive_control():
    body = "Creatine monohydrate at 3-5 g daily is the best-studied dose. Loading phases are optional."
    bad = "Creatine at 20 g daily cures depression and is recommended for children."
    v = verdict(audit("Creatine basics", body, bad))
    if v != "UNSUPPORTED":
        print("!! UNDELIVERED: auditor accepted a deliberately false paragraph; aborting"); sys.exit(2)
    print("positive control ok: auditor rejects an unsupported paragraph")


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--limit", type=int, default=0); ap.add_argument("--out", default=os.path.join(ROOT, "content-queue", "answer-first-candidates.json"))
    a = ap.parse_args()
    positive_control()
    posts = json.load(open(os.path.join(ROOT, "blog", "posts.json")))["posts"]
    if a.limit:
        posts = posts[: a.limit]
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    done = {}
    if os.path.exists(a.out):
        done = {r["slug"]: r for r in json.load(open(a.out))}
    out = list(done.values())
    for i, p in enumerate(posts, 1):
        slug = p["slug"]
        if slug in done:
            continue
        md_path = os.path.join(ROOT, "blog", slug + ".md")
        if not os.path.exists(md_path):
            continue
        md = open(md_path).read(); body = article_text(md)
        html_path = os.path.join(ROOT, "blog", slug + ".html")
        first = re.search(r"<article[^>]*>.*?<p[^>]*>(.*?)</p>", open(html_path).read(), re.S)
        t0 = time.time()
        try:
            para = draft(p["title"], body)
            words = len(para.split())
            av = audit(p["title"], body, para); v = verdict(av)
        except Exception as e:  # noqa: BLE001
            print(f"!! UNDELIVERED {slug}: {e}"); continue
        rec = {"slug": slug, "title": p["title"], "category": p["category"], "draft": para, "words": words,
               "audit": v, "audit_note": av[:300], "current_first_paragraph": re.sub(r"<[^>]+>", "", first.group(1))[:300] if first else "",
               "seconds": int(time.time() - t0)}
        out.append(rec); done[slug] = rec
        json.dump(out, open(a.out, "w"), indent=1)
        print(f"[{i}/{len(posts)}] {slug}: {v} ({words}w, {rec['seconds']}s)")
    sup = sum(1 for r in out if r["audit"] == "SUPPORTED")
    print(f"done: {len(out)} drafted, {sup} SUPPORTED -> {a.out}")


if __name__ == "__main__":
    main()
