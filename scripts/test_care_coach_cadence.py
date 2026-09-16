#!/usr/bin/env python3
"""Regression test — Care Coach cadence must have exactly one published value.

G-2: /weight-loss simultaneously advertised "weekly check-ins" and "bi-weekly
Care Coaching" while the authoritative product spec is MONTHLY with additional
sessions available on request. A contradiction here is a trust and conversion
defect and is also read by answer engines, so it must fail the build.

Run:  python3 scripts/test_care_coach_cadence.py
"""
import re, sys, pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
PAGES = ["weight-loss/index.html", "mens-weight-loss/index.html", "womens-weight-loss/index.html"]
AUTHORITATIVE = "monthly"
CADENCE = re.compile(
    r"(monthly|bi-?weekly|weekly|every other week)[^.<]{0,40}"
    r"(Care Coach|Care Coaching|check-?ins? with a Care Coach)", re.I)

def main() -> int:
    failures, seen = [], set()
    for rel in PAGES:
        p = ROOT / rel
        if not p.is_file():
            failures.append(f"{rel}: missing"); continue
        text = p.read_text(encoding="utf-8", errors="replace")
        for m in CADENCE.finditer(text):
            value = re.sub(r"[-\s]", "", m.group(1).lower())
            seen.add(value)
            if value != AUTHORITATIVE:
                line = text[:m.start()].count("\n") + 1
                failures.append(f"{rel}:{line} advertises '{m.group(1)}' Care Coaching "
                                f"(authoritative value is '{AUTHORITATIVE}')")
    if len(seen) > 1:
        failures.append(f"multiple cadence values published at once: {sorted(seen)}")
    if failures:
        print("CARE COACH CADENCE: FAIL")
        for f in failures: print(f"  - {f}")
        return 1
    print(f"CARE COACH CADENCE: PASS — one published value ('{AUTHORITATIVE}') across {len(PAGES)} pages")
    return 0

if __name__ == "__main__":
    sys.exit(main())
