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

WHAT IS NOT AUTOMATED, AND WHY
------------------------------
Route B's per-step figures (225,333 CKA · 127,232 CKS · 352,565 cumulative · 60,541 optional)
are NOT recomputed here. They are measured over a set of files the step table names in prose,
and reverse-engineering that set does not reproduce the published numbers: step 1 reads
"Orientation, Act I, Act IV", but summing those three directories gives 46,834 against a
published 46,795 — so the real scope excludes something by a rule stated nowhere. Guessing it
would replace a stale number with a confident wrong one, which is worse. Instead this script
checks the arithmetic those figures must satisfy internally, and warns when the course total
moves underneath them so a human knows to remeasure. Encoding the step→file map as data (and
generating that table) is the honest fix; see PLATFORM-DEPTH-PLAN.md, Phase 0.
"""
from __future__ import annotations
import os, re, sys, glob

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
COURSE_DIR = os.path.join(REPO, "networking-fundamentals")


def words(path: str) -> int:
    with open(path, encoding="utf-8", errors="replace") as fh:
        return len(fh.read().split())


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
     r"(?<=Measured, it is \*\*352,565 against )[\d,]+(?=\*\*)", "course"),
]

# The optional track is quoted as a percentage of the course in two places. Same numerator,
# and they disagreed. Both are recomputed from the measured total.
OPTIONAL_WORDS = 60_541
PCT_CLAIMS = [
    ("exam-prep/the-exam-path.md",
     r"(?<=Only 60,541 words — )[\d.]+(?=% — sit outside both curricula)"),
    ("exam-prep/the-exam-path.md",
     r"(?<=^60,541 words, )[\d.]+(?=% of the course)"),
]

# Route B's hand-measured figures, and the identity they must satisfy.
ROUTE_B = {"cka": 225_333, "cks_only": 127_232, "cumulative": 352_565}


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

    want_pct = round(OPTIONAL_WORDS / m["course"] * 100, 1)
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
                issues.append(("WARN", f"wordcount: {rel_path} calls the 30,801-word optional track "
                                       f"{got}% of the course; against {fmt(m['course'])} it is "
                                       f"{want_pct}% — run tools/remeasure.py --write"))

    if ROUTE_B["cka"] + ROUTE_B["cks_only"] != ROUTE_B["cumulative"]:
        issues.append(("WARN", "wordcount: Route B's CKA + CKS-only figures no longer sum to the "
                               "published cumulative total"))
    if ROUTE_B["cumulative"] + OPTIONAL_WORDS > m["course"]:
        issues.append(("WARN", f"wordcount: Route B claims {fmt(ROUTE_B['cumulative'])} on-path plus "
                               f"{fmt(OPTIONAL_WORDS)} optional = "
                               f"{fmt(ROUTE_B['cumulative'] + OPTIONAL_WORDS)} words, which exceeds "
                               f"the {fmt(m['course'])} the course contains"))
    else:
        unaccounted = m["course"] - ROUTE_B["cumulative"] - OPTIONAL_WORDS
        if unaccounted > 5_000:
            issues.append(("WARN", f"wordcount: {fmt(unaccounted)} words are on neither Route B's "
                                   f"path nor its optional track — the step figures were measured "
                                   f"against a smaller course and want remeasuring"))
    return issues


def write_claims(m: dict) -> list[str]:
    changed = []
    want_pct = f"{round(OPTIONAL_WORDS / m['course'] * 100, 1)}"
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
    pct = OPTIONAL_WORDS / m["course"] * 100
    print(f"  Route B through CKA (hand-measured) {fmt(ROUTE_B['cka']):>9}"
          f"   {ROUTE_B['cka'] / m['course'] * 100:.0f}% of the course")
    print(f"  Route B through CKS (hand-measured) {fmt(ROUTE_B['cumulative']):>9}"
          f"   {ROUTE_B['cumulative'] / m['course'] * 100:.0f}% of the course")
    print(f"  optional track      (hand-measured) {fmt(OPTIONAL_WORDS):>9}   {pct:.1f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
