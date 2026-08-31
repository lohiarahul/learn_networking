#!/usr/bin/env python3
"""
remeasure.py — the course's published word counts, measured rather than remembered.

Four files quote the size of this course to the reader, and until this script existed all four
were hand-maintained with nothing checking them. They drifted into three generations of the same
number living side by side:

    376,651   JOURNEY-MAP.md, exam-prep/README.md, AUDIT.md   (oldest)
    386,959   exam-prep/the-exam-path.md                      (remeasured, partially)
    387,850   what the files actually contained

Worse than any single stale figure: `the-exam-path.md` quoted the *same* 30,801-word optional
track as "8.0%" in its header and "8.2%" sixty lines later, because the header had been
remeasured against the new total and the body had not. A reader cannot tell which is wrong, and
in a course whose whole claim is that it measures rather than estimates, that is a defect about
more than arithmetic.

So: the derivable numbers are derived here, and the hand-measured ones are at least held to
their own arithmetic.

    python3 tools/remeasure.py            # report every measurement
    python3 tools/remeasure.py --check    # verify published claims; exit 1 on mismatch
    python3 tools/remeasure.py --write    # rewrite stale claims in place

`check_pedagogy.py` calls `claim_issues()` as a *warning* check, which runs course-wide only —
so a single-lesson save is never blocked by a total it cannot know it changed. `--check` is the
hard gate: run it before publishing, and after any commit that adds or removes prose.

WHAT USED NOT TO BE AUTOMATED, AND WHY IT NOW IS
-------------------------------------------------
Route B's per-step figures used to live here as hardcoded constants, with a docstring explaining
why: reverse-engineering the step table's prose ("Orientation, Act I, Act IV") into a file set
did not reproduce the published number — summing those three directories gave 46,834 against a
published 46,795, a 39-word gap with no stated rule behind it. Guessing the rule would have
replaced a stale number with a confident wrong one.

Retried once more before this rewrite, at both the commit that published 46,795 and the commit
that first quoted the 46,834 figure: both give **exactly 46,795** for the three directories,
`wc -w` and `len(read().split())` agreeing to the word. The gap does not reproduce, and nothing
found supports the "some rule excludes 39 words" explanation — the figures simply agreed the
whole time, and nobody re-summed them after the first measurement to notice they still did.

That retired the reason for hardcoding. `reference/routes.json` now names the step→file map as
data, `routes_lib.py` turns it into word and drill counts, and `tools/gen-route-tables.py`
regenerates every route page from the same arithmetic this module now reads (`path_words`,
`path_drills`, `optional_words`) rather than duplicating it. `tools/harness/invariants/routes.py`
checks it on every run; a route page more than a few words stale is a `routes.published-figures`
finding, not something waiting to be rediscovered four phases later.
"""
from __future__ import annotations
import os, re, sys, glob

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import routes_lib
from routes_lib import words

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COURSE_DIR = os.path.join(REPO, "networking-fundamentals")


def course_md() -> list[str]:
    """Every Markdown file under networking-fundamentals/.

    This directory holds only hand-written course source — the site's copy lives under
    site/src/content/docs/ and is a generated projection, excluded from every count here.
    """
    return sorted(glob.glob(os.path.join(COURSE_DIR, "**", "*.md"), recursive=True))


def measure() -> dict:
    files = course_md()
    total = sum(words(f) for f in files)

    acts = {}
    for d in sorted(glob.glob(os.path.join(COURSE_DIR, "*"))):
        if not os.path.isdir(d):
            continue
        act_files = glob.glob(os.path.join(d, "**", "*.md"), recursive=True)
        if act_files:
            acts[os.path.basename(d)] = sum(words(f) for f in act_files)

    return {"course": total, "files": len(files), "acts": acts}


# ── Published claims ─────────────────────────────────────────────────────────
# Each entry: (file, regex with exactly one capture group around the number, metric key).
# The regexes are written against the real prose and are deliberately narrow — a loose pattern
# that silently stops matching would leave the claim unchecked, which is the failure mode this
# whole script exists to remove. `--check` therefore fails on a regex that matches nothing, not
# just on a number that disagrees.
#
# AUDIT.md is deliberately absent. It is a dated historical record — "the course was 357,717
# words when this audit was written and is 376,651 now" is a true statement *about a past
# moment*, and rewriting it to today's figure would falsify the history rather than update a
# claim. Its numbers are stamped as-of instead, so they read as history and not as live claims.
CLAIMS = [
    ("JOURNEY-MAP.md",
     r"(?<=Narrative order, all )[\d,]+(?= words, nothing skipped)", "course"),
    ("exam-prep/README.md",
     r"(?<=The course is )[\d,]+(?=\s*\n>\s*words in narrative order)", "course"),
    ("exam-prep/the-exam-path.md",
     r"(?<=Measured, it is \*\*371,953 against )[\d,]+(?=\*\*)", "course"),
]

# The optional track's word total and percentage are derived from reference/routes.json —
# `routes_lib.optional_words()` — rather than hardcoded, which is what let the *same* number
# read "8.0%" in one place and "8.2%" in another the last time this was measured by hand.
PCT_CLAIMS = [
    ("exam-prep/the-exam-path.md",
     r"(?<=Only 61,273 words — )[\d.]+(?=% — sit outside both curricula)"),
    ("exam-prep/the-exam-path.md",
     r"(?<=^61,273 words, )[\d.]+(?=% of the course)"),
]


def _routes() -> dict:
    return routes_lib.load()["B"]


def fmt(n: int) -> str:
    return f"{n:,}"


def read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def claim_issues(measured: dict | None = None) -> list[tuple[str, str]]:
    """Return [(level, message)] for every published claim that disagrees with measurement.

    Shaped to plug straight into check_pedagogy.py's issue list.
    """
    m = measured or measure()
    issues: list[tuple[str, str]] = []

    for rel_path, pattern, key in CLAIMS:
        path = os.path.join(REPO, rel_path)
        if not os.path.exists(path):
            issues.append(("WARN", f"wordcount: {rel_path} not found — a published claim about "
                                   f"the course's size is no longer being checked"))
            continue
        found = re.findall(pattern, read(path), re.MULTILINE)
        if not found:
            issues.append(("WARN", f"wordcount: the claim pattern for {rel_path} matches nothing — "
                                   f"the prose was reworded and this figure is now unchecked"))
            continue
        for got in found:
            if int(got.replace(",", "")) != m[key]:
                issues.append(("WARN", f"wordcount: {rel_path} says {got} words; measured "
                                       f"{fmt(m[key])} — run tools/remeasure.py --write"))

    optional_words = routes_lib.optional_words(_routes())
    want_pct = round(optional_words / m["course"] * 100, 1)
    for rel_path, pattern in PCT_CLAIMS:
        path = os.path.join(REPO, rel_path)
        if not os.path.exists(path):
            continue
        found = re.findall(pattern, read(path), re.MULTILINE)
        if not found:
            issues.append(("WARN", f"wordcount: an optional-track percentage in {rel_path} is no "
                                   f"longer matched by its pattern"))
            continue
        for got in found:
            if abs(float(got) - want_pct) > 0.05:
                issues.append(("WARN", f"wordcount: {rel_path} calls the {fmt(optional_words)}-word "
                                       f"optional track {got}% of the course; against "
                                       f"{fmt(m['course'])} it is {want_pct}% — run "
                                       f"tools/remeasure.py --write"))

    # Route B's own arithmetic (steps summing to its summaries, the summaries matching what's
    # printed) is checked by `routes.published-figures` and `routes.step-globs-resolve` — see
    # tools/harness/invariants/routes.py — which read the same reference/routes.json this does,
    # so there is nothing left for this function to duplicate.
    return issues


def write_claims(m: dict) -> list[str]:
    changed = []
    want_pct = f"{round(routes_lib.optional_words(_routes()) / m['course'] * 100, 1)}"
    edits: list[tuple[str, str, str]] = [(p, pat, fmt(m[k])) for p, pat, k in CLAIMS]
    edits += [(p, pat, want_pct) for p, pat in PCT_CLAIMS]

    for rel_path, pattern, value in edits:
        path = os.path.join(REPO, rel_path)
        if not os.path.exists(path):
            continue
        before = read(path)
        after = re.sub(pattern, value, before, flags=re.MULTILINE)
        if after != before:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(after)
            changed.append(f"{rel_path} → {value}")
    return changed


def main(argv: list[str]) -> int:
    m = measure()

    if "--write" in argv:
        for line in write_claims(m) or ["(nothing stale)"]:
            print(f"  wrote {line}")
        remaining = claim_issues()
        for lvl, msg in remaining:
            print(f"  ⚠ {msg}")
        return 0

    if "--check" in argv:
        issues = claim_issues(m)
        for _lvl, msg in issues:
            print(f"  ✗ {msg}")
        if not issues:
            print(f"✓ every published word count matches measurement ({fmt(m['course'])} words)")
            return 0
        print(f"\n{len(issues)} stale or unverifiable claim(s)")
        return 1

    print(f"course total   {fmt(m['course']):>10}  words across {m['files']} Markdown files")
    print()
    for act, n in sorted(m["acts"].items(), key=lambda kv: -kv[1]):
        print(f"  {act:<34} {fmt(n):>9}")
    print()
    route_b = _routes()
    cka = routes_lib.cumulative_words(route_b, 7)
    cks = routes_lib.cumulative_words(route_b, 9)
    optional = routes_lib.optional_words(route_b)
    print(f"  Route B through CKA (from routes.json) {fmt(cka):>9}"
          f"   {cka / m['course'] * 100:.0f}% of the course")
    print(f"  Route B through CKS (from routes.json) {fmt(cks):>9}"
          f"   {cks / m['course'] * 100:.0f}% of the course")
    print(f"  optional track      (from routes.json) {fmt(optional):>9}"
          f"   {optional / m['course'] * 100:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
