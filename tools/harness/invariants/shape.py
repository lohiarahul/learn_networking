"""The shape of a lesson: it asks before it tells, and it closes its rung of the ladder.

Four invariants that between them encode the method — a wall the reader hits (`Predict
first`), a milestone they can self-assess against, a forward pointer to the next question,
and a cap on the milestone so it stays a check rather than becoming a recap.

Moved verbatim from `tools/check_pedagogy.py` — the bodies are unchanged, so the
parity test in `tools/harness/selftest.py` can prove the move changed no behaviour.
"""
from __future__ import annotations
import os, re
from ..corpus import has, is_lesson, read
from ..model import ACT_DIRS, DIAGNOSE_EXEMPT, FORWARD_MARKERS, MILESTONE_MARKERS, MILESTONE_MAX_WORDS, PREDICTION_EXEMPT, PREDICTION_MARKERS
from ..paths import COURSE, rel


def check_act_shape(_files):
    issues = []
    need = ["README.md", "test-yourself.md", "diagnose.md", "in-the-wild.md"]
    for a in ACT_DIRS:
        for fn in need:
            if fn == "diagnose.md" and a in DIAGNOSE_EXEMPT:
                continue
            if not os.path.exists(os.path.join(COURSE, a, fn)):
                issues.append(("FAIL", f"act-shape: {a} is missing {fn}"))
    return issues


def check_prediction(files):
    issues = []
    for f in files:
        r = os.path.relpath(f, COURSE)
        if not is_lesson(f):
            continue
        if r in PREDICTION_EXEMPT:
            continue
        if not has(read(f), PREDICTION_MARKERS):
            issues.append(("FAIL", f"no 'Predict first' in lesson: {rel(f)} "
                                   f"(add one, or add to PREDICTION_EXEMPT if it's setup)"))
    return issues


def check_ladder(files):
    issues = []
    for f in files:
        if not is_lesson(f):
            continue
        t = read(f)
        if not has(t, MILESTONE_MARKERS):
            issues.append(("FAIL", f"ladder: no milestone ('you can now'/'you understand this "
                                   f"when'/…) in {rel(f)}"))
        if not has(t, FORWARD_MARKERS):
            issues.append(("FAIL", f"ladder: no forward pointer ('Next:' link) in {rel(f)}"))
    return issues


def check_milestone_length(files):
    """A milestone block must stay a *check*, not become a recap of the lesson.

    `check_ladder` above asserts the block exists. Nothing asserted it was still short, and one
    had quietly become a table of contents: `act-10/04-deciding-before-it-exists.md` carried 18
    bullets and 475 words, in a course where every other milestone is prose. A reader cannot
    self-assess against 18 claims — they skim it, which is the same outcome as not having one.

    The threshold is measured, not chosen. Across the 90 milestone blocks in the course the
    median is 74 words and the maximum is 86: the distribution stops dead just short of a
    ninety-word ceiling nobody wrote down. 100 sits above every block that exists, with enough
    headroom that a legitimate edit does not trip it, and still catches a block five times the
    norm. If a lesson genuinely needs more, the surplus is a summary and wants its own heading.

    Applies to any Markdown under the course, not just numbered lessons: `the-whole-stack.md`
    carries a milestone too, and it is exactly the kind of long capstone page that would drift.
    """
    issues = []
    for f in files:
        if os.path.relpath(os.path.abspath(f), COURSE).startswith(os.pardir):
            continue
        lines = read(f).split("\n")
        i = 0
        while i < len(lines):
            if not (lines[i].startswith(">") and has(lines[i], MILESTONE_MARKERS)):
                i += 1
                continue
            block = []
            while i < len(lines) and lines[i].startswith(">"):
                block.append(re.sub(r"^>\s?", "", lines[i]))
                i += 1
            words = len(" ".join(block).split())
            if words > MILESTONE_MAX_WORDS:
                issues.append(("FAIL", f"milestone block is {words} words (max "
                                       f"{MILESTONE_MAX_WORDS}, course median 74) in {rel(f)} "
                                       f"— cut it to a check, or give the summary its own heading"))
    return issues
